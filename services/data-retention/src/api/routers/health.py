"""
Health and statistics router for data-retention service.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from ..models import HealthResponse, StatisticsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/v1/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint.

    Returns service health status including storage metrics and alerts.
    """
    try:
        service = request.app.state.service
        # Get service status
        service_status = service.get_service_status()

        # Get storage metrics
        storage_metrics = service.get_storage_metrics()

        # Get active alerts
        storage_alerts = service.get_storage_alerts()

        # Determine overall health
        overall_status = "healthy"
        if storage_alerts:
            critical_alerts = [alert for alert in storage_alerts if alert.get("severity") == "critical"]
            if critical_alerts:
                overall_status = "critical"
            else:
                overall_status = "warning"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_status": service_status,
            "storage_metrics": storage_metrics,
            "active_alerts": len(storage_alerts),
            "alerts": storage_alerts
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Internal server error"
            }
        )


@router.get("/stats", response_model=StatisticsResponse)
@router.get("/api/v1/stats", response_model=StatisticsResponse)
async def get_statistics(request: Request):
    """
    Get service statistics.

    Returns comprehensive service statistics including policy, cleanup, storage, compression, and backup statistics.
    """
    try:
        service = request.app.state.service
        stats = service.get_service_statistics()
        return stats
    except Exception as e:
        logger.error(f"Get statistics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})

