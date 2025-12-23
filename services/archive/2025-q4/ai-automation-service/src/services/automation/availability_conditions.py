"""
Availability Condition Utilities for Automation

Adds availability checks to automations to prevent failures when entities are unavailable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_entity_ids_from_yaml(yaml_data: dict[str, Any]) -> set[str]:
    """
    Extract all entity IDs from automation YAML.
    
    Searches through triggers, conditions, and actions to find all entity references.
    
    Args:
        yaml_data: Parsed YAML automation data
        
    Returns:
        Set of entity IDs found in the automation
    """
    entity_ids = set()
    
    # Extract from triggers
    triggers = yaml_data.get("trigger", [])
    if isinstance(triggers, list):
        for trigger in triggers:
            if isinstance(trigger, dict):
                entity_id = trigger.get("entity_id")
                if entity_id:
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)
    
    # Extract from conditions
    conditions = yaml_data.get("condition", [])
    if isinstance(conditions, list):
        for condition in conditions:
            if isinstance(condition, dict):
                entity_id = condition.get("entity_id")
                if entity_id:
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)
    
    # Extract from actions
    actions = yaml_data.get("action", [])
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict):
                # Check target.entity_id
                target = action.get("target", {})
                if isinstance(target, dict):
                    target_entity_id = target.get("entity_id")
                    if target_entity_id:
                        if isinstance(target_entity_id, str):
                            entity_ids.add(target_entity_id)
                        elif isinstance(target_entity_id, list):
                            entity_ids.update(target_entity_id)
                
                # Check direct entity_id in action
                entity_id = action.get("entity_id")
                if entity_id:
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)
                
                # Recursively check nested structures (sequence, choose, parallel, etc.)
                entity_ids.update(_extract_entities_from_nested_action(action))
    
    return entity_ids


def _extract_entities_from_nested_action(action: dict[str, Any]) -> set[str]:
    """Extract entity IDs from nested action structures (sequence, choose, parallel, etc.)."""
    entity_ids = set()
    
    # Check sequence
    sequence = action.get("sequence", [])
    if isinstance(sequence, list):
        for item in sequence:
            if isinstance(item, dict):
                entity_id = item.get("entity_id")
                if entity_id:
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)
                # Check target in sequence items
                target = item.get("target", {})
                if isinstance(target, dict):
                    target_entity_id = target.get("entity_id")
                    if target_entity_id:
                        if isinstance(target_entity_id, str):
                            entity_ids.add(target_entity_id)
                        elif isinstance(target_entity_id, list):
                            entity_ids.update(target_entity_id)
    
    # Check choose
    choose = action.get("choose", [])
    if isinstance(choose, list):
        for choice in choose:
            if isinstance(choice, dict):
                # Check conditions in choice
                conditions = choice.get("conditions", [])
                if isinstance(conditions, list):
                    for condition in conditions:
                        if isinstance(condition, dict):
                            entity_id = condition.get("entity_id")
                            if entity_id:
                                if isinstance(entity_id, str):
                                    entity_ids.add(entity_id)
                                elif isinstance(entity_id, list):
                                    entity_ids.update(entity_id)
                # Check actions in choice
                actions = choice.get("sequence", [])
                if isinstance(actions, list):
                    for item in actions:
                        if isinstance(item, dict):
                            entity_id = item.get("entity_id")
                            if entity_id:
                                if isinstance(entity_id, str):
                                    entity_ids.add(entity_id)
                                elif isinstance(entity_id, list):
                                    entity_ids.update(entity_id)
    
    # Check parallel
    parallel = action.get("parallel", [])
    if isinstance(parallel, list):
        for item in parallel:
            if isinstance(item, dict):
                entity_id = item.get("entity_id")
                if entity_id:
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)
    
    return entity_ids


def add_availability_conditions(
    yaml_data: dict[str, Any],
    entity_ids: set[str] | None = None
) -> dict[str, Any]:
    """
    Add availability conditions to automation YAML.
    
    Adds template conditions that check entities are not "unavailable" or "unknown"
    before using them in the automation. This prevents automation failures when
    entities go offline.
    
    Args:
        yaml_data: Parsed YAML automation data
        entity_ids: Optional set of entity IDs to check. If None, extracts from yaml_data.
        
    Returns:
        Modified YAML data with availability conditions added
    """
    if entity_ids is None:
        entity_ids = extract_entity_ids_from_yaml(yaml_data)
    
    if not entity_ids:
        logger.debug("No entities found to add availability checks")
        return yaml_data
    
    # Get existing conditions or create new list
    conditions = yaml_data.get("condition", [])
    if not isinstance(conditions, list):
        conditions = []
    
    # Create availability conditions for each entity
    # Use template condition to check state is not unavailable/unknown
    availability_conditions = []
    for entity_id in sorted(entity_ids):  # Sort for deterministic output
        # Create template condition that checks entity is not unavailable/unknown
        availability_condition = {
            "condition": "template",
            "value_template": (
                f"{{{{ states('{entity_id}') not in ['unavailable', 'unknown'] }}}}"
            )
        }
        availability_conditions.append(availability_condition)
        logger.debug(f"Added availability check for entity: {entity_id}")
    
    # Prepend availability conditions to existing conditions
    # This ensures availability is checked before other conditions
    yaml_data["condition"] = availability_conditions + conditions
    
    logger.info(f"Added {len(availability_conditions)} availability condition(s) to automation")
    
    return yaml_data

