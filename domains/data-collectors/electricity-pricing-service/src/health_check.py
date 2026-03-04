"""Health Check Handler for Electricity Pricing Service."""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check state tracker for electricity pricing service."""

    STARTUP_GRACE_PERIOD = 300  # 5 minutes

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
            if time_since_last > 7200:  # 2 hours
                healthy = False
        elif uptime > self.STARTUP_GRACE_PERIOD:
            healthy = False

        return {
            "status": "healthy" if healthy else "degraded",
            "service": "electricity-pricing-service",
            "uptime_seconds": uptime,
            "last_successful_fetch": (
                self.last_successful_fetch.isoformat() if self.last_successful_fetch else None
            ),
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "success_rate": (
                self.total_fetches / (self.total_fetches + self.failed_fetches)
                if (self.total_fetches + self.failed_fetches) > 0
                else 0
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }
