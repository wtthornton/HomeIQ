"""Prometheus metrics middleware and endpoint for HomeIQ services.

Provides automatic HTTP request instrumentation and a /metrics endpoint
in Prometheus text exposition format.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


def create_metrics_registry(service_name: str) -> dict[str, Any]:
    """Create a Prometheus metrics registry with standard HomeIQ metrics.

    Returns a dict with 'registry' and individual metric references.
    """
    registry = CollectorRegistry()

    request_count = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
        registry=registry,
    )
    request_latency = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
        registry=registry,
    )
    error_count = Counter(
        "http_errors_total",
        "Total HTTP errors (4xx and 5xx)",
        ["method", "path", "status"],
        registry=registry,
    )
    active_connections = Gauge(
        "http_active_connections",
        "Number of active HTTP connections",
        registry=registry,
    )

    # Pool metrics (populated by pool_metrics_collector if DB is configured)
    pool_checked_out = Gauge(
        "db_pool_checked_out",
        "Number of checked-out database connections",
        registry=registry,
    )
    pool_utilization = Gauge(
        "db_pool_utilization_percent",
        "Database connection pool utilization percentage",
        registry=registry,
    )

    return {
        "registry": registry,
        "request_count": request_count,
        "request_latency": request_latency,
        "error_count": error_count,
        "active_connections": active_connections,
        "pool_checked_out": pool_checked_out,
        "pool_utilization": pool_utilization,
        "service_name": service_name,
    }


def add_prometheus_middleware(app: FastAPI, metrics: dict[str, Any]) -> None:
    """Add Prometheus instrumentation middleware and /metrics endpoint."""
    registry = metrics["registry"]
    request_count = metrics["request_count"]
    request_latency = metrics["request_latency"]
    error_count = metrics["error_count"]
    active_connections = metrics["active_connections"]

    # Paths to exclude from metrics collection
    _excluded = {"/metrics", "/health", "/", "/docs", "/openapi.json", "/redoc"}

    @app.middleware("http")
    async def _prometheus_middleware(request: Request, call_next: Any) -> Response:
        path = request.url.path
        if path in _excluded:
            return await call_next(request)

        method = request.method
        active_connections.inc()
        start = time.monotonic()
        try:
            response = await call_next(request)
            status = str(response.status_code)
            request_count.labels(method=method, path=path, status=status).inc()
            if response.status_code >= 400:
                error_count.labels(method=method, path=path, status=status).inc()
            return response
        except Exception:
            request_count.labels(method=method, path=path, status="500").inc()
            error_count.labels(method=method, path=path, status="500").inc()
            raise
        finally:
            elapsed = time.monotonic() - start
            request_latency.labels(method=method, path=path).observe(elapsed)
            active_connections.dec()

    @app.get("/metrics", include_in_schema=False)
    async def _metrics_endpoint() -> PlainTextResponse:
        # Try to update pool metrics before serving
        _update_pool_metrics(metrics)
        data = generate_latest(registry)
        return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)


def _update_pool_metrics(metrics: dict[str, Any]) -> None:
    """Attempt to update database pool metrics from homeiq-data."""
    try:
        from homeiq_data.database_pool import (  # noqa: F401
            _engines,
            check_pool_health,
        )

        for url in list(_engines.keys()):
            stats = check_pool_health(url)
            if "error" not in stats:
                metrics["pool_checked_out"].set(stats.get("checked_out", 0))
                metrics["pool_utilization"].set(stats.get("utilization_percent", 0))
                break  # Use first engine's stats
    except (ImportError, Exception):
        pass  # homeiq-data not installed or no engines — skip pool metrics
