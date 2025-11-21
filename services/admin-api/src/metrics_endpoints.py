"""
Metrics API Endpoints
Epic 17.3: Essential Performance Metrics
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

# Add shared directory to path for imports
sys.path.append(str(Path(__file__).parent / "../../shared"))

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from shared.metrics_collector import MetricsCollector, get_metrics_collector

logger = logging.getLogger(__name__)


class ServiceMetrics(BaseModel):
    """Service metrics model"""
    service: str
    timestamp: str
    uptime_seconds: float
    counters: dict[str, int]
    gauges: dict[str, float]
    timers: dict[str, dict[str, float]]
    system: dict[str, Any]


class MetricsEndpoints:
    """Metrics monitoring endpoints"""

    def __init__(self, metrics_collector: MetricsCollector | None = None):
        """Initialize metrics endpoints"""
        self.router = APIRouter()
        self.metrics_collector = metrics_collector or get_metrics_collector("admin-api")
        self.service_urls = {
            "websocket-ingestion": os.getenv("WEBSOCKET_INGESTION_URL", "http://localhost:8001"),
            "data-retention": os.getenv("DATA_RETENTION_URL", "http://localhost:8080"),
            "log-aggregator": os.getenv("LOG_AGGREGATOR_URL", "http://localhost:8015"),
        }

        self._add_routes()

    def _add_routes(self):
        """Add metrics routes"""

        @self.router.get("/metrics")
        async def get_admin_metrics():
            """Get admin-api service metrics"""
            try:
                return self.metrics_collector.get_all_metrics()
            except Exception as e:
                logger.exception(f"Error getting metrics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get metrics: {e!s}",
                )

        @self.router.get("/metrics/all", response_model=dict[str, ServiceMetrics])
        async def get_all_services_metrics():
            """Get metrics from all services"""
            try:
                all_metrics = {}

                # Get admin-api metrics
                all_metrics["admin-api"] = self.metrics_collector.get_all_metrics()

                # Get metrics from other services
                for service_name, service_url in self.service_urls.items():
                    try:
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                            async with session.get(f"{service_url}/metrics") as response:
                                if response.status == 200:
                                    all_metrics[service_name] = await response.json()
                                else:
                                    logger.warning(f"Failed to get metrics from {service_name}: HTTP {response.status}")
                    except Exception as e:
                        logger.warning(f"Could not fetch metrics from {service_name}: {e}")

                return all_metrics
            except Exception as e:
                logger.exception(f"Error getting all services metrics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get all services metrics: {e!s}",
                )

        @self.router.get("/metrics/system")
        async def get_system_metrics():
            """Get system metrics for admin-api"""
            try:
                return self.metrics_collector.get_system_metrics()
            except Exception as e:
                logger.exception(f"Error getting system metrics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get system metrics: {e!s}",
                )

        @self.router.get("/metrics/summary")
        async def get_metrics_summary():
            """Get aggregated metrics summary across all services"""
            try:
                all_metrics = {}

                # Collect metrics from all services
                for service_name in ["admin-api", *list(self.service_urls.keys())]:
                    try:
                        if service_name == "admin-api":
                            metrics = self.metrics_collector.get_all_metrics()
                        else:
                            service_url = self.service_urls[service_name]
                            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                                async with session.get(f"{service_url}/metrics") as response:
                                    if response.status == 200:
                                        metrics = await response.json()
                                    else:
                                        continue

                        all_metrics[service_name] = metrics
                    except Exception as e:
                        logger.debug(f"Could not fetch metrics from {service_name}: {e}")
                        continue

                # Aggregate summary
                summary = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "services_count": len(all_metrics),
                    "services": list(all_metrics.keys()),
                    "aggregate": {
                        "total_cpu_percent": 0.0,
                        "total_memory_mb": 0.0,
                        "total_uptime_seconds": 0.0,
                        "total_requests": 0,
                        "avg_response_time_ms": 0.0,
                    },
                }

                # Calculate aggregates
                total_requests = 0
                total_response_time = 0.0
                response_count = 0

                for service_name, metrics in all_metrics.items():
                    # System metrics
                    if "system" in metrics:
                        if "cpu" in metrics["system"]:
                            summary["aggregate"]["total_cpu_percent"] += metrics["system"]["cpu"].get("percent", 0)
                        if "memory" in metrics["system"]:
                            summary["aggregate"]["total_memory_mb"] += metrics["system"]["memory"].get("rss_mb", 0)

                    # Uptime
                    summary["aggregate"]["total_uptime_seconds"] += metrics.get("uptime_seconds", 0)

                    # Request counts
                    if "counters" in metrics:
                        for key, value in metrics["counters"].items():
                            if "request" in key.lower() or "call" in key.lower():
                                total_requests += value

                    # Response times
                    if "timers" in metrics:
                        for key, timer in metrics["timers"].items():
                            if "request" in key.lower() or "response" in key.lower():
                                total_response_time += timer.get("avg_ms", 0)
                                response_count += 1

                summary["aggregate"]["total_requests"] = total_requests
                if response_count > 0:
                    summary["aggregate"]["avg_response_time_ms"] = total_response_time / response_count

                return summary
            except Exception as e:
                logger.exception(f"Error getting metrics summary: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get metrics summary: {e!s}",
                )

        @self.router.post("/metrics/reset")
        async def reset_metrics():
            """Reset metrics counters for admin-api"""
            try:
                self.metrics_collector.reset_metrics()
                return {
                    "status": "success",
                    "message": "Metrics reset successfully",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            except Exception as e:
                logger.exception(f"Error resetting metrics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reset metrics: {e!s}",
                )


def create_metrics_router(metrics_collector: MetricsCollector | None = None) -> APIRouter:
    """
    Create and return metrics router

    Args:
        metrics_collector: Optional metrics collector instance

    Returns:
        FastAPI APIRouter with metrics endpoints
    """
    endpoints = MetricsEndpoints(metrics_collector)
    return endpoints.router

