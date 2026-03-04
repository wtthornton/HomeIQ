"""
AI Pattern Service - Main FastAPI Application

Epic 39, Story 39.5: Pattern Service Foundation

This service was extracted from ai-automation-service for independent scaling and maintainability.
It handles:
- Pattern detection and analysis
- Synergy detection between devices
- Community pattern sharing
- Scheduled pattern analysis (daily cron jobs)

Architecture:
- FastAPI application with async/await support
- SQLAlchemy async database layer
- MQTT client for notifications (with automatic reconnection)
- Pattern analysis scheduler (cron-based)
- Observability integration (optional)

Key Features:
- Automatic MQTT reconnection with exponential backoff
- Graceful error handling (service continues even if scheduler fails)
- CORS support for frontend integration
- Health check endpoints
"""

import logging

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

# Setup logging (use shared logging config)
try:
    from homeiq_observability.logging_config import setup_logging
    logger = setup_logging("ai-pattern-service", group_name="automation-intelligence")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-pattern-service")

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

from .api import community_pattern_router, health_router, pattern_router, synergy_router
from .clients.mqtt_client import MQTTNotificationClient
from .config import settings
from .database import init_db
from .scheduler import PatternAnalysisScheduler

# Global scheduler instance (Epic 39, Story 39.6)
pattern_scheduler: PatternAnalysisScheduler | None = None
mqtt_client: MQTTNotificationClient | None = None


# ---------------------------------------------------------------------------
# Startup / shutdown hooks
# ---------------------------------------------------------------------------

async def _startup_db() -> None:
    """Initialize database."""
    db_ok = await init_db()
    if db_ok:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")


async def _startup_observability() -> None:
    """Setup observability if available."""
    if OBSERVABILITY_AVAILABLE:
        setup_tracing("ai-pattern-service")
        logger.info("Observability initialized")


async def _startup_mqtt_and_scheduler() -> None:
    """Initialize MQTT client and pattern analysis scheduler."""
    global pattern_scheduler, mqtt_client

    # Initialize MQTT client (Epic 39, Story 39.6)
    if settings.mqtt_broker:
        try:
            client = MQTTNotificationClient(
                broker=settings.mqtt_broker,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
                enabled=True,
            )
            if client.connect():
                mqtt_client = client
                logger.info("MQTT client connected to %s:%s", client.broker, client.port)
            else:
                logger.warning("MQTT client connection failed to %s:%s", client.broker, client.port)
        except Exception as e:
            logger.warning("MQTT client initialization failed: %s", e)
    else:
        logger.info("MQTT broker not configured, notifications disabled")

    # Initialize and start scheduler (Epic 39, Story 39.6)
    try:
        scheduler = PatternAnalysisScheduler(
            cron_schedule=settings.analysis_schedule,
            enable_incremental=settings.enable_incremental,
        )
        if mqtt_client:
            scheduler.set_mqtt_client(mqtt_client)
        scheduler.start()
        pattern_scheduler = scheduler
        logger.info("Pattern analysis scheduler started (schedule: %s)", settings.analysis_schedule)
    except Exception as e:
        logger.error("Scheduler initialization failed: %s", e, exc_info=True)


async def _shutdown_scheduler() -> None:
    """Stop pattern analysis scheduler."""
    global pattern_scheduler
    if pattern_scheduler:
        try:
            pattern_scheduler.stop()
            logger.info("Pattern analysis scheduler stopped")
        except Exception as e:
            logger.warning("Error stopping scheduler: %s", e)


async def _shutdown_mqtt() -> None:
    """Disconnect MQTT client."""
    global mqtt_client
    if mqtt_client:
        try:
            mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
        except Exception as e:
            logger.warning("Error disconnecting MQTT client: %s", e)


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_db, name="database")
lifespan.on_startup(_startup_observability, name="observability")
lifespan.on_startup(_startup_mqtt_and_scheduler, name="mqtt-and-scheduler")
lifespan.on_shutdown(_shutdown_scheduler, name="scheduler")
lifespan.on_shutdown(_shutdown_mqtt, name="mqtt")


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
    title="AI Pattern Service",
    description="Pattern detection, synergy analysis, and community patterns service",
    version="1.0.0",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Register error handlers
if register_error_handlers:
    register_error_handlers(app)

# Instrument FastAPI for observability
if OBSERVABILITY_AVAILABLE:
    try:
        instrument_fastapi(app, "ai-pattern-service")
        app.add_middleware(CorrelationMiddleware)
    except Exception as e:
        logger.warning("Failed to instrument FastAPI: %s", e)


def _register_core_routers() -> None:
    """Register core routers for the application."""
    from .api import analysis_router

    # NOTE: health_router's /health is superseded by StandardHealthCheck;
    # health_router still provides /ready, /live, /database/integrity, /database/repair
    app.include_router(health_router.router, tags=["health"])
    app.include_router(pattern_router.router, tags=["patterns"])
    # CRITICAL: Include specific_router FIRST to ensure /stats and /list are matched before /{synergy_id}
    # FastAPI matches routes in the order they're registered, so specific routes must come first
    try:
        if hasattr(synergy_router, 'specific_router'):
            app.include_router(synergy_router.specific_router, tags=["synergies"])
            logger.info("Included specific_router with /stats and /list routes")
        else:
            logger.error("specific_router not found in synergy_router module!")
    except Exception as e:
        logger.error("Failed to include specific_router: %s", e, exc_info=True)
    app.include_router(synergy_router.router, tags=["synergies"])
    app.include_router(community_pattern_router.router, tags=["community-patterns"])
    app.include_router(analysis_router.router, tags=["analysis"])


def _register_blueprint_routers() -> None:
    """Register blueprint-related routers."""
    # Include Blueprint Opportunity Router (Phase 2 - Blueprint-First Architecture)
    try:
        if hasattr(synergy_router, 'blueprint_router'):
            app.include_router(synergy_router.blueprint_router, tags=["blueprint-opportunities"])
            logger.info("Included blueprint_router for Blueprint Opportunity Engine")
        else:
            logger.warning("blueprint_router not found in synergy_router module")
    except Exception as e:
        logger.warning("Failed to include blueprint_router: %s", e)


def _register_enhancement_routers() -> None:
    """Register analytics, rating, and tracking routers."""
    # Include Analytics, Rating, and Tracking Routers (Patterns & Synergies Enhancement)
    try:
        from .analytics.routes import router as analytics_router
        app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
        logger.info("Included analytics_router for Blueprint Analytics")
    except ImportError as e:
        logger.warning("Analytics router not available: %s", e)

    try:
        from .rating.routes import router as rating_router
        app.include_router(rating_router, prefix="/api/v1", tags=["ratings"])
        logger.info("Included rating_router for Blueprint Rating System")
    except ImportError as e:
        logger.warning("Rating router not available: %s", e)

    try:
        from .tracking.routes import router as tracking_router
        app.include_router(tracking_router, prefix="/api/v1", tags=["tracking"])
        logger.info("Included tracking_router for Execution Tracking")
    except ImportError as e:
        logger.warning("Tracking router not available: %s", e)


# Include routers
_register_core_routers()
_register_blueprint_routers()
_register_enhancement_routers()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
