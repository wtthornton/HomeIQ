"""Health Check Handler for Energy Correlator Service"""

import logging
from datetime import datetime, timezone

from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Simple health check handler"""

    def __init__(self):
        self.last_successful_fetch: datetime | None = None
        self.total_fetches = 0
        self.failed_fetches = 0
        self.start_time = datetime.now(timezone.utc)

    async def handle(self, request: web.Request) -> web.Response:
        """Handle health check request"""

        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        success_rate = (
            1.0 if self.total_fetches == 0
            else (self.total_fetches - self.failed_fetches) / self.total_fetches
        )

        # Determine status based on success rate and recency
        if self.total_fetches == 0 and uptime < 120:
            status = "starting"
        elif success_rate < 0.5:
            status = "unhealthy"
        elif success_rate < 0.9:
            status = "degraded"
        else:
            status = "healthy"

        # Also check staleness - if last success was too long ago
        if self.last_successful_fetch:
            seconds_since_success = (
                datetime.now(timezone.utc) - self.last_successful_fetch
            ).total_seconds()
            if seconds_since_success > 300:  # 5 minutes with no success
                status = "unhealthy"

        health_data = {
            "status": status,
            "service": "energy-correlator",
            "uptime_seconds": uptime,
            "last_successful_fetch": (
                self.last_successful_fetch.isoformat()
                if self.last_successful_fetch else None
            ),
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "success_rate": success_rate
        }

        status_code = 200 if status in ("healthy", "starting") else 503
        return web.json_response(health_data, status=status_code)

