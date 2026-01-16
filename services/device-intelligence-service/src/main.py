"""
Device Intelligence Service - Main FastAPI Application

This service provides centralized device discovery and intelligence processing
for the Home Assistant Ingestor system.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.database_management import router as database_management_router
from .api.device_mappings_router import router as device_mappings_router
from .api.devices import router as devices_router
from .api.discovery import router as discovery_router
from .api.discovery import shutdown_discovery_service
from .api.health import router as health_router
from .api.health_router import router as health_api_router
from .api.hygiene_router import router as hygiene_router
from .api.name_enhancement_router import router as name_enhancement_router
from .api.predictions_router import router as predictions_router
from .api.recommendations_router import router as recommendations_router
from .api.storage import router as storage_router
from .api.team_tracker_router import router as team_tracker_router
from .api.websocket_router import router as websocket_router
from .config import Settings
from .core.database import close_database, initialize_database
from .core.predictive_analytics import PredictiveAnalyticsEngine
from .scheduler.training_scheduler import TrainingScheduler

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
    analytics_engine: PredictiveAnalyticsEngine | None = None
    training_scheduler: TrainingScheduler | None = None
    logger.info("🚀 Device Intelligence Service starting up...")
    logger.info(f"📊 Service configuration loaded: Port {settings.DEVICE_INTELLIGENCE_PORT}")

    try:
        settings.validate_required_runtime_fields()
        await initialize_database(settings)
        logger.info("✅ Database initialized successfully")

        analytics_engine = PredictiveAnalyticsEngine()
        await analytics_engine.initialize_models()
        app.state.analytics_engine = analytics_engine
        logger.info("✅ Predictive analytics engine initialized")

        # Start training scheduler (Epic 46.2: Built-in Nightly Training Scheduler)
        training_scheduler = TrainingScheduler(settings, analytics_engine)
        training_scheduler.start()
        app.state.training_scheduler = training_scheduler
        logger.info("✅ Training scheduler initialized")

        yield
    finally:
        logger.info("🛑 Device Intelligence Service shutting down...")
        
        # Stop training scheduler
        if training_scheduler:
            training_scheduler.stop()
        
        await shutdown_discovery_service()

        if analytics_engine:
            await analytics_engine.shutdown()

        await close_database()
        logger.info("✅ Resources closed gracefully")

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
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request/response logging middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> Any:
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
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
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
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
app.include_router(hygiene_router)
app.include_router(name_enhancement_router)
app.include_router(team_tracker_router, tags=["Team Tracker"])
app.include_router(devices_router, prefix="/api", tags=["Devices"])
app.include_router(device_mappings_router)  # Epic AI-24: Device Mapping Library

# Root endpoint
@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint providing service information."""
    return {
        "service": "Device Intelligence Service",
        "version": "1.0.0",
        "status": "operational",
        "port": settings.DEVICE_INTELLIGENCE_PORT,
        "docs": "/docs",
        "health": "/health/"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.DEVICE_INTELLIGENCE_HOST,
        port=settings.DEVICE_INTELLIGENCE_PORT,
        reload=True
    )
