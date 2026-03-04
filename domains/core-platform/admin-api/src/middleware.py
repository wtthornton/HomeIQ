"""Middleware configuration for the Admin API service.

Handles observability (OpenTelemetry tracing, correlation IDs),
CORS policy, rate limiting, and request logging.
"""

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from homeiq_observability.correlation_middleware import FastAPICorrelationMiddleware
from homeiq_observability.logging_config import setup_logging

# Import observability modules
try:
    from homeiq_observability.observability import (
        CorrelationMiddleware as ObservabilityCorrelationMiddleware,
    )
    from homeiq_observability.observability import instrument_fastapi, setup_tracing

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

from homeiq_data.rate_limiter import RateLimiter, rate_limit_middleware

logger = setup_logging("admin-api.middleware")


def setup_observability(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing and correlation middleware.

    Uses ObservabilityCorrelationMiddleware when available,
    otherwise falls back to FastAPICorrelationMiddleware.

    Args:
        app: The FastAPI application instance.
    """
    if OBSERVABILITY_AVAILABLE:
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        if setup_tracing("admin-api", otlp_endpoint):
            logger.info("OpenTelemetry tracing configured")
        if instrument_fastapi(app, "admin-api"):
            logger.info("FastAPI app instrumented for tracing")
        app.add_middleware(ObservabilityCorrelationMiddleware)
    else:
        app.add_middleware(FastAPICorrelationMiddleware)


def setup_cors(
    app: FastAPI,
    *,
    origins: list[str],
    methods: list[str],
    headers: list[str],
) -> None:
    """Configure CORS middleware with safe credential handling.

    Disables ``allow_credentials`` when wildcard origins are used
    to prevent browser security bypass.

    Args:
        app: The FastAPI application instance.
        origins: Allowed CORS origins.
        methods: Allowed HTTP methods.
        headers: Allowed request headers.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=methods,
        allow_headers=headers,
    )


def register_rate_limit_middleware(app: FastAPI, rate_limiter: RateLimiter) -> None:
    """Register the rate limiting middleware on the FastAPI app.

    Args:
        app: The FastAPI application instance.
        rate_limiter: Configured rate limiter instance.
    """

    @app.middleware("http")
    async def apply_rate_limit(request: Request, call_next: Any) -> Response:
        return await rate_limit_middleware(request, call_next, rate_limiter)


def register_logging_middleware(app: FastAPI) -> tuple:
    """Register the request logging middleware and return counter references.

    Returns a mutable list ``[request_count, error_count]`` that the
    middleware increments on each request. Callers can read these
    counters to compute error rates.

    Args:
        app: The FastAPI application instance.

    Returns:
        Mutable list ``[request_count, error_count]``.
    """
    counters = [0, 0]  # [request_count, error_count]

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Response:
        req_start = datetime.now(UTC)
        response = await call_next(request)
        counters[0] += 1
        if response.status_code >= 500:
            counters[1] += 1
        elapsed = (datetime.now(UTC) - req_start).total_seconds()
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {elapsed:.3f}s"
        )
        return response

    return counters
