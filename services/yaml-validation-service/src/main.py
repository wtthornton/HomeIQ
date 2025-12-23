"""
YAML Validation Service - Main FastAPI Application

Epic 51, Story 51.4: Create Unified Validation Service

This service provides comprehensive YAML validation, normalization, and rendering
for Home Assistant automations.
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

# Setup logging
try:
    from shared.logging_config import setup_logging
    logger = setup_logging("yaml-validation-service")
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("yaml-validation-service")

# Import shared error handler
try:
    from shared.error_handler import register_error_handlers
except ImportError:
    logger.warning("Shared error handler not available, using default error handling")
    register_error_handlers = None

from .api.health_router import router as health_router
from .api.validation_router import router as validation_router
from .config import settings

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service on startup and cleanup on shutdown."""
    logger.info("=" * 60)
    logger.info("YAML Validation Service Starting Up")
    logger.info("=" * 60)
    logger.info(f"Service Port: {settings.service_port}")
    logger.info(f"Validation Level: {settings.validation_level}")
    logger.info(f"Data API: {settings.data_api_url}")
    logger.info("=" * 60)
    logger.info("✅ YAML Validation Service startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("YAML Validation Service Shutting Down")
    logger.info("=" * 60)

# Create FastAPI app
app = FastAPI(
    title="YAML Validation Service",
    description="Comprehensive YAML validation, normalization, and rendering for Home Assistant automations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
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

# Include routers
app.include_router(health_router)
app.include_router(validation_router)

@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint providing service information."""
    return {
        "service": "yaml-validation-service",
        "version": "1.0.0",
        "status": "operational",
        "epic": "Epic 51: YAML Automation Quality Enhancement & Validation Pipeline"
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

