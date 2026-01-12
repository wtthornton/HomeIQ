"""
HomeIQ JSON to AutomationSpec Converter

Converts HomeIQ JSON Automation format to AutomationSpec for YAML rendering.
Preserves HomeIQ metadata in AutomationSpec.extra for later retrieval.
"""

import logging
from typing import Any

from shared.yaml_validation_service.schema import (
    ActionSpec,
    AutomationMode,
    AutomationSpec,
    ConditionSpec,
    MaxExceeded,
    TriggerSpec,
)

from .schema import (
    HomeIQAction,
    HomeIQAutomation,
    HomeIQCondition,
    HomeIQTrigger,
    Target,
    TriggerConfig,
)

logger = logging.getLogger(__name__)


class HomeIQToAutomationSpecConverter:
    """
    Converts HomeIQ JSON Automation to AutomationSpec.
    
    Preserves HomeIQ metadata in AutomationSpec.extra for later retrieval.
    """
    
    def convert(self, homeiq_automation: HomeIQAutomation) -> AutomationSpec:
        """
        Convert HomeIQ JSON Automation to AutomationSpec.
        
        Args:
            homeiq_automation: HomeIQ JSON Automation instance
        
        Returns:
            AutomationSpec instance with HomeIQ metadata preserved in extra
        """
        # Convert triggers
        triggers = [self._convert_trigger(t) for t in homeiq_automation.triggers]
        
        # Convert conditions
        conditions = None
        if homeiq_automation.conditions:
            conditions = [self._convert_condition(c) for c in homeiq_automation.conditions]
        
        # Convert actions
        actions = [self._convert_action(a) for a in homeiq_automation.actions]
        
        # Preserve HomeIQ metadata in extra
        extra: dict[str, Any] = {
            "homeiq_version": homeiq_automation.version,
            "homeiq_metadata": homeiq_automation.homeiq_metadata.model_dump(),
            "device_context": homeiq_automation.device_context.model_dump(),
            "area_context": homeiq_automation.area_context,
        }
        
        if homeiq_automation.pattern_context:
            extra["pattern_context"] = homeiq_automation.pattern_context.model_dump()
        
        if homeiq_automation.safety_checks:
            extra["safety_checks"] = homeiq_automation.safety_checks.model_dump()
        
        if homeiq_automation.energy_impact:
            extra["energy_impact"] = homeiq_automation.energy_impact.model_dump()
        
        if homeiq_automation.dependencies:
            extra["dependencies"] = homeiq_automation.dependencies
        
        # Create AutomationSpec
        spec = AutomationSpec(
            id=homeiq_automation.id,
            alias=homeiq_automation.alias,
            description=homeiq_automation.description,
            initial_state=homeiq_automation.initial_state,
            mode=homeiq_automation.mode,
            trigger=triggers,
            condition=conditions,
            action=actions,
            max_exceeded=homeiq_automation.max_exceeded,
            tags=homeiq_automation.tags,
            extra=extra
        )
        
        logger.debug(f"Converted HomeIQ automation '{homeiq_automation.alias}' to AutomationSpec")
        return spec
    
    def _target_to_dict(self, target: Target) -> dict[str, Any]:
        """Convert Target model to YAML-compatible dict."""
        target_dict: dict[str, Any] = {}
        if target.area_id:
            target_dict["area_id"] = target.area_id
        if target.floor_id:
            target_dict["floor_id"] = target.floor_id
        if target.labels:
            target_dict["labels"] = target.labels
        if target.device_id:
            target_dict["device_id"] = target.device_id
        if target.entity_id:
            target_dict["entity_id"] = target.entity_id
        return target_dict
    
    def _map_trigger_config_to_yaml(
        self, 
        platform: str, 
        config: TriggerConfig
    ) -> dict[str, Any]:
        """
        Map generic trigger configuration to YAML-compatible fields.
        
        Maps platform-agnostic config to HA 2026.1 YAML format.
        """
        yaml_fields: dict[str, Any] = {}
        
        # Always include entity_id if present
        if config.entity_id:
            yaml_fields["entity_id"] = config.entity_id
        
        # Copy all parameters directly (they're already in YAML-compatible format)
        # Examples:
        # - state triggers: {"to": "on", "from": "off"}
        # - time triggers: {"at": "08:00:00"}
        # - button triggers: {"action": "press"}
        # - climate triggers: {"mode": "heating", "temperature_threshold": 20.0}
        yaml_fields.update(config.parameters)
        
        return yaml_fields
    
    def _convert_trigger(self, trigger: HomeIQTrigger) -> TriggerSpec:
        """Convert HomeIQ trigger to TriggerSpec."""
        trigger_data: dict[str, Any] = {
            "platform": trigger.platform,
        }
        
        # Map trigger config to YAML fields
        yaml_fields = self._map_trigger_config_to_yaml(
            platform=trigger.platform,
            config=trigger.config
        )
        trigger_data.setdefault("extra", {}).update(yaml_fields)
        
        # Handle enhanced targeting
        if trigger.target:
            target_dict = self._target_to_dict(trigger.target)
            if target_dict:
                trigger_data.setdefault("extra", {})["target"] = target_dict
        
        # Merge any additional extra fields
        if trigger.extra:
            trigger_data.setdefault("extra", {}).update(trigger.extra)
        
        return TriggerSpec(**trigger_data)
    
    def _convert_condition(self, condition: HomeIQCondition) -> ConditionSpec:
        """Convert HomeIQ condition to ConditionSpec."""
        condition_data: dict[str, Any] = {
            "condition": condition.condition,
        }
        
        # Copy standard fields
        if condition.entity_id is not None:
            condition_data["entity_id"] = condition.entity_id
        if condition.state is not None:
            condition_data["state"] = condition.state
        if condition.above is not None:
            condition_data["above"] = condition.above
        if condition.below is not None:
            condition_data["below"] = condition.below
        
        # Handle enhanced targeting
        if condition.target:
            target_dict = self._target_to_dict(condition.target)
            if target_dict:
                condition_data.setdefault("extra", {})["target"] = target_dict
        
        # Merge extra fields
        if condition.extra:
            condition_data.setdefault("extra", {}).update(condition.extra)
        
        return ConditionSpec(**condition_data)
    
    def _convert_action(self, action: HomeIQAction) -> ActionSpec:
        """Convert HomeIQ action to ActionSpec."""
        action_data: dict[str, Any] = {}
        
        # Copy standard fields
        if action.service:
            action_data["service"] = action.service
        if action.scene:
            action_data["scene"] = action.scene
        if action.delay:
            action_data["delay"] = action.delay
        if action.data:
            action_data["data"] = action.data
        
        # Handle enhanced targeting (REPLACES old dict target)
        if action.target:
            target_dict = self._target_to_dict(action.target)
            if target_dict:
                action_data["target"] = target_dict
        
        # Advanced actions
        if action.choose:
            action_data["choose"] = action.choose
        if action.repeat:
            action_data["repeat"] = action.repeat
        if action.parallel:
            action_data["parallel"] = action.parallel
        if action.sequence:
            action_data["sequence"] = action.sequence
        
        # Error handling
        if action.error:
            action_data["error"] = action.error
        
        # HomeIQ extensions (preserve in extra)
        if action.energy_impact_w is not None:
            action_data.setdefault("extra", {})["energy_impact_w"] = action.energy_impact_w
        
        # Merge extra fields
        if action.extra:
            action_data.setdefault("extra", {}).update(action.extra)
        
        return ActionSpec(**action_data)

