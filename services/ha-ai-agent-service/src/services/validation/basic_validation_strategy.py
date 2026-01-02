"""
Basic Validation Strategy.

This strategy provides basic YAML parsing and structure validation as a
last resort when other validation services are unavailable.
"""

import logging
from typing import Any

import yaml

from ...models.automation_models import ValidationResult
from .validation_strategy import ValidationStrategy

logger = logging.getLogger(__name__)


class BasicValidationStrategy(ValidationStrategy):
    """Basic validation strategy using YAML parsing."""

    def __init__(self, tool_handler: Any):
        """
        Initialize basic validation strategy.

        Args:
            tool_handler: HAToolHandler instance (for access to helper methods)
        """
        self.tool_handler = tool_handler

    @property
    def name(self) -> str:
        """Return the name of this validation strategy."""
        return "Basic Validation"

    async def validate(self, automation_yaml: str) -> ValidationResult:
        """
        Validate automation YAML using basic parsing and structure checks.

        Args:
            automation_yaml: YAML string to validate

        Returns:
            ValidationResult with validation status
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # Parse YAML
            automation_dict = yaml.safe_load(automation_yaml)

            if not isinstance(automation_dict, dict):
                errors.append("Automation YAML must be a dictionary")
                return ValidationResult(
                    valid=False,
                    errors=errors,
                    warnings=warnings,
                )

            # Check required fields
            if "trigger" not in automation_dict:
                errors.append(
                    "Missing required field: 'trigger' (2025.10+ format uses singular 'trigger:', not 'triggers:')"
                )
            elif not automation_dict["trigger"]:
                errors.append("Field 'trigger' cannot be empty")

            if "action" not in automation_dict:
                errors.append(
                    "Missing required field: 'action' (2025.10+ format uses singular 'action:', not 'actions:')"
                )
            elif not automation_dict["action"]:
                errors.append("Field 'action' cannot be empty")

            # Check optional but recommended fields
            if "alias" not in automation_dict:
                warnings.append("Missing recommended field: 'alias' (used for identification)")

            if "description" not in automation_dict:
                warnings.append("Missing recommended field: 'description' (helps with automation management)")

            if "initial_state" not in automation_dict:
                warnings.append(
                    "Missing recommended field: 'initial_state' (should be 'true' for 2025.10+ compliance). "
                    "2025.10+ format requires explicit initial_state: true"
                )

            # Check for group entities and provide warnings
            entities = self.tool_handler._extract_entities_from_yaml(automation_dict)
            group_entities = [eid for eid in entities if self.tool_handler._is_group_entity(eid)]
            if group_entities:
                warnings.append(
                    f"Group entities detected: {', '.join(group_entities)}. "
                    "Groups don't have 'last_changed' attribute - templates accessing group.last_changed will fail. "
                    "Use individual entities with condition: state and for: option instead for continuous occupancy detection."
                )

            # CRITICAL: Mandatory entity validation (recommendation #2 from HA_AGENT_API_FLOW_ANALYSIS.md)
            # Validate that all entities exist in Home Assistant
            entity_validation_errors, entity_validation_warnings = await self._validate_entities(
                entities
            )
            errors.extend(entity_validation_errors)
            warnings.extend(entity_validation_warnings)

            # Validate trigger structure
            if "trigger" in automation_dict:
                trigger = automation_dict["trigger"]
                if isinstance(trigger, list):
                    if len(trigger) == 0:
                        errors.append("Trigger list cannot be empty")
                elif isinstance(trigger, dict) and "platform" not in trigger:
                    errors.append("Trigger must have a 'platform' field")

            # Validate action structure
            if "action" in automation_dict:
                action = automation_dict["action"]
                if isinstance(action, list) and len(action) == 0:
                    errors.append("Action list cannot be empty")
                elif isinstance(action, dict):
                    if "service" not in action and "scene" not in action:
                        errors.append("Action must have either 'service' or 'scene' field")

            # Pattern detection for motion-based dimming automations
            dimming_warnings = self._detect_dimming_pattern_issues(automation_dict)
            warnings.extend(dimming_warnings)

            valid = len(errors) == 0

            return ValidationResult(
                valid=valid,
                errors=errors,
                warnings=warnings,
            )

        except yaml.YAMLError as e:
            return ValidationResult(
                valid=False,
                errors=[f"YAML syntax error: {str(e)}"],
                warnings=warnings,
            )
        except Exception as e:
            logger.error(f"Error validating automation YAML: {e}", exc_info=True)
            return ValidationResult(
                valid=False,
                errors=[str(e)],
                warnings=warnings,
            )

    async def _validate_entities(
        self, entities: list[str]
    ) -> tuple[list[str], list[str]]:
        """
        Validate that all entities exist in Home Assistant.

        Args:
            entities: List of entity IDs to validate

        Returns:
            Tuple of (error_messages, warning_messages)
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not entities or not self.tool_handler.data_api_client:
            return errors, warnings

        try:
            all_entities = await self.tool_handler.data_api_client.fetch_entities()
            valid_entity_ids = {e.get("entity_id") for e in all_entities if e.get("entity_id")}
            invalid_entities = [
                eid for eid in entities 
                if eid not in valid_entity_ids and not self.tool_handler._is_group_entity(eid)
            ]
            
            if invalid_entities:
                # Provide helpful error messages with suggestions (recommendation #8)
                for invalid_entity in invalid_entities:
                    error_msg = self._build_entity_error_message(
                        invalid_entity, valid_entity_ids
                    )
                    errors.append(error_msg)

        except Exception as e:
            logger.warning(f"Failed to validate entities via Data API: {e}")
            warnings.append(
                "Could not validate entity existence (Data API unavailable). "
                "Entity validation skipped."
            )

        return errors, warnings

    def _build_entity_error_message(
        self, invalid_entity: str, valid_entity_ids: set[str]
    ) -> str:
        """
        Build error message for invalid entity with suggestions.

        Args:
            invalid_entity: The invalid entity ID
            valid_entity_ids: Set of valid entity IDs for matching

        Returns:
            Error message string with suggestions if available
        """
        entity_domain = invalid_entity.split(".")[0] if "." in invalid_entity else None
        
        if entity_domain:
            similar_entities = [
                eid for eid in valid_entity_ids 
                if eid.startswith(f"{entity_domain}.") and 
                abs(len(eid) - len(invalid_entity)) <= 3
            ][:3]  # Limit to 3 suggestions
            
            if similar_entities:
                suggestions = ", ".join(similar_entities)
                return (
                    f"Invalid entity ID: '{invalid_entity}'. "
                    f"Did you mean: {suggestions}?"
                )
        
        return f"Invalid entity ID: '{invalid_entity}' (entity does not exist)"

    def _detect_dimming_pattern_issues(
        self, automation_dict: dict[str, Any]
    ) -> list[str]:
        """
        Detect common issues in motion-based dimming automations.

        Args:
            automation_dict: Parsed automation dictionary

        Returns:
            List of warning messages for detected issues
        """
        warnings: list[str] = []

        # Check if this looks like a dimming automation
        description = automation_dict.get("description", "").lower()
        alias = automation_dict.get("alias", "").lower()
        is_dimming = (
            "dim" in description or "dim" in alias or
            "dimming" in description or "dimming" in alias
        )

        if not is_dimming:
            return warnings

        # Check for common issues
        action = automation_dict.get("action", [])
        if not isinstance(action, list) or len(action) == 0:
            return warnings

        # Check trigger structure for dimming automations (check this first, even without choose action)
        trigger = automation_dict.get("trigger", [])
        if isinstance(trigger, list):
            # Check if single trigger has both "on" and "off" states
            for trig in trigger:
                if isinstance(trig, dict):
                    to_states = trig.get("to", [])
                    # Handle both list and string cases
                    if isinstance(to_states, list) and "on" in to_states and "off" in to_states:
                        warnings.append(
                            "Motion-based dimming: Consider using separate triggers for motion detection "
                            "(to: 'on') and no-motion timeout (to: 'off' with for: option) instead of "
                            "a single trigger with both states."
                        )

        # Check for choose action with dimming pattern
        choose_action = None
        for act in action:
            if isinstance(act, dict) and "choose" in act:
                choose_action = act["choose"]
                break

        if not choose_action or not isinstance(choose_action, list):
            return warnings

        # Check for issues in each branch
        for branch in choose_action:
            if not isinstance(branch, dict) or "sequence" not in branch:
                continue

            sequence = branch.get("sequence", [])
            if not isinstance(sequence, list):
                continue

            # Check for repeat blocks with brightness_step
            for seq_item in sequence:
                if not isinstance(seq_item, dict):
                    continue

                # Check for repeat block
                if "repeat" in seq_item:
                    repeat_block = seq_item["repeat"]
                    if isinstance(repeat_block, dict):
                        repeat_seq = repeat_block.get("sequence", [])
                        
                        # Check if using brightness_step
                        has_brightness_step = False
                        for repeat_item in repeat_seq:
                            if isinstance(repeat_item, dict):
                                service = repeat_item.get("service", "")
                                data = repeat_item.get("data", {})
                                if service == "light.turn_on" and "brightness_step" in data:
                                    has_brightness_step = True
                                    break

                        if has_brightness_step:
                            # Check for count vs until
                            if "count" not in repeat_block and "until" in repeat_block:
                                warnings.append(
                                    "Motion-based dimming: Consider using 'count' instead of 'until' condition "
                                    "for brightness_step dimming. 'until' conditions checking 'light.{area}' "
                                    "entities may fail (these entities don't exist). Use 'count: ceil(max_brightness / step_size)' "
                                    "and add explicit 'light.turn_off' after the repeat block."
                                )

                            # Check if explicit turn_off exists after repeat
                            repeat_index = sequence.index(seq_item)
                            has_turn_off_after = False
                            if repeat_index + 1 < len(sequence):
                                next_item = sequence[repeat_index + 1]
                                if isinstance(next_item, dict):
                                    service = next_item.get("service", "")
                                    target = next_item.get("target", {})
                                    if service == "light.turn_off":
                                        has_turn_off_after = True

                            if not has_turn_off_after:
                                warnings.append(
                                    "Motion-based dimming: Add explicit 'light.turn_off' action after the "
                                    "dimming repeat block to ensure lights are completely off."
                                )

        # Check for conditions with individual 'for:' options
        for branch in choose_action:
            if not isinstance(branch, dict) or "conditions" not in branch:
                continue

            conditions = branch.get("conditions", [])
            if not isinstance(conditions, list):
                continue

            for cond in conditions:
                if isinstance(cond, dict) and cond.get("condition") == "and":
                    and_conditions = cond.get("conditions", [])
                    if isinstance(and_conditions, list):
                        for_and_conditions = [
                            c for c in and_conditions
                            if isinstance(c, dict) and "for" in c
                        ]
                        if len(for_and_conditions) > 1:
                            warnings.append(
                                "Motion-based dimming: Individual 'for:' options in 'and' conditions check "
                                "independently, not together. Use trigger 'for:' option instead, then check "
                                "current state in conditions."
                            )

        return warnings
