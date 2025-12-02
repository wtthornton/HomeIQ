"""
Tag Determination Utilities for Automations

Automatically determines appropriate tags for automations based on
their content, enabling better organization and filtering.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def determine_automation_tags(
    yaml_data: dict[str, Any],
    suggestion: dict[str, Any] | None = None
) -> list[str]:
    """
    Determine appropriate tags for an automation based on its content.
    
    Tags help organize and filter automations in Home Assistant.
    
    Standard tags:
    - ai-generated: All AI-generated automations
    - energy: Energy management (lights, climate, power)
    - security: Security and safety (locks, alarms, cameras)
    - comfort: Comfort and convenience (climate, lighting scenes)
    - convenience: Convenience features (notifications, reminders)
    - presence: Presence-based automations (motion, occupancy)
    - time-based: Time-scheduled automations
    - climate: Climate control
    - lighting: Lighting control
    
    Args:
        yaml_data: Parsed automation YAML data
        suggestion: Optional suggestion data for additional context
        
    Returns:
        List of tags
    """
    tags = set()
    
    # Always add ai-generated tag
    tags.add("ai-generated")
    
    # Analyze triggers
    triggers = yaml_data.get("trigger", [])
    for trigger in triggers:
        if not isinstance(trigger, dict):
            continue
        
        platform = trigger.get("platform", "")
        entity_id = trigger.get("entity_id", "")
        
        # Time-based triggers
        if platform in ["time", "time_pattern", "sun"]:
            tags.add("time-based")
        
        # Presence-based triggers
        if isinstance(entity_id, str):
            entity_lower = entity_id.lower()
            if any(keyword in entity_lower for keyword in ["motion", "presence", "occupancy"]):
                tags.add("presence")
            if any(keyword in entity_lower for keyword in ["door", "window", "contact"]):
                tags.add("security")
    
    # Analyze actions
    actions = yaml_data.get("action", [])
    for action in actions:
        if not isinstance(action, dict):
            continue
        
        service = action.get("service", "")
        entity_id = action.get("entity_id", "")
        target = action.get("target", {})
        
        # Extract entity_id from target if present
        if isinstance(target, dict) and "entity_id" in target:
            target_entity = target["entity_id"]
            if isinstance(target_entity, str):
                entity_id = target_entity
            elif isinstance(target_entity, list) and target_entity:
                entity_id = " ".join(target_entity)
        
        # Service-based tags
        service_lower = service.lower()
        
        # Security tags
        if any(keyword in service_lower for keyword in ["lock", "alarm", "security", "camera"]):
            tags.add("security")
        
        # Energy tags
        if any(keyword in service_lower for keyword in ["light", "switch", "power", "energy"]):
            tags.add("energy")
        
        # Climate tags
        if any(keyword in service_lower for keyword in ["climate", "thermostat", "temperature", "fan", "hvac"]):
            tags.add("climate")
            tags.add("comfort")
        
        # Lighting tags
        if "light" in service_lower:
            tags.add("lighting")
        
        # Notification tags
        if "notify" in service_lower:
            tags.add("convenience")
        
        # Entity-based tags
        if isinstance(entity_id, str):
            entity_lower = entity_id.lower()
            
            # Security entities
            if any(keyword in entity_lower for keyword in ["lock", "alarm", "security", "camera"]):
                tags.add("security")
            
            # Climate entities
            if any(keyword in entity_lower for keyword in ["climate", "thermostat", "fan", "hvac"]):
                tags.add("climate")
                tags.add("comfort")
            
            # Lighting entities
            if "light" in entity_lower:
                tags.add("lighting")
            
            # Energy entities
            if any(keyword in entity_lower for keyword in ["power", "energy", "consumption"]):
                tags.add("energy")
    
    # Analyze description for additional context
    description = yaml_data.get("description", "")
    if description:
        desc_lower = description.lower()
        
        # Security keywords
        if any(keyword in desc_lower for keyword in ["security", "lock", "alarm", "protect", "safe"]):
            tags.add("security")
        
        # Energy keywords
        if any(keyword in desc_lower for keyword in ["energy", "power", "save", "efficient"]):
            tags.add("energy")
        
        # Comfort keywords
        if any(keyword in desc_lower for keyword in ["comfort", "cozy", "temperature", "warm", "cool"]):
            tags.add("comfort")
        
        # Convenience keywords
        if any(keyword in desc_lower for keyword in ["remind", "notify", "alert", "convenient"]):
            tags.add("convenience")
    
    # Ensure at least one category tag (besides ai-generated)
    category_tags = tags - {"ai-generated", "time-based", "presence"}
    if not category_tags:
        # Default to convenience if no specific category detected
        tags.add("convenience")
    
    return sorted(list(tags))


def add_tags_to_automation(
    yaml_data: dict[str, Any],
    suggestion: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Add tags to automation YAML.
    
    Args:
        yaml_data: Parsed automation YAML data
        suggestion: Optional suggestion data for additional context
        
    Returns:
        YAML data with tags added
    """
    try:
        # Skip if tags already present
        if "tags" in yaml_data and yaml_data["tags"]:
            logger.debug("Tags already present, skipping determination")
            return yaml_data
        
        # Determine tags
        tags = determine_automation_tags(yaml_data, suggestion)
        
        # Add to YAML
        yaml_data["tags"] = tags
        logger.debug(f"Added tags: {', '.join(tags)}")
        
        return yaml_data
    
    except Exception as e:
        logger.debug(f"Could not add tags: {e}")
        return yaml_data

