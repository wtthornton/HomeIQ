"""Main FastAPI application for Activity Recognition Service."""

import logging
import sys
from pathlib import Path

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api.routes import load_model, router
from .config import settings


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

async def _startup_model() -> None:
    """Load ONNX model on startup."""
    model_path = Path(settings.model_path)
    if model_path.exists():
        success = load_model(model_path)
        if success:
            logger.info("ONNX model loaded successfully, path=%s", model_path)
        else:
            logger.warning("Failed to load ONNX model, path=%s", model_path)
    else:
        logger.info(
            "No ONNX model found. Train a model and export to ONNX. path=%s",
            model_path,
        )


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_model, name="model")


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
    title="Activity Recognition Service",
    version="1.0.0",
    description="ML-powered activity recognition from smart home sensors",
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
        reload=settings.debug,
    )
