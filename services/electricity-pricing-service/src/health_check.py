"""
Health Check Handler for Electricity Pricing Service
"""

import logging
from datetime import datetime

from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check endpoint handler"""

    def __init__(self):
        self.start_time = datetime.now()
        self.last_successful_fetch = None
        self.total_fetches = 0
        self.failed_fetches = 0

    async def handle(self, request):
        """Handle health check request"""

        uptime = (datetime.now() - self.start_time).total_seconds()

        # Determine health status
        healthy = True
        if self.last_successful_fetch:
            time_since_last = (datetime.now() - self.last_successful_fetch).total_seconds()
            if time_since_last > 7200:  # 2 hours without successful fetch
                healthy = False

        status = {
            "status": "healthy" if healthy else "degraded",
            "service": "electricity-pricing-service",
            "uptime_seconds": uptime,
            "last_successful_fetch": self.last_successful_fetch.isoformat() if self.last_successful_fetch else None,
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "success_rate": (self.total_fetches - self.failed_fetches) / self.total_fetches if self.total_fetches > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }

        return web.json_response(status, status=200 if healthy else 503)

