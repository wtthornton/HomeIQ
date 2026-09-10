"""
Rule Recommendation ML Service - Main Application

FastAPI service that provides rule recommendations based on
the Wyze Rule Recommendation dataset.

Port: 8035
"""

from pathlib import Path

from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api.routes import init_feedback_store, init_memory_client, load_model, router
from .config import settings

logger = setup_logging("rule-recommendation-ml", group_name="blueprints")


# ---------------------------------------------------------------------------
# Startup / shutdown hooks
# ---------------------------------------------------------------------------


async def _startup_init() -> None:
    """Initialize feedback store, memory client, and load model."""
    # Initialize feedback store (must be before model load). FeedbackStore
    # is PostgreSQL-backed and needs a DB URL string, never a filesystem path.
    db_url = settings.effective_database_url or None
    init_feedback_store(db_url)
    logger.info("Feedback store ready (db_url=%s)", db_url)

    # Initialize memory client (Story 30.3: Rating & Feedback Memory)
    await init_memory_client()

    # Load model if it exists
    model_path = Path(settings.model_path)
    if model_path.exists():
        success = load_model(model_path)
        if success:
            logger.info("Model loaded successfully (path=%s)", model_path)
        else:
            logger.warning("Failed to load model (path=%s)", model_path)
    else:
        logger.info(
            "No pre-trained model found. Train a model and save to %s.",
            model_path,
        )


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_init, name="feedback-store-and-model")


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
    title="Rule Recommendation ML Service",
    description="ML-powered rule recommendations for HomeIQ based on Wyze dataset",
    version="1.0.0",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Include routers
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=settings.debug,
    )
