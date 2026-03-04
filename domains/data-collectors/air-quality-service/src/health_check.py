"""Health Check Handler for Air Quality Service."""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check state tracker for air quality service."""

    def __init__(self) -> None:
        self.start_time = datetime.now(UTC)
        self.last_successful_fetch: datetime | None = None
        self.total_fetches: int = 0
        self.failed_fetches: int = 0
        self.total_writes: int = 0
        self.failed_writes: int = 0
        self.last_api_success: bool = False
        self.last_influxdb_success: bool = False

    def get_status(self) -> dict:
        """Return health status dictionary."""
        uptime = (datetime.now(UTC) - self.start_time).total_seconds()

        healthy = True
        if self.last_successful_fetch:
            time_since_last = (datetime.now(UTC) - self.last_successful_fetch).total_seconds()
            if time_since_last > 7200:  # 2 hours
                healthy = False

        # If fetches have been attempted but none succeeded, report degraded
        if self.total_fetches > 0 and self.total_fetches == self.failed_fetches:
            healthy = False

        return {
            "status": "healthy" if healthy else "degraded",
            "service": "air-quality-service",
            "uptime_seconds": uptime,
            "last_successful_fetch": (
                self.last_successful_fetch.isoformat() if self.last_successful_fetch else None
            ),
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "total_writes": self.total_writes,
            "failed_writes": self.failed_writes,
            "success_rate": (
                (self.total_fetches - self.failed_fetches) / self.total_fetches
                if self.total_fetches > 0
                else 0
            ),
            "components": {
                "openweather_api": "connected" if self.last_api_success else "disconnected",
                "influxdb": "connected" if self.last_influxdb_success else "disconnected",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
