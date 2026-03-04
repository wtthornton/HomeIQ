"""Activity Writer Service — FastAPI application and routes."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from homeiq_observability.logging_config import setup_logging

from . import __version__
from .service import ActivityWriterService

load_dotenv()

SERVICE_NAME: str = "activity-writer"
SERVICE_VERSION: str = __version__

logger = setup_logging(SERVICE_NAME)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

activity_writer: ActivityWriterService | None = None


async def startup() -> None:
    """Create and start the background writer service."""
    global activity_writer  # noqa: PLW0603
    activity_writer = ActivityWriterService()
    await activity_writer.startup()


async def shutdown() -> None:
    """Gracefully stop the writer service."""
    if activity_writer:
        await activity_writer.shutdown()


app = FastAPI(
    title="Activity Writer Service",
    description="Periodic activity recognition pipeline",
    version=SERVICE_VERSION,
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with service info and available routes."""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": ["/health", "/metrics"],
    }


@app.get("/health")
async def health() -> JSONResponse:
    """Liveness/health check for container orchestration."""
    if not activity_writer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    healthy = activity_writer.cycles_failed == 0 or activity_writer.last_successful_run is not None
    status = "healthy" if healthy else "degraded"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": status,
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            **activity_writer.get_metrics(),
        },
    )


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Return cycle success/failure metrics."""
    if not activity_writer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return activity_writer.get_metrics()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVICE_PORT", "8035"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")  # noqa: S104
