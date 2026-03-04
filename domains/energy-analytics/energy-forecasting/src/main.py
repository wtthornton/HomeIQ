"""
Energy Forecasting Service - Main Application

FastAPI service that provides energy consumption forecasting.

Port: 8037
"""

import asyncio
import logging
import sys
from pathlib import Path

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from . import __version__
from .api.routes import load_model, router
from .config import settings


def _configure_logging() -> None:
    """Configure structured logging for the service."""
    import os

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.dev.ConsoleRenderer()
                if os.getenv("DEBUG")
                else structlog.processors.JSONRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Configure structured logging
_configure_logging()
logger = structlog.get_logger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeout."""

    def __init__(self, app, timeout: float = 30.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout,
            )
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out"},
            )


def _load_forecasting_model() -> None:
    """Load energy forecasting model if available."""
    model_path = Path(settings.model_path)

    # Check for config in either format
    config_pkl = model_path.with_suffix(".config.pkl")
    config_json = model_path.with_suffix(".config.json")

    if config_pkl.exists() or config_json.exists():
        success = load_model(model_path)
        if success:
            logger.info("Model loaded successfully", path=str(model_path))
        else:
            logger.warning("Failed to load model", path=str(model_path))
    else:
        logger.info(
            "No model found. Train a model and save to the configured path.",
            path=str(model_path),
        )


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

async def _startup_model() -> None:
    """Load the forecasting model on startup."""
    _load_forecasting_model()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_model, name="model")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version=__version__,
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Energy Forecasting Service",
    version=__version__,
    description="ML-powered energy consumption forecasting for HomeIQ",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Add timeout middleware
app.add_middleware(TimeoutMiddleware, timeout=settings.request_timeout_seconds)

# Include routers
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": __version__,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
