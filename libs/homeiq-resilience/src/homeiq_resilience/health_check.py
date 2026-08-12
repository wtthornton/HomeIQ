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
        "git_sha": "0abbae91",
        "build_time": "2026-03-13T19:00:00Z",
        "uptime_seconds": 3600,
        "checks": [
            {"name": "database", "status": "healthy", "latency_ms": 2.1},
            {"name": "ha", "status": "unhealthy", "latency_ms": 5012.3}
        ]
    }
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Type alias for dependency check functions. Each returns either a bool
# (True = healthy) or a dict with an "ok" bool plus arbitrary detail keys
# (credential presence, age of last successful fetch, ...). The detail form
# feeds the ``/ready`` endpoint (TAP-5903).
HealthCheckFn = Callable[[], Awaitable[bool | dict[str, Any]]]


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
        self.git_sha = os.environ.get("GIT_SHA", "unknown")
        self.build_time = os.environ.get("BUILD_TIME", "unknown")
        self.include_timestamp = include_timestamp
        self._start_time = time.monotonic()
        self._checks: list[tuple[str, HealthCheckFn]] = []

        self.router = APIRouter(tags=["health"])
        self.router.add_api_route("/health", self._health_endpoint, methods=["GET"])
        # /health is liveness (always 200 — Docker restarts on it); /ready is
        # strict: 503 when any registered check fails OR when no checks are
        # registered, because a service that cannot demonstrate readiness must
        # not read as ready. A green that cannot go red is worse than no
        # signal (TAP-5903: 58 containers reported healthy while 7 of 8
        # collectors produced no data).
        self.router.add_api_route("/ready", self._ready_endpoint, methods=["GET"])

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

    async def _run_checks(self) -> list[dict[str, Any]]:
        """Run every registered check, normalizing bool and dict returns."""
        results: list[dict[str, Any]] = []
        for name, fn in self._checks:
            start = time.monotonic()
            detail: dict[str, Any] = {}
            try:
                raw = await fn()
                if isinstance(raw, dict):
                    ok = bool(raw.get("ok", False))
                    detail = {k: v for k, v in raw.items() if k != "ok"}
                else:
                    ok = bool(raw)
            except Exception:
                ok = False
                logger.warning("Health check '%s' raised an exception", name, exc_info=True)
            elapsed_ms = (time.monotonic() - start) * 1000
            entry: dict[str, Any] = {
                "name": name,
                "ok": ok,
                "latency_ms": round(elapsed_ms, 1),
            }
            if detail:
                entry["detail"] = detail
            results.append(entry)
        return results

    async def _health_endpoint(self) -> dict[str, Any]:
        """Handler for ``GET /health``."""
        raw_results = await self._run_checks()
        checks_results: list[dict[str, Any]] = [
            {
                "name": r["name"],
                "status": "healthy" if r["ok"] else "unhealthy",
                "latency_ms": r["latency_ms"],
            }
            for r in raw_results
        ]
        all_healthy = all(r["ok"] for r in raw_results)

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
            "git_sha": self.git_sha,
            "build_time": self.build_time,
            "uptime_seconds": round(time.monotonic() - self._start_time),
        }

        if checks_results:
            response["checks"] = checks_results
            # Build dependencies summary (name -> friendly status)
            dependencies: dict[str, str] = {}
            for check_result in checks_results:
                raw = check_result["status"]
                dependencies[check_result["name"]] = "ok" if raw == "healthy" else "down"
            response["dependencies"] = dependencies

        if self.include_timestamp:
            response["timestamp"] = datetime.now(UTC).isoformat()

        return response

    async def _ready_endpoint(self) -> JSONResponse:
        """Handler for ``GET /ready`` — strict, dependency-aware readiness."""
        results = await self._run_checks()
        payload: dict[str, Any] = {
            "service": self.service_name,
            "version": self.version,
            "checks": results,
        }
        if self.include_timestamp:
            payload["timestamp"] = datetime.now(UTC).isoformat()

        if not results:
            payload["ready"] = False
            payload["reason"] = "no readiness checks registered"
            return JSONResponse(payload, status_code=503)

        ready = all(r["ok"] for r in results)
        payload["ready"] = ready
        if not ready:
            payload["reason"] = ", ".join(r["name"] for r in results if not r["ok"]) + " not ready"
        return JSONResponse(payload, status_code=200 if ready else 503)

    async def get_status(self) -> dict[str, Any]:
        """Programmatic access to health status (same as endpoint response)."""
        return await self._health_endpoint()
