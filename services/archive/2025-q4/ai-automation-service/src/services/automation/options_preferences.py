"""
Options-Based Preference Detection for Automations

Extracts and uses entity options to inform automation suggestions
and respect user-configured preferences.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_entity_preferences(
    entities: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """
    Extract user preferences from entity options.
    
    Entity options contain user-configured defaults and preferences:
    - Light: default_brightness, preferred_color, transition_time
    - Climate: target_temperature, mode_preference
    - Media Player: default_volume, source_preference
    
    Args:
        entities: List of entity dictionaries with options
        
    Returns:
        Dictionary mapping entity_id -> preferences
    """
    preferences = {}
    
    for entity in entities:
        entity_id = entity.get("entity_id")
        options = entity.get("options")
        
        if not entity_id or not options or not isinstance(options, dict):
            continue
        
        # Extract domain-specific preferences
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        
        entity_prefs = {}
        
        if domain == "light":
            # Light preferences
            if "default_brightness" in options:
                entity_prefs["default_brightness"] = options["default_brightness"]
            if "preferred_color" in options:
                entity_prefs["preferred_color"] = options["preferred_color"]
            if "transition_time" in options:
                entity_prefs["transition_time"] = options["transition_time"]
        
        elif domain == "climate":
            # Climate preferences
            if "target_temperature" in options:
                entity_prefs["target_temperature"] = options["target_temperature"]
            if "mode_preference" in options:
                entity_prefs["mode_preference"] = options["mode_preference"]
        
        elif domain == "media_player":
            # Media player preferences
            if "default_volume" in options:
                entity_prefs["default_volume"] = options["default_volume"]
            if "source_preference" in options:
                entity_prefs["source_preference"] = options["source_preference"]
        
        elif domain == "fan":
            # Fan preferences
            if "default_speed" in options:
                entity_prefs["default_speed"] = options["default_speed"]
        
        elif domain == "cover":
            # Cover preferences
            if "default_position" in options:
                entity_prefs["default_position"] = options["default_position"]
        
        if entity_prefs:
            preferences[entity_id] = entity_prefs
    
    logger.debug(f"Extracted preferences for {len(preferences)} entities")
    return preferences


def apply_preferences_to_action(
    action: dict[str, Any],
    preferences: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """
    Apply user preferences to an automation action.
    
    Modifies action data to respect user-configured defaults from options.
    
    Args:
        action: Action dictionary
        preferences: Entity preferences from extract_entity_preferences()
        
    Returns:
        Action with preferences applied
    """
    # Extract entity_id from action
    entity_id = action.get("entity_id")
    target = action.get("target", {})
    
    if isinstance(target, dict) and "entity_id" in target:
        target_entity = target["entity_id"]
        if isinstance(target_entity, str):
            entity_id = target_entity
        elif isinstance(target_entity, list) and target_entity:
            entity_id = target_entity[0]  # Use first entity for preferences
    
    if not entity_id or entity_id not in preferences:
        return action  # No preferences for this entity
    
    entity_prefs = preferences[entity_id]
    service = action.get("service", "")
    
    # Apply preferences based on service
    if "turn_on" in service:
        # Apply turn_on preferences
        if "data" not in action:
            action["data"] = {}
        
        # Light preferences
        if "default_brightness" in entity_prefs and "brightness" not in action["data"]:
            action["data"]["brightness"] = entity_prefs["default_brightness"]
            logger.debug(f"Applied default brightness {entity_prefs['default_brightness']} to {entity_id}")
        
        if "preferred_color" in entity_prefs and "rgb_color" not in action["data"]:
            action["data"]["rgb_color"] = entity_prefs["preferred_color"]
            logger.debug(f"Applied preferred color to {entity_id}")
        
        if "transition_time" in entity_prefs and "transition" not in action["data"]:
            action["data"]["transition"] = entity_prefs["transition_time"]
        
        # Media player preferences
        if "default_volume" in entity_prefs and "volume_level" not in action["data"]:
            action["data"]["volume_level"] = entity_prefs["default_volume"]
        
        # Fan preferences
        if "default_speed" in entity_prefs and "percentage" not in action["data"]:
            action["data"]["percentage"] = entity_prefs["default_speed"]
    
    elif "set_temperature" in service:
        # Apply climate preferences
        if "data" not in action:
            action["data"] = {}
        
        if "target_temperature" in entity_prefs and "temperature" not in action["data"]:
            action["data"]["temperature"] = entity_prefs["target_temperature"]
            logger.debug(f"Applied target temperature {entity_prefs['target_temperature']} to {entity_id}")
        
        if "mode_preference" in entity_prefs and "hvac_mode" not in action["data"]:
            action["data"]["hvac_mode"] = entity_prefs["mode_preference"]
    
    elif "set_cover_position" in service:
        # Apply cover preferences
        if "data" not in action:
            action["data"] = {}
        
        if "default_position" in entity_prefs and "position" not in action["data"]:
            action["data"]["position"] = entity_prefs["default_position"]
    
    return action


def enhance_entity_context_with_options(
    entities: list[dict[str, Any]]
) -> str:
    """
    Build enhanced entity context text including options/preferences.
    
    Creates human-readable text describing entity preferences for LLM prompts.
    
    Args:
        entities: List of entity dictionaries with options
        
    Returns:
        Formatted text describing entity preferences
    """
    preferences = extract_entity_preferences(entities)
    
    if not preferences:
        return ""
    
    context_lines = ["Entity Preferences (from options):"]
    
    for entity_id, prefs in preferences.items():
        # Find entity friendly name
        entity_name = entity_id
        for entity in entities:
            if entity.get("entity_id") == entity_id:
                entity_name = entity.get("friendly_name") or entity.get("name_by_user") or entity_id
                break
        
        pref_items = []
        for key, value in prefs.items():
            # Format preference nicely
            key_readable = key.replace("_", " ").title()
            pref_items.append(f"{key_readable}: {value}")
        
        if pref_items:
            context_lines.append(f"  - {entity_name} ({entity_id}): {', '.join(pref_items)}")
    
    return "\n".join(context_lines)


def apply_preferences_to_yaml(
    yaml_data: dict[str, Any],
    entities: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Apply user preferences to automation YAML.
    
    Modifies action data to respect user-configured defaults from entity options.
    
    Args:
        yaml_data: Parsed automation YAML data
        entities: List of entity dictionaries with options
        
    Returns:
        YAML data with preferences applied
    """
    try:
        preferences = extract_entity_preferences(entities)
        
        if not preferences:
            return yaml_data  # No preferences to apply
        
        actions = yaml_data.get("action", [])
        if not isinstance(actions, list):
            return yaml_data
        
        # Apply preferences to each action
        enhanced_actions = []
        for action in actions:
            if isinstance(action, dict):
                enhanced_action = apply_preferences_to_action(action, preferences)
                enhanced_actions.append(enhanced_action)
            else:
                enhanced_actions.append(action)
        
        yaml_data["action"] = enhanced_actions
        logger.debug(f"Applied preferences to {len(enhanced_actions)} actions")
        
        return yaml_data
    
    except Exception as e:
        logger.debug(f"Could not apply preferences: {e}")
        return yaml_data

