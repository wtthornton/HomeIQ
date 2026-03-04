"""Data API Service -- Tier-1 feature data hub.

Provides HA event queries (InfluxDB), device/entity browsing,
integration management, sports data, analytics, and HA automation.
All sensitive routes require Bearer authentication via AuthManager.

Modules:
    _service.py   -- DataAPIService class (auth, lifecycle)
    _app_setup.py -- middleware and router registration
    _models.py    -- Pydantic response models
    config.py     -- Settings (BaseServiceSettings)
"""

from __future__ import annotations

import os
import pathlib
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from ._models import APIResponse, ErrorResponse
from ._service import DataAPIService
from .cache import cache
from .config import settings
from .database import check_db_health, init_db

try:
    from homeiq_data.error_handler import register_error_handlers
except ImportError:
    register_error_handlers = None  # type: ignore[assignment]

load_dotenv()
logger = setup_logging("data-api")

# -- service instance -------------------------------------------------------

data_api_service = DataAPIService()
SERVICE_START_TIME = data_api_service.start_time  # backward compat for health/analytics endpoints


# -- lifecycle hooks --------------------------------------------------------

async def _startup() -> None:
    """DB init and service start."""
    try:
        from homeiq_ha.deployment_validation import log_deployment_info
        log_deployment_info("data-api")
    except ImportError:
        pass
    pathlib.Path("./data").mkdir(exist_ok=True)
    await init_db()
    await data_api_service.startup()


async def _shutdown() -> None:
    """Service shutdown."""
    await data_api_service.shutdown()


# -- ServiceLifespan --------------------------------------------------------

_lifespan = ServiceLifespan(settings.service_name)
_lifespan.on_startup(_startup, name="data-api-init")
_lifespan.on_shutdown(_shutdown, name="data-api-cleanup")

# -- StandardHealthCheck ----------------------------------------------------

_health = StandardHealthCheck(
    service_name=settings.service_name,
    version=settings.api_version,
)


async def _check_db_healthy() -> bool:
    """Dependency check for PostgreSQL."""
    try:
        result = await check_db_health()
        return result.get("status") == "connected"
    except Exception:
        return False


async def _check_influxdb_healthy() -> bool:
    """Dependency check for InfluxDB."""
    try:
        conn = data_api_service.influxdb_client.get_connection_status()
        return conn.get("is_connected", False)
    except Exception:
        return False


_health.register_check("database", _check_db_healthy)
_health.register_check("influxdb", _check_influxdb_healthy)

# -- App creation -----------------------------------------------------------

app = create_app(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=_lifespan.handler,
    health_check=_health,
    cors_origins=settings.get_cors_origins_list(),
)

# Wire data-api-specific middleware and routers
from ._app_setup import configure_middleware, register_routers  # noqa: E402

configure_middleware(app, data_api_service)
register_routers(app, data_api_service)


# -- custom endpoints (preserved from original) -----------------------------

@app.get("/health/detailed")
async def health_check_detailed() -> dict:
    """Detailed health check with dependencies and error-rate metrics."""
    svc = data_api_service
    influx = svc.influxdb_client.get_connection_status()
    err = round(svc.failed_requests / svc.total_requests * 100, 2) if svc.total_requests else 0.0
    return {
        "status": "healthy" if svc.is_running else "unhealthy",
        "service": "data-api", "version": svc.api_version,
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - svc.start_time).total_seconds(),
        "metrics": {"total_requests": svc.total_requests,
                     "failed_requests": svc.failed_requests,
                     "error_rate_percent": err},
        "cache": cache.get_stats(), "rate_limiter": svc.rate_limiter.get_stats(),
        "dependencies": {
            "influxdb": {"status": "connected" if influx["is_connected"] else "disconnected",
                         "url": influx["url"], "query_count": influx["query_count"],
                         "avg_query_time_ms": influx["avg_query_time_ms"],
                         "success_rate": influx["success_rate"]},
            "database": await check_db_health()},
        "authentication": {"api_key_required": not svc.allow_anonymous}}


@app.get("/api/info", response_model=APIResponse)
async def api_info() -> APIResponse:
    """API information endpoint."""
    svc = data_api_service
    return APIResponse(success=True, message="Data API info", data={
        "title": svc.api_title, "version": svc.api_version,
        "description": svc.api_description,
        "endpoints": {"health": "/health", "events": "/api/v1/events",
                       "devices": "/api/v1/devices", "sports": "/api/v1/sports"},
        "authentication": {"api_key_required": not svc.allow_anonymous}})


# -- error handlers ---------------------------------------------------------

if register_error_handlers:
    register_error_handlers(app)
else:
    @app.exception_handler(HTTPException)
    async def _http_err(_req, exc: HTTPException):  # noqa: ANN001,ANN201
        return JSONResponse(status_code=exc.status_code,
                            content=ErrorResponse(error=exc.detail,
                                                  error_code=f"HTTP_{exc.status_code}").model_dump())

    @app.exception_handler(Exception)
    async def _general_err(_req, exc: Exception):  # noqa: ANN001,ANN201
        logger.error("Unhandled: %s", exc, exc_info=True)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content=ErrorResponse(error="Internal server error",
                                                  error_code="INTERNAL_ERROR").model_dump())

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0",  # noqa: S104
                port=settings.service_port,
                reload=os.getenv("RELOAD", "false").lower() == "true",
                log_level=settings.log_level.lower())
