"""
Schedule Management Router

Endpoints for managing scheduled automation tasks.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..registry.spec_registry import SpecRegistry

logger = logging.getLogger(__name__)

# Scheduler (optional, imported if available)
try:
    from ..queue.scheduler import get_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    get_scheduler = None

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

# Initialize spec registry
spec_registry = SpecRegistry(settings.database_url)


@router.get("")
async def list_schedules(
    home_id: str = settings.home_id
) -> Dict[str, Any]:
    """
    List all scheduled automations.
    
    Args:
        home_id: Home ID
    
    Returns:
        List of scheduled automations
    """
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not available (Huey not configured)"
        )
    
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized"
        )
    
    try:
        # Get all active specs and filter for scheduled ones
        # Note: This would need a method to list all specs
        # For now, return registered schedules
        
        schedules = []
        for spec_id, job_id in scheduler.registered_schedules.items():
            spec = spec_registry.get_spec(spec_id, home_id)
            if not spec:
                continue
            
            # Find schedule trigger
            triggers = spec.get("triggers", [])
            schedule_trigger = None
            for trigger in triggers:
                if trigger.get("type") == "schedule":
                    schedule_trigger = trigger
                    break
            
            if schedule_trigger:
                schedule_status = scheduler.get_schedule_status(spec_id)
                schedules.append({
                    "spec_id": spec_id,
                    "alias": spec.get("alias", spec_id),
                    "cron": schedule_trigger.get("cron"),
                    "job_id": job_id,
                    "status": schedule_status
                })
        
        return {
            "success": True,
            "count": len(schedules),
            "schedules": schedules
        }
        
    except Exception as e:
        logger.error(f"Error listing schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{spec_id}/enable")
async def enable_schedule(
    spec_id: str,
    home_id: str = settings.home_id
) -> Dict[str, Any]:
    """
    Enable scheduled automation.
    
    Args:
        spec_id: Automation spec ID
        home_id: Home ID
    
    Returns:
        Enable status
    """
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not available (Huey not configured)"
        )
    
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized"
        )
    
    try:
        # Get spec
        spec = spec_registry.get_spec(spec_id, home_id)
        if not spec:
            raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")
        
        # Find schedule trigger
        triggers = spec.get("triggers", [])
        schedule_trigger = None
        for trigger in triggers:
            if trigger.get("type") == "schedule":
                schedule_trigger = trigger
                break
        
        if not schedule_trigger:
            raise HTTPException(
                status_code=400,
                detail=f"Spec {spec_id} does not have a schedule trigger"
            )
        
        cron_expr = schedule_trigger.get("cron")
        if not cron_expr:
            raise HTTPException(
                status_code=400,
                detail=f"Schedule trigger for {spec_id} missing cron expression"
            )
        
        # Register schedule
        job_id = scheduler.register_scheduled_automation(
            spec_id=spec_id,
            home_id=home_id,
            cron_expr=cron_expr
        )
        
        return {
            "success": True,
            "spec_id": spec_id,
            "job_id": job_id,
            "cron": cron_expr,
            "status": "enabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling schedule for {spec_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{spec_id}/disable")
async def disable_schedule(
    spec_id: str
) -> Dict[str, Any]:
    """
    Disable scheduled automation.
    
    Args:
        spec_id: Automation spec ID
    
    Returns:
        Disable status
    """
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not available (Huey not configured)"
        )
    
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized"
        )
    
    try:
        # Unregister schedule
        success = scheduler.unregister_scheduled_automation(spec_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Schedule for spec {spec_id} not found"
            )
        
        return {
            "success": True,
            "spec_id": spec_id,
            "status": "disabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling schedule for {spec_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{spec_id}/next-run")
async def get_next_run(
    spec_id: str,
    home_id: str = settings.home_id
) -> Dict[str, Any]:
    """
    Get next run time for scheduled automation.
    
    Args:
        spec_id: Automation spec ID
        home_id: Home ID
    
    Returns:
        Next run time information
    """
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not available (Huey not configured)"
        )
    
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized"
        )
    
    try:
        # Get schedule status
        schedule_status = scheduler.get_schedule_status(spec_id)
        
        if not schedule_status:
            raise HTTPException(
                status_code=404,
                detail=f"Schedule for spec {spec_id} not found"
            )
        
        # Get spec for cron expression
        spec = spec_registry.get_spec(spec_id, home_id)
        if not spec:
            raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")
        
        # Find schedule trigger
        triggers = spec.get("triggers", [])
        schedule_trigger = None
        for trigger in triggers:
            if trigger.get("type") == "schedule":
                schedule_trigger = trigger
                break
        
        if not schedule_trigger:
            raise HTTPException(
                status_code=400,
                detail=f"Spec {spec_id} does not have a schedule trigger"
            )
        
        # Note: Huey doesn't expose next run time directly
        # We would need to calculate it from cron expression
        # For now, return the cron expression
        
        return {
            "success": True,
            "spec_id": spec_id,
            "cron": schedule_trigger.get("cron"),
            "job_id": schedule_status.get("job_id"),
            "enabled": schedule_status.get("enabled", True),
            "next_run": None  # Would calculate from cron
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting next run for {spec_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
