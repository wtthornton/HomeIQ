"""
Description Enhancement Utilities for Automations

Enhances automation descriptions with full context including triggers,
behavior, time ranges, and device friendly names.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def enhance_automation_description(
    yaml_data: dict[str, Any],
    entity_names: dict[str, str] | None = None
) -> dict[str, Any]:
    """
    Enhance automation description with full context.
    
    Adds or improves description to include:
    - Trigger conditions (what starts the automation)
    - Expected behavior (what happens)
    - Time ranges or conditions (when it happens)
    - Device friendly names (not just entity IDs)
    
    Args:
        yaml_data: Parsed automation YAML data
        entity_names: Optional mapping of entity_id -> friendly_name
        
    Returns:
        YAML data with enhanced description
    """
    try:
        # Get existing description
        existing_desc = yaml_data.get("description", "")
        
        # If description is already comprehensive, don't override
        if existing_desc and len(existing_desc) > 100:
            logger.debug("Description already comprehensive, skipping enhancement")
            return yaml_data
        
        # Build enhanced description
        triggers = yaml_data.get("trigger", [])
        conditions = yaml_data.get("condition", [])
        actions = yaml_data.get("action", [])
        
        # Describe what happens (actions)
        action_desc = _describe_actions(actions, entity_names)
        
        # Describe when it happens (triggers)
        trigger_desc = _describe_triggers(triggers, entity_names)
        
        # Describe conditions (if any)
        condition_desc = _describe_conditions(conditions, entity_names)
        
        # Build complete description
        parts = []
        if action_desc:
            parts.append(action_desc)
        if trigger_desc:
            parts.append(f"triggered by {trigger_desc}")
        if condition_desc:
            parts.append(f"when {condition_desc}")
        
        enhanced_desc = " ".join(parts)
        
        # Only update if we generated something meaningful
        if enhanced_desc and len(enhanced_desc) > 20:
            yaml_data["description"] = enhanced_desc
            logger.debug(f"Enhanced description: {enhanced_desc[:100]}...")
        
        return yaml_data
    
    except Exception as e:
        logger.debug(f"Could not enhance description: {e}")
        return yaml_data


def _describe_actions(
    actions: list[dict[str, Any]],
    entity_names: dict[str, str] | None
) -> str:
    """Describe automation actions in natural language."""
    if not actions:
        return ""
    
    action_parts = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        
        service = action.get("service", "")
        if not service:
            continue
        
        # Extract entity or target
        entity_desc = _get_entity_description(action, entity_names)
        
        # Describe the action
        if "turn_on" in service:
            action_parts.append(f"turn on {entity_desc}")
        elif "turn_off" in service:
            action_parts.append(f"turn off {entity_desc}")
        elif "toggle" in service:
            action_parts.append(f"toggle {entity_desc}")
        elif "set_temperature" in service:
            action_parts.append(f"set temperature for {entity_desc}")
        elif "lock" in service:
            action_parts.append(f"lock {entity_desc}")
        elif "unlock" in service:
            action_parts.append(f"unlock {entity_desc}")
        elif "notify" in service:
            action_parts.append("send notification")
        else:
            action_parts.append(f"{service.split('.')[-1]} {entity_desc}")
    
    if not action_parts:
        return ""
    
    # Join with commas and "and" for last item
    if len(action_parts) == 1:
        return action_parts[0]
    elif len(action_parts) == 2:
        return f"{action_parts[0]} and {action_parts[1]}"
    else:
        return ", ".join(action_parts[:-1]) + f", and {action_parts[-1]}"


def _describe_triggers(
    triggers: list[dict[str, Any]],
    entity_names: dict[str, str] | None
) -> str:
    """Describe automation triggers in natural language."""
    if not triggers:
        return ""
    
    trigger_parts = []
    for trigger in triggers:
        if not isinstance(trigger, dict):
            continue
        
        platform = trigger.get("platform", "")
        
        if platform == "time":
            at_time = trigger.get("at")
            if at_time:
                trigger_parts.append(f"time at {at_time}")
        elif platform == "time_pattern":
            trigger_parts.append("time pattern")
        elif platform == "sun":
            event = trigger.get("event", "")
            trigger_parts.append(f"{event}")
        elif platform == "state":
            entity_id = trigger.get("entity_id", "")
            entity_name = _get_friendly_name(entity_id, entity_names)
            to_state = trigger.get("to", "")
            if to_state:
                trigger_parts.append(f"{entity_name} changing to {to_state}")
            else:
                trigger_parts.append(f"{entity_name} state change")
        elif platform == "numeric_state":
            entity_id = trigger.get("entity_id", "")
            entity_name = _get_friendly_name(entity_id, entity_names)
            above = trigger.get("above")
            below = trigger.get("below")
            if above:
                trigger_parts.append(f"{entity_name} above {above}")
            elif below:
                trigger_parts.append(f"{entity_name} below {below}")
            else:
                trigger_parts.append(f"{entity_name} numeric change")
        elif platform == "event":
            event_type = trigger.get("event_type", "event")
            trigger_parts.append(f"{event_type}")
        else:
            trigger_parts.append(f"{platform} trigger")
    
    if not trigger_parts:
        return ""
    
    # Join with "or" for multiple triggers
    if len(trigger_parts) == 1:
        return trigger_parts[0]
    else:
        return " or ".join(trigger_parts)


def _describe_conditions(
    conditions: list[dict[str, Any]],
    entity_names: dict[str, str] | None
) -> str:
    """Describe automation conditions in natural language."""
    if not conditions:
        return ""
    
    condition_parts = []
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        
        condition_type = condition.get("condition", "")
        
        if condition_type == "state":
            entity_id = condition.get("entity_id", "")
            entity_name = _get_friendly_name(entity_id, entity_names)
            state = condition.get("state", "")
            if state:
                condition_parts.append(f"{entity_name} is {state}")
        elif condition_type == "time":
            after = condition.get("after")
            before = condition.get("before")
            if after and before:
                condition_parts.append(f"between {after} and {before}")
            elif after:
                condition_parts.append(f"after {after}")
            elif before:
                condition_parts.append(f"before {before}")
        elif condition_type == "numeric_state":
            entity_id = condition.get("entity_id", "")
            entity_name = _get_friendly_name(entity_id, entity_names)
            above = condition.get("above")
            below = condition.get("below")
            if above:
                condition_parts.append(f"{entity_name} above {above}")
            elif below:
                condition_parts.append(f"{entity_name} below {below}")
        elif condition_type == "template":
            condition_parts.append("custom condition")
        else:
            condition_parts.append(f"{condition_type} condition")
    
    if not condition_parts:
        return ""
    
    # Join with "and" for multiple conditions
    return " and ".join(condition_parts)


def _get_entity_description(
    action: dict[str, Any],
    entity_names: dict[str, str] | None
) -> str:
    """Get entity description from action (entity_id or target)."""
    # Check target first
    target = action.get("target")
    if target and isinstance(target, dict):
        if "area_id" in target:
            return f"devices in {target['area_id']}"
        elif "device_id" in target:
            return f"device {target['device_id']}"
        elif "entity_id" in target:
            entity_id = target["entity_id"]
            if isinstance(entity_id, list):
                if len(entity_id) == 1:
                    return _get_friendly_name(entity_id[0], entity_names)
                else:
                    return f"{len(entity_id)} devices"
            else:
                return _get_friendly_name(entity_id, entity_names)
    
    # Check entity_id directly
    entity_id = action.get("entity_id")
    if entity_id:
        if isinstance(entity_id, list):
            if len(entity_id) == 1:
                return _get_friendly_name(entity_id[0], entity_names)
            else:
                return f"{len(entity_id)} devices"
        else:
            return _get_friendly_name(entity_id, entity_names)
    
    return "device"


def _get_friendly_name(
    entity_id: str | list[str],
    entity_names: dict[str, str] | None
) -> str:
    """Get friendly name for entity ID."""
    if isinstance(entity_id, list):
        if len(entity_id) == 1:
            entity_id = entity_id[0]
        else:
            return f"{len(entity_id)} devices"
    
    if not isinstance(entity_id, str):
        return "device"
    
    # Try to get friendly name from mapping
    if entity_names and entity_id in entity_names:
        return entity_names[entity_id]
    
    # Extract friendly name from entity ID
    # e.g., "light.kitchen_ceiling" -> "kitchen ceiling"
    parts = entity_id.split(".", 1)
    if len(parts) == 2:
        name = parts[1].replace("_", " ").title()
        return name
    
    return entity_id

