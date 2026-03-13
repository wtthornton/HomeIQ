"""AI Training Service - Main FastAPI Application.

Epic 39, Story 39.1: Training Service Foundation.
Uses shared library pattern: create_app + ServiceLifespan + StandardHealthCheck.
"""

from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api import training_router
from .config import settings
from .database import init_db

logger = setup_logging("ai-training-service", group_name="ml-engine")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

async def _startup_db() -> None:
    """Initialize database connection."""
    db_ok = await init_db()
    if db_ok:
        logger.info("AI Training Service database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_db, name="database")


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
    title="AI Training Service",
    version="1.0.0",
    description="Training service for AI models, synthetic data generation, and model evaluation",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Include API routes (health is auto-included by create_app)
app.include_router(training_router.router, prefix="/api/v1/training", tags=["training"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
