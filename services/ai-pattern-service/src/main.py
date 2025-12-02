"""
AI Pattern Service - Main FastAPI Application

Epic 39, Story 39.5: Pattern Service Foundation
Extracted from ai-automation-service for independent scaling and maintainability.
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

from .api import health_router
from .clients.mqtt_client import MQTTNotificationClient
from .config import settings
from .database import init_db
from .scheduler import PatternAnalysisScheduler

# Global scheduler instance (Epic 39, Story 39.6)
pattern_scheduler: PatternAnalysisScheduler | None = None
mqtt_client: MQTTNotificationClient | None = None

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service on startup and cleanup on shutdown"""
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
    if settings.mqtt_broker:
        try:
            mqtt_client = MQTTNotificationClient(
                broker=settings.mqtt_broker,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
                enabled=True
            )
            mqtt_client.connect()
            logger.info(f"✅ MQTT client connected to {settings.mqtt_broker}:{settings.mqtt_port}")
        except Exception as e:
            logger.warning(f"⚠️ MQTT client initialization failed: {e}")
            mqtt_client = None
    else:
        logger.info("ℹ️ MQTT broker not configured, notifications disabled")
    
    # Initialize and start scheduler (Epic 39, Story 39.6)
    try:
        pattern_scheduler = PatternAnalysisScheduler(
            cron_schedule=settings.analysis_schedule,
            enable_incremental=settings.enable_incremental
        )
        
        if mqtt_client:
            pattern_scheduler.set_mqtt_client(mqtt_client)
        
        pattern_scheduler.start()
        logger.info(f"✅ Pattern analysis scheduler started (schedule: {settings.analysis_schedule})")
    except Exception as e:
        logger.error(f"❌ Scheduler initialization failed: {e}", exc_info=True)
        # Don't fail startup if scheduler fails - service can still handle API requests
        pattern_scheduler = None
    
    logger.info("✅ AI Pattern Service startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("AI Pattern Service Shutting Down")
    logger.info("=" * 60)
    
    # Stop scheduler (Epic 39, Story 39.6)
    if pattern_scheduler:
        try:
            pattern_scheduler.stop()
            logger.info("✅ Pattern analysis scheduler stopped")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping scheduler: {e}")
    
    # Disconnect MQTT client
    if mqtt_client:
        try:
            mqtt_client.disconnect()
            logger.info("✅ MQTT client disconnected")
        except Exception as e:
            logger.warning(f"⚠️ Error disconnecting MQTT client: {e}")

# Create FastAPI app
app = FastAPI(
    title="AI Pattern Service",
    description="Pattern detection, synergy analysis, and community patterns service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
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

# Include routers
app.include_router(health_router.router, tags=["health"])

@app.get("/")
async def root():
    """Root endpoint"""
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
        port=8020,
        reload=True,
        log_level=settings.log_level.lower()
    )

