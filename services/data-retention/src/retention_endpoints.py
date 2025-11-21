"""
Retention Service API Endpoints
"""

import logging

from aiohttp import web

logger = logging.getLogger(__name__)


class RetentionEndpoints:
    """API endpoints for retention operations"""

    def __init__(self, view_manager, retention_manager, archival_manager, analytics):
        self.view_manager = view_manager
        self.retention_manager = retention_manager
        self.archival_manager = archival_manager
        self.analytics = analytics

    async def get_stats(self, request):
        """GET /retention/stats - Get storage metrics"""

        try:
            metrics = await self.analytics.calculate_storage_metrics()
            return web.json_response(metrics)
        except Exception as e:
            logger.exception(f"Error getting stats: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def downsample_hourly(self, request):
        """POST /retention/downsample-hourly - Manual trigger"""

        try:
            result = await self.retention_manager.downsample_hot_to_warm()
            return web.json_response(result)
        except Exception as e:
            logger.exception(f"Error downsampling: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def downsample_daily(self, request):
        """POST /retention/downsample-daily - Manual trigger"""

        try:
            result = await self.retention_manager.downsample_warm_to_cold()
            return web.json_response(result)
        except Exception as e:
            logger.exception(f"Error downsampling: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def archive_s3(self, request):
        """POST /retention/archive-s3 - Manual trigger"""

        try:
            result = await self.archival_manager.archive_to_s3()
            return web.json_response(result)
        except Exception as e:
            logger.exception(f"Error archiving: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def refresh_views(self, request):
        """POST /retention/refresh-views - Manual trigger"""

        try:
            result = await self.view_manager.refresh_all_views()
            return web.json_response(result)
        except Exception as e:
            logger.exception(f"Error refreshing views: {e}")
            return web.json_response({"error": str(e)}, status=500)

    def add_routes(self, app: web.Application):
        """Add routes to application"""

        app.router.add_get("/retention/stats", self.get_stats)
        app.router.add_post("/retention/downsample-hourly", self.downsample_hourly)
        app.router.add_post("/retention/downsample-daily", self.downsample_daily)
        app.router.add_post("/retention/archive-s3", self.archive_s3)
        app.router.add_post("/retention/refresh-views", self.refresh_views)

        logger.info("Retention API endpoints registered")

