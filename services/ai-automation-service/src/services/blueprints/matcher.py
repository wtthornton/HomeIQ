"""
Blueprint Matcher Service

Matches user suggestions to available blueprints based on device types and use case.
"""

import logging
import re
from typing import Any

from ...utils.miner_integration import MinerIntegration

logger = logging.getLogger(__name__)


class BlueprintMatcher:
    """
    Match user suggestions to available blueprints.
    
    Calculates fit scores based on:
    - Device type compatibility (60% weight)
    - Use case alignment (30% weight)
    - Integration compatibility (10% weight)
    """

    def __init__(self, miner: MinerIntegration):
        """
        Initialize blueprint matcher.

        Args:
            miner: MinerIntegration instance for fetching blueprints
        """
        self.miner = miner

    async def find_best_match(
        self,
        suggestion: dict[str, Any],
        validated_entities: dict[str, str],
        devices_involved: list[str] | None = None
    ) -> dict[str, Any] | None:
        """
        Find the best matching blueprint for a suggestion.

        Args:
            suggestion: Suggestion dictionary with description, devices_involved, etc.
            validated_entities: Dictionary mapping device names to entity_ids
            devices_involved: List of device types (e.g., ['light', 'binary_sensor'])

        Returns:
            Dictionary with blueprint, fit_score, and metadata, or None if no match
        """
        if not devices_involved:
            devices_involved = suggestion.get("devices_involved", [])

        if not devices_involved:
            logger.debug("No devices_involved in suggestion, cannot match blueprints")
            return None

        # Extract use case from suggestion description
        use_case = self._extract_use_case(suggestion.get("description", ""))

        # Search for blueprints matching device types
        blueprints = await self._search_blueprints(devices_involved, use_case)

        if not blueprints:
            logger.debug("No blueprints found for devices: %s", devices_involved)
            return None

        # Calculate fit scores for each blueprint
        best_match = None
        best_score = 0.0

        for blueprint in blueprints:
            fit_score = self._calculate_fit_score(
                blueprint=blueprint,
                suggestion=suggestion,
                devices_involved=devices_involved,
                validated_entities=validated_entities,
                use_case=use_case
            )

            if fit_score > best_score:
                best_score = fit_score
                best_match = {
                    "blueprint": blueprint,
                    "fit_score": fit_score,
                    "blueprint_yaml": blueprint.get("yaml", ""),
                    "metadata": blueprint.get("metadata", {})
                }

        if best_match and best_score > 0:
            logger.info(
                "Found blueprint match: %s (fit_score: %.2f)",
                best_match["metadata"].get("_blueprint_metadata", {}).get("name", "Unknown"),
                best_score
            )
            return best_match

        return None

    async def _search_blueprints(
        self,
        devices_involved: list[str],
        use_case: str | None = None
    ) -> list[dict[str, Any]]:
        """Search for blueprints matching device types."""
        all_blueprints = []

        # Search for each device type
        for device in devices_involved:
            # Normalize device type (e.g., "light" from "light.office")
            device_type = device.split(".")[0] if "." in device else device

            blueprints = await self.miner.search_blueprints(
                device=device_type,
                use_case=use_case,
                min_quality=0.7,
                limit=20
            )
            all_blueprints.extend(blueprints)

        # Deduplicate by ID
        seen_ids = set()
        unique_blueprints = []

        for blueprint in all_blueprints:
            blueprint_id = blueprint.get("id")
            if blueprint_id and blueprint_id not in seen_ids:
                seen_ids.add(blueprint_id)
                unique_blueprints.append(blueprint)

        return unique_blueprints

    def _calculate_fit_score(
        self,
        blueprint: dict[str, Any],
        suggestion: dict[str, Any],
        devices_involved: list[str],
        validated_entities: dict[str, str],
        use_case: str | None = None
    ) -> float:
        """
        Calculate fit score for a blueprint (0.0-1.0).

        Scoring:
        - Device match: 60% weight
        - Use case match: 30% weight
        - Integration compatibility: 10% weight
        """
        metadata = blueprint.get("metadata", {})
        blueprint_vars = metadata.get("_blueprint_variables", {})
        blueprint_devices = metadata.get("_blueprint_devices", [])

        # 1. Device match score (60% weight)
        device_match = self._calculate_device_match(
            blueprint_devices=blueprint_devices,
            devices_involved=devices_involved,
            blueprint_vars=blueprint_vars,
            validated_entities=validated_entities
        )

        # 2. Use case match score (30% weight)
        use_case_match = self._calculate_use_case_match(
            blueprint=blueprint,
            suggestion=suggestion,
            use_case=use_case
        )

        # 3. Integration compatibility (10% weight)
        integration_match = 1.0  # Assume compatible (can be enhanced later)

        # Weighted fit score
        fit_score = (
            device_match * 0.6 +
            use_case_match * 0.3 +
            integration_match * 0.1
        )

        return fit_score

    def _calculate_device_match(
        self,
        blueprint_devices: list[str],
        devices_involved: list[str],
        blueprint_vars: dict[str, Any],
        validated_entities: dict[str, str]
    ) -> float:
        """Calculate device compatibility score (0.0-1.0)."""
        if not blueprint_devices or not devices_involved:
            return 0.0

        # Normalize device types (extract domain from entity_ids)
        involved_domains = set()
        for device in devices_involved:
            if "." in device:
                domain = device.split(".")[0]
            else:
                domain = device
            involved_domains.add(domain)

        blueprint_domains = set(blueprint_devices)

        # Calculate overlap
        overlap = involved_domains.intersection(blueprint_domains)
        total_required = len(blueprint_domains)

        if total_required == 0:
            return 0.0

        # Check if we have entities for required blueprint inputs
        entity_match_score = 0.0
        if blueprint_vars:
            matched_inputs = 0
            total_inputs = len(blueprint_vars)

            for input_name, input_spec in blueprint_vars.items():
                required_domain = input_spec.get("domain", "")
                device_class = input_spec.get("device_class", "")

                # Check if we have a matching entity
                for entity_name, entity_id in validated_entities.items():
                    entity_domain = entity_id.split(".")[0] if "." in entity_id else ""
                    if entity_domain == required_domain:
                        matched_inputs += 1
                        break

            if total_inputs > 0:
                entity_match_score = matched_inputs / total_inputs

        # Combine domain overlap and entity matching
        domain_overlap_score = len(overlap) / max(len(involved_domains), total_required)
        combined_score = (domain_overlap_score * 0.5 + entity_match_score * 0.5)

        return min(combined_score, 1.0)

    def _calculate_use_case_match(
        self,
        blueprint: dict[str, Any],
        suggestion: dict[str, Any],
        use_case: str | None = None
    ) -> float:
        """Calculate use case alignment score (0.0-1.0)."""
        metadata = blueprint.get("metadata", {})
        blueprint_metadata = metadata.get("_blueprint_metadata", {})
        blueprint_description = blueprint_metadata.get("description", "").lower()
        blueprint_use_case = blueprint.get("use_case", "").lower()

        suggestion_description = suggestion.get("description", "").lower()

        # Check if use_case matches
        if use_case and blueprint_use_case:
            if use_case.lower() == blueprint_use_case.lower():
                return 1.0

        # Check keyword overlap in descriptions
        suggestion_words = set(re.findall(r'\b\w+\b', suggestion_description))
        blueprint_words = set(re.findall(r'\b\w+\b', blueprint_description))

        if not suggestion_words or not blueprint_words:
            return 0.5  # Neutral if no keywords

        overlap = suggestion_words.intersection(blueprint_words)
        total_unique = len(suggestion_words.union(blueprint_words))

        if total_unique == 0:
            return 0.5

        keyword_score = len(overlap) / total_unique
        return min(keyword_score * 2, 1.0)  # Scale up for better matching

    def _extract_use_case(self, description: str) -> str | None:
        """Extract use case from description using keywords."""
        description_lower = description.lower()

        use_case_keywords = {
            "energy": ["energy", "power", "save", "efficient", "consumption"],
            "comfort": ["comfort", "temperature", "climate", "warm", "cool"],
            "security": ["security", "alarm", "lock", "door", "motion", "presence"],
            "convenience": ["convenience", "automate", "automatic", "schedule"]
        }

        for use_case, keywords in use_case_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                return use_case

        return None

