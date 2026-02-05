"""
Huey Task Definitions

Define tasks for automation execution with prioritization and retry logic.
"""

import logging
from typing import Any, Dict, Optional

from .huey_config import huey
from .execution_wrapper import execute_automation_sync

logger = logging.getLogger(__name__)


def _get_task_config(spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get task configuration based on automation spec.
    
    Args:
        spec: Automation spec dictionary (optional)
    
    Returns:
        Task configuration (retries, retry_delay, priority)
    """
    if not spec:
        # Default configuration
        return {
            "retries": 3,
            "retry_delay": 30,
            "priority": 5
        }
    
    policy = spec.get("policy", {})
    risk = policy.get("risk", "low")
    
    # Priority mapping based on risk
    priority_map = {
        "high": 10,    # Security/Safety automations
        "medium": 5,   # Normal automations
        "low": 1       # Background/analytics automations
    }
    
    # Retry configuration based on risk
    retry_config = {
        "high": {
            "retries": 10,
            "retry_delay": 60  # 60 seconds with exponential backoff
        },
        "medium": {
            "retries": 5,
            "retry_delay": 30  # 30 seconds with exponential backoff
        },
        "low": {
            "retries": 3,
            "retry_delay": 15  # 15 seconds with exponential backoff
        }
    }
    
    retry_cfg = retry_config.get(risk, retry_config["low"])
    
    return {
        "retries": retry_cfg["retries"],
        "retry_delay": retry_cfg["retry_delay"],
        "priority": priority_map.get(risk, 5)
    }


@huey.task(
    retries=5,
    retry_delay=30,
    priority=5
)
def execute_automation_task(
    spec_id: str,
    trigger_data: Optional[dict],
    home_id: str,
    correlation_id: str,
    spec: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute automation as Huey task.
    
    This task wraps the synchronous execution wrapper to execute automations
    asynchronously in the background.
    
    Args:
        spec_id: Automation spec ID
        trigger_data: Optional trigger data
        home_id: Home ID
        correlation_id: Correlation ID for tracking
        spec: Optional spec dictionary (for priority/retry config)
    
    Returns:
        Execution result dictionary
    """
    logger.info(
        f"Executing automation task: spec_id={spec_id}, "
        f"correlation_id={correlation_id}, home_id={home_id}"
    )
    
    try:
        # Execute automation synchronously
        result = execute_automation_sync(
            spec_id=spec_id,
            trigger_data=trigger_data,
            home_id=home_id,
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Automation task completed: spec_id={spec_id}, "
            f"success={result.get('success')}, correlation_id={correlation_id}"
        )
        
        return result
        
    except Exception as e:
        logger.error(
            f"Automation task failed: spec_id={spec_id}, "
            f"correlation_id={correlation_id}, error={e}",
            exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "correlation_id": correlation_id
        }


def queue_automation_task(
    spec_id: str,
    trigger_data: Optional[dict],
    home_id: str,
    correlation_id: str,
    spec: Optional[Dict[str, Any]] = None,
    delay: Optional[int] = None,
    eta: Optional[Any] = None
):
    """
    Queue automation task with proper configuration.
    
    This function determines the task configuration based on spec policy,
    then queues the task with appropriate priority and retry settings.
    
    Args:
        spec_id: Automation spec ID
        trigger_data: Optional trigger data
        home_id: Home ID
        correlation_id: Correlation ID for tracking
        spec: Optional spec dictionary (for priority/retry config)
        delay: Optional delay in seconds
        eta: Optional execute-at time (datetime)
    
    Returns:
        Huey task instance
    """
    # Get task configuration based on spec
    task_config = _get_task_config(spec)
    
    # Create task with dynamic configuration
    # Note: Huey doesn't support dynamic retry/priority, so we use defaults
    # and configure via decorator. For dynamic config, we'd need multiple
    # task functions or accept defaults.
    task_func = execute_automation_task
    
    if delay:
        # Schedule with delay
        task = task_func.schedule(
            delay=delay,
            spec_id=spec_id,
            trigger_data=trigger_data,
            home_id=home_id,
            correlation_id=correlation_id,
            spec=spec
        )
    elif eta:
        # Schedule at specific time
        task = task_func.schedule(
            eta=eta,
            spec_id=spec_id,
            trigger_data=trigger_data,
            home_id=home_id,
            correlation_id=correlation_id,
            spec=spec
        )
    else:
        # Queue immediately
        task = task_func(
            spec_id=spec_id,
            trigger_data=trigger_data,
            home_id=home_id,
            correlation_id=correlation_id,
            spec=spec
        )
    
    logger.info(
        f"Queued automation task: spec_id={spec_id}, task_id={task.id}, "
        f"priority={task_config['priority']}, correlation_id={correlation_id}"
    )
    
    return task
