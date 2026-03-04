"""Activity Writer Service -- FastAPI application and routes."""

from __future__ import annotations

import logging
import sys
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from . import __version__
from .config import settings
from .service import ActivityWriterService


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()
logger = logging.getLogger(__name__)

SERVICE_VERSION: str = __version__

# ---------------------------------------------------------------------------
# Shared service instance
# ---------------------------------------------------------------------------

activity_writer: ActivityWriterService | None = None


async def _startup_writer() -> None:
    """Create and start the background writer service."""
    global activity_writer  # noqa: PLW0603
    activity_writer = ActivityWriterService()
    await activity_writer.startup()


async def _shutdown_writer() -> None:
    """Gracefully stop the writer service."""
    if activity_writer:
        await activity_writer.shutdown()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_writer, name="writer")
lifespan.on_shutdown(_shutdown_writer, name="writer")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version=SERVICE_VERSION,
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Activity Writer Service",
    version=SERVICE_VERSION,
    description="Periodic activity recognition pipeline",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with service info and available routes."""
    return {
        "service": settings.service_name,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": ["/health", "/metrics"],
    }


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Return cycle success/failure metrics."""
    if not activity_writer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return activity_writer.get_metrics()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        log_level="info",
    )
