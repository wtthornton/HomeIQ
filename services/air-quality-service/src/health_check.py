"""Health Check Handler for Air Quality Service"""

import logging
from datetime import datetime, timezone

from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check endpoint handler"""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.last_successful_fetch = None
        self.total_fetches = 0
        self.failed_fetches = 0
        self.total_writes = 0
        self.failed_writes = 0
        self.last_api_success = False
        self.last_influxdb_success = False

    async def handle(self, request):
        """Handle health check request"""

        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        healthy = True
        if self.last_successful_fetch:
            time_since_last = (datetime.now(timezone.utc) - self.last_successful_fetch).total_seconds()
            if time_since_last > 7200:  # 2 hours
                healthy = False

        status = {
            "status": "healthy" if healthy else "degraded",
            "service": "air-quality-service",
            "uptime_seconds": uptime,
            "last_successful_fetch": self.last_successful_fetch.isoformat() if self.last_successful_fetch else None,
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "total_writes": self.total_writes,
            "failed_writes": self.failed_writes,
            "success_rate": (self.total_fetches - self.failed_fetches) / self.total_fetches if self.total_fetches > 0 else 0,
            "components": {
                "openweather_api": "connected" if self.last_api_success else "disconnected",
                "influxdb": "connected" if self.last_influxdb_success else "disconnected"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return web.json_response(status, status=200 if healthy else 503)

