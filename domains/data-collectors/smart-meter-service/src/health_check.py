"""Health Check Handler for Smart Meter Service."""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check state tracker for smart meter service."""

    def __init__(self) -> None:
        self.start_time = datetime.now(UTC)
        self.last_successful_fetch: datetime | None = None
        self.total_fetches: int = 0
        self.failed_fetches: int = 0

    def get_status(self) -> dict:
        """Return health status dictionary."""
        uptime = (datetime.now(UTC) - self.start_time).total_seconds()

        healthy = True
        if self.last_successful_fetch:
            time_since_last = (datetime.now(UTC) - self.last_successful_fetch).total_seconds()
            if time_since_last > 600:  # 10 minutes
                healthy = False

        return {
            "status": "healthy" if healthy else "degraded",
            "service": "smart-meter-service",
            "uptime_seconds": uptime,
            "last_successful_fetch": (
                self.last_successful_fetch.isoformat() if self.last_successful_fetch else None
            ),
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "success_rate": (
                (self.total_fetches - self.failed_fetches) / self.total_fetches
                if self.total_fetches > 0
                else 0
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }
