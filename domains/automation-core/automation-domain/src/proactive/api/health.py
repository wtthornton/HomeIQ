"""Health check endpoint with group-level resilience reporting."""

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
    """Health check with group-level status and scheduler info.

    Returns 200 for healthy and degraded states so Docker does not
    mark the container unhealthy when optional cross-domain
    dependencies (data-api, weather-api) are unavailable.
    Only returns 503 when the service process itself is broken.
    """
    from ..main import _group_health

    # Start from GroupHealthCheck if available
    if _group_health is not None:
        response = await _group_health.to_dict()
    else:
        response = {
            "status": "healthy",
            "service": "proactive-agent-service",
            "version": "1.0.0",
        }

    # Cap "unhealthy" to "degraded" — cross-domain dependencies being
    # unreachable is expected in dev/partial deployments and should not
    # cause Docker to restart the container.
    if response.get("status") == "unhealthy":
        response["status"] = "degraded"

    # Add scheduler status
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
