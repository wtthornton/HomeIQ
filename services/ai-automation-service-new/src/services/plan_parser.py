"""
Structured Plan Parser

Epic 51, Story 51.8: Implement Structured Plan Generation

Parses structured JSON/object plans from LLM into AutomationSpec.
"""

import json
import logging
from typing import Any

from yaml_validation_service.schema import (
    ActionSpec,
    AutomationMode,
    AutomationSpec,
    ConditionSpec,
    MaxExceeded,
    TriggerSpec,
)

logger = logging.getLogger(__name__)


class PlanParser:
    """
    Parses structured JSON plans from LLM into AutomationSpec.
    
    Handles:
    - JSON parsing and validation
    - Type conversion (strings to enums, etc.)
    - Default value handling
    - Error recovery
    """

    def __init__(self):
        """Initialize plan parser."""
        pass

    def parse_plan(self, plan_json: str | dict[str, Any]) -> AutomationSpec:
        """
        Parse structured plan JSON into AutomationSpec.
        
        Args:
            plan_json: JSON string or dictionary containing automation plan
            
        Returns:
            AutomationSpec instance
            
        Raises:
            ValueError: If plan cannot be parsed or is invalid
        """
        try:
            # Parse JSON if string
            if isinstance(plan_json, str):
                # Try to extract JSON from markdown code blocks if present
                if "```" in plan_json:
                    # Extract JSON from code block
                    lines = plan_json.split("\n")
                    json_lines = []
                    in_code_block = False
                    for line in lines:
                        if line.strip().startswith("```"):
                            in_code_block = not in_code_block
                            continue
                        if in_code_block:
                            json_lines.append(line)
                    plan_json = "\n".join(json_lines)
                
                plan_dict = json.loads(plan_json)
            else:
                plan_dict = plan_json
            
            # Validate required fields
            if not isinstance(plan_dict, dict):
                raise ValueError("Plan must be a JSON object")
            
            # Parse alias (required)
            alias = plan_dict.get("alias") or plan_dict.get("name")
            if not alias:
                raise ValueError("Plan must contain 'alias' or 'name' field")
            
            # Parse description
            description = plan_dict.get("description", "")
            
            # Parse trigger
            trigger_data = plan_dict.get("trigger") or plan_dict.get("triggers", [])
            if not isinstance(trigger_data, list):
                trigger_data = [trigger_data]
            
            triggers = []
            for trigger_item in trigger_data:
                if isinstance(trigger_item, dict):
                    trigger = self._parse_trigger(trigger_item)
                    if trigger:
                        triggers.append(trigger)
            
            if not triggers:
                raise ValueError("Plan must contain at least one trigger")
            
            # Parse action
            action_data = plan_dict.get("action") or plan_dict.get("actions", [])
            if not isinstance(action_data, list):
                action_data = [action_data]
            
            actions = []
            for action_item in action_data:
                if isinstance(action_item, dict):
                    action = self._parse_action(action_item)
                    if action:
                        actions.append(action)
            
            if not actions:
                raise ValueError("Plan must contain at least one action")
            
            # Parse optional fields
            automation_id = plan_dict.get("id")
            initial_state = plan_dict.get("initial_state", True)
            mode_str = plan_dict.get("mode", "single")
            mode = self._parse_mode(mode_str)
            
            max_exceeded_str = plan_dict.get("max_exceeded")
            max_exceeded = self._parse_max_exceeded(max_exceeded_str) if max_exceeded_str else None
            
            # Parse conditions (optional)
            condition_data = plan_dict.get("condition") or plan_dict.get("conditions")
            conditions = None
            if condition_data:
                if not isinstance(condition_data, list):
                    condition_data = [condition_data]
                conditions = []
                for condition_item in condition_data:
                    if isinstance(condition_item, dict):
                        condition = self._parse_condition(condition_item)
                        if condition:
                            conditions.append(condition)
            
            # Parse tags (optional)
            tags = plan_dict.get("tags")
            if tags and not isinstance(tags, list):
                tags = [tags]
            
            # Create AutomationSpec
            spec = AutomationSpec(
                id=automation_id,
                alias=alias,
                description=description,
                initial_state=initial_state,
                mode=mode,
                trigger=triggers,
                condition=conditions,
                action=actions,
                max_exceeded=max_exceeded,
                tags=tags
            )
            
            logger.debug(f"Successfully parsed plan: {alias}")
            return spec
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in plan: {e}")
        except Exception as e:
            logger.error(f"Error parsing plan: {e}")
            raise ValueError(f"Failed to parse plan: {e}")

    def _parse_trigger(self, trigger_dict: dict[str, Any]) -> TriggerSpec | None:
        """Parse trigger dictionary into TriggerSpec."""
        try:
            platform = trigger_dict.get("platform") or trigger_dict.get("trigger")
            if not platform:
                return None
            
            # Create trigger with all fields
            trigger_data = {"platform": platform}
            
            # Copy all other fields
            for key, value in trigger_dict.items():
                if key not in ["platform", "trigger"]:
                    trigger_data[key] = value
            
            return TriggerSpec(**trigger_data)
        except Exception as e:
            logger.warning(f"Failed to parse trigger: {e}")
            return None

    def _parse_action(self, action_dict: dict[str, Any]) -> ActionSpec | None:
        """Parse action dictionary into ActionSpec."""
        try:
            service = action_dict.get("service") or action_dict.get("action")
            if not service:
                return None
            
            # Create action with all fields
            action_data = {"service": service}
            
            # Copy all other fields
            for key, value in action_dict.items():
                if key not in ["service", "action"]:
                    action_data[key] = value
            
            return ActionSpec(**action_data)
        except Exception as e:
            logger.warning(f"Failed to parse action: {e}")
            return None

    def _parse_condition(self, condition_dict: dict[str, Any]) -> ConditionSpec | None:
        """Parse condition dictionary into ConditionSpec."""
        try:
            condition_type = condition_dict.get("condition") or condition_dict.get("type")
            if not condition_type:
                return None
            
            # Create condition with all fields
            condition_data = {"condition": condition_type}
            
            # Copy all other fields
            for key, value in condition_dict.items():
                if key not in ["condition", "type"]:
                    condition_data[key] = value
            
            return ConditionSpec(**condition_data)
        except Exception as e:
            logger.warning(f"Failed to parse condition: {e}")
            return None

    def _parse_mode(self, mode_str: str) -> AutomationMode:
        """Parse mode string into AutomationMode enum."""
        mode_str = mode_str.lower().strip()
        mode_map = {
            "single": AutomationMode.SINGLE,
            "restart": AutomationMode.RESTART,
            "queued": AutomationMode.QUEUED,
            "parallel": AutomationMode.PARALLEL,
        }
        return mode_map.get(mode_str, AutomationMode.SINGLE)

    def _parse_max_exceeded(self, max_exceeded_str: str) -> MaxExceeded:
        """Parse max_exceeded string into MaxExceeded enum."""
        max_exceeded_str = max_exceeded_str.lower().strip()
        max_exceeded_map = {
            "silent": MaxExceeded.SILENT,
            "warning": MaxExceeded.WARNING,
            "error": MaxExceeded.ERROR,
        }
        return max_exceeded_map.get(max_exceeded_str, MaxExceeded.SILENT)

