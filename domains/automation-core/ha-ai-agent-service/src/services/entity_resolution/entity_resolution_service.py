"""
Entity Resolution Service.

Extracts business rules from system prompt to testable code for resolving
entities from user prompts based on area, keywords, and device types.
Story 62.5: Dynamic area resolution from data-api /api/areas.
Story 62.8: Enhanced alias scoring.
"""

import logging
import time
from typing import Any

from ...clients.data_api_client import DataAPIClient
from .entity_resolution_result import EntityResolutionResult

logger = logging.getLogger(__name__)

# Story 62.5: Fallback areas used only when data-api is unreachable
_FALLBACK_AREAS = [
    "office", "kitchen", "bedroom", "living room", "bathroom",
    "garage", "basement", "attic", "hallway", "dining room",
]


class EntityResolutionService:
    """
    Service for resolving entities from user prompts.

    Implements business rules:
    1. Area filtering first (filter by area_id)
    2. Positional keyword matching (top, left, right, back, front, desk, ceiling, floor)
    3. Device type matching (LED, WLED, strip, bulb)
    4. Validation (verify matches user description)
    """

    # Story 62.5: Area cache TTL in seconds
    _AREA_CACHE_TTL = 300  # 5 minutes

    # Positional keywords for matching
    POSITIONAL_KEYWORDS = {
        "top",
        "left",
        "right",
        "back",
        "front",
        "desk",
        "ceiling",
        "floor",
        "bottom",
    }

    # Device type keywords
    DEVICE_TYPE_KEYWORDS = {
        "led": ["led", "wled"],
        "strip": ["strip", "stripes"],
        "bulb": ["bulb", "light", "lamp"],
    }

    # Pattern keywords for combined device descriptions
    # (e.g., "switch LED" = LED indicator on switch)
    # These patterns are checked BEFORE device type keywords to prevent false matches
    PATTERN_KEYWORDS = {
        "switch_led": [
            "switch led",
            "switch's led",
            "switch indicator",
            "led on switch",
            "switch led indicator",
        ],
        "switch_button": ["switch button", "button on switch"],
    }

    def __init__(self, data_api_client: DataAPIClient | None = None):
        """
        Initialize entity resolution service.

        Args:
            data_api_client: Data API client for entity queries (optional)
        """
        self.data_api_client = data_api_client
        # Story 62.5: Cached area list (populated lazily)
        self._area_cache: list[str] = []
        self._area_cache_time: float = 0.0

    async def resolve_entities(
        self,
        user_prompt: str,
        context_entities: list[dict[str, Any]] | None = None,
        target_domain: str | None = None,
    ) -> EntityResolutionResult:
        """
        Resolve entities from user prompt using business rules.

        Args:
            user_prompt: User's natural language request
            context_entities: Optional list of entities from context (preferred)
            target_domain: Optional domain filter (e.g., "light", "switch")

        Returns:
            EntityResolutionResult with matched entities and confidence scores
        """
        try:
            # Step 1: Extract area from prompt (Story 62.5: async dynamic lookup)
            area_id = await self._extract_area_from_prompt(user_prompt)

            # Step 2: Get entities (from context or API)
            if context_entities:
                entities = context_entities
            elif self.data_api_client:
                # Fetch entities from API if context not available
                entities = await self.data_api_client.fetch_entities()
            else:
                return EntityResolutionResult(
                    success=False,
                    error="No entity data available (context or data_api_client required)",
                )

            # Step 3: Filter by area first (if area mentioned)
            if area_id:
                entities = self._filter_by_area(entities, area_id)
                if not entities:
                    return EntityResolutionResult(
                        success=False,
                        error=f"No entities found in area '{area_id}'",
                        matched_areas=[area_id],
                    )

            # Step 4: Filter by domain if specified
            if target_domain:
                entities = self._filter_by_domain(entities, target_domain)

            # Step 4.5: Story 62.6 — Exclude ai:ignore entities
            entities = [
                e for e in entities
                if "ai:ignore" not in (e.get("labels") or [])
            ]

            # Step 5: Extract keywords from prompt
            # Check patterns FIRST (before device type keywords) to prevent false matches
            pattern_keywords = self._extract_pattern_keywords(user_prompt)
            positional_keywords = self._extract_positional_keywords(user_prompt)
            # Only extract device type keywords if no pattern matched
            # (prevents "switch LED" matching LED devices)
            device_type_keywords = (
                set()
                if pattern_keywords
                else self._extract_device_type_keywords(user_prompt)
            )

            # Step 6: Score and match entities
            scored_entities = self._score_entities(
                entities,
                user_prompt,
                positional_keywords,
                device_type_keywords,
                pattern_keywords,
            )

            # Step 7: Select best matches
            matched_entities = self._select_matches(scored_entities, user_prompt)

            # Step 8: Validate matches
            validation_result = self._validate_matches(
                matched_entities, user_prompt, area_id
            )

            # Story 62.6: Check if any matched entity requires confirmation
            needs_confirm = any(
                e.get("requires_confirmation", False) for e in matched_entities
            )

            return EntityResolutionResult(
                success=validation_result["valid"],
                matched_entities=[e["entity_id"] for e in matched_entities],
                matched_areas=[area_id] if area_id else [],
                confidence_score=validation_result["confidence"],
                warnings=validation_result["warnings"],
                error=validation_result.get("error"),
                requires_confirmation=needs_confirm,
            )

        except Exception as e:
            logger.error(f"Error resolving entities: {e}", exc_info=True)
            return EntityResolutionResult(
                success=False,
                error=f"Entity resolution failed: {str(e)}",
            )

    async def _refresh_area_cache(self) -> None:
        """Story 62.5: Refresh area cache from data-api if expired."""
        now = time.monotonic()
        if self._area_cache and (now - self._area_cache_time) < self._AREA_CACHE_TTL:
            return  # Cache still valid

        if not self.data_api_client:
            self._area_cache = list(_FALLBACK_AREAS)
            self._area_cache_time = now
            return

        try:
            areas = await self.data_api_client.get_areas()
            # Build display_name → area_id list, sorted longest-first
            # to match "living room" before "living"
            area_names = []
            for a in areas:
                area_id = a.get("area_id", "")
                display = a.get("display_name", area_id.replace("_", " ").title())
                area_names.append(display.lower())
            # Sort by length descending so longer names match first
            area_names.sort(key=len, reverse=True)
            self._area_cache = area_names
            self._area_cache_time = now
            logger.info("Refreshed area cache: %d areas", len(area_names))
        except Exception:
            logger.warning("Failed to refresh area cache, using fallback")
            if not self._area_cache:
                self._area_cache = list(_FALLBACK_AREAS)
            self._area_cache_time = now  # Don't retry immediately

    async def _extract_area_from_prompt(self, user_prompt: str) -> str | None:
        """
        Extract area ID from user prompt using dynamic area list.

        Story 62.5: Fetches areas from data-api (cached 5 min), falls back
        to hardcoded list if unavailable. Sorted longest-first to prevent
        "bed" matching before "bedroom".
        """
        await self._refresh_area_cache()

        prompt_lower = user_prompt.lower()
        for area in self._area_cache:
            if area in prompt_lower:
                return area.replace(" ", "_")

        return None

    def _filter_by_area(
        self, entities: list[dict[str, Any]], area_id: str
    ) -> list[dict[str, Any]]:
        """
        Filter entities by area ID.

        Args:
            entities: List of entity dictionaries
            area_id: Area ID to filter by

        Returns:
            Filtered list of entities
        """
        # Normalize area_id for comparison
        area_id_normalized = area_id.lower().replace(" ", "_")
        filtered = []

        for entity in entities:
            entity_area = (entity.get("area_id") or "").lower().replace(" ", "_")
            if entity_area == area_id_normalized:
                filtered.append(entity)

        return filtered

    def _filter_by_domain(
        self, entities: list[dict[str, Any]], domain: str
    ) -> list[dict[str, Any]]:
        """
        Filter entities by domain.

        Args:
            entities: List of entity dictionaries
            domain: Domain to filter by (e.g., "light", "switch")

        Returns:
            Filtered list of entities
        """
        return [
            e
            for e in entities
            if e.get("domain", "").lower() == domain.lower()
            or e.get("entity_id", "").startswith(f"{domain}.")
        ]

    def _extract_positional_keywords(self, user_prompt: str) -> set[str]:
        """
        Extract positional keywords from user prompt.

        Args:
            user_prompt: User's natural language request

        Returns:
            Set of positional keywords found
        """
        prompt_lower = user_prompt.lower()
        found_keywords = set()

        for keyword in self.POSITIONAL_KEYWORDS:
            if keyword in prompt_lower:
                found_keywords.add(keyword)

        return found_keywords

    def _extract_device_type_keywords(self, user_prompt: str) -> set[str]:
        """
        Extract device type keywords from user prompt.

        Args:
            user_prompt: User's natural language request

        Returns:
            Set of device type keywords found
        """
        prompt_lower = user_prompt.lower()
        found_keywords = set()

        for device_type, keywords in self.DEVICE_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    found_keywords.add(device_type)
                    break

        return found_keywords

    def _extract_pattern_keywords(self, user_prompt: str) -> set[str]:
        """
        Extract pattern keywords from user prompt.

        Example: "switch LED" = LED indicator on switch.

        Pattern keywords are checked BEFORE device type keywords to prevent false matches.
        For example, "office switch led" should match switch LED attributes, not LED devices.

        Args:
            user_prompt: User's natural language request

        Returns:
            Set of pattern keywords found
        """
        prompt_lower = user_prompt.lower()
        found_patterns = set()

        for pattern_name, patterns in self.PATTERN_KEYWORDS.items():
            for pattern in patterns:
                if pattern in prompt_lower:
                    found_patterns.add(pattern_name)
                    break

        return found_patterns

    def _score_entities(
        self,
        entities: list[dict[str, Any]],
        user_prompt: str,
        positional_keywords: set[str],
        device_type_keywords: set[str],
        pattern_keywords: set[str],
    ) -> list[dict[str, Any]]:
        """
        Score entities based on keyword matches.

        Args:
            entities: List of entity dictionaries
            user_prompt: User's natural language request
            positional_keywords: Set of positional keywords found
            device_type_keywords: Set of device type keywords found
            pattern_keywords: Set of pattern keywords found (e.g., "switch_led")

        Returns:
            List of entities with scores
        """
        scored = []
        prompt_lower = user_prompt.lower()

        for entity in entities:
            score = 0.0
            entity_id = entity.get("entity_id", "").lower()
            friendly_name = entity.get("friendly_name", "").lower()
            aliases = [a.lower() for a in entity.get("aliases") or []]

            # Search text combines entity_id, friendly_name, and aliases
            search_text = f"{entity_id} {friendly_name} {' '.join(aliases)}"

            # Story 62.8: Alias-first scoring (whole-phrase matching)
            for alias in aliases:
                if alias == prompt_lower or alias in prompt_lower:
                    # Exact or contained match — high boost
                    score += 3.0
                    break
                if any(word in alias.split() for word in prompt_lower.split()):
                    # Partial word overlap with alias
                    score += 1.5
                    break

            # Score pattern keyword matches FIRST (highest priority)
            # Pattern: "switch_led" → boost entities with both "switch" and "led" in name
            if "switch_led" in pattern_keywords:
                # Boost entities with both "switch" and "led" in name (LED indicator on switch)
                if "switch" in search_text and "led" in search_text:
                    score += 3.0  # High boost for pattern match
                    # Extra boost for LED effect sensors (sensor.*_led_effect)
                    if "sensor" in entity_id and "_led_effect" in entity_id:
                        score += 2.0  # Perfect match for LED effect sensor
                elif "led_effect" in search_text or "led effect" in friendly_name:
                    score += 2.0  # Good match for LED effect entities

            # Score positional keyword matches
            for keyword in positional_keywords:
                if keyword in search_text:
                    score += 1.0

            # Score device type keyword matches (only if no pattern matched)
            for device_type in device_type_keywords:
                for keyword in self.DEVICE_TYPE_KEYWORDS.get(device_type, []):
                    if keyword in search_text:
                        score += 1.0
                        break

            # Bonus for whole-word matches in friendly_name (avoid substring false positives)
            if friendly_name and any(
                word in friendly_name.split() for word in prompt_lower.split()
            ):
                score += 0.5

            # Story 62.6: Label-aware scoring boosts
            entity_labels = set(entity.get("labels") or [])
            requires_confirmation = False
            if "ai:automatable" in entity_labels:
                score += 0.5  # Boost automatable entities
            if "ai:critical" in entity_labels:
                requires_confirmation = True
            if "sensor:primary" in entity_labels:
                score += 0.3  # Prefer primary sensors over duplicates

            scored.append(
                {
                    **entity,
                    "score": score,
                    "requires_confirmation": requires_confirmation,
                }
            )

        return scored

    def _select_matches(
        self, scored_entities: list[dict[str, Any]], _user_prompt: str
    ) -> list[dict[str, Any]]:
        """
        Select best matching entities based on scores.

        Business rule:
        - 2-3 matches → list all
        - 4+ → use most specific (highest score)
        - 0-1 → return all (let validation handle)

        Args:
            scored_entities: List of entities with scores
            user_prompt: User's natural language request

        Returns:
            List of selected entities
        """
        # Sort by score descending
        sorted_entities = sorted(
            scored_entities, key=lambda e: e.get("score", 0.0), reverse=True
        )

        # Filter entities with score > 0
        matched = [e for e in sorted_entities if e.get("score", 0.0) > 0]

        if len(matched) == 0:
            # No matches - return all entities (validation will handle)
            return sorted_entities[:5]  # Limit to top 5
        if len(matched) <= 3:
            # 2-3 matches → list all
            return matched
        # 4+ matches → use most specific (highest score)
        # Return top matches with same score as highest
        top_score = matched[0]["score"]
        return [e for e in matched if e["score"] == top_score]

    def _validate_matches(
        self,
        matched_entities: list[dict[str, Any]],
        _user_prompt: str,
        _area_id: str | None,
    ) -> dict[str, Any]:
        """
        Validate that matched entities match user's description.

        Args:
            matched_entities: List of matched entities
            user_prompt: User's natural language request
            area_id: Area ID if specified

        Returns:
            Dictionary with validation result
        """
        if not matched_entities:
            return {
                "valid": False,
                "confidence": 0.0,
                "error": "No entities matched",
                "warnings": [],
            }

        # Check if matches have scores > 0
        has_scored_matches = any(e.get("score", 0.0) > 0 for e in matched_entities)

        if not has_scored_matches:
            return {
                "valid": False,
                "confidence": 0.0,
                "error": "No entities matched user description",
                "warnings": ["Consider checking entity names or area"],
            }

        # Calculate confidence based on scores
        scores = [e.get("score", 0.0) for e in matched_entities]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        confidence = min(avg_score / 3.0, 1.0)  # Normalize to 0-1

        warnings = []
        if confidence < 0.5:
            warnings.append("Low confidence match - verify entities are correct")
        if len(matched_entities) > 3:
            warnings.append(
                f"Multiple matches ({len(matched_entities)}) - using most specific"
            )

        return {
            "valid": True,
            "confidence": confidence,
            "warnings": warnings,
        }
