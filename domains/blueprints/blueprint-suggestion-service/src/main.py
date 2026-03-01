"""Main FastAPI application for Blueprint Suggestion Service."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import init_schema_cache, router
from .config import settings
from .database import close_db, get_db_context, init_db

from homeiq_resilience import GroupHealthCheck, wait_for_dependency


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# Configure logging
_configure_logging()
logger = logging.getLogger(__name__)

# Module-level health checker, initialised during lifespan.
_group_health: GroupHealthCheck | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    global _group_health

    # Startup
    logger.info("Starting %s on port %s", settings.service_name, settings.service_port)
    db_ok = await init_db()
    if db_ok:
        # Cache schema check so we don't run PRAGMA on every GET /suggestions
        async with get_db_context() as db:
            await init_schema_cache(db)
    else:
        logger.warning("Database unavailable — starting in degraded mode")

    # Probe cross-group dependencies (non-fatal)
    data_api_available = await wait_for_dependency(
        url=settings.data_api_url, name="data-api", max_retries=10,
    )

    # Structured group health
    _group_health = GroupHealthCheck(
        group_name="automation-intelligence", version="1.0.0",
    )
    _group_health.register_dependency("data-api", settings.data_api_url)

    if not data_api_available:
        _group_health.add_degraded_feature(
            "blueprint-matching (data-api unreachable at startup)"
        )

    logger.info("Blueprint Suggestion Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Blueprint Suggestion Service...")
    await close_db()
    logger.info("Blueprint Suggestion Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Blueprint Suggestion Service",
    description="Matches Home Assistant Blueprints to devices and provides scored suggestions",
    version="1.0.0",
    lifespan=lifespan,
)

def _get_cors_origins() -> list[str]:
    """Get list of allowed CORS origins."""
    if settings.cors_origins:
        return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    return ["*"]  # Development default


# Add CORS middleware
# Never combine allow_credentials=True with wildcard origins (violates CORS spec)
_origins = _get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict:
    """Structured health check with dependency status."""
    if _group_health is None:
        return {"status": "starting", "service": settings.service_name}
    return await _group_health.to_dict()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # nosec B104 — Docker container binds all interfaces
        port=settings.service_port,
        reload=True,
    )
