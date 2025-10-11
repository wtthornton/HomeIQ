"""Health Check Handler for Calendar Service"""

import logging
from aiohttp import web
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Health check endpoint handler"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.last_successful_fetch = None
        self.total_fetches = 0
        self.failed_fetches = 0
        self.oauth_valid = False
    
    async def handle(self, request):
        """Handle health check request"""
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        healthy = self.oauth_valid
        if self.last_successful_fetch:
            time_since_last = (datetime.now() - self.last_successful_fetch).total_seconds()
            if time_since_last > 1800:  # 30 minutes
                healthy = False
        
        status = {
            "status": "healthy" if healthy else "degraded",
            "service": "calendar-service",
            "uptime_seconds": uptime,
            "oauth_valid": self.oauth_valid,
            "last_successful_fetch": self.last_successful_fetch.isoformat() if self.last_successful_fetch else None,
            "total_fetches": self.total_fetches,
            "failed_fetches": self.failed_fetches,
            "success_rate": (self.total_fetches - self.failed_fetches) / self.total_fetches if self.total_fetches > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        return web.json_response(status, status=200 if healthy else 503)

