"""FastAPI application setup for data-retention service.

Uses homeiq-resilience shared library for standardized app creation,
lifespan management, and health checks.
"""

import logging
import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from ..config import settings
from .routers import backup, cleanup, health, policies, retention

logger = logging.getLogger(__name__)

# --- Authentication ---
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify the API key for mutation endpoints."""
    expected_key = settings.data_retention_api_key
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if not api_key or not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# --- Service state ---
_service = None


async def _startup() -> None:
    """Initialize the DataRetentionService on startup."""
    global _service
    # Lazy import to avoid circular dependency
    from ..main import DataRetentionService

    logger.info("Starting Data Retention Service...")
    _service = DataRetentionService()
    app.state.service = _service
    await _service.start()
    logger.info("Data Retention Service started")


async def _shutdown() -> None:
    """Shut down the DataRetentionService."""
    if _service:
        logger.info("Shutting down Data Retention Service...")
        await _service.stop()
        logger.info("Data Retention Service stopped")


# --- Health checks ---
async def _check_cleanup_service() -> bool:
    """Check if cleanup service is initialized."""
    return _service is not None and _service.cleanup_service is not None


async def _check_storage_monitor() -> bool:
    """Check if storage monitor is initialized."""
    return _service is not None and _service.storage_monitor is not None


async def _check_scheduler() -> bool:
    """Check if scheduler is initialized."""
    return _service is not None and _service.scheduler is not None


# --- Lifespan ---
lifespan = ServiceLifespan("data-retention")
lifespan.on_startup(_startup, name="data-retention-service")
lifespan.on_shutdown(_shutdown, name="data-retention-service")

# --- Standard health check ---
std_health = StandardHealthCheck(service_name="data-retention", version="1.0.0")
std_health.register_check("cleanup-service", _check_cleanup_service)
std_health.register_check("storage-monitor", _check_storage_monitor)
std_health.register_check("scheduler", _check_scheduler)

# --- Create app ---
app = create_app(
    title="Data Retention Service",
    version="1.0.0",
    description="Service for data retention, cleanup, backup, and storage management",
    lifespan=lifespan.handler,
    health_check=std_health,
    cors_origins=settings.get_cors_origins_list(),
)

# Include routers - GET-only routers (monitoring) without auth
app.include_router(health.router)

# Mutation routers require API key authentication
app.include_router(policies.router, dependencies=[Depends(verify_api_key)])
app.include_router(cleanup.router, dependencies=[Depends(verify_api_key)])
app.include_router(backup.router, dependencies=[Depends(verify_api_key)])
app.include_router(retention.router, dependencies=[Depends(verify_api_key)])
