"""Main FastAPI application for Blueprint Suggestion Service."""

from __future__ import annotations

import logging
import sys

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api.routes import init_schema_cache, router
from .config import settings
from .database import close_db, get_db_context, init_db


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


# ---------------------------------------------------------------------------
# Startup / shutdown hooks
# ---------------------------------------------------------------------------

async def _startup_db() -> None:
    """Initialize database and cache schema."""
    db_ok = await init_db()
    if db_ok:
        # Cache schema check so we don't run PRAGMA on every GET /suggestions
        async with get_db_context() as db:
            await init_schema_cache(db)
        logger.info("Blueprint Suggestion Service database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_db, name="database")
lifespan.on_shutdown(close_db, name="database")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Blueprint Suggestion Service",
    description="Matches Home Assistant Blueprints to devices and provides scored suggestions",
    version="1.0.0",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Include API routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
