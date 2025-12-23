"""
AI Automation Service - Main FastAPI Application

Epic 39, Story 39.10: Automation Service Foundation

This service was extracted from ai-automation-service for independent scaling and maintainability.
It handles:
- Automation suggestion generation
- YAML generation for Home Assistant automations
- Deployment of automations to Home Assistant
- Automation lifecycle management (enable/disable/rollback)

Architecture:
- FastAPI application with async/await support
- SQLAlchemy async database layer
- Authentication middleware (mandatory)
- Rate limiting middleware
- CORS support for frontend integration
- Observability integration (OpenTelemetry, if available)

Dependencies:
- shared.logging_config: Centralized logging
- shared.error_handler: Error handling
- shared.observability: Tracing and metrics (optional)
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
    logger = setup_logging("ai-automation-service")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-automation-service")

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

from .api import health_router, suggestion_router, deployment_router, pattern_router
from .api.middlewares import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    start_rate_limit_cleanup,
    stop_rate_limit_cleanup
)
from .config import settings
from .database import init_db

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize service on startup and cleanup on shutdown.
    
    This lifespan context manager handles:
    - Database initialization
    - Observability setup (if available)
    - Rate limiting cleanup task startup
    - Graceful shutdown of background tasks
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control is yielded to the application runtime
        
    Raises:
        Exception: If database initialization fails (prevents service startup)
    """
    logger.info("=" * 60)
    logger.info("AI Automation Service Starting Up")
    logger.info("=" * 60)
    logger.info(f"Service Port: {settings.service_port}")
    logger.info(f"Database: {settings.database_path}")
    logger.info(f"Data API: {settings.data_api_url}")
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
            setup_tracing("ai-automation-service")
            logger.info("✅ Observability initialized")
        except Exception as e:
            logger.warning(f"Observability setup failed: {e}")
    
    # Start rate limit cleanup task
    try:
        await start_rate_limit_cleanup()
        logger.info("✅ Rate limiting initialized")
    except Exception as e:
        logger.warning(f"Rate limit cleanup setup failed: {e}")
    
    logger.info("✅ AI Automation Service startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("AI Automation Service Shutting Down")
    logger.info("=" * 60)
    
    # Stop rate limit cleanup
    try:
        await stop_rate_limit_cleanup()
    except Exception as e:
        logger.warning(f"Rate limit cleanup shutdown failed: {e}")

# Create FastAPI app
app = FastAPI(
    title="AI Automation Service",
    description="Automation service for suggestion generation, YAML generation, and deployment to Home Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
# CRITICAL: Restrict origins in production
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Register error handlers
if register_error_handlers:
    register_error_handlers(app)

# Instrument FastAPI for observability
if OBSERVABILITY_AVAILABLE:
    try:
        instrument_fastapi(app, "ai-automation-service")
        app.add_middleware(CorrelationMiddleware)
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")

# Authentication middleware (MANDATORY - cannot be disabled)
app.add_middleware(AuthenticationMiddleware)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
from .api import analysis_router

app.include_router(health_router, tags=["health"])
app.include_router(suggestion_router, tags=["suggestions"])
app.include_router(deployment_router, tags=["deployment"])
app.include_router(pattern_router.router, tags=["patterns"])
app.include_router(analysis_router.router, tags=["analysis"])

@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint providing service information.
    
    Returns:
        dict: Service metadata including name, version, status, and implementation note
    """
    return {
        "service": "ai-automation-service",
        "version": "1.0.0",
        "status": "operational",
        "note": "Foundation service - full implementation in progress (Story 39.10)"
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

