"""
AI Training Service - Main FastAPI Application

Epic 39, Story 39.1: Training Service Foundation
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
    logger = setup_logging("ai-training-service")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-training-service")

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

from .api import health_router, training_router
from .config import settings
from .database import init_db

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service on startup and cleanup on shutdown"""
    logger.info("=" * 60)
    logger.info("AI Training Service Starting Up")
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
            setup_tracing("ai-training-service")
            logger.info("✅ Observability initialized")
        except Exception as e:
            logger.warning(f"Observability setup failed: {e}")
    
    logger.info("✅ AI Training Service startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("AI Training Service Shutting Down")
    logger.info("=" * 60)

# Create FastAPI app
app = FastAPI(
    title="AI Training Service",
    description="Training service for AI models, synthetic data generation, and model evaluation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
# CRITICAL: Restrict origins in production - allow_origins=["*"] is a security risk
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restrict to known origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # Restrict to needed methods
    allow_headers=["Content-Type", "Authorization"],  # Restrict headers
)

# Register error handlers
if register_error_handlers:
    register_error_handlers(app)

# Instrument FastAPI for observability
if OBSERVABILITY_AVAILABLE:
    try:
        instrument_fastapi(app, "ai-training-service")
        app.add_middleware(CorrelationMiddleware)
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")

# Include routers
app.include_router(health_router.router, prefix="/health", tags=["health"])
app.include_router(training_router.router, prefix="/api/v1/training", tags=["training"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ai-training-service",
        "version": "1.0.0",
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8022,
        reload=True,
        log_level=settings.log_level.lower()
    )

