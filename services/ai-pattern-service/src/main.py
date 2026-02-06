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
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Setup logging (use shared logging config)
try:
    from shared.logging_config import setup_logging
    logger = setup_logging("ai-pattern-service")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-pattern-service")

# Import shared error handler
try:
    from shared.error_handler import register_error_handlers
except ImportError:
    logger.warning("Shared error handler not available, using default error handling")
    register_error_handlers = None

# Import observability modules
try:
    from shared.observability import CorrelationMiddleware, instrument_fastapi, setup_tracing
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    logger.warning("Observability modules not available")
    OBSERVABILITY_AVAILABLE = False

from .api import health_router, pattern_router, synergy_router, community_pattern_router
from .clients.mqtt_client import MQTTNotificationClient
from .config import settings
from .database import init_db
from .scheduler import PatternAnalysisScheduler

# Global scheduler instance (Epic 39, Story 39.6)
pattern_scheduler: PatternAnalysisScheduler | None = None
mqtt_client: MQTTNotificationClient | None = None


async def _initialize_mqtt_client() -> MQTTNotificationClient | None:
    """Initialize and connect MQTT client for notifications."""
    if not settings.mqtt_broker:
        logger.info("ℹ️ MQTT broker not configured, notifications disabled")
        return None
    
    try:
        client = MQTTNotificationClient(
            broker=settings.mqtt_broker,
            port=settings.mqtt_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            enabled=True
        )
        if client.connect():
            logger.info(f"✅ MQTT client connected to {client.broker}:{client.port}")
            return client
        else:
            logger.warning(f"⚠️ MQTT client connection failed to {client.broker}:{client.port}")
            return None
    except Exception as e:
        logger.warning(f"⚠️ MQTT client initialization failed: {e}")
        return None


async def _initialize_scheduler(client: MQTTNotificationClient | None) -> PatternAnalysisScheduler | None:
    """Initialize and start pattern analysis scheduler."""
    try:
        scheduler = PatternAnalysisScheduler(
            cron_schedule=settings.analysis_schedule,
            enable_incremental=settings.enable_incremental
        )
        
        if client:
            scheduler.set_mqtt_client(client)
        
        scheduler.start()
        logger.info(f"✅ Pattern analysis scheduler started (schedule: {settings.analysis_schedule})")
        return scheduler
    except Exception as e:
        logger.error(f"❌ Scheduler initialization failed: {e}", exc_info=True)
        # Don't fail startup if scheduler fails - service can still handle API requests
        return None


async def _shutdown_scheduler() -> None:
    """Stop pattern analysis scheduler."""
    global pattern_scheduler
    if pattern_scheduler:
        try:
            pattern_scheduler.stop()
            logger.info("✅ Pattern analysis scheduler stopped")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping scheduler: {e}")


