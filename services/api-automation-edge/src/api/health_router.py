"""
Health Check Router
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Huey task queue (optional, imported if available)
try:
    from ..task_queue.huey_config import huey
    from ..task_queue.scheduler import get_scheduler
    HUEY_AVAILABLE = True
except ImportError:
    HUEY_AVAILABLE = False
    huey = None
    get_scheduler = None


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint with queue status.
    
    Returns:
        Health status including queue metrics
    """
    status: Dict[str, Any] = {
        "status": "healthy",
        "service": "api-automation-edge"
    }
    
    # Add queue status if Huey is available
    if HUEY_AVAILABLE and huey and settings.use_task_queue:
        try:
            # Get queue metrics
            pending_tasks = huey.pending()
            scheduled_tasks = huey.scheduled()
            
            pending_count = len(list(pending_tasks))
            scheduled_count = len(list(scheduled_tasks))
            
            # Get scheduler status
            scheduler = get_scheduler()
            registered_schedules = len(scheduler.registered_schedules) if scheduler else 0
            
            status["queue"] = {
                "enabled": True,
                "pending": pending_count,
                "scheduled": scheduled_count,
                "total": pending_count + scheduled_count,
                "registered_schedules": registered_schedules,
                "consumer_status": "running"  # Would track actual consumer status
            }
            
        except Exception as e:
            logger.warning(f"Error getting queue status: {e}")
            status["queue"] = {
                "enabled": True,
                "error": str(e),
                "consumer_status": "error"
            }
    elif settings.use_task_queue:
        # Task queue enabled but Huey not available
        status["queue"] = {
            "enabled": True,
            "available": False,
            "error": "Huey not configured",
            "consumer_status": "unavailable"
        }
    else:
        # Task queue disabled
        status["queue"] = {
            "enabled": False
        }
    
    return status
