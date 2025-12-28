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
    
    def _convert_trigger(self, trigger: HomeIQTrigger) -> TriggerSpec:
        """Convert HomeIQ trigger to TriggerSpec."""
        trigger_data: dict[str, Any] = {
            "platform": trigger.platform,
        }
        
        # Copy standard fields
        if trigger.entity_id is not None:
            trigger_data["entity_id"] = trigger.entity_id
        if trigger.to is not None:
            trigger_data["to"] = trigger.to
        if trigger.from_state is not None:
            trigger_data["from"] = trigger.from_state
        if trigger.at is not None:
            trigger_data["at"] = trigger.at
        if trigger.minutes is not None:
            trigger_data["minutes"] = trigger.minutes
        if trigger.hours is not None:
            trigger_data["hours"] = trigger.hours
        if trigger.days is not None:
            trigger_data["days"] = trigger.days
        
        # Preserve HomeIQ extensions in extra
        if trigger.device_id or trigger.area_id:
            trigger_data["extra"] = {}
            if trigger.device_id:
                trigger_data["extra"]["device_id"] = trigger.device_id
            if trigger.area_id:
                trigger_data["extra"]["area_id"] = trigger.area_id
        
        # Merge with existing extra
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
        
        # Preserve HomeIQ extensions in extra
        if condition.device_id or condition.area_id:
            condition_data["extra"] = {}
            if condition.device_id:
                condition_data["extra"]["device_id"] = condition.device_id
            if condition.area_id:
                condition_data["extra"]["area_id"] = condition.area_id
        
        # Merge with existing extra
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
        if action.target:
            action_data["target"] = action.target
        if action.data:
            action_data["data"] = action.data
        if action.choose:
            action_data["choose"] = action.choose
        if action.repeat:
            action_data["repeat"] = action.repeat
        if action.parallel:
            action_data["parallel"] = action.parallel
        if action.sequence:
            action_data["sequence"] = action.sequence
        if action.error:
            action_data["error"] = action.error
        elif action.continue_on_error is not None:
            action_data["continue_on_error"] = action.continue_on_error
        
        # Preserve HomeIQ extensions in extra
        if action.energy_impact_w is not None:
            action_data["extra"] = {"energy_impact_w": action.energy_impact_w}
        
        # Merge with existing extra
        if action.extra:
            action_data.setdefault("extra", {}).update(action.extra)
        
        return ActionSpec(**action_data)

