"""
Alert API Endpoints
Epic 17.4: Critical Alerting System
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../shared"))

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from shared.alert_manager import AlertManager, AlertSeverity, AlertStatus, get_alert_manager

logger = logging.getLogger(__name__)


class AlertResponse(BaseModel):
    """Alert response model"""
    id: str
    name: str
    severity: str
    status: str
    message: str
    service: str
    metric: str | None = None
    current_value: float | None = None
    threshold_value: float | None = None
    created_at: str | None = None
    resolved_at: str | None = None
    acknowledged_at: str | None = None
    metadata: dict[str, Any] | None = None


class AlertSummaryResponse(BaseModel):
    """Alert summary response model"""
    total_active: int
    critical: int
    warning: int
    info: int
    total_alerts: int
    alert_history_count: int


class AlertEndpoints:
    """Alert management endpoints"""

    def __init__(self, alert_manager: AlertManager | None = None):
        """Initialize alert endpoints"""
        self.router = APIRouter()
        self.alert_manager = alert_manager or get_alert_manager("admin-api")
        self._add_routes()

    def _add_routes(self):
        """Add alert routes"""

        @self.router.get("/alerts", response_model=list[AlertResponse])
        async def get_all_alerts(
            severity: str | None = Query(None, description="Filter by severity"),
            status_filter: str | None = Query(None, alias="status", description="Filter by status"),
        ):
            """
            Get all alerts with optional filtering

            Args:
                severity: Filter by severity (info, warning, critical)
                status_filter: Filter by status (active, acknowledged, resolved)

            Returns:
                List of alerts
            """
            try:
                alerts = list(self.alert_manager.alerts.values())

                # Filter by severity
                if severity:
                    try:
                        sev = AlertSeverity(severity.lower())
                        alerts = [a for a in alerts if a.severity == sev]
                    except ValueError as err:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid severity: {severity}",
                        ) from err

                # Filter by status
                if status_filter:
                    try:
                        stat = AlertStatus(status_filter.lower())
                        alerts = [a for a in alerts if a.status == stat]
                    except ValueError as err:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid status: {status_filter}",
                        ) from err

                # Sort by created_at (most recent first)
                alerts.sort(key=lambda x: x.created_at or "", reverse=True)

                return [AlertResponse(**a.to_dict()) for a in alerts]

            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Error getting alerts: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get alerts: {e!s}",
                )

        @self.router.get("/alerts/active", response_model=list[AlertResponse])
        async def get_active_alerts(
            severity: str | None = Query(None, description="Filter by severity"),
        ):
            """
            Get only active alerts

            Args:
                severity: Filter by severity (optional)

            Returns:
                List of active alerts
            """
            try:
                sev = None
                if severity:
                    try:
                        sev = AlertSeverity(severity.lower())
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid severity: {severity}",
                        )

                alerts = self.alert_manager.get_active_alerts(sev)
                return [AlertResponse(**a.to_dict()) for a in alerts]

            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Error getting active alerts: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get active alerts: {e!s}",
                )

        @self.router.get("/alerts/summary", response_model=AlertSummaryResponse)
        async def get_alert_summary():
            """
            Get alert summary statistics

            Returns:
                Alert summary with counts by severity and status
            """
            try:
                summary = self.alert_manager.get_alert_summary()
                return AlertSummaryResponse(**summary)
            except Exception as e:
                logger.exception(f"Error getting alert summary: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get alert summary: {e!s}",
                )

        @self.router.get("/alerts/{alert_id}", response_model=AlertResponse)
        async def get_alert(alert_id: str):
            """
            Get specific alert by ID

            Args:
                alert_id: Alert ID

            Returns:
                Alert details
            """
            try:
                alert = self.alert_manager.get_alert(alert_id)
                if not alert:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Alert not found: {alert_id}",
                    )

                return AlertResponse(**alert.to_dict())
            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Error getting alert {alert_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get alert: {e!s}",
                )

        @self.router.post("/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(alert_id: str):
            """
            Acknowledge an alert

            Args:
                alert_id: Alert ID to acknowledge

            Returns:
                Success message
            """
            try:
                success = self.alert_manager.acknowledge_alert(alert_id)
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Alert not found: {alert_id}",
                    )

                return {
                    "status": "success",
                    "message": f"Alert acknowledged: {alert_id}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Error acknowledging alert {alert_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to acknowledge alert: {e!s}",
                )

        @self.router.post("/alerts/{alert_id}/resolve")
        async def resolve_alert(alert_id: str):
            """
            Resolve an alert

            Args:
                alert_id: Alert ID to resolve

            Returns:
                Success message
            """
            try:
                success = self.alert_manager.resolve_alert(alert_id)
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Alert not found: {alert_id}",
                    )

                return {
                    "status": "success",
                    "message": f"Alert resolved: {alert_id}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Error resolving alert {alert_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to resolve alert: {e!s}",
                )

        @self.router.delete("/alerts/cleanup")
        async def cleanup_resolved_alerts(
            older_than_hours: int = Query(24, description="Clear alerts resolved more than X hours ago"),
        ):
            """
            Clean up old resolved alerts

            Args:
                older_than_hours: Hours threshold for cleanup

            Returns:
                Success message
            """
            try:
                self.alert_manager.clear_resolved_alerts(older_than_hours)
                return {
                    "status": "success",
                    "message": f"Cleaned up resolved alerts older than {older_than_hours} hours",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            except Exception as e:
                logger.exception(f"Error cleaning up alerts: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to cleanup alerts: {e!s}",
                )


def create_alert_router(alert_manager: AlertManager | None = None) -> APIRouter:
    """
    Create and return alert router

    Args:
        alert_manager: Optional alert manager instance

    Returns:
        FastAPI APIRouter with alert endpoints
    """
    endpoints = AlertEndpoints(alert_manager)
    return endpoints.router

