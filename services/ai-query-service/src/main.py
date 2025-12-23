"""
AI Query Service - Main FastAPI Application

Epic 39, Story 39.9: Query Service Foundation
Extracted from ai-automation-service for independent scaling and low-latency query processing.

This service handles:
- Natural language query processing
- Entity extraction and clarification
- Query suggestions and refinement
- Low-latency query responses (<500ms P95 target)

Architecture:
- FastAPI application with async/await support
- SQLAlchemy async database layer
- Observability integration (optional)
- CORS middleware for frontend access

Key Features:
- Database initialization on startup
- Graceful error handling
- Observability support (OpenTelemetry)
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
    logger = setup_logging("ai-query-service")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-query-service")

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

from .api import health_router, query_router
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
    - Graceful shutdown
    
    Args:
        app: FastAPI application instance
    
    Yields:
        None: Control is yielded to the application runtime
    
    Raises:
        Exception: If database initialization fails (prevents service startup)
    """
    logger.info("=" * 60)
    logger.info("AI Query Service Starting Up")
    logger.info("=" * 60)
    logger.info(f"Service Port: {settings.service_port}")
    logger.info(f"Data API: {settings.data_api_url}")
    logger.info(f"Query Timeout: {settings.query_timeout}s")
    logger.info(f"Cache Enabled: {settings.enable_caching}")
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
            setup_tracing("ai-query-service")
            logger.info("✅ Observability initialized")
        except Exception as e:
            logger.warning(f"Observability setup failed: {e}")
    
    logger.info("✅ AI Query Service startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("AI Query Service Shutting Down")
    logger.info("=" * 60)

# Create FastAPI app
app = FastAPI(
    title="AI Query Service",
    description="Low-latency query service for natural language automation queries",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
# CRITICAL: Cannot use allow_origins=["*"] with allow_credentials=True (security vulnerability)
# Use specific origins when credentials are needed, or remove allow_credentials if using wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Health dashboard
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # AI Automation standalone UI
        "http://127.0.0.1:3001",
        "http://ai-automation-ui",  # Container network
        "http://ai-automation-ui:80",
        "http://homeiq-dashboard",  # Health dashboard container
        "http://homeiq-dashboard:80"
    ],
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
        instrument_fastapi(app, "ai-query-service")
        app.add_middleware(CorrelationMiddleware)
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")

# TODO: Story 39.10 - Add authentication middleware
# CRITICAL: Authentication should be added before production deployment
# See ai-automation-service/src/api/middlewares.py for AuthenticationMiddleware pattern
# app.add_middleware(AuthenticationMiddleware)

# TODO: Story 39.10 - Add rate limiting middleware
# CRITICAL: Rate limiting should be added before production deployment
# See ai-automation-service/src/api/middlewares.py for RateLimitMiddleware pattern
# if settings.rate_limit_enabled:
#     app.add_middleware(RateLimitMiddleware, ...)

# Include routers
app.include_router(health_router.router, tags=["health"])
app.include_router(query_router.router, tags=["query"])

@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        dict: Service information including name, version, and status.
    """
    return {
        "service": "ai-query-service",
        "version": "1.0.0",
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8018,
        reload=True,
        log_level=settings.log_level.lower()
    )

