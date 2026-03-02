"""Unified health check endpoint for HomeIQ services.

Provides a standard ``/health`` endpoint that returns consistent JSON
across all 50 microservices, replacing 8+ divergent implementations.

Usage::

    from homeiq_resilience import StandardHealthCheck

    health = StandardHealthCheck(
        service_name="device-recommender",
        version="1.0.0",
    )
    health.register_check("database", check_db_connection)
    health.register_check("ha", check_ha_connection)

    # In your FastAPI app:
    app.include_router(health.router)

Response format::

    {
        "status": "healthy",
        "service": "device-recommender",
        "version": "1.0.0",
        "uptime_seconds": 3600,
        "checks": [
            {"name": "database", "status": "healthy", "latency_ms": 2.1},
            {"name": "ha", "status": "unhealthy", "latency_ms": 5012.3}
        ]
    }
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Type alias for dependency check functions.
# Each must return True (healthy) or False (unhealthy).
HealthCheckFn = Callable[[], Awaitable[bool]]


class StandardHealthCheck:
    """Unified health check that auto-registers a ``/health`` GET endpoint.

    Parameters
    ----------
    service_name:
        Human-readable service name included in every response.
    version:
        Application version string.
    include_timestamp:
        Whether to include an ISO-8601 timestamp in the response.
    """

    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        *,
        include_timestamp: bool = True,
    ) -> None:
        self.service_name = service_name
        self.version = version
        self.include_timestamp = include_timestamp
        self._start_time = time.monotonic()
        self._checks: list[tuple[str, HealthCheckFn]] = []

        self.router = APIRouter(tags=["health"])
        self.router.add_api_route("/health", self._health_endpoint, methods=["GET"])

    def register_check(self, name: str, fn: HealthCheckFn) -> None:
        """Register a named dependency check.

        Parameters
        ----------
        name:
            Human-readable name (e.g. ``"database"``, ``"influxdb"``).
        fn:
            Async callable returning ``True`` if the dependency is healthy.
        """
        self._checks.append((name, fn))

    async def _health_endpoint(self) -> dict[str, Any]:
        """Handler for ``GET /health``."""
        checks_results: list[dict[str, Any]] = []
        all_healthy = True

        for name, fn in self._checks:
            start = time.monotonic()
            try:
                ok = await fn()
            except Exception:
                ok = False
                logger.warning("Health check '%s' raised an exception", name, exc_info=True)
            elapsed_ms = (time.monotonic() - start) * 1000

            status = "healthy" if ok else "unhealthy"
            if not ok:
                all_healthy = False

            checks_results.append({
                "name": name,
                "status": status,
                "latency_ms": round(elapsed_ms, 1),
            })

        # Determine overall status
        if not self._checks or all_healthy:
            overall = "healthy"
        elif all(c["status"] == "unhealthy" for c in checks_results):
            overall = "unhealthy"
        else:
            overall = "degraded"

        response: dict[str, Any] = {
            "status": overall,
            "service": self.service_name,
            "version": self.version,
            "uptime_seconds": round(time.monotonic() - self._start_time),
        }

        if checks_results:
            response["checks"] = checks_results

        if self.include_timestamp:
            response["timestamp"] = datetime.now(UTC).isoformat()

        return response

    async def get_status(self) -> dict[str, Any]:
        """Programmatic access to health status (same as endpoint response)."""
        return await self._health_endpoint()
