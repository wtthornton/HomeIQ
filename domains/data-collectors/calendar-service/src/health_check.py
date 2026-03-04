"""Health Check Handler for Calendar Service"""

import logging
from datetime import UTC, datetime

from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check endpoint handler"""

    def __init__(self):
        self.start_time = datetime.now(UTC)
        self.last_successful_fetch = None
        self.total_fetches = 0
        self.failed_fetches = 0
        self.ha_connected = False
        self.calendar_count = 0
        self.calendars_discovered = 0

    async def handle(self, _request):
        """Handle health check request"""

        uptime = (datetime.now(UTC) - self.start_time).total_seconds()

        healthy = self.ha_connected
        status_detail = None

        # No calendars discovered means misconfiguration
        if self.calendar_count > 0 and self.calendars_discovered == 0:
            healthy = False
            status_detail = "no_calendars_found"

        if self.last_successful_fetch:
            time_since_last = (datetime.now(UTC) - self.last_successful_fetch).total_seconds()
            if time_since_last > 1800:  # 30 minutes
                healthy = False

        status = {
            "status": "healthy" if healthy else "degraded",
            "status_detail": status_detail,
            "service": "calendar-service",
            "integration_type": "home_assistant",
            "uptime_seconds": uptime,
            "ha_connected": self.ha_connected,
            "calendar_count": self.calendar_count,
            "calendars_discovered": self.calendars_discovered,
            "last_successful_fetch": self.last_successful_fetch.isoformat() if self.last_successful_fetch else None,
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "success_rate": (self.total_fetches - self.failed_fetches) / self.total_fetches if self.total_fetches > 0 else 0,
            "timestamp": datetime.now(UTC).isoformat()
        }

        # Always return HTTP 200 — degraded states are informational, not failures.
        # Returning 503 for degraded causes Docker healthcheck failures (e.g., 24
        # consecutive failures for "no_calendars_found") even though the service
        # itself is running correctly and will recover when calendars appear.
        return web.json_response(status, status=200)
