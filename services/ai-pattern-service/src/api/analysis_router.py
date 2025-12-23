"""
Analysis Router - API endpoints for pattern analysis status and scheduling

Epic 39: Pattern Service API endpoints
Provides REST API for checking analysis status and schedule information.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import main as main_module
from ..config import settings
from ..database import get_db
from ..crud.patterns import get_patterns

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/status")
async def get_analysis_status(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get current analysis status and pattern statistics.
    
    Returns:
        Status information including pattern counts and last run details
    """
    try:
        # Get pattern stats from database
        patterns = await get_patterns(db, limit=10000)
        
        # Calculate statistics
        total_patterns = len(patterns)
        by_type = {}
        total_confidence = 0.0
        unique_device_set = set()
        
        for p in patterns:
            # Handle both dict and Pattern object
            if isinstance(p, dict):
                pattern_type = p.get("pattern_type", "unknown")
                confidence = p.get("confidence", 0.0)
                device_id = p.get("device_id")
            else:
                pattern_type = p.pattern_type
                confidence = p.confidence
                device_id = p.device_id
            
            by_type[pattern_type] = by_type.get(pattern_type, 0) + 1
            total_confidence += confidence
            
            if device_id:
                individual_devices = device_id.split('+')
                unique_device_set.update(individual_devices)
        
        avg_confidence = total_confidence / total_patterns if total_patterns > 0 else 0.0
        unique_devices = len(unique_device_set)
        
        # Get scheduler status (access dynamically to get current value)
        pattern_scheduler = main_module.pattern_scheduler
        scheduler_status = "running" if pattern_scheduler and pattern_scheduler.is_running else "stopped"
        last_run = None
        if pattern_scheduler and hasattr(pattern_scheduler, 'last_run_result'):
            last_run = pattern_scheduler.last_run_result
        
        return {
            "status": "ready",
            "patterns": {
                "total_patterns": total_patterns,
                "by_type": by_type,
                "unique_devices": unique_devices,
                "avg_confidence": round(avg_confidence, 3)
            },
            "scheduler": {
                "status": scheduler_status,
                "schedule": settings.analysis_schedule,
                "last_run": last_run
            },
            "suggestions": {
                "pending_count": 0,
                "recent": []
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to get analysis status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis status: {str(e)}"
        ) from e


@router.get("/schedule")
async def get_analysis_schedule() -> dict[str, Any]:
    """
    Get information about the analysis schedule.
    
    Returns:
        Schedule information including cron expression and next run time
    """
    try:
        schedule_info = {
            "schedule": settings.analysis_schedule,
            "enabled": main_module.pattern_scheduler is not None and main_module.pattern_scheduler.is_running if main_module.pattern_scheduler else False,
            "incremental_enabled": settings.enable_incremental,
            "next_run": None,  # TODO: Calculate next run time from cron schedule
            "last_run": None
        }
        
        pattern_scheduler = main_module.pattern_scheduler
        if pattern_scheduler and hasattr(pattern_scheduler, 'last_run_result'):
            schedule_info["last_run"] = pattern_scheduler.last_run_result
        
        return schedule_info
    
    except Exception as e:
        logger.error(f"Failed to get analysis schedule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis schedule: {str(e)}"
        ) from e


@router.post("/trigger")
async def trigger_analysis(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """
    Manually trigger pattern analysis job.
    
    Returns:
        Status of the triggered analysis
    """
    try:
        # Access scheduler dynamically to get current value
        pattern_scheduler = main_module.pattern_scheduler
        if not pattern_scheduler:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pattern analysis scheduler is not available"
            )
        
        if pattern_scheduler.is_running:
            # Trigger manual run in background
            # BackgroundTasks can handle async functions directly
            async def run_analysis_task():
                try:
                    await pattern_scheduler.run_pattern_analysis()
                except Exception as e:
                    logger.error(f"Background analysis task failed: {e}", exc_info=True)
            
            background_tasks.add_task(run_analysis_task)
            
            return {
                "success": True,
                "message": "Pattern analysis triggered successfully",
                "status": "running"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pattern analysis scheduler is not running"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger analysis: {str(e)}"
        ) from e

