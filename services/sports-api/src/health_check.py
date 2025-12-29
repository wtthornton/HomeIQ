"""
Health Check Handler for Sports API Service
Epic 31 Architecture Pattern
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .main import SportsService

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Handles health check requests with component status"""

    def __init__(self, service_name: str, version: str):
        """Initialize health check handler"""
        self.service_name = service_name
        self.version = version
        self.start_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.last_check_time: datetime | None = None

    async def handle(self, service: SportsService | None) -> dict[str, Any]:
        """
        Handle health check request
        
        Returns:
            Dict with service health status
        """
        try:
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            self.last_check_time = now
            uptime = now - self.start_time

            health_data = {
                "status": self._resolve_status(service),
                "service": self.service_name,
                "version": self.version,
                "uptime": str(uptime),
                "uptime_seconds": int(uptime.total_seconds()),
                "timestamp": now.isoformat(),
                "components": self._component_status(service),
                "metrics": self._metrics(service, now)
            }

            return health_data

        except Exception as e:
            logger.exception("Health check failed")
            return {
                "status": "unhealthy",
                "service": self.service_name,
                "version": self.version,
                "error": str(e),
                "timestamp": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
            }

    def get_uptime_seconds(self) -> int:
        """Get service uptime in seconds"""
        uptime = datetime.utcnow().replace(tzinfo=timezone.utc) - self.start_time
        return int(uptime.total_seconds())

    def _resolve_status(self, service: SportsService | None) -> str:
        if not service:
            return "initializing"
        if service.background_task and service.background_task.done():
            return "degraded"
        # Check if InfluxDB writes are failing persistently
        if (hasattr(service, 'influx_write_failure_count') and
            service.influx_write_failure_count > 0 and
            hasattr(service, 'influx_write_success_count') and
            service.influx_write_success_count == 0):
            # All writes failing, no successes
            return "degraded"
        return "healthy"

    def _component_status(self, service: SportsService | None) -> dict[str, str]:
        if not service:
            return {
                "api": "initializing",
                "ha_client": "initializing",
                "cache": "initializing",
                "influxdb": "initializing",
                "background_task": "not_started"
            }

        session_state = "healthy" if service.session and not service.session.closed else "not_initialized"
        cache_state = "healthy" if service.cached_sensors else "empty"

        # InfluxDB status: check client exists AND recent writes are succeeding
        if not service.influxdb_client:
            influx_state = "not_initialized"
        elif service.last_influx_write_error:
            # If there's a recent error, check if writes are failing
            influx_state = "degraded"  # Client exists but writes are failing
        elif service.last_influx_write:
            # Check if last write was recent (within last 30 minutes)
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            write_age = (now - service.last_influx_write).total_seconds()
            if write_age > 1800:  # 30 minutes
                influx_state = "degraded"  # No recent successful writes
            else:
                influx_state = "healthy"
        else:
            # Client exists but no writes yet
            influx_state = "initializing"
        if not service.background_task:
            task_state = "not_started"
        elif service.background_task.cancelled():
            task_state = "cancelled"
        elif service.background_task.done():
            task_state = "stopped"
        else:
            task_state = "running"

        if service.last_background_error:
            task_state = "error"

        return {
            "api": "healthy",
            "ha_client": session_state,
            "cache": cache_state,
            "influxdb": influx_state,
            "background_task": task_state
        }

    def _metrics(self, service: SportsService | None, now: datetime) -> dict[str, Any]:
        if not service:
            return {}

        cache_age = None
        if service.cache_time:
            cache_age = (now - service.cache_time).total_seconds()

        return {
            "fetch_count": service.fetch_count,
            "sensors_processed": service.sensors_processed,
            "poll_interval_seconds": service.poll_interval,
            "cache_age_seconds": cache_age,
            "last_successful_fetch": service.last_successful_fetch.isoformat() if service.last_successful_fetch else None,
            "last_influx_write": service.last_influx_write.isoformat() if service.last_influx_write else None,
            "last_influx_write_error": service.last_influx_write_error,
            "influx_write_success_count": getattr(service, 'influx_write_success_count', 0),
            "influx_write_failure_count": getattr(service, 'influx_write_failure_count', 0),
            "last_background_error": service.last_background_error,
            "cached_sensors_count": len(service.cached_sensors) if service.cached_sensors else 0
        }

