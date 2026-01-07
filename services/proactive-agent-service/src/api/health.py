"""Health check endpoint"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()

# Global scheduler service reference (set by main.py)
_scheduler_service: Any = None


def set_scheduler_service_for_health(service: Any):
    """Set scheduler service reference (called from main.py)"""
    global _scheduler_service
    _scheduler_service = service


@router.get("/health")
async def health_check():
    """
    Health check endpoint with scheduler status.
    
    Returns:
        Health status including scheduler information
    """
    response = {
        "status": "healthy",
        "service": "proactive-agent-service",
        "version": "1.0.0",
    }
    
    # Add scheduler status if available
    if _scheduler_service is not None:
        try:
            scheduler_running = _scheduler_service.is_running()
            next_run = _scheduler_service.get_next_run_time()
            
            response["scheduler"] = {
                "enabled": True,
                "running": scheduler_running,
                "next_run": next_run.isoformat() if next_run else None,
            }
        except Exception:
            response["scheduler"] = {
                "enabled": True,
                "running": False,
                "error": "Failed to get scheduler status",
            }
    else:
        response["scheduler"] = {
            "enabled": False,
            "running": False,
            "next_run": None,
        }
    
    return response

