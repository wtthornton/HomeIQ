"""
Pattern Composer - Multi-pattern composition and YAML generation

Handles composition strategies for multiple pattern matches:
- Merge: Same trigger → combine actions
- Separate: Different triggers → create multiple automations
- Hybrid: Pattern + LLM enhancement
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .pattern_matcher import PatternMatch
from .common_patterns import generate_automation_id

logger = logging.getLogger(__name__)


@dataclass
class ComposedAutomation:
    """Result of composing one or more patterns into automation(s)"""
    automations: List[Dict[str, Any]]  # List of YAML automations
    strategy: str  # merge, separate, hybrid, pure_pattern
    patterns_used: List[str]  # Pattern IDs used
    confidence: float


class PatternComposer:
    """
    Composes multiple pattern matches into final automation(s).

    Strategies:
    - Pure pattern: Single pattern, direct YAML generation
    - Merged patterns: Multiple patterns with same trigger
    - Separate automations: Multiple patterns with different triggers
    - Hybrid: Pattern + LLM enhancement for customizations
    """

    async def compose(
        self,
        matches: List[PatternMatch],
        user_request: str
    ) -> ComposedAutomation:
        """
        Compose pattern matches into final automation(s).

        Args:
            matches: List of pattern matches (sorted by confidence)
            user_request: Original user request

        Returns:
            ComposedAutomation with strategy and generated YAML(s)
        """
        if not matches:
            raise ValueError("No pattern matches to compose")

        # Single pattern match - pure pattern strategy
        if len(matches) == 1:
            return await self._pure_pattern_strategy(matches[0])

        # Multiple patterns - analyze triggers
        trigger_groups = self._group_by_trigger(matches)

        if len(trigger_groups) == 1:
            # All patterns share same trigger → merge
            return await self._merge_strategy(matches)
        else:
            # Different triggers → separate automations
            return await self._separate_strategy(matches)

    async def _pure_pattern_strategy(self, match: PatternMatch) -> ComposedAutomation:
        """Generate automation from single pattern"""
        logger.info(f"Using pure pattern strategy for '{match.pattern_id}'")

        yaml_str = self._generate_yaml(match)

        return ComposedAutomation(
            automations=[{
                'yaml': yaml_str,
                'pattern_id': match.pattern_id,
                'title': match.pattern.name,
                'description': match.pattern.description
            }],
            strategy='pure_pattern',
            patterns_used=[match.pattern_id],
            confidence=match.confidence
        )

    async def _merge_strategy(self, matches: List[PatternMatch]) -> ComposedAutomation:
        """Merge multiple patterns with same trigger into one automation"""
        logger.info(f"Merging {len(matches)} patterns into single automation")

        # Use highest confidence pattern as base
        base_match = matches[0]

        # Generate base YAML
        base_yaml = self._generate_yaml(base_match)

        # TODO: In full implementation, parse YAML and merge actions from other patterns
        # For now, just use the best match
        logger.warning("Pattern merging not fully implemented - using best match only")

        pattern_ids = [m.pattern_id for m in matches]
        avg_confidence = sum(m.confidence for m in matches) / len(matches)

        return ComposedAutomation(
            automations=[{
                'yaml': base_yaml,
                'pattern_id': base_match.pattern_id,
                'title': f"Merged: {base_match.pattern.name}",
                'description': f"Combined {len(matches)} patterns",
                'merged_from': pattern_ids
            }],
            strategy='merged_patterns',
            patterns_used=pattern_ids,
            confidence=avg_confidence
        )

    async def _separate_strategy(self, matches: List[PatternMatch]) -> ComposedAutomation:
        """Create separate automations for each pattern"""
        logger.info(f"Creating {len(matches)} separate automations")

        automations = []
        pattern_ids = []

        for match in matches:
            yaml_str = self._generate_yaml(match)
            automations.append({
                'yaml': yaml_str,
                'pattern_id': match.pattern_id,
                'title': match.pattern.name,
                'description': match.pattern.description
            })
            pattern_ids.append(match.pattern_id)

        avg_confidence = sum(m.confidence for m in matches) / len(matches)

        return ComposedAutomation(
            automations=automations,
            strategy='separate_automations',
            patterns_used=pattern_ids,
            confidence=avg_confidence
        )

    def _group_by_trigger(self, matches: List[PatternMatch]) -> Dict[str, List[PatternMatch]]:
        """
        Group pattern matches by trigger type.

        Returns dict mapping trigger_key → list of matches
        """
        groups = {}

        for match in matches:
            # Extract trigger info from variables
            # For simplicity, we'll check common trigger variables
            trigger_key = self._get_trigger_key(match)

            if trigger_key not in groups:
                groups[trigger_key] = []
            groups[trigger_key].append(match)

        return groups

    def _get_trigger_key(self, match: PatternMatch) -> str:
        """
        Get trigger key for grouping.

        Examples:
        - motion_sensor:binary_sensor.porch → "state:binary_sensor.porch"
        - person:person.user → "state:person.user"
        - time:07:00:00 → "time:07:00:00"
        """
        variables = match.variables

        # Check for common trigger variable patterns
        if 'motion_sensor' in variables:
            return f"state:{variables['motion_sensor']}"
        elif 'person' in variables:
            return f"state:{variables['person']}"
        elif 'door_sensor' in variables:
            return f"state:{variables['door_sensor']}"
        elif 'time' in variables:
            return f"time:{variables['time']}"
        else:
            # Fallback: use pattern ID (different triggers)
            return f"pattern:{match.pattern_id}"

    def _generate_yaml(self, match: PatternMatch) -> str:
        """
        Generate YAML from pattern match by filling template variables.

        Args:
            match: Pattern match with extracted variables

        Returns:
            Complete YAML automation string
        """
        template = match.pattern.template
        variables = match.variables.copy()

        # Generate automation ID
        automation_id = generate_automation_id(match.pattern_id, variables)
        variables['automation_id'] = automation_id

        # Generate alias (use pattern name + entity names)
        variables['alias'] = self._generate_alias(match)

        # Add derived variables
        variables.update(self._generate_derived_variables(match))

        # Fill template
        try:
            yaml_str = template.format(**variables)
            return yaml_str
        except KeyError as e:
            logger.error(f"Missing variable in template: {e}")
            logger.error(f"Available variables: {list(variables.keys())}")
            raise

    def _generate_alias(self, match: PatternMatch) -> str:
        """Generate friendly automation alias"""
        pattern_name = match.pattern.name

        # Try to include entity names for context
        variables = match.variables
        entity_names = []

        for var_name, var_value in variables.items():
            if '.' in var_value:  # Likely an entity_id
                # Extract friendly name from entity_id
                friendly = var_value.split('.')[1].replace('_', ' ').title()
                entity_names.append(friendly)

        if entity_names:
            return f"{pattern_name}: {', '.join(entity_names[:2])}"
        else:
            return pattern_name

    def _generate_derived_variables(self, match: PatternMatch) -> Dict[str, str]:
        """
        Generate derived variables from extracted variables.

        Examples:
        - motion_sensor → motion_sensor_name (friendly name)
        - timeout → timeout_padded (zero-padded for YAML time format)
        """
        derived = {}
        variables = match.variables

        # Generate friendly names from entity IDs
        for var_name, var_value in variables.items():
            if '.' in var_value:  # Entity ID
                friendly = var_value.split('.')[1].replace('_', ' ').title()
                derived[f"{var_name}_name"] = friendly

        # Pad timeout values for HH:MM:SS format
        for key in ['timeout', 'wait_time', 'no_motion_delay']:
            if key in variables:
                value = int(variables[key])
                derived[f"{key}_padded"] = f"{value:02d}"

        # Generate action_type_readable
        if 'action_type' in variables:
            action = variables['action_type']
            derived['action_type_readable'] = action.replace('_', ' ').title()

        # Format offset for sun trigger
        if 'offset' in variables:
            offset = int(variables['offset'])
            if offset >= 0:
                derived['offset_formatted'] = f"+00:{offset:02d}:00"
            else:
                derived['offset_formatted'] = f"-00:{abs(offset):02d}:00"

        return derived


def get_pattern_composer() -> PatternComposer:
    """Factory function to create pattern composer"""
    return PatternComposer()