async def _shutdown_mqtt_client() -> None:
    """Disconnect MQTT client."""
    global mqtt_client
    if mqtt_client:
        try:
            mqtt_client.disconnect()
            logger.info("✅ MQTT client disconnected")
        except Exception as e:
            logger.warning(f"⚠️ Error disconnecting MQTT client: {e}")


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize service on startup and cleanup on shutdown.
    
    This lifespan context manager handles:
    - Database initialization
    - Observability setup (if available)
    - MQTT client initialization and connection
    - Pattern analysis scheduler startup
    - Graceful shutdown of scheduler and MQTT client
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control is yielded to the application runtime
        
    Raises:
        Exception: If database initialization fails (prevents service startup)
    """
    global pattern_scheduler, mqtt_client
    
    logger.info("=" * 60)
    logger.info("AI Pattern Service Starting Up")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise
    
    # Setup observability if available
    if OBSERVABILITY_AVAILABLE:
        try:
            setup_tracing("ai-pattern-service")
            logger.info("✅ Observability initialized")
        except Exception as e:
            logger.warning(f"Observability setup failed: {e}")
    
    # Initialize MQTT client (Epic 39, Story 39.6)
    mqtt_client = await _initialize_mqtt_client()
    
    # Initialize and start scheduler (Epic 39, Story 39.6)
    pattern_scheduler = await _initialize_scheduler(mqtt_client)
    
    logger.info("✅ AI Pattern Service startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("AI Pattern Service Shutting Down")
    logger.info("=" * 60)
    
    # Stop scheduler (Epic 39, Story 39.6)
    await _shutdown_scheduler()
    
    # Disconnect MQTT client
    await _shutdown_mqtt_client()

# Create FastAPI app
app = FastAPI(
    title="AI Pattern Service",
    description="Pattern detection, synergy analysis, and community patterns service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
# CRITICAL FIX: Restrict CORS origins for security
# In production, set CORS_ORIGINS environment variable to specific allowed origins
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Restricted to configured origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
        logger.warning(f"Failed to instrument FastAPI: {e}")

def _register_core_routers(app: FastAPI) -> None:
    """Register core routers for the application."""
    from .api import analysis_router
    
    app.include_router(health_router.router, tags=["health"])
    app.include_router(pattern_router.router, tags=["patterns"])
    # CRITICAL: Include specific_router FIRST to ensure /stats and /list are matched before /{synergy_id}
    # FastAPI matches routes in the order they're registered, so specific routes must come first
    try:
        if hasattr(synergy_router, 'specific_router'):
            app.include_router(synergy_router.specific_router, tags=["synergies"])
            logger.info("✅ Included specific_router with /stats and /list routes")
        else:
            logger.error("❌ specific_router not found in synergy_router module!")
    except Exception as e:
        logger.error(f"❌ Failed to include specific_router: {e}", exc_info=True)
    app.include_router(synergy_router.router, tags=["synergies"])
    app.include_router(community_pattern_router.router, tags=["community-patterns"])
    app.include_router(analysis_router.router, tags=["analysis"])


def _register_blueprint_routers(app: FastAPI) -> None:
    """Register blueprint-related routers."""
    # Include Blueprint Opportunity Router (Phase 2 - Blueprint-First Architecture)
    try:
        if hasattr(synergy_router, 'blueprint_router'):
            app.include_router(synergy_router.blueprint_router, tags=["blueprint-opportunities"])
            logger.info("✅ Included blueprint_router for Blueprint Opportunity Engine")
        else:
            logger.warning("⚠️ blueprint_router not found in synergy_router module")
    except Exception as e:
        logger.warning(f"⚠️ Failed to include blueprint_router: {e}")


def _register_enhancement_routers(app: FastAPI) -> None:
    """Register analytics, rating, and tracking routers."""
    # Include Analytics, Rating, and Tracking Routers (Patterns & Synergies Enhancement)
    try:
        from .analytics.routes import router as analytics_router
        app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
        logger.info("✅ Included analytics_router for Blueprint Analytics")
    except ImportError as e:
        logger.warning(f"⚠️ Analytics router not available: {e}")

    try:
        from .rating.routes import router as rating_router
        app.include_router(rating_router, prefix="/api/v1", tags=["ratings"])
        logger.info("✅ Included rating_router for Blueprint Rating System")
    except ImportError as e:
        logger.warning(f"⚠️ Rating router not available: {e}")

    try:
        from .tracking.routes import router as tracking_router
        app.include_router(tracking_router, prefix="/api/v1", tags=["tracking"])
        logger.info("✅ Included tracking_router for Execution Tracking")
    except ImportError as e:
        logger.warning(f"⚠️ Tracking router not available: {e}")


# Include routers
_register_core_routers(app)
_register_blueprint_routers(app)
_register_enhancement_routers(app)

@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint providing service information.
    
    Returns:
        dict: Service metadata including name, version, and status
    """
    return {
        "service": "ai-pattern-service",
        "version": "1.0.0",
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

