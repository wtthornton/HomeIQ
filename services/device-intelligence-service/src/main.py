"""
Device Intelligence Service - Main FastAPI Application

This service provides centralized device discovery and intelligence processing
for the Home Assistant Ingestor system.
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import Settings
from .api.health import router as health_router
from .api.discovery import router as discovery_router
from .api.storage import router as storage_router
from .api.websocket_router import router as websocket_router
from .api.health_router import router as health_api_router
from .api.predictions_router import router as predictions_router
from .api.recommendations_router import router as recommendations_router
from .api.database_management import router as database_management_router
from .core.database import initialize_database
from .core.predictive_analytics import PredictiveAnalyticsEngine

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","service":"device-intelligence"}'
)
logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("🚀 Device Intelligence Service starting up...")
    logger.info(f"📊 Service configuration loaded: Port {settings.DEVICE_INTELLIGENCE_PORT}")
    
    # Initialize database
    await initialize_database(settings)
    logger.info("✅ Database initialized successfully")
    
    # Initialize predictive analytics engine
    analytics_engine = PredictiveAnalyticsEngine()
    await analytics_engine.initialize_models()
    logger.info("✅ Predictive analytics engine initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Device Intelligence Service shutting down...")
    # Cleanup resources here

# Create FastAPI application
app = FastAPI(
    title="Device Intelligence Service",
    description="Centralized device discovery and intelligence processing for Home Assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request/response logging middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header and log requests/responses."""
    start_time = time.perf_counter()
    
    # Log request
    logger.info(f"📥 Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    logger.info(f"📤 Response: {response.status_code} ({process_time:.3f}s)")
    
    return response

# Add error handling middleware
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.error(f"❌ Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"❌ Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "path": str(request.url)
        }
    )

# Include API routers
app.include_router(health_router, tags=["Health"])
app.include_router(discovery_router, prefix="/api", tags=["Discovery"])
app.include_router(storage_router, prefix="/api", tags=["Storage"])
app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(health_api_router, tags=["Health API"])
app.include_router(predictions_router, tags=["Predictions"])
app.include_router(recommendations_router, tags=["Recommendations"])
app.include_router(database_management_router, prefix="/api", tags=["Database Management"])

# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint providing service information."""
    return {
        "service": "Device Intelligence Service",
        "version": "1.0.0",
        "status": "operational",
        "port": settings.DEVICE_INTELLIGENCE_PORT,
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.DEVICE_INTELLIGENCE_HOST,
        port=settings.DEVICE_INTELLIGENCE_PORT,
        reload=True
    )
