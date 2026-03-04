"""Public endpoint handlers for the Admin API service.

Contains the unauthenticated health/metrics endpoints and
their associated response-builder logic. Extracted from
AdminAPIService to keep main.py under 300 lines.
"""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from homeiq_observability.logging_config import setup_logging
from homeiq_observability.monitoring import StatsEndpoints

from .helpers import (
    build_health_summary,
    compute_error_rate,
    empty_real_time_metrics,
    format_uptime,
    gather_dependency_checks,
)

logger = setup_logging("admin-api.endpoints")


def register_public_endpoints(
    app: FastAPI,
    *,
    stats_endpoints: StatsEndpoints,
    allow_anonymous: bool,
    docs_enabled: bool,
    rate_limiter: Any,
    start_time: float,
    counters: list[int],
) -> None:
    """Register unauthenticated public endpoints on *app*.

    Args:
        app: FastAPI application instance.
        stats_endpoints: StatsEndpoints for real-time metrics.
        allow_anonymous: Whether anonymous access is allowed.
        docs_enabled: Whether API docs are enabled.
        rate_limiter: Rate limiter instance for stats.
        start_time: Module start time (``time.time()`` epoch).
        counters: Mutable ``[request_count, error_count]`` list.
    """

    @app.get("/api/health")
    async def simple_health() -> dict[str, Any]:
        """Return simple health status."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "admin-api",
        }

    @app.get("/api/v1/health")
    async def enhanced_health() -> dict[str, Any]:
        """Return enhanced health with dependency checks and metrics."""
        return await _build_enhanced_health(
            allow_anonymous=allow_anonymous,
            docs_enabled=docs_enabled,
            rate_limiter=rate_limiter,
            start_time=start_time,
            counters=counters,
        )

    @app.get("/api/metrics/realtime")
    async def simple_metrics() -> dict[str, Any]:
        """Return static real-time metrics stub."""
        return {
            "success": True,
            "events_per_second": 0.0,
            "active_api_calls": 0,
            "active_sources": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/v1/real-time-metrics")
    async def rt_metrics() -> dict[str, Any]:
        """Return consolidated real-time metrics (no auth required)."""
        return await _build_real_time_metrics(stats_endpoints)


async def _build_enhanced_health(
    *,
    allow_anonymous: bool,
    docs_enabled: bool,
    rate_limiter: Any,
    start_time: float,
    counters: list[int],
) -> dict[str, Any]:
    """Build enhanced health response with dependency checks."""
    try:
        up = time.time() - start_time
        deps = await gather_dependency_checks()
        ok = all(d.get("status") == "healthy" for d in deps)
        return {
            "status": "healthy" if ok else "degraded",
            "service": "admin-api",
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": round(up, 2),
            "uptime_human": format_uptime(up),
            "dependencies": deps,
            "security": {
                "api_key_required": not allow_anonymous,
                "docs_enabled": docs_enabled,
                "rate_limit": rate_limiter.get_stats(),
            },
            "metrics": {
                "uptime_human": format_uptime(up),
                "uptime_seconds": round(up, 2),
                "total_requests": counters[0],
                "error_rate": compute_error_rate(counters[0], counters[1]),
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "admin-api",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
        }


async def _build_real_time_metrics(
    stats_endpoints: StatsEndpoints,
) -> dict[str, Any]:
    """Build real-time metrics from stats endpoints."""
    try:
        er = await stats_endpoints._get_current_event_rate()
        api = await stats_endpoints._get_all_api_metrics()
        ds = await stats_endpoints._get_active_data_sources()
        return {
            "events_per_hour": er * 3600,
            "api_calls_active": api["active_calls"],
            "data_sources_active": ds,
            "api_metrics": api["api_metrics"],
            "inactive_apis": api["inactive_apis"],
            "error_apis": api["error_apis"],
            "total_apis": api["total_apis"],
            "health_summary": build_health_summary(api),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        return empty_real_time_metrics(error=str(e))
