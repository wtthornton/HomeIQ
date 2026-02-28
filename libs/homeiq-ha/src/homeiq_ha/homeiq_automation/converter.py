"""
HomeIQ JSON to AutomationSpec Converter

Converts HomeIQ JSON Automation format to AutomationSpec for YAML rendering.
Preserves HomeIQ metadata in AutomationSpec.extra for later retrieval.
"""

import logging
from typing import Any

from homeiq_ha.yaml_validation_service.schema import (
    ActionSpec,
    AutomationSpec,
    ConditionSpec,
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

# Fields copied from Target model to YAML dict when truthy
_TARGET_FIELDS = ("area_id", "floor_id", "labels", "device_id", "entity_id")

# Optional HomeIQ metadata attrs that use model_dump()
_OPTIONAL_MODEL_EXTRAS = ("pattern_context", "safety_checks", "energy_impact")

# Action fields copied directly when truthy
_ACTION_DIRECT_FIELDS = (
    "service", "scene", "delay", "data",
    "choose", "repeat", "parallel", "sequence", "error",
)

# Condition fields copied when not None
_CONDITION_FIELDS = ("entity_id", "state", "above", "below")


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
        triggers = [self._convert_trigger(t) for t in homeiq_automation.triggers]
        conditions = (
            [self._convert_condition(c) for c in homeiq_automation.conditions]
            if homeiq_automation.conditions else None
        )
        actions = [self._convert_action(a) for a in homeiq_automation.actions]

        extra = self._build_extra(homeiq_automation)

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

        logger.debug("Converted HomeIQ automation '%s' to AutomationSpec", homeiq_automation.alias)
        return spec

    def _build_extra(self, automation: HomeIQAutomation) -> dict[str, Any]:
        """Build the extra metadata dict from a HomeIQ automation."""
        extra: dict[str, Any] = {
            "homeiq_version": automation.version,
            "homeiq_metadata": automation.homeiq_metadata.model_dump(),
            "device_context": automation.device_context.model_dump(),
            "area_context": automation.area_context,
        }

        for attr in _OPTIONAL_MODEL_EXTRAS:
            val = getattr(automation, attr, None)
            if val:
                extra[attr] = val.model_dump()

        if automation.dependencies:
            extra["dependencies"] = automation.dependencies

        return extra

    def _target_to_dict(self, target: Target) -> dict[str, Any]:
        """Convert Target model to YAML-compatible dict."""
        return {
            field: getattr(target, field)
            for field in _TARGET_FIELDS
            if getattr(target, field)
        }

    def _map_trigger_config_to_yaml(
        self,
        _platform: str,
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

    def _merge_target_and_extra(
        self, data: dict[str, Any], target: Target | None, extra: dict[str, Any] | None
    ) -> None:
        """Merge target and extra fields into the data dict in-place."""
        if target:
            target_dict = self._target_to_dict(target)
            if target_dict:
                data.setdefault("extra", {})["target"] = target_dict
        if extra:
            data.setdefault("extra", {}).update(extra)

    def _convert_condition(self, condition: HomeIQCondition) -> ConditionSpec:
        """Convert HomeIQ condition to ConditionSpec."""
        condition_data: dict[str, Any] = {"condition": condition.condition}

        for field in _CONDITION_FIELDS:
            val = getattr(condition, field)
            if val is not None:
                condition_data[field] = val

        self._merge_target_and_extra(condition_data, condition.target, condition.extra)
        return ConditionSpec(**condition_data)

    def _convert_action(self, action: HomeIQAction) -> ActionSpec:
        """Convert HomeIQ action to ActionSpec."""
        action_data: dict[str, Any] = {}

        for field in _ACTION_DIRECT_FIELDS:
            val = getattr(action, field, None)
            if val:
                action_data[field] = val

        # Enhanced targeting (top-level, not in extra)
        if action.target:
            target_dict = self._target_to_dict(action.target)
            if target_dict:
                action_data["target"] = target_dict

        # HomeIQ extensions (preserve in extra)
        if action.energy_impact_w is not None:
            action_data.setdefault("extra", {})["energy_impact_w"] = action.energy_impact_w

        if action.extra:
            action_data.setdefault("extra", {}).update(action.extra)

        return ActionSpec(**action_data)

