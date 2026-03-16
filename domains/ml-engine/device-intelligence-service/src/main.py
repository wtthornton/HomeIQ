"""Device Intelligence Service - Main FastAPI Application.

Centralized device discovery and intelligence processing
for the Home Assistant Ingestor system.
Uses shared library pattern: create_app + ServiceLifespan + StandardHealthCheck.
"""

import logging
import sys
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api.database_management import router as database_management_router
from .api.device_mappings_router import router as device_mappings_router
from .api.discovery import router as discovery_router
from .api.discovery import shutdown_discovery_service
from .api.health import router as health_router
from .api.health_router import router as health_api_router
from .api.hygiene_router import router as hygiene_router
from .api.name_enhancement_router import router as name_enhancement_router
from .api.naming_router import router as naming_router
from .api.predictions_router import router as predictions_router
from .api.recommendations_router import router as recommendations_router
from .api.storage import router as storage_router
from .api.team_tracker_router import router as team_tracker_router
from .api.websocket_router import router as websocket_router
from .config import Settings
from .core.database import close_database, initialize_database
from .core.predictive_analytics import PredictiveAnalyticsEngine
from .scheduler.training_scheduler import TrainingScheduler

# Load settings first so log level is available
settings = Settings()


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='{"timestamp":"%(asctime)s","level":"%(levelname)s",'
        '"message":"%(message)s","service":"device-intelligence"}',
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton resources (set during startup, cleaned up during shutdown)
# ---------------------------------------------------------------------------
_analytics_engine: PredictiveAnalyticsEngine | None = None
_training_scheduler: TrainingScheduler | None = None


async def _startup_db() -> None:
    """Initialize database connection."""
    db_ok = await initialize_database(settings)
    if db_ok:
        logger.info("Database initialized successfully")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")


async def _startup_analytics() -> None:
    """Initialize predictive analytics engine and training scheduler."""
    global _analytics_engine, _training_scheduler  # noqa: PLW0603

    settings.validate_required_runtime_fields()

    _analytics_engine = PredictiveAnalyticsEngine()
    await _analytics_engine.initialize_models()
    logger.info("Predictive analytics engine initialized")

    _training_scheduler = TrainingScheduler(settings, _analytics_engine)
    _training_scheduler.start()
    logger.info("Training scheduler initialized")


async def _shutdown_resources() -> None:
    """Stop training scheduler, discovery service, analytics engine, and database."""
    if _training_scheduler:
        _training_scheduler.stop()

    await shutdown_discovery_service()

    if _analytics_engine:
        await _analytics_engine.shutdown()

    await close_database()
    logger.info("Resources closed gracefully")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_db, name="database")
lifespan.on_startup(_startup_analytics, name="analytics-engine")
lifespan.on_shutdown(_shutdown_resources, name="all-resources")


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
    title="Device Intelligence Service",
    version="1.0.0",
    description="Centralized device discovery and intelligence processing for Home Assistant",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_allowed_origins(),
)


# ---------------------------------------------------------------------------
# Custom middleware (service-specific, not in shared library)
# ---------------------------------------------------------------------------

@app.middleware("http")
async def check_api_key(request: Request, call_next: Any) -> Any:
    """Check API key for non-health endpoints (CRIT-3)."""
    skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/"]
    path = request.url.path
    if any(path == p or path.startswith(p + "/") for p in skip_paths if p != "/") or path == "/":
        return await call_next(request)

    if not settings.API_KEY:
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

    return await call_next(request)


# ---------------------------------------------------------------------------
# Custom exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.error("Validation error: %s", exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "path": str(request.url),
        },
    )


# ---------------------------------------------------------------------------
# Inject analytics engine into app.state for route handlers
# ---------------------------------------------------------------------------

@app.middleware("http")
async def _inject_state(request: Request, call_next: Any) -> Any:
    """Expose analytics engine and training scheduler on app.state."""
    if _analytics_engine is not None and not hasattr(request.app.state, "analytics_engine"):
        request.app.state.analytics_engine = _analytics_engine
    if _training_scheduler is not None and not hasattr(request.app.state, "training_scheduler"):
        request.app.state.training_scheduler = _training_scheduler
    return await call_next(request)


# ---------------------------------------------------------------------------
# Include API routers (health /health is auto-included by create_app)
# ---------------------------------------------------------------------------

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
# NOTE: devices_router (api/devices.py) is NOT included here because
# storage_router already serves the identical /api/devices/* routes with
# real DeviceService logic.
app.include_router(device_mappings_router)  # Epic AI-24: Device Mapping Library
app.include_router(naming_router)  # Epic 64: Naming Convention


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
