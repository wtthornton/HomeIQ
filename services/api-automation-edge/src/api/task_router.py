"""
Task Management Router

Endpoints for managing queued automation tasks.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..config import settings

logger = logging.getLogger(__name__)

# Huey task queue (optional, imported if available)
try:
    from ..task_queue.huey_config import huey
    HUEY_AVAILABLE = True
except ImportError:
    HUEY_AVAILABLE = False
    huey = None

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    """
    Get task status and result.
    
    Args:
        task_id: Task ID from queue_automation_task response
    
    Returns:
        Task status and result dictionary
    """
    if not HUEY_AVAILABLE or not huey:
        raise HTTPException(
            status_code=503,
            detail="Task queue not available (Huey not configured)"
        )
    
    try:
        # Get task from Huey
        task = huey.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Check if task is finished
        is_finished = task.is_finished()
        result = None
        
        if is_finished:
            try:
                result = task.get(blocking=False)
            except Exception as e:
                logger.warning(f"Failed to get task result: {e}")
                result = {"error": str(e)}
        
        return {
            "task_id": task_id,
            "is_finished": is_finished,
            "result": result,
            "status": "completed" if is_finished else "pending"
        }
        
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str) -> Dict[str, Any]:
    """
    Cancel a pending task.
    
    Args:
        task_id: Task ID to cancel
    
    Returns:
        Cancellation status
    """
    if not HUEY_AVAILABLE or not huey:
        raise HTTPException(
            status_code=503,
            detail="Task queue not available (Huey not configured)"
        )
    
    try:
        # Revoke task in Huey
        huey.revoke(task_id, revoke_once=False)
        
        logger.info(f"Task {task_id} revoked")
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "cancelled",
            "message": f"Task {task_id} has been cancelled"
        }
        
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status: pending, completed, failed"),
    spec_id: Optional[str] = Query(None, description="Filter by spec_id"),
    limit: int = Query(100, description="Maximum number of tasks to return")
) -> Dict[str, Any]:
    """
    List tasks with optional filters.
    
    Args:
        status: Filter by status
        spec_id: Filter by automation spec ID
        limit: Maximum number of tasks to return
    
    Returns:
        List of tasks
    """
    if not HUEY_AVAILABLE or not huey:
        raise HTTPException(
            status_code=503,
            detail="Task queue not available (Huey not configured)"
        )
    
    try:
        # Get pending tasks
        pending_tasks = huey.pending()
        
        # Get scheduled tasks
        scheduled_tasks = huey.scheduled()
        
        # Combine and filter
        all_tasks = list(pending_tasks) + list(scheduled_tasks)
        
        # Apply filters
        filtered_tasks = []
        for task_id in all_tasks[:limit]:
            try:
                task = huey.get_task(task_id)
                if not task:
                    continue
                
                # Check status filter
                is_finished = task.is_finished()
                task_status = "completed" if is_finished else "pending"
                
                if status and task_status != status:
                    continue
                
                # Get task metadata
                task_info = {
                    "task_id": task_id,
                    "status": task_status,
                    "is_finished": is_finished
                }
                
                # Try to get result if finished
                if is_finished:
                    try:
                        result = task.get(blocking=False)
                        task_info["result"] = result
                    except Exception:
                        pass
                
                filtered_tasks.append(task_info)
                
            except Exception as e:
                logger.warning(f"Error processing task {task_id}: {e}")
                continue
        
        return {
            "success": True,
            "count": len(filtered_tasks),
            "tasks": filtered_tasks
        }
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_task_history(
    spec_id: Optional[str] = Query(None, description="Filter by spec_id"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, description="Maximum number of tasks to return")
) -> Dict[str, Any]:
    """
    Get task execution history.
    
    Args:
        spec_id: Filter by automation spec ID
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        limit: Maximum number of tasks to return
    
    Returns:
        Task execution history
    """
    if not HUEY_AVAILABLE or not huey:
        raise HTTPException(
            status_code=503,
            detail="Task queue not available (Huey not configured)"
        )
    
    try:
        # Parse date filters
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format: {start_date}"
                )
        
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format: {end_date}"
                )
        
        # Get all finished tasks (limited by Huey's result storage)
        # Note: Huey doesn't have a built-in history query, so we'll need to
        # track task results separately if full history is needed
        # For now, return limited history from pending/completed tasks
        
        # This is a placeholder - full history would require additional storage
        return {
            "success": True,
            "message": "Task history requires additional storage (not yet implemented)",
            "count": 0,
            "tasks": []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/status")
async def get_queue_status() -> Dict[str, Any]:
    """
    Get task queue health metrics.
    
    Returns:
        Queue status including depth, consumer status, etc.
    """
    if not HUEY_AVAILABLE or not huey:
        raise HTTPException(
            status_code=503,
            detail="Task queue not available (Huey not configured)"
        )
    
    try:
        # Get queue metrics
        pending_tasks = huey.pending()
        scheduled_tasks = huey.scheduled()
        
        pending_count = len(list(pending_tasks))
        scheduled_count = len(list(scheduled_tasks))
        
        return {
            "success": True,
            "queue": {
                "pending": pending_count,
                "scheduled": scheduled_count,
                "total": pending_count + scheduled_count
            },
            "consumer": {
                "available": HUEY_AVAILABLE,
                "status": "running"  # Would need to track consumer status
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
