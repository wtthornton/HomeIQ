"""Health monitoring route handlers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .schemas import (
    EnvironmentHealthResponse,
    IntegrationStatus,
)

logger = logging.getLogger(__name__)

health_router = APIRouter(tags=["health"])


@health_router.get("/api/health/environment", response_model=EnvironmentHealthResponse)
async def get_environment_health(
    request: Request, db: AsyncSession = Depends(get_db),
) -> EnvironmentHealthResponse:
    """Get comprehensive environment health status."""
    try:
        health_service = getattr(request.app.state, "monitor", None)
        if not health_service:
            from .schemas import HealthStatus, PerformanceMetrics
            return EnvironmentHealthResponse(
                health_score=0, ha_status=HealthStatus.UNKNOWN, ha_version=None,
                integrations=[], performance=PerformanceMetrics(response_time_ms=0.0),
                issues_detected=["Health monitoring service not initialized."],
                timestamp=datetime.now(UTC),
            )
        return await health_service.check_environment_health(db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Environment health endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@health_router.get("/api/health/trends")
async def get_health_trends(
    request: Request, hours: int = 24, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return health trends over the specified time period."""
    try:
        continuous_monitor = getattr(request.app.state, "continuous_monitor", None)
        if not continuous_monitor:
            raise HTTPException(status_code=503, detail="Continuous monitoring not initialized")
        return await continuous_monitor.get_health_trends(db, hours)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting health trends")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@health_router.get("/api/health/integrations")
async def get_integrations_health(
    request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return detailed health status for all integrations."""
    try:
        integration_checker = getattr(request.app.state, "integration_checker", None)
        if not integration_checker:
            raise HTTPException(status_code=503, detail="Integration health checker not initialized")
        check_results = await integration_checker.check_all_integrations()
        await _store_integration_health_results(db, check_results)
        return {
            "timestamp": datetime.now(UTC),
            "total_integrations": len(check_results),
            "healthy_count": sum(1 for r in check_results if r.status == IntegrationStatus.HEALTHY),
            "warning_count": sum(1 for r in check_results if r.status == IntegrationStatus.WARNING),
            "error_count": sum(1 for r in check_results if r.status == IntegrationStatus.ERROR),
            "not_configured_count": sum(1 for r in check_results if r.status == IntegrationStatus.NOT_CONFIGURED),
            "integrations": [r.model_dump() for r in check_results],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error checking integrations")
        raise HTTPException(status_code=500, detail="Internal server error") from e


async def _store_integration_health_results(db: AsyncSession, check_results: list) -> None:
    """Store integration health check results in database."""
    try:
        from .models import IntegrationHealth
        for result in check_results:
            db.add(IntegrationHealth(
                integration_name=result.integration_name,
                integration_type=result.integration_type,
                status=result.status.value,
                is_configured=result.is_configured,
                is_connected=result.is_connected,
                error_message=result.error_message,
                last_check=result.last_check,
                check_details=result.check_details,
            ))
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error storing integration health results", exc_info=e)
