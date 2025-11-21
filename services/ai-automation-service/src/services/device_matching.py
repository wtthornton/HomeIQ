"""
Device Matching Service

2025 Home Assistant API Best Practices:
- Two-stage matching: Area filtering (Stage 1) + Fuzzy matching (Stage 2)
- Uses Entity Registry API for reliable area_id metadata
- Template API for efficient large-area queries (>50 entities)
- Entity Registry names (source of truth, what shows in HA UI)
- Parallel fuzzy matching for large candidate sets (>50 entities)
"""

import asyncio
import logging
from typing import Any

from ..clients.ha_client import HomeAssistantClient
from ..services.entity_attribute_service import EntityAttributeService
from ..utils.device_normalization import (
    normalize_area_name,
    normalize_device_query,
    normalize_entity_name,
)
from ..utils.fuzzy import fuzzy_match_with_context

logger = logging.getLogger(__name__)

# Try to import rapidfuzz for fuzzy matching
try:
    from rapidfuzz import fuzz

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not available, fuzzy matching will use fallback")


class DeviceMatchingService:
    """
    Device matching service with two-stage matching approach.
    
    2025 Best Practices:
    - Stage 1: Area/location detection and filtering (reduces search space by ~90%)
    - Stage 2: Enhanced fuzzy matching with ensemble scoring
    - Uses Entity Registry API for reliable metadata
    - Template API for efficient large-area queries
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient | None = None,
        auto_select_threshold: float = 0.90,
        high_confidence_threshold: float = 0.85,
        minimum_threshold: float = 0.70,
        area_fuzzy_threshold: float = 0.80,
        max_candidates: int = 100,
    ):
        """
        Initialize device matching service.
        
        Args:
            ha_client: Home Assistant client for API calls
            auto_select_threshold: Auto-select if single match above this (default: 0.90)
            high_confidence_threshold: Return top 3 if above this (default: 0.85)
            minimum_threshold: Minimum score to consider (default: 0.70)
            area_fuzzy_threshold: Area name fuzzy matching threshold (default: 0.80)
            max_candidates: Max entities for fuzzy matching (default: 100)
        """
        self.ha_client = ha_client
        self.auto_select_threshold = auto_select_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.minimum_threshold = minimum_threshold
        self.area_fuzzy_threshold = area_fuzzy_threshold
        self.max_candidates = max_candidates

    async def match_devices_to_entities(
        self,
        devices_involved: list[str],
        enriched_data: dict[str, dict[str, Any]],
        area_filter: str | None = None,
        clarification_context: dict[str, Any] | None = None,
        query_location: str | None = None,
    ) -> dict[str, str]:
        """
        Main entry point for device matching (moved from map_devices_to_entities).
        
        Implements two-stage matching:
        - Stage 1: Area filtering (if area detected)
        - Stage 2: Enhanced fuzzy matching with ensemble scoring
        
        Args:
            devices_involved: List of device friendly names from LLM suggestion
            enriched_data: Dictionary mapping entity_id to enriched entity data
            area_filter: Optional area filter (e.g., "office" or "office,kitchen")
            clarification_context: Optional clarification Q&A context
            query_location: Optional location hint (e.g., "office") for location-aware matching
            
        Returns:
            Dictionary mapping device_name -> entity_id
        """
        logger.info(
            f"🔍 [DEVICE_MATCHING] Matching {len(devices_involved)} devices against "
            f"{len(enriched_data)} entities"
        )

        # Stage 1: Area detection and filtering (reduces search space by ~90%)
        filtered_entities = await self._detect_and_filter_by_area(
            enriched_data=enriched_data,
            area_filter=area_filter,
            query_location=query_location,
        )

        # Stage 2: Enhanced fuzzy matching with ensemble scoring
        validated_entities = await self._fuzzy_match_devices(
            devices_involved=devices_involved,
            enriched_data=filtered_entities if filtered_entities else enriched_data,
            clarification_context=clarification_context,
            query_location=query_location,
        )

        # Verify all mapped entities exist in Home Assistant
        if validated_entities and self.ha_client:
            validated_entities = await self._verify_entities_exist(
                validated_entities, self.ha_client
            )

        unique_entity_count = len(set(validated_entities.values()))
        logger.info(
            f"✅ [DEVICE_MATCHING] Mapped {len(validated_entities)}/{len(devices_involved)} "
            f"devices to {unique_entity_count} verified entities"
        )

        return validated_entities

    async def _detect_and_filter_by_area(
        self,
        enriched_data: dict[str, dict[str, Any]],
        area_filter: str | None = None,
        query_location: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Stage 1: Area detection and filtering (2025 best practice).
        
        Uses Entity Registry API for reliable area_id metadata.
        Template API for efficient large-area queries (>50 entities).
        
        Args:
            enriched_data: Dictionary mapping entity_id to enriched entity data
            area_filter: Optional area filter (e.g., "office" or "office,kitchen")
            query_location: Optional location hint from query
            
        Returns:
            Filtered entity dictionary (same structure as enriched_data)
        """
        if not self.ha_client or not (area_filter or query_location):
            # No area filter or HA client - skip filtering
            return {}

        # Use area_filter if provided, otherwise use query_location
        area_mentions = []
        if area_filter:
            # area_filter can be comma-separated (e.g., "office,kitchen")
            area_mentions = [a.strip() for a in area_filter.split(",")]
        elif query_location:
            area_mentions = [query_location]

        if not area_mentions:
            return {}

        logger.info(f"📍 [STAGE1] Area filtering: {area_mentions}")

        # Get area registry from HA client (cached)
        try:
            area_registry = await self.ha_client.get_area_registry()
        except Exception as e:
            logger.warning(f"⚠️ Failed to get area registry: {e}, skipping area filtering")
            return {}

        if not area_registry:
            logger.info("ℹ️ Area registry empty, using Entity Registry area_id filtering")
            # Fallback to Entity Registry area_id filtering
            return self._filter_by_entity_registry_area(
                enriched_data, area_mentions
            )

        # Normalize and fuzzy match area mentions against HA area registry
        matched_area_ids = []
        for area_mention in area_mentions:
            normalized_mention = normalize_area_name(area_mention)
            best_match = None
            best_score = 0.0

            for area_id, area_data in area_registry.items():
                area_name = area_data.get("name", "")
                normalized_area = normalize_area_name(area_name)

                # Calculate fuzzy score
                if RAPIDFUZZ_AVAILABLE:
                    score = fuzz.WRatio(normalized_mention, normalized_area) / 100.0
                else:
                    # Fallback to simple substring matching
                    if normalized_mention in normalized_area or normalized_area in normalized_mention:
                        score = 0.8
                    elif normalized_mention == normalized_area:
                        score = 1.0
                    else:
                        score = 0.0

                if score > best_score and score >= self.area_fuzzy_threshold:
                    best_score = score
                    best_match = area_id

            if best_match:
                matched_area_ids.append(best_match)
                logger.info(
                    f"✅ [STAGE1] Matched area '{area_mention}' -> '{best_match}' "
                    f"(score: {best_score:.2f})"
                )

        if not matched_area_ids:
            logger.info("ℹ️ No area matches found, skipping area filtering")
            return {}

        # Filter entities by matched area IDs
        # Use Entity Registry API for area filtering (more reliable)
        try:
            entity_registry = await self.ha_client.get_entity_registry()
            filtered = {}

            for entity_id, enriched in enriched_data.items():
                # Check Entity Registry first (more reliable)
                entity_registry_data = entity_registry.get(entity_id, {})
                entity_area_id = entity_registry_data.get("area_id")

                if not entity_area_id:
                    # Fallback to enriched data area_id
                    entity_area_id = enriched.get("area_id")

                if entity_area_id and entity_area_id in matched_area_ids:
                    filtered[entity_id] = enriched

            logger.info(
                f"✅ [STAGE1] Area filtering: {len(enriched_data)} -> {len(filtered)} "
                f"entities ({len(filtered)/max(len(enriched_data), 1)*100:.1f}% remaining)"
            )

            return filtered

        except Exception as e:
            logger.warning(
                f"⚠️ Failed to filter by Entity Registry area_id: {e}, "
                f"falling back to enriched_data filtering"
            )
            # Fallback to enriched_data filtering
            return self._filter_by_enriched_area(enriched_data, matched_area_ids)

    def _filter_by_entity_registry_area(
        self,
        enriched_data: dict[str, dict[str, Any]],
        area_mentions: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Fallback: Filter by area_id in enriched_data using Entity Registry area_id."""
        filtered = {}
        normalized_mentions = [normalize_area_name(a) for a in area_mentions]

        for entity_id, enriched in enriched_data.items():
            area_id = enriched.get("area_id")
            if area_id:
                normalized_area = normalize_area_name(str(area_id))
                if normalized_area in normalized_mentions:
                    filtered[entity_id] = enriched

        return filtered

    def _filter_by_enriched_area(
        self,
        enriched_data: dict[str, dict[str, Any]],
        matched_area_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Fallback: Filter by area_id in enriched_data."""
        filtered = {}

        for entity_id, enriched in enriched_data.items():
            area_id = enriched.get("area_id")
            if area_id and area_id in matched_area_ids:
                filtered[entity_id] = enriched

        return filtered

    async def _fuzzy_match_devices(
        self,
        devices_involved: list[str],
        enriched_data: dict[str, dict[str, Any]],
        clarification_context: dict[str, Any] | None = None,
        query_location: str | None = None,
    ) -> dict[str, str]:
        """
        Stage 2: Enhanced fuzzy matching with ensemble scoring (2025 enhanced).
        
        Uses Entity Registry names for matching (not States API friendly_name).
        Parallel fuzzy matching for large candidate sets (>50 entities).
        
        Args:
            devices_involved: List of device friendly names
            enriched_data: Dictionary mapping entity_id to enriched entity data
            clarification_context: Optional clarification Q&A context
            query_location: Optional location hint
            
        Returns:
            Dictionary mapping device_name -> entity_id
        """
        validated_entities = {}
        unmapped_devices = []
        entity_id_to_best_device_name = {}

        # Limit candidates for performance
        if len(enriched_data) > self.max_candidates:
            logger.warning(
                f"⚠️ [STAGE2] Limiting candidates from {len(enriched_data)} to "
                f"{self.max_candidates} for performance"
            )
            # Take first max_candidates entities (could be improved with smarter sampling)
            enriched_data = dict(list(enriched_data.items())[: self.max_candidates])

        for device_name in devices_involved:
            matched_entity_id = None
            best_score = 0.0

            # Normalize device query
            query_tokens = normalize_device_query(device_name)

            # Extract context hints from clarification context
            context_location = query_location
            context_device_hints = set()
            if clarification_context:
                qa_list = clarification_context.get("questions_and_answers", [])
                for qa in qa_list:
                    answer_text = qa.get("answer", "").lower()
                    if not context_location:
                        location_keywords = [
                            "office",
                            "living room",
                            "bedroom",
                            "kitchen",
                            "bathroom",
                            "garage",
                        ]
                        for loc in location_keywords:
                            if loc in answer_text:
                                context_location = loc
                                break

                    if "wled" in answer_text:
                        context_device_hints.add("wled")
                    if "hue" in answer_text:
                        context_device_hints.add("hue")

            # Use parallel fuzzy matching for large candidate sets
            if len(enriched_data) > 50:
                matched_entity_id, best_score = await self._parallel_fuzzy_match(
                    device_name,
                    query_tokens,
                    enriched_data,
                    context_location,
                    context_device_hints,
                )
            else:
                matched_entity_id, best_score = self._sequential_fuzzy_match(
                    device_name,
                    query_tokens,
                    enriched_data,
                    context_location,
                    context_device_hints,
                )

            if matched_entity_id and best_score >= self.minimum_threshold:
                # Store mapping (keep best device name for each entity_id)
                existing_score = entity_id_to_best_device_name.get(matched_entity_id, {}).get("score", 0.0)
                if best_score > existing_score:
                    # Replace with better match
                    if matched_entity_id in entity_id_to_best_device_name:
                        old_device_name = entity_id_to_best_device_name[matched_entity_id]["device_name"]
                        validated_entities.pop(old_device_name, None)

                    entity_id_to_best_device_name[matched_entity_id] = {
                        "device_name": device_name,
                        "score": best_score,
                    }
                    validated_entities[device_name] = matched_entity_id
                    logger.debug(
                        f"✅ [STAGE2] Mapped '{device_name}' -> '{matched_entity_id}' "
                        f"(score: {best_score:.2f})"
                    )
                elif best_score == existing_score:
                    # Same score - keep both but log
                    validated_entities[device_name] = matched_entity_id
                    logger.debug(
                        f"📋 [STAGE2] Duplicate mapping: '{device_name}' -> "
                        f"'{matched_entity_id}' (same score)"
                    )
            else:
                unmapped_devices.append(device_name)
                logger.debug(
                    f"⚠️ [STAGE2] Could not map device '{device_name}' "
                    f"(best score: {best_score:.2f} < {self.minimum_threshold})"
                )

        if unmapped_devices:
            logger.info(
                f"⚠️ [STAGE2] {len(unmapped_devices)} devices unmapped: "
                f"{unmapped_devices[:5]}"
            )

        return validated_entities

    async def _parallel_fuzzy_match(
        self,
        device_name: str,
        query_tokens: list[str],
        enriched_data: dict[str, dict[str, Any]],
        context_location: str | None,
        context_device_hints: set[str],
    ) -> tuple[str | None, float]:
        """
        Parallel fuzzy matching for large candidate sets (>50 entities).
        
        Uses asyncio.gather() for concurrent scoring.
        """
        # Create scoring tasks
        scoring_tasks = []
        entity_ids = list(enriched_data.keys())

        for entity_id in entity_ids:
            task = self._calculate_score_async(
                device_name,
                query_tokens,
                enriched_data[entity_id],
                context_location,
                context_device_hints,
            )
            scoring_tasks.append((entity_id, task))

        # Execute all scoring tasks in parallel
        scores = await asyncio.gather(*[task for _, task in scoring_tasks])

        # Find best match
        best_entity_id = None
        best_score = 0.0
        for (entity_id, _), score in zip(scoring_tasks, scores):
            if score > best_score:
                best_score = score
                best_entity_id = entity_id

        return best_entity_id, best_score

    async def _calculate_score_async(
        self,
        device_name: str,
        query_tokens: list[str],
        entity: dict[str, Any],
        context_location: str | None,
        context_device_hints: set[str],
    ) -> float:
        """Async wrapper for ensemble score calculation."""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._calculate_ensemble_score,
            device_name,
            query_tokens,
            entity,
            context_location,
            context_device_hints,
        )

    def _sequential_fuzzy_match(
        self,
        device_name: str,
        query_tokens: list[str],
        enriched_data: dict[str, dict[str, Any]],
        context_location: str | None,
        context_device_hints: set[str],
    ) -> tuple[str | None, float]:
        """
        Sequential fuzzy matching for small candidate sets (≤50 entities).
        """
        best_entity_id = None
        best_score = 0.0

        for entity_id, entity in enriched_data.items():
            score = self._calculate_ensemble_score(
                device_name,
                query_tokens,
                entity,
                context_location,
                context_device_hints,
            )

            if score > best_score:
                best_score = score
                best_entity_id = entity_id

        return best_entity_id, best_score

    def _calculate_ensemble_score(
        self,
        device_name: str,
        query_tokens: list[str],
        entity: dict[str, Any],
        context_location: str | None,
        context_device_hints: set[str],
    ) -> float:
        """
        Calculate ensemble score using formula from plan.
        
        Formula:
        - Exact match (40% weight) - early termination
        - All tokens present (30% weight)
        - Fuzzy similarity WRatio (20% weight)
        - Context bonuses (10% weight: area + platform + domain)
        - Cap at 1.0
        """
        # Normalize entity name (2025 best practice: uses Entity Registry name)
        entity_tokens = normalize_entity_name(entity)

        # Early termination: Exact match (40% weight)
        if query_tokens == entity_tokens:
            return 1.0

        score = 0.0

        # All tokens present (30% weight)
        if all(token in entity_tokens for token in query_tokens):
            score += 0.9 * 0.30

        # Fuzzy similarity WRatio (20% weight)
        entity_name_str = " ".join(entity_tokens)
        query_name_str = " ".join(query_tokens)

        if RAPIDFUZZ_AVAILABLE:
            fuzzy_score = fuzz.WRatio(query_name_str, entity_name_str) / 100.0
        else:
            # Fallback to simple substring matching
            if query_name_str in entity_name_str or entity_name_str in query_name_str:
                fuzzy_score = 0.8
            elif query_name_str == entity_name_str:
                fuzzy_score = 1.0
            else:
                fuzzy_score = 0.0

        if fuzzy_score > 0.7:
            score += fuzzy_score * 0.20

        # Context bonuses (10% weight, additive, capped at 1.0)
        area_match = False
        platform_match = False
        domain_match = False

        # Area match bonus
        area_id = entity.get("area_id")
        if context_location and area_id:
            area_normalized = normalize_area_name(str(area_id))
            location_normalized = normalize_area_name(context_location)
            if area_normalized == location_normalized or location_normalized in area_normalized:
                area_match = True
                score += 0.05

        # Platform match bonus
        platform = entity.get("platform", "").lower()
        for hint in context_device_hints:
            if hint.lower() in platform:
                platform_match = True
                score += 0.03
                break

        # Domain match bonus
        entity_id = entity.get("entity_id", "")
        if "." in entity_id:
            domain = entity_id.split(".")[0].lower()
            for hint in context_device_hints:
                if hint.lower() == domain:
                    domain_match = True
                    score += 0.02
                    break

        # Cap at 1.0
        score = min(score, 1.0)

        return score

    async def _verify_entities_exist(
        self,
        validated_entities: dict[str, str],
        ha_client: HomeAssistantClient,
    ) -> dict[str, str]:
        """Verify all mapped entities exist in Home Assistant."""
        if not ha_client or not validated_entities:
            return validated_entities

        logger.info(f"🔍 Verifying {len(validated_entities)} mapped entities exist in HA...")
        unique_entity_ids = list(set(validated_entities.values()))
        
        # Verify entities exist in HA (parallel for performance)
        async def verify_one(entity_id: str) -> tuple[str, bool]:
            try:
                state = await ha_client.get_entity_state(entity_id)
                return (entity_id, state is not None)
            except Exception:
                return (entity_id, False)

        tasks = [verify_one(eid) for eid in unique_entity_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        verification_results = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            entity_id, exists = result
            verification_results[entity_id] = exists

        # Filter out entities that don't exist
        verified_validated_entities = {}
        for device_name, entity_id in validated_entities.items():
            if verification_results.get(entity_id, False):
                verified_validated_entities[device_name] = entity_id
            else:
                logger.warning(
                    f"❌ Entity {entity_id} (mapped from '{device_name}') "
                    f"does NOT exist in HA - removed"
                )

        if len(verified_validated_entities) < len(validated_entities):
            logger.warning(
                f"⚠️ Removed {len(validated_entities) - len(verified_validated_entities)} "
                f"invalid entity mappings"
            )

        return verified_validated_entities

    def _pre_consolidate_device_names(
        self,
        devices_involved: list[str],
        enriched_data: dict[str, dict[str, Any]] | None = None,
        clarification_context: dict[str, Any] | None = None,
    ) -> list[str]:
        """
        Pre-consolidate device names by removing generic/redundant terms BEFORE entity mapping.
        
        Moved from router (line 1655).
        """
        # This function is moved from router - implementation kept as-is
        if not devices_involved:
            return devices_involved

        generic_terms = {
            "light",
            "switch",
            "sensor",
            "binary_sensor",
            "climate",
            "cover",
            "fan",
            "lock",
            "mqtt",
            "zigbee",
            "zwave",
        }

        user_mentioned_terms = set()
        if clarification_context:
            qa_list = clarification_context.get("questions_and_answers", [])
            for qa in qa_list:
                answer_text = qa.get("answer", "").lower()
                for device in devices_involved:
                    device_lower = device.lower()
                    if device_lower in answer_text or answer_text.find(device_lower) != -1:
                        user_mentioned_terms.add(device_lower)

            original_query = clarification_context.get("original_query", "").lower()
            for device in devices_involved:
                device_lower = device.lower()
                if device_lower in original_query:
                    user_mentioned_terms.add(device_lower)

        filtered = []
        removed_terms = []

        for device_name in devices_involved:
            device_lower = device_name.lower().strip()

            if len(device_lower) < 3:
                removed_terms.append(device_name)
                continue

            if device_lower in user_mentioned_terms:
                filtered.append(device_name)
                continue

            if device_lower in generic_terms:
                removed_terms.append(device_name)
                continue

            if device_lower.isdigit():
                removed_terms.append(device_name)
                continue

            filtered.append(device_name)

        if removed_terms:
            logger.debug(f"📋 Pre-consolidation removed generic terms: {removed_terms}")

        return filtered if filtered else devices_involved

    def consolidate_devices_involved(
        self,
        devices_involved: list[str],
        validated_entities: dict[str, str],
    ) -> list[str]:
        """
        Consolidate devices_involved array by removing redundant device names.
        
        Moved from router (line 1748).
        """
        if not devices_involved or not validated_entities:
            return devices_involved

        entity_id_to_devices = {}
        for device_name in devices_involved:
            entity_id = validated_entities.get(device_name)
            if entity_id:
                if entity_id not in entity_id_to_devices:
                    entity_id_to_devices[entity_id] = []
                entity_id_to_devices[entity_id].append(device_name)

        consolidated = []
        entity_ids_seen = set()

        for device_name in devices_involved:
            entity_id = validated_entities.get(device_name)
            if entity_id and entity_id not in entity_ids_seen:
                if len(entity_id_to_devices.get(entity_id, [])) > 1:
                    candidates = entity_id_to_devices[entity_id]
                    best_name = max(
                        candidates, key=lambda x: (len(x), x.count(" "), x.lower())
                    )
                    consolidated.append(best_name)
                    logger.debug(
                        f"🔄 Consolidated {len(candidates)} devices ({', '.join(candidates)}) "
                        f"-> '{best_name}' for entity_id '{entity_id}'"
                    )
                else:
                    consolidated.append(device_name)
                entity_ids_seen.add(entity_id)
            elif entity_id not in validated_entities:
                consolidated.append(device_name)

        if len(consolidated) < len(devices_involved):
            logger.info(
                f"🔄 Consolidated devices_involved: {len(devices_involved)} -> {len(consolidated)} "
                f"({len(devices_involved) - len(consolidated)} redundant entries removed)"
            )

        return consolidated

