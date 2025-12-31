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
            if entities and self.tool_handler.data_api_client:
                try:
                    all_entities = await self.tool_handler.data_api_client.fetch_entities()
                    valid_entity_ids = {e.get("entity_id") for e in all_entities if e.get("entity_id")}
                    invalid_entities = [
                        eid for eid in entities 
                        if eid not in valid_entity_ids and not self.tool_handler._is_group_entity(eid)
                    ]
                    
                    if invalid_entities:
                        # Provide helpful error messages with suggestions (recommendation #8)
                        error_messages = []
                        for invalid_entity in invalid_entities:
                            # Try to find similar entity names (fuzzy matching for suggestions)
                            entity_domain = invalid_entity.split(".")[0] if "." in invalid_entity else None
                            similar_entities = []
                            if entity_domain:
                                similar_entities = [
                                    eid for eid in valid_entity_ids 
                                    if eid.startswith(f"{entity_domain}.") and 
                                    abs(len(eid) - len(invalid_entity)) <= 3
                                ][:3]  # Limit to 3 suggestions
                            
                            if similar_entities:
                                suggestions = ", ".join(similar_entities)
                                error_messages.append(
                                    f"Invalid entity ID: '{invalid_entity}'. "
                                    f"Did you mean: {suggestions}?"
                                )
                            else:
                                error_messages.append(f"Invalid entity ID: '{invalid_entity}' (entity does not exist)")
                        
                        errors.extend(error_messages)
                except Exception as e:
                    logger.warning(f"Failed to validate entities via Data API: {e}")
                    warnings.append(
                        "Could not validate entity existence (Data API unavailable). "
                        "Entity validation skipped."
                    )

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
