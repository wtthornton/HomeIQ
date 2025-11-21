"""
Health Check Handler for Admin API Service
"""

import logging
from datetime import datetime

from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Handles health check requests"""

    def __init__(self):
        self.start_time = datetime.now()

    async def handle(self, request):
        """Handle health check request"""
        try:
            # Basic health check - service is running
            health_data = {
                "status": "healthy",
                "service": "admin-api",
                "uptime": str(datetime.now() - self.start_time),
                "timestamp": datetime.now().isoformat(),
            }

            return web.json_response(health_data, status=200)

        except Exception as e:
            logger.exception(f"Health check failed: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)},
                status=500,
            )
