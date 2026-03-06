"""FastAPI application wiring: middleware, routers, error handlers.

Extracted from main.py to keep the service module under 200 lines
for maintainability index compliance.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from homeiq_observability.correlation_middleware import FastAPICorrelationMiddleware
from homeiq_observability.endpoints import create_integration_router
from homeiq_observability.logging_config import setup_logging

from .activity_endpoints import router as activity_router
from .alert_endpoints import AlertEndpoints
from .analytics_endpoints import router as analytics_router
from .api.mcp_router import router as mcp_router
from .automation_analytics_endpoints import router as automation_analytics_router
from .automation_internal_endpoints import router as automation_internal_router
from .config_manager import config_manager
from .devices_endpoints import router as devices_router
from .energy_endpoints import router as energy_router
from .evaluation_endpoints import router as evaluation_router
from .events_endpoints import EventsEndpoints
from .ha_automation_endpoints import router as ha_automation_router
from .hygiene_endpoints import router as hygiene_router
from .jobs_endpoints import router as jobs_router
from .metrics_endpoints import create_metrics_router
from .metrics_state import metrics_buffer
from .sports_endpoints import router as sports_router

if TYPE_CHECKING:
    from fastapi import FastAPI

    from ._service import DataAPIService

logger = setup_logging("data-api")

# Observability imports (optional)
try:
    from homeiq_observability.observability import (
        CorrelationMiddleware as ObservabilityCorrelationMiddleware,
    )
    from homeiq_observability.observability import instrument_fastapi, setup_tracing

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False


def configure_middleware(app: FastAPI, svc: DataAPIService) -> None:
    """Add observability, CORS, rate-limit, and metrics middleware."""
    # Observability / tracing
    if OBSERVABILITY_AVAILABLE:
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        if setup_tracing("data-api", otlp_endpoint):
            logger.info("OpenTelemetry tracing configured")
        if instrument_fastapi(app, "data-api"):
            logger.info("FastAPI app instrumented for tracing")
        app.add_middleware(ObservabilityCorrelationMiddleware)
    else:
        app.add_middleware(FastAPICorrelationMiddleware)

    # CORS — never allow credentials with wildcard origins
    _creds = "*" not in svc.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=svc.cors_origins,
        allow_credentials=_creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    from homeiq_data.rate_limiter import rate_limit_middleware

    @app.middleware("http")
    async def apply_rate_limit(request, call_next):  # noqa: ANN001,ANN201
        return await rate_limit_middleware(request, call_next, svc.rate_limiter)

    # Metrics collection
    @app.middleware("http")
    async def collect_metrics(request, call_next):  # noqa: ANN001,ANN201
        if request.url.path == "/health":
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        svc.total_requests += 1
        is_error = response.status_code >= 400
        if is_error:
            svc.failed_requests += 1
        metrics_buffer.record_request(elapsed_ms, is_error)
        return response


def register_routers(app: FastAPI, svc: DataAPIService) -> None:
    """Include all endpoint routers with authentication dependency."""
    auth = [Depends(svc.auth_manager.get_current_user)]

    # Authenticated routers
    _routers = [
        (activity_router, "/api/v1", None),
        (EventsEndpoints().router, "/api/v1", "Events"),
        (devices_router, "", "Devices & Entities"),
        (AlertEndpoints().router, "/api/v1", "Alerts"),
        (create_metrics_router(), "/api/v1", "Metrics"),
        (create_integration_router(config_manager), "/api/v1", "Integrations"),
        (sports_router, "/api/v1", "Sports Data"),
        (ha_automation_router, "/api/v1", "Home Assistant Automation"),
        (analytics_router, "/api/v1", "Analytics"),
        (energy_router, "/api/v1", "Energy"),
        (hygiene_router, "", "Device Hygiene"),
        (evaluation_router, "/api/v1", "Agent Evaluation"),
        (jobs_router, "", "Background Jobs"),
        (mcp_router, "", "MCP Tools"),
    ]
    for router, prefix, tag in _routers:
        kwargs: dict = {"dependencies": auth}
        if prefix:
            kwargs["prefix"] = prefix
        if tag:
            kwargs["tags"] = [tag]
        app.include_router(router, **kwargs)

    # Internal (no auth) routers
    app.include_router(automation_internal_router, tags=["Automation Trace (Internal)"])
    app.include_router(
        automation_analytics_router,
        prefix="/api/v1",
        tags=["Automation Analytics"],
        dependencies=auth,
    )
