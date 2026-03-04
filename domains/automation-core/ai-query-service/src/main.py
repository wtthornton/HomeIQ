"""
AI Query Service - Main FastAPI Application

Epic 39, Story 39.9: Query Service Foundation
Extracted from ai-automation-service for independent scaling and low-latency query processing.

This service handles:
- Natural language query processing
- Entity extraction and clarification
- Query suggestions and refinement
- Low-latency query responses (<500ms P95 target)
"""

import logging

from homeiq_resilience import ServiceLifespan, create_app

# Setup logging (use shared logging config)
try:
    from homeiq_observability.logging_config import setup_logging

    logger = setup_logging("ai-query-service")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-query-service")

# Import shared error handler
try:
    from homeiq_data.error_handler import register_error_handlers
except ImportError:
    logger.warning("Shared error handler not available, using default error handling")
    register_error_handlers = None

# Import observability modules
try:
    from homeiq_observability.observability import (
        CorrelationMiddleware,
        instrument_fastapi,
        setup_tracing,
    )

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    logger.warning("Observability modules not available")
    OBSERVABILITY_AVAILABLE = False

from .api import health_router, query_router
from .api.middlewares import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    start_rate_limit_cleanup,
    stop_rate_limit_cleanup,
)
from .config import settings
from .database import init_db


# ---------------------------------------------------------------------------
# Startup / Shutdown hooks for ServiceLifespan
# ---------------------------------------------------------------------------

async def _startup() -> None:
    """Initialize all resources on startup."""
    logger.info("Service Port: %s", settings.service_port)
    logger.info("Data API: %s", settings.data_api_url)
    logger.info("Query Timeout: %ss", settings.query_timeout)
    logger.info("Cache Enabled: %s", settings.enable_caching)

    # Initialize database
    db_ok = await init_db()
    if db_ok:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")

    # Setup observability if available
    if OBSERVABILITY_AVAILABLE:
        try:
            setup_tracing("ai-query-service")
            logger.info("Observability initialized")
        except Exception:
            logger.warning("Observability setup failed", exc_info=True)

    # Start rate limit cleanup background task
    if settings.rate_limit_enabled:
        await start_rate_limit_cleanup()
        logger.info("Rate limit cleanup task started")


async def _shutdown() -> None:
    """Cleanup all resources on shutdown."""
    await stop_rate_limit_cleanup()


# ---------------------------------------------------------------------------
# Lifespan (ServiceLifespan)
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup, name="services")
lifespan.on_shutdown(_shutdown, name="services")


# ---------------------------------------------------------------------------
# App (create_app factory -- provides CORS, request-id, timing, exception handler)
# ---------------------------------------------------------------------------

app = create_app(
    title="AI Query Service",
    version="1.0.0",
    description="Low-latency query service for natural language automation queries",
    lifespan=lifespan.handler,
    # No StandardHealthCheck -- this service has a custom health_router with /ready and /live
    cors_origins=settings.get_cors_origins_list(),
    cors_allow_credentials=True,
)

# Register error handlers
if register_error_handlers:
    register_error_handlers(app)

# Instrument FastAPI for observability
if OBSERVABILITY_AVAILABLE:
    try:
        instrument_fastapi(app, "ai-query-service")
        app.add_middleware(CorrelationMiddleware)
    except Exception:
        logger.warning("Failed to instrument FastAPI", exc_info=True)

# Authentication middleware (validates API keys for external requests)
app.add_middleware(AuthenticationMiddleware)

# Rate limiting middleware (token bucket algorithm)
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(health_router.router, tags=["health"])
app.include_router(query_router.router, tags=["query"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )

