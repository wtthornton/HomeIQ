"""
YAML Normalizer

Epic 51, Story 51.3: Build YAML Normalizer & Auto-Correction

Normalizes YAML to canonical format:
- Plural keys → singular (triggers → trigger, actions → action)
- Field name corrections (action: → service:, trigger: → platform:)
- Error handling format (continue_on_error → error)
- Target structure optimization
"""

import logging
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class YAMLNormalizer:
    """
    Normalizes Home Assistant automation YAML to canonical format.
    
    Fixes common format errors:
    - triggers: → trigger:
    - actions: → action:
    - action: field in action steps → service:
    - trigger: field in trigger items → platform:
    - continue_on_error: true → error: continue
    """

    def __init__(self):
        """Initialize normalizer."""
        pass

    def normalize(self, yaml_content: str) -> tuple[str, list[str]]:
        """
        Normalize YAML content to canonical format.
        
        Args:
            yaml_content: Raw YAML string (may contain format errors)
            
        Returns:
            Tuple of (normalized_yaml, fixes_applied)
        """
        fixes_applied: list[str] = []
        
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            if not isinstance(data, dict):
                return (yaml_content, fixes_applied)
            
            # Apply normalizations
            normalized_data = self._normalize_dict(data, fixes_applied)
            
            # Render back to YAML
            normalized_yaml = yaml.safe_dump(
                normalized_data,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=1000,
                indent=2
            )
            
            return (normalized_yaml.strip(), fixes_applied)
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to normalize YAML: {e}")
            return (yaml_content, fixes_applied)
        except Exception as e:
            logger.error(f"Unexpected error during normalization: {e}")
            return (yaml_content, fixes_applied)

    def _normalize_dict(self, data: dict[str, Any], fixes_applied: list[str]) -> dict[str, Any]:
        """Recursively normalize dictionary."""
        result: dict[str, Any] = {}
        
        for key, value in data.items():
            # Fix plural keys → singular
            if key == "triggers":
                result["trigger"] = self._normalize_value(value, fixes_applied, "triggers → trigger")
                fixes_applied.append("Fixed: 'triggers' → 'trigger'")
            elif key == "actions":
                result["action"] = self._normalize_value(value, fixes_applied, "actions → action")
                fixes_applied.append("Fixed: 'actions' → 'action'")
            elif key == "conditions":
                result["condition"] = self._normalize_value(value, fixes_applied, "conditions → condition")
                fixes_applied.append("Fixed: 'conditions' → 'condition'")
            # Fix error handling
            elif key == "continue_on_error":
                if value is True:
                    result["error"] = "continue"
                    fixes_applied.append("Fixed: 'continue_on_error: true' → 'error: continue'")
                elif value is False:
                    result["error"] = "stop"
                    fixes_applied.append("Fixed: 'continue_on_error: false' → 'error: stop'")
                # Don't include if value is None
            else:
                # Normalize value recursively
                result[key] = self._normalize_value(value, fixes_applied, f"key '{key}'")
        
        # Normalize trigger items
        if "trigger" in result and isinstance(result["trigger"], list):
            result["trigger"] = [self._normalize_trigger_item(item, fixes_applied) for item in result["trigger"]]
        
        # Normalize action items
        if "action" in result and isinstance(result["action"], list):
            result["action"] = [self._normalize_action_item(item, fixes_applied) for item in result["action"]]
        
        return result

    def _normalize_value(self, value: Any, fixes_applied: list[str], context: str) -> Any:
        """Recursively normalize value."""
        if isinstance(value, dict):
            return self._normalize_dict(value, fixes_applied)
        elif isinstance(value, list):
            return [self._normalize_value(item, fixes_applied, context) for item in value]
        else:
            return value

    def _normalize_trigger_item(self, item: dict[str, Any], fixes_applied: list[str]) -> dict[str, Any]:
        """Normalize a trigger item."""
        if not isinstance(item, dict):
            return item
        
        result: dict[str, Any] = {}
        
        for key, value in item.items():
            # Fix trigger: field → platform:
            if key == "trigger":
                if isinstance(value, str):
                    result["platform"] = value
                    fixes_applied.append("Fixed: trigger item 'trigger:' → 'platform:'")
                else:
                    result[key] = value
            else:
                result[key] = self._normalize_value(value, fixes_applied, f"trigger.{key}")
        
        return result

    def _normalize_action_item(self, item: dict[str, Any], fixes_applied: list[str]) -> dict[str, Any]:
        """Normalize an action item."""
        if not isinstance(item, dict):
            return item
        
        result: dict[str, Any] = {}
        
        for key, value in item.items():
            # Fix action: field → service:
            if key == "action":
                if isinstance(value, str):
                    result["service"] = value
                    fixes_applied.append("Fixed: action item 'action:' → 'service:'")
                else:
                    result[key] = value
            # Fix error handling
            elif key == "continue_on_error":
                if value is True:
                    result["error"] = "continue"
                    fixes_applied.append("Fixed: action 'continue_on_error: true' → 'error: continue'")
                elif value is False:
                    result["error"] = "stop"
                    fixes_applied.append("Fixed: action 'continue_on_error: false' → 'error: stop'")
            else:
                result[key] = self._normalize_value(value, fixes_applied, f"action.{key}")
        
        return result

