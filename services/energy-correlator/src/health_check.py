"""Health Check Handler for Energy Correlator Service"""

import logging
from datetime import datetime

from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Simple health check handler"""

    def __init__(self):
        self.last_successful_fetch: datetime | None = None
        self.total_fetches = 0
        self.failed_fetches = 0
        self.start_time = datetime.now()

    async def handle(self, request):
        """Handle health check request"""

        uptime = (datetime.now() - self.start_time).total_seconds()
        success_rate = (
            1.0 if self.total_fetches == 0
            else (self.total_fetches - self.failed_fetches) / self.total_fetches
        )

        health_data = {
            "status": "healthy",
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

        return web.json_response(health_data)

