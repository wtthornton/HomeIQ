"""Helper functions for the Admin API service.

Extracted from main.py to improve maintainability and reduce file size.
Contains dependency health checking, metrics computation, and formatting utilities.
"""

import asyncio
import os
import time
from datetime import UTC, datetime
from typing import Any

import aiohttp
from homeiq_observability.logging_config import setup_logging

logger = setup_logging("admin-api.helpers")


def format_uptime(uptime_seconds: float) -> str:
    """Format uptime seconds into a human-readable string like '2h 15m 30s'."""
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    return f"{hours}h {minutes}m {seconds}s"


def compute_error_rate(request_count: int, error_count: int) -> float:
    """Compute error rate percentage, safe against zero-division."""
    total = request_count if request_count > 0 else 1
    return round((error_count / total) * 100, 2)


def build_health_summary(api_stats: dict[str, Any]) -> dict[str, Any]:
    """Build a health summary dict from aggregated API statistics.

    Args:
        api_stats: Dictionary containing active_calls, inactive_apis,
            error_apis, and total_apis keys.

    Returns:
        Dictionary with healthy, unhealthy, total, and health_percentage fields.
    """
    total = api_stats["total_apis"]
    active = api_stats["active_calls"]
    inactive = api_stats["inactive_apis"]
    errors = api_stats["error_apis"]
    pct = round((active / total) * 100, 1) if total > 0 else 0
    return {
        "healthy": active,
        "unhealthy": inactive + errors,
        "total": total,
        "health_percentage": pct,
    }


async def check_dependency(name: str, url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Check the health of a dependency service by hitting its /health endpoint.

    Args:
        name: Human-readable name of the dependency.
        url: Base URL of the dependency service.
        timeout: HTTP request timeout in seconds.

    Returns:
        Dictionary with name, status, response_time_ms (or error), and last_check.
    """
    try:
        start = time.time()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:  # noqa: SIM117
            async with session.get(f"{url}/health") as response:
                elapsed = (time.time() - start) * 1000
                return {
                    "name": name,
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "response_time_ms": round(elapsed, 2),
                    "last_check": datetime.now(UTC).isoformat(),
                }
    except Exception as e:
        return {
            "name": name,
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now(UTC).isoformat(),
        }


async def gather_dependency_checks() -> list[dict[str, Any]]:
    """Run health checks against all core dependencies concurrently.

    Checks InfluxDB, WebSocket Ingestion, and Data API services
    using environment variables for URL resolution.

    Returns:
        List of dependency health check results.
    """
    influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    websocket_url = os.getenv("WEBSOCKET_INGESTION_URL", "http://websocket-ingestion:8001")
    data_api_url = os.getenv("DATA_API_URL", "http://data-api:8006")

    raw_results = await asyncio.gather(
        check_dependency("InfluxDB", influxdb_url),
        check_dependency("WebSocket Ingestion", websocket_url),
        check_dependency("Data API", data_api_url),
        return_exceptions=True,
    )

    dependencies: list[dict[str, Any]] = []
    for check in raw_results:
        if isinstance(check, Exception):
            dependencies.append({
                "name": "unknown",
                "status": "unhealthy",
                "error": str(check),
                "last_check": datetime.now(UTC).isoformat(),
            })
        else:
            dependencies.append(check)
    return dependencies


_EMPTY_REAL_TIME_METRICS: dict[str, Any] = {
    "events_per_hour": 0,
    "api_calls_active": 0,
    "data_sources_active": [],
    "api_metrics": [],
    "inactive_apis": 0,
    "error_apis": 0,
    "total_apis": 0,
    "health_summary": {
        "healthy": 0,
        "unhealthy": 0,
        "total": 0,
        "health_percentage": 0,
    },
}


def empty_real_time_metrics(error: str | None = None) -> dict[str, Any]:
    """Return an empty real-time metrics response for error fallback.

    Args:
        error: Optional error message to include.

    Returns:
        Dictionary with zeroed metrics and current timestamp.
    """
    result = {**_EMPTY_REAL_TIME_METRICS, "timestamp": datetime.now(UTC).isoformat()}
    if error:
        result["error"] = error
    return result
