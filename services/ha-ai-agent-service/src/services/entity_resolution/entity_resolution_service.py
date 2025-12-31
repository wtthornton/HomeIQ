"""
Entity Resolution Service.

Extracts business rules from system prompt to testable code for resolving
entities from user prompts based on area, keywords, and device types.
"""

import logging
from typing import Any, Optional

from ...clients.data_api_client import DataAPIClient
from .entity_resolution_result import EntityResolutionResult

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """
    Service for resolving entities from user prompts.

    Implements business rules:
    1. Area filtering first (filter by area_id)
    2. Positional keyword matching (top, left, right, back, front, desk, ceiling, floor)
    3. Device type matching (LED, WLED, strip, bulb)
    4. Validation (verify matches user description)
    """

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

    def __init__(self, data_api_client: Optional[DataAPIClient] = None):
        """
        Initialize entity resolution service.

        Args:
            data_api_client: Data API client for entity queries (optional)
        """
        self.data_api_client = data_api_client

    async def resolve_entities(
        self,
        user_prompt: str,
        context_entities: Optional[list[dict[str, Any]]] = None,
        target_domain: Optional[str] = None,
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
            # Step 1: Extract area from prompt
            area_id = self._extract_area_from_prompt(user_prompt)

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

            # Step 5: Extract keywords from prompt
            positional_keywords = self._extract_positional_keywords(user_prompt)
            device_type_keywords = self._extract_device_type_keywords(user_prompt)

            # Step 6: Score and match entities
            scored_entities = self._score_entities(
                entities,
                user_prompt,
                positional_keywords,
                device_type_keywords,
            )

            # Step 7: Select best matches
            matched_entities = self._select_matches(scored_entities, user_prompt)

            # Step 8: Validate matches
            validation_result = self._validate_matches(
                matched_entities, user_prompt, area_id
            )

            return EntityResolutionResult(
                success=validation_result["valid"],
                matched_entities=[e["entity_id"] for e in matched_entities],
                matched_areas=[area_id] if area_id else [],
                confidence_score=validation_result["confidence"],
                warnings=validation_result["warnings"],
                error=validation_result.get("error"),
            )

        except Exception as e:
            logger.error(f"Error resolving entities: {e}", exc_info=True)
            return EntityResolutionResult(
                success=False,
                error=f"Entity resolution failed: {str(e)}",
            )

    def _extract_area_from_prompt(self, user_prompt: str) -> Optional[str]:
        """
        Extract area ID from user prompt.

        Args:
            user_prompt: User's natural language request

        Returns:
            Area ID if found, None otherwise
        """
        # Common area names (could be expanded with actual area names from context)
        area_keywords = {
            "office",
            "kitchen",
            "bedroom",
            "living room",
            "bathroom",
            "garage",
            "basement",
            "attic",
        }

        prompt_lower = user_prompt.lower()
        for area in area_keywords:
            if area in prompt_lower:
                # Return area as-is (could normalize to area_id format)
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
            entity_area = entity.get("area_id", "").lower().replace(" ", "_")
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

    def _score_entities(
        self,
        entities: list[dict[str, Any]],
        user_prompt: str,
        positional_keywords: set[str],
        device_type_keywords: set[str],
    ) -> list[dict[str, Any]]:
        """
        Score entities based on keyword matches.

        Args:
            entities: List of entity dictionaries
            user_prompt: User's natural language request
            positional_keywords: Set of positional keywords found
            device_type_keywords: Set of device type keywords found

        Returns:
            List of entities with scores
        """
        scored = []
        prompt_lower = user_prompt.lower()

        for entity in entities:
            score = 0.0
            entity_id = entity.get("entity_id", "").lower()
            friendly_name = entity.get("friendly_name", "").lower()
            aliases = [a.lower() for a in entity.get("aliases", [])]

            # Search text combines entity_id, friendly_name, and aliases
            search_text = f"{entity_id} {friendly_name} {' '.join(aliases)}"

            # Score positional keyword matches
            for keyword in positional_keywords:
                if keyword in search_text:
                    score += 1.0

            # Score device type keyword matches
            for device_type in device_type_keywords:
                for keyword in self.DEVICE_TYPE_KEYWORDS.get(device_type, []):
                    if keyword in search_text:
                        score += 1.0
                        break

            # Bonus for exact matches in friendly_name
            if friendly_name and any(
                word in friendly_name for word in prompt_lower.split()
            ):
                score += 0.5

            scored.append(
                {
                    **entity,
                    "score": score,
                }
            )

        return scored

    def _select_matches(
        self, scored_entities: list[dict[str, Any]], user_prompt: str
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
        elif len(matched) <= 3:
            # 2-3 matches → list all
            return matched
        else:
            # 4+ matches → use most specific (highest score)
            # Return top matches with same score as highest
            top_score = matched[0]["score"]
            return [e for e in matched if e["score"] == top_score]

    def _validate_matches(
        self,
        matched_entities: list[dict[str, Any]],
        user_prompt: str,
        area_id: Optional[str],
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
