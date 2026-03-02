"""FastAPI application factory for HomeIQ services.

Standardizes app creation across all 34+ FastAPI services with
consistent middleware, exception handling, and health endpoint.

Usage::

    from homeiq_resilience import create_app, StandardHealthCheck

    health = StandardHealthCheck(service_name="my-service", version="1.0.0")

    app = create_app(
        title="My Service",
        version="1.0.0",
        lifespan=my_lifespan,
        health_check=health,
    )
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .health_check import StandardHealthCheck

logger = logging.getLogger(__name__)


def create_app(
    title: str,
    version: str = "1.0.0",
    description: str = "",
    *,
    lifespan: Any | None = None,
    health_check: StandardHealthCheck | None = None,
    cors_origins: list[str] | None = None,
    cors_allow_credentials: bool = False,
    include_request_id: bool = True,
    include_timing: bool = True,
) -> FastAPI:
    """Create a standard HomeIQ FastAPI application.

    Parameters
    ----------
    title:
        Application title for OpenAPI docs.
    version:
        Application version string.
    description:
        Application description for OpenAPI docs.
    lifespan:
        Optional async context manager for startup/shutdown.
    health_check:
        Optional ``StandardHealthCheck`` instance.  Its router is
        auto-included if provided.
    cors_origins:
        List of allowed CORS origins.  Defaults to ``["*"]``.
    cors_allow_credentials:
        Whether to allow credentials in CORS.  Should be ``False``
        when origins is ``["*"]``.
    include_request_id:
        Add ``X-Request-ID`` header middleware.
    include_timing:
        Add ``X-Process-Time`` header middleware.
    """
    app = FastAPI(
        title=title,
        version=version,
        description=description,
        lifespan=lifespan,
    )

    # --- CORS middleware ---
    origins = cors_origins if cors_origins is not None else ["*"]
    # Security: never allow credentials with wildcard origins
    safe_credentials = cors_allow_credentials and "*" not in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=safe_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Request ID middleware ---
    if include_request_id:

        @app.middleware("http")
        async def _request_id_middleware(request: Request, call_next: Any) -> Response:
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
            request.state.request_id = request_id
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

    # --- Timing middleware ---
    if include_timing:

        @app.middleware("http")
        async def _timing_middleware(request: Request, call_next: Any) -> Response:
            start = time.monotonic()
            response = await call_next(request)
            elapsed = time.monotonic() - start
            response.headers["X-Process-Time"] = f"{elapsed:.4f}"
            return response

    # --- Standard exception handler ---
    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("Unhandled exception [request_id=%s]", request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": request_id,
            },
        )

    # --- Health check router ---
    if health_check is not None:
        app.include_router(health_check.router)

    # --- Root endpoint ---
    @app.get("/")
    async def _root() -> dict[str, str]:
        return {
            "service": title,
            "version": version,
            "status": "running",
        }

    return app
