"""YAML Validation Service - Main FastAPI Application.

Epic 51, Story 51.4: Create Unified Validation Service

This service provides comprehensive YAML validation, normalization, and rendering
for Home Assistant automations.
"""

import logging
import sys

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api.validation_router import router as validation_router
from .config import settings


def _configure_logging() -> None:
    """Configure logging for the service."""
    try:
        from homeiq_observability.logging_config import setup_logging

        setup_logging(settings.service_name)
    except ImportError:
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

async def _startup_log() -> None:
    logger.info("Service Port: %s", settings.service_port)
    logger.info("Validation Level: %s", settings.validation_level)
    logger.info("Data API: %s", settings.data_api_url)


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_log, name="config_log")

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
    title="YAML Validation Service",
    version="1.0.0",
    description="Comprehensive YAML validation, normalization, and rendering for Home Assistant automations",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Register shared error handlers if available
try:
    from homeiq_data.error_handler import register_error_handlers

    register_error_handlers(app)
except ImportError:
    logger.debug("Shared error handler not available, using default error handling")

# Include routers
app.include_router(validation_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
