"""Health Check Handler for Carbon Intensity Service."""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check state tracker for carbon intensity service."""

    def __init__(self) -> None:
        self.start_time = datetime.now(UTC)
        self.last_successful_fetch: datetime | None = None
        self.last_token_refresh: datetime | None = None
        self.total_fetches: int = 0
        self.failed_fetches: int = 0
        self.token_refresh_count: int = 0
        self.credentials_missing: bool = False
        self.influxdb_write_failures: int = 0
        self.last_successful_write: datetime | None = None

    def get_status(self) -> dict:
        """Return health status dictionary."""
        uptime = (datetime.now(UTC) - self.start_time).total_seconds()

        healthy = True
        status_detail = "operational"
        status_label = "healthy"

        if self.credentials_missing:
            healthy = True
            status_label = "unconfigured"
            status_detail = "credentials_missing"
        elif self.last_successful_fetch:
            time_since_last = (datetime.now(UTC) - self.last_successful_fetch).total_seconds()
            if time_since_last > 1800:  # 30 minutes
                healthy = False
                status_label = "degraded"
                status_detail = "stale_data"
        elif self.total_fetches > 0:
            healthy = False
            status_label = "degraded"
            status_detail = "all_fetches_failed"
        elif self.total_fetches == 0:
            status_detail = "starting"

        return {
            "status": status_label,
            "status_detail": status_detail,
            "service": "carbon-intensity-service",
            "uptime_seconds": uptime,
            "last_successful_fetch": (
                self.last_successful_fetch.isoformat() if self.last_successful_fetch else None
            ),
            "last_token_refresh": (
                self.last_token_refresh.isoformat() if self.last_token_refresh else None
            ),
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "token_refresh_count": self.token_refresh_count,
            "success_rate": (
                (self.total_fetches - self.failed_fetches) / self.total_fetches
                if self.total_fetches > 0
                else 0
            ),
            "credentials_configured": not self.credentials_missing,
            "influxdb_write_failures": self.influxdb_write_failures,
            "last_successful_write": (
                self.last_successful_write.isoformat() if self.last_successful_write else None
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }
