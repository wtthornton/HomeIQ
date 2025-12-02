"""
Error Handling Utilities for Automation Actions

Adds error handling to automation actions to prevent cascading failures.
"""

import logging
from typing import Any

from ...contracts.models import Action

logger = logging.getLogger(__name__)


def add_error_handling_to_actions(
    actions: list[Action],
    critical_action_indices: set[int] | None = None
) -> list[Action]:
    """
    Add error handling to non-critical actions.
    
    Non-critical actions are wrapped with error: "continue" to prevent
    single action failures from breaking entire automation sequences.
    
    Critical actions (e.g., security, safety) are left without error handling
    so failures are immediately detected.
    
    Args:
        actions: List of actions to process
        critical_action_indices: Set of action indices that are critical (0-based)
                                 If None, auto-detect critical actions
    
    Returns:
        List of actions with error handling applied
    """
    if critical_action_indices is None:
        critical_action_indices = _detect_critical_actions(actions)
    
    enhanced_actions = []
    for i, action in enumerate(actions):
        if i in critical_action_indices:
            # Critical action: no error handling (failures should stop automation)
            enhanced_actions.append(action)
        else:
            # Non-critical action: add error handling
            enhanced_action = _add_error_handling_to_action(action)
            enhanced_actions.append(enhanced_action)
    
    return enhanced_actions


def _detect_critical_actions(actions: list[Action]) -> set[int]:
    """
    Detect critical actions that should not have error handling.
    
    Critical actions include:
    - Security actions (locks, alarms)
    - Safety actions (emergency notifications)
    - Climate actions that could affect safety
    
    Args:
        actions: List of actions to analyze
    
    Returns:
        Set of critical action indices (0-based)
    """
    critical_indices = set()
    
    critical_keywords = [
        "lock", "alarm", "security", "emergency", "notify",
        "climate.set_temperature", "water_heater"
    ]
    
    for i, action in enumerate(actions):
        service_lower = action.service.lower()
        entity_id_lower = ""
        
        if action.entity_id:
            if isinstance(action.entity_id, str):
                entity_id_lower = action.entity_id.lower()
            elif isinstance(action.entity_id, list):
                entity_id_lower = " ".join(str(eid).lower() for eid in action.entity_id)
        
        combined_text = f"{service_lower} {entity_id_lower}".lower()
        
        # Check for critical keywords
        if any(keyword in combined_text for keyword in critical_keywords):
            critical_indices.add(i)
            logger.debug(f"Detected critical action at index {i}: {action.service}")
    
    return critical_indices


def _add_error_handling_to_action(action: Action) -> Action:
    """
    Add error handling to a single action.
    
    Sets error: "continue" to allow automation to continue if this action fails.
    
    Args:
        action: Action to add error handling to
    
    Returns:
        Action with error handling applied
    """
    # If action already has error field set, don't override
    if action.error is not None:
        return action
    
    # Create new action with error handling
    action_dict = action.model_dump(exclude_none=True)
    action_dict["error"] = "continue"
    
    return Action(**action_dict)

