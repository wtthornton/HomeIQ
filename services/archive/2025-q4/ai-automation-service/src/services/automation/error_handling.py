"""
Error Handling Utilities for Automation Actions

Adds error handling to automation actions to prevent cascading failures.
Supports both simple error handling (error: "continue") and advanced choose blocks
for conditional error handling with fallback actions.
"""

import logging
from typing import Any, Union

from ...contracts.models import Action

logger = logging.getLogger(__name__)


def add_error_handling_to_actions(
    actions: list[Action],
    critical_action_indices: set[int] | None = None,
    use_choose_blocks: bool = False
) -> list[Union[Action, dict[str, Any]]]:
    """
    Add error handling to non-critical actions.
    
    Non-critical actions are wrapped with error: "continue" (or continue_on_error: true)
    to prevent single action failures from breaking entire automation sequences.
    
    Optionally uses choose blocks for conditional error handling with fallback actions.
    
    Critical actions (e.g., security, safety) are left without error handling
    so failures are immediately detected.
    
    Args:
        actions: List of actions to process
        critical_action_indices: Set of action indices that are critical (0-based)
                                 If None, auto-detect critical actions
        use_choose_blocks: If True, use choose blocks for sophisticated error handling
                          If False, use simple error: "continue" (default)
    
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
            if use_choose_blocks and _should_use_choose_block(action):
                enhanced_action = _add_choose_block_error_handling(action)
            else:
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
    
    Sets error: "continue" (or continue_on_error: true) to allow automation
    to continue if this action fails.
    
    Args:
        action: Action to add error handling to
    
    Returns:
        Action with error handling applied
    """
    # If action already has error field set, don't override
    if action.error is not None or getattr(action, 'continue_on_error', None) is not None:
        return action
    
    # Create new action with error handling
    # Use continue_on_error for better HA 2025 compatibility
    action_dict = action.model_dump(exclude_none=True)
    action_dict["continue_on_error"] = True
    
    return Action(**action_dict)


def _should_use_choose_block(action: Action) -> bool:
    """
    Determine if action should use choose block for error handling.
    
    Choose blocks are used for actions that:
    - Have entity_id targets (can check availability)
    - Are service calls (not sequences or other complex actions)
    - Would benefit from fallback behavior
    
    Args:
        action: Action to evaluate
    
    Returns:
        True if choose block should be used, False otherwise
    """
    # Only use choose blocks for service calls with entity targets
    if not action.service:
        return False
    
    # Must have entity_id or target to check availability
    if not action.entity_id and not getattr(action, 'target', None):
        return False
    
    # Don't use choose blocks for already complex actions
    if hasattr(action, 'choose') or hasattr(action, 'sequence'):
        return False
    
    return True


def _add_choose_block_error_handling(action: Action) -> dict[str, Any]:
    """
    Add choose block error handling to an action.
    
    Wraps action in a choose block that:
    1. Checks entity availability before executing
    2. Executes action if entity is available
    3. Falls back to logging/notification if entity unavailable
    
    Args:
        action: Action to wrap
    
    Returns:
        Dictionary representing choose block action
    """
    action_dict = action.model_dump(exclude_none=True)
    
    # Extract entity_id for availability check
    entity_id = None
    if action.entity_id:
        if isinstance(action.entity_id, str):
            entity_id = action.entity_id
        elif isinstance(action.entity_id, list) and action.entity_id:
            entity_id = action.entity_id[0]  # Use first entity for check
    elif hasattr(action, 'target') and action.target:
        target = action.target
        if isinstance(target, dict):
            target_entity_id = target.get('entity_id')
            if target_entity_id:
                if isinstance(target_entity_id, str):
                    entity_id = target_entity_id
                elif isinstance(target_entity_id, list) and target_entity_id:
                    entity_id = target_entity_id[0]
    
    # Build choose block
    choose_block: dict[str, Any] = {
        "choose": []
    }
    
    # Main action branch (entity available)
    if entity_id:
        choose_block["choose"].append({
            "conditions": [
                {
                    "condition": "template",
                    "value_template": (
                        f"{{{{ states('{entity_id}') not in ['unavailable', 'unknown'] }}}}"
                    )
                }
            ],
            "sequence": [action_dict]
        })
    else:
        # No entity to check, just execute with error handling
        action_dict["continue_on_error"] = True
        return action_dict
    
    # Fallback branch (entity unavailable) - log and continue
    choose_block["choose"].append({
        "conditions": [
            {
                "condition": "template",
                "value_template": (
                    f"{{{{ states('{entity_id}') in ['unavailable', 'unknown'] }}}}"
                )
            }
        ],
        "sequence": [
            {
                "service": "system_log.write",
                "data": {
                    "message": f"Automation action skipped: {entity_id} is unavailable",
                    "level": "warning"
                },
                "continue_on_error": True
            }
        ]
    })
    
    # Default: execute action with error handling (fallback)
    choose_block["default"] = [
        {
            **action_dict,
            "continue_on_error": True
        }
    ]
    
    logger.debug(f"Wrapped action in choose block for error handling: {action.service}")
    return choose_block

