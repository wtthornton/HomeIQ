"""
YAML Renderer for AutomationSpec

Epic 51, Story 51.1: Canonical Automation Schema & YAML Renderer

Converts AutomationSpec (canonical schema) to Home Assistant YAML format.
Ensures deterministic, correct YAML output following 2025.10+ standards.
"""

import logging
from typing import Any

import yaml

from .schema import ActionSpec, AutomationSpec, ConditionSpec, TriggerSpec

logger = logging.getLogger(__name__)


class AutomationRenderer:
    """
    Renders AutomationSpec to Home Assistant YAML format.
    
    Ensures:
    - Singular keys (trigger:, action:) not plural (triggers:, actions:)
    - Correct field names (platform:, service:) not variants
    - Proper error handling format (error: continue) not (continue_on_error: true)
    - 2025.10+ compliance
    """

    def __init__(self):
        """Initialize renderer."""
        pass

    def render(self, spec: AutomationSpec) -> str:
        """
        Render AutomationSpec to YAML string.
        
        Args:
            spec: AutomationSpec instance
            
        Returns:
            YAML string in Home Assistant format
        """
        yaml_dict = self._spec_to_dict(spec)
        
        # Use safe_dump with explicit formatting for consistency
        yaml_str = yaml.safe_dump(
            yaml_dict,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,  # Prevent line wrapping
            indent=2
        )
        
        return yaml_str.strip()

    def _spec_to_dict(self, spec: AutomationSpec) -> dict[str, Any]:
        """Convert AutomationSpec to dictionary."""
        result: dict[str, Any] = {}
        
        # Required fields
        if spec.id:
            result["id"] = spec.id
        result["alias"] = spec.alias
        if spec.description:
            result["description"] = spec.description
        result["initial_state"] = spec.initial_state
        result["mode"] = spec.mode.value if hasattr(spec.mode, "value") else spec.mode
        
        # Trigger (singular, not plural)
        result["trigger"] = [self._trigger_to_dict(t) for t in spec.trigger]
        
        # Condition (optional)
        if spec.condition:
            result["condition"] = [self._condition_to_dict(c) for c in spec.condition]
        
        # Action (singular, not plural)
        result["action"] = [self._action_to_dict(a) for a in spec.action]
        
        # Optional fields
        if spec.max_exceeded:
            result["max_exceeded"] = spec.max_exceeded.value if hasattr(spec.max_exceeded, "value") else spec.max_exceeded
        if spec.tags:
            result["tags"] = spec.tags
        
        # Additional fields
        if spec.extra:
            result.update(spec.extra)
        
        return result

    def _trigger_to_dict(self, trigger: TriggerSpec) -> dict[str, Any]:
        """Convert TriggerSpec to dictionary."""
        result: dict[str, Any] = {"platform": trigger.platform}
        
        # Common trigger fields
        if trigger.entity_id is not None:
            result["entity_id"] = trigger.entity_id
        if trigger.to is not None:
            result["to"] = trigger.to
        if trigger.from_state is not None:
            result["from"] = trigger.from_state
        if trigger.at is not None:
            result["at"] = trigger.at
        if trigger.minutes is not None:
            result["minutes"] = trigger.minutes
        if trigger.hours is not None:
            result["hours"] = trigger.hours
        if trigger.days is not None:
            result["days"] = trigger.days
        
        # Additional fields
        if trigger.extra:
            result.update(trigger.extra)
        
        return result

    def _condition_to_dict(self, condition: ConditionSpec) -> dict[str, Any]:
        """Convert ConditionSpec to dictionary."""
        result: dict[str, Any] = {"condition": condition.condition}
        
        if condition.entity_id is not None:
            result["entity_id"] = condition.entity_id
        if condition.state is not None:
            result["state"] = condition.state
        if condition.above is not None:
            result["above"] = condition.above
        if condition.below is not None:
            result["below"] = condition.below
        
        # Additional fields
        if condition.extra:
            result.update(condition.extra)
        
        return result

    def _action_to_dict(self, action: ActionSpec) -> dict[str, Any]:
        """Convert ActionSpec to dictionary."""
        result: dict[str, Any] = {}
        
        # Primary action fields (service, scene, delay)
        if action.service:
            result["service"] = action.service
        if action.scene:
            result["scene"] = action.scene
        if action.delay:
            result["delay"] = action.delay
        
        # Target
        if action.target:
            result["target"] = action.target
        
        # Data
        if action.data:
            result["data"] = action.data
        
        # Advanced actions
        if action.choose:
            result["choose"] = action.choose
        if action.repeat:
            result["repeat"] = action.repeat
        if action.parallel:
            result["parallel"] = action.parallel
        if action.sequence:
            result["sequence"] = action.sequence
        
        # Error handling (use 'error', not 'continue_on_error')
        if action.error:
            result["error"] = action.error
        elif action.continue_on_error is not None:
            # Legacy support: convert continue_on_error to error
            result["error"] = "continue" if action.continue_on_error else "stop"
        
        # Additional fields
        if action.extra:
            result.update(action.extra)
        
        return result

