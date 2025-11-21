"""
Simplified Health Endpoint for Dashboard Integration
Shared simple health service for admin-api and data-api.
"""

import logging
import os
from datetime import datetime
from typing import Any

import aiohttp
from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)


class SimpleHealthService:
    """Simplified health service for dashboard integration"""

    def __init__(self):
        self.router = APIRouter()
        self.service_urls = {
            "websocket-ingestion": os.getenv("WEBSOCKET_INGESTION_URL", "http://websocket-ingestion:8000"),
            "influxdb": os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
        }
        self._add_routes()

    def _add_routes(self):
        """Add simplified health routes"""

        @self.router.get("/health")
        async def get_health():
            """Get simplified health status for dashboard"""
            try:
                # Check basic service connectivity
                services_status = await self._check_services_simple()
                logger.info(f"Services status: {services_status}")

                # Determine overall status
                healthy_services = sum(1 for status in services_status.values() if status.get("status") == "healthy")
                total_services = len(services_status)

                if healthy_services == total_services:
                    overall_status = "healthy"
                elif healthy_services > 0:
                    overall_status = "degraded"
                else:
                    overall_status = "unhealthy"

                # Get WebSocket service data
                websocket_data = services_status.get("websocket-ingestion", {})
                websocket_health = websocket_data.get("health_data", {})
                connection_data = websocket_health.get("connection", {})
                subscription_data = websocket_health.get("subscription", {})

                # Return simplified response with real WebSocket data
                return {
                    "overall_status": overall_status,
                    "admin_api_status": "healthy",
                    "ingestion_service": {
                        "status": overall_status,
                        "websocket_connection": {
                            "is_connected": connection_data.get("is_running", False),
                            "last_connection_time": websocket_health.get("timestamp", datetime.now().isoformat()),
                            "connection_attempts": connection_data.get("connection_attempts", 0),
                            "last_error": connection_data.get("last_error"),
                        },
                        "event_processing": {
                            "status": "healthy" if subscription_data.get("is_subscribed", False) else "degraded",
                            "events_per_minute": subscription_data.get("event_rate_per_minute", 0.0),
                            "total_events": subscription_data.get("total_events_received", 0),
                            "error_rate": 0,
                        },
                        "weather_enrichment": {
                            "enabled": True,
                            "cache_hits": websocket_health.get("weather_enrichment", {}).get("cache_hits", 0),
                            "api_calls": websocket_health.get("weather_enrichment", {}).get("weather_client_stats", {}).get("total_requests", 0),
                            "last_error": None,
                        },
                        "influxdb_storage": {
                            "is_connected": services_status.get("influxdb", {}).get("status") == "healthy",
                            "last_write_time": datetime.now().isoformat(),
                            "write_errors": 0,
                        },
                    },
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                logger.exception(f"Error getting health status: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get health status",
                )

        @self.router.get("/stats")
        async def get_stats(period: str = "1h"):
            """Get simplified statistics for dashboard"""
            try:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "period": period,
                    "metrics": {
                        "total_events": 0,
                        "events_per_minute": 0,
                        "processing_time_avg": 0,
                        "error_rate": 0,
                    },
                    "trends": {},
                    "alerts": [],
                }
            except Exception as e:
                logger.exception(f"Error getting statistics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get statistics",
                )

    async def _check_services_simple(self) -> dict[str, dict[str, Any]]:
        """Check service health with simplified logic"""
        services_status = {}

        for service_name, service_url in self.service_urls.items():
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.get(f"{service_url}/health") as response:
                        if response.status == 200:
                            # Get detailed health data for WebSocket service
                            if service_name == "websocket-ingestion":
                                health_data = await response.json()
                                services_status[service_name] = {
                                    "status": "healthy",
                                    "response_time": 0,
                                    "health_data": health_data,
                                }
                            else:
                                services_status[service_name] = {"status": "healthy", "response_time": 0}
                        else:
                            services_status[service_name] = {"status": "unhealthy", "error": f"HTTP {response.status}"}
            except Exception as e:
                services_status[service_name] = {"status": "unhealthy", "error": str(e)}

        return services_status



# Create router instance
simple_health_service = SimpleHealthService()
router = simple_health_service.router
