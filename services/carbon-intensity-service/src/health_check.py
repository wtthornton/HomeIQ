"""
Health Check Handler for Carbon Intensity Service
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
        self.last_token_refresh = None
        self.total_fetches = 0
        self.failed_fetches = 0
        self.token_refresh_count = 0
        self.credentials_missing = False  # Track if credentials are not configured

    async def handle(self, request):
        """Handle health check request"""

        uptime = (datetime.now() - self.start_time).total_seconds()

        # Determine health status
        healthy = True
        status_detail = "operational"

        if self.credentials_missing:
            # Service is running but credentials not configured
            healthy = True  # Still healthy, just not configured
            status_detail = "credentials_missing"
        elif self.last_successful_fetch:
            time_since_last = (datetime.now() - self.last_successful_fetch).total_seconds()
            if time_since_last > 1800:  # 30 minutes without successful fetch
                healthy = False
                status_detail = "degraded"
        elif self.total_fetches == 0:
            # No fetches attempted yet (startup)
            status_detail = "starting"

        status = {
            "status": "healthy" if healthy else "degraded",
            "status_detail": status_detail,  # NEW: Detailed status
            "service": "carbon-intensity-service",
            "uptime_seconds": uptime,
            "last_successful_fetch": self.last_successful_fetch.isoformat() if self.last_successful_fetch else None,
            "last_token_refresh": self.last_token_refresh.isoformat() if self.last_token_refresh else None,
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "token_refresh_count": self.token_refresh_count,
            "success_rate": (self.total_fetches - self.failed_fetches) / self.total_fetches if self.total_fetches > 0 else 0,
            "credentials_configured": not self.credentials_missing,  # NEW: Flag for frontend
            "timestamp": datetime.now().isoformat()
        }

        return web.json_response(status, status=200 if healthy else 503)

