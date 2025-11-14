"""
Community Pattern Learner

Discovers automation patterns from automation-miner corpus.
Automatically expands the Common Patterns Library with proven community templates.
"""

from typing import Dict, List, Optional, Any, Tuple
from collections import Counter
import logging
import httpx
import re

from ..patterns import PatternDefinition, PatternVariable

logger = logging.getLogger(__name__)


class CommunityPatternLearner:
    """
    Learn patterns from automation-miner community corpus.

    Analyzes high-quality automations to discover common patterns,
    then generates PatternDefinition objects for the pattern library.
    """

    def __init__(self, miner_base_url: str = "http://localhost:8029"):
        """
        Initialize community pattern learner.

        Args:
            miner_base_url: Base URL for automation-miner service
        """
        self.miner_url = miner_base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def discover_patterns(
        self,
        min_quality: float = 0.7,
        min_occurrences: int = 10
    ) -> List[PatternDefinition]:
        """
        Discover common automation patterns from community corpus.

        Args:
            min_quality: Minimum quality score for automations
            min_occurrences: Minimum times a pattern must appear

        Returns:
            List of discovered PatternDefinition objects
        """
        logger.info(f"Discovering patterns from community corpus (quality >= {min_quality})")

        # Step 1: Fetch high-quality automations
        automations = await self._fetch_quality_automations(min_quality)

        if not automations:
            logger.warning("No automations found in corpus")
            return []

        logger.info(f"Analyzing {len(automations)} automations for patterns")

        # Step 2: Group automations by device combinations
        device_groups = self._group_by_devices(automations)

        # Step 3: Find patterns that appear frequently
        discovered_patterns = []

        for device_combo, autos in device_groups.items():
            if len(autos) >= min_occurrences:
                logger.info(
                    f"Found pattern: {device_combo} "
                    f"({len(autos)} instances)"
                )

                # Extract pattern from examples
                pattern = await self._extract_pattern(device_combo, autos)

                if pattern:
                    discovered_patterns.append(pattern)

        logger.info(f"Discovered {len(discovered_patterns)} new patterns")

        return discovered_patterns

    async def _fetch_quality_automations(
        self,
        min_quality: float
    ) -> List[Dict[str, Any]]:
        """
        Fetch high-quality automations from miner.

        Args:
            min_quality: Minimum quality score

        Returns:
            List of automation metadata dictionaries
        """
        try:
            response = await self.client.get(
                f"{self.miner_url}/api/automation-miner/corpus/search",
                params={
                    "min_quality": min_quality,
                    "limit": 500
                }
            )

            response.raise_for_status()
            data = response.json()

            automations = data.get("automations", [])
            logger.info(f"Fetched {len(automations)} automations from miner")

            return automations

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch automations from miner: {e}")
            return []

    def _group_by_devices(
        self,
        automations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group automations by device combination.

        Args:
            automations: List of automation metadata

        Returns:
            Dict mapping device_combo -> list of automations
        """
        groups = {}

        for auto in automations:
            devices = auto.get("devices", [])

            # Skip if no devices or too many (too specific)
            if not devices or len(devices) > 4:
                continue

            # Create sorted device combination key
            device_combo = tuple(sorted(devices))

            if device_combo not in groups:
                groups[device_combo] = []

            groups[device_combo].append(auto)

        return groups

    async def _extract_pattern(
        self,
        device_combo: Tuple[str, ...],
        automations: List[Dict[str, Any]]
    ) -> Optional[PatternDefinition]:
        """
        Extract common pattern from group of similar automations.

        Args:
            device_combo: Tuple of device types
            automations: List of automations with these devices

        Returns:
            PatternDefinition or None if pattern can't be extracted
        """
        # Analyze common attributes
        use_cases = [a.get("use_case") for a in automations]
        most_common_use_case = Counter(use_cases).most_common(1)[0][0]

        complexity_levels = [a.get("complexity") for a in automations]
        most_common_complexity = Counter(complexity_levels).most_common(1)[0][0]

        # Extract common keywords from titles
        all_titles = " ".join([a.get("title", "") for a in automations]).lower()
        keywords = self._extract_keywords(all_titles, device_combo)

        # Generate pattern metadata
        pattern_id = f"community_{'_'.join(device_combo)}"
        pattern_name = self._generate_pattern_name(device_combo, all_titles)
        description = f"Community pattern: {pattern_name}"

        # Generate pattern variables from device types
        variables = []
        for device in device_combo:
            variables.append(
                PatternVariable(
                    name=device,
                    type=device,
                    domain=self._get_domain_for_device(device),
                    description=f"{device.replace('_', ' ').title()} to control"
                )
            )

        # Calculate priority based on occurrence count
        occurrence_count = len(automations)
        priority = min(90, 50 + (occurrence_count // 10))  # Cap at 90

        # Generate placeholder template
        # (Real implementation would analyze actual YAML structures)
        template = self._generate_placeholder_template(device_combo, pattern_id)

        return PatternDefinition(
            id=pattern_id,
            name=pattern_name,
            description=description,
            category=most_common_use_case,
            keywords=keywords,
            variables=variables,
            template=template,
            priority=priority
        )

    def _extract_keywords(
        self,
        text: str,
        device_combo: Tuple[str, ...]
    ) -> List[str]:
        """Extract relevant keywords from text"""
        # Start with device names
        keywords = list(device_combo)

        # Common automation keywords
        common_words = [
            'auto', 'automatic', 'turn', 'on', 'off', 'when', 'if',
            'schedule', 'time', 'trigger', 'control', 'smart'
        ]

        words = re.findall(r'\b\w{4,}\b', text)  # Words 4+ chars
        word_counts = Counter(words)

        # Add frequently occurring words (excluding common words)
        for word, count in word_counts.most_common(15):
            if word not in common_words and word not in keywords:
                keywords.append(word)

        return keywords[:15]  # Limit to 15 keywords

    def _generate_pattern_name(
        self,
        device_combo: Tuple[str, ...],
        titles_text: str
    ) -> str:
        """Generate friendly pattern name"""
        # Check for common pattern names in titles
        if "motion" in titles_text and "light" in titles_text:
            return "Motion-Activated Lighting"
        elif "door" in titles_text and "alert" in titles_text:
            return "Door Alert System"
        elif "climate" in titles_text or "temperature" in titles_text:
            return "Climate Control Automation"
        else:
            # Fallback: Create name from devices
            devices_str = ", ".join([d.replace('_', ' ').title() for d in device_combo])
            return f"{devices_str} Automation"

    def _get_domain_for_device(self, device: str) -> str:
        """Map device type to HA domain"""
        # Handle compound device types
        if 'sensor' in device:
            return 'binary_sensor' if 'binary' in device or 'motion' in device or 'door' in device else 'sensor'

        # Direct mappings
        domain_map = {
            'light': 'light',
            'switch': 'switch',
            'climate': 'climate',
            'thermostat': 'climate',
            'cover': 'cover',
            'lock': 'lock',
            'camera': 'camera',
            'fan': 'fan'
        }

        return domain_map.get(device, device)

    def _generate_placeholder_template(
        self,
        device_combo: Tuple[str, ...],
        pattern_id: str
    ) -> str:
        """
        Generate placeholder template.

        Real implementation would analyze actual automation YAML
        structures from the corpus and generate proper templates.
        For now, returns a basic template structure.
        """
        devices_str = ", ".join(["{" + d + "}" for d in device_combo])

        return f"""id: '{{automation_id}}'
alias: '{{alias}}'
description: 'Community pattern using {devices_str}'
mode: single
triggers:
  - trigger: state
    entity_id: {{{device_combo[0]}}}
    to: 'on'
conditions: []
actions:
  - action: homeassistant.turn_on
    target:
      entity_id: {{{device_combo[-1] if len(device_combo) > 1 else device_combo[0]}}}
"""

    async def get_pattern_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about patterns in the corpus.

        Returns:
            Dictionary with pattern statistics
        """
        try:
            response = await self.client.get(
                f"{self.miner_url}/api/automation-miner/corpus/stats"
            )

            response.raise_for_status()
            stats = response.json()

            return {
                "total_automations": stats.get("count", 0),
                "avg_quality": stats.get("avg_quality_score", 0),
                "device_types": stats.get("unique_devices", 0),
                "use_cases": stats.get("use_cases", {})
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch statistics: {e}")
            return {}

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


def get_pattern_learner(miner_url: str = "http://localhost:8029") -> CommunityPatternLearner:
    """Factory function to create pattern learner"""
    return CommunityPatternLearner(miner_url)
