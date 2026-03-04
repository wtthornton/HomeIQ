"""Data API Service — Tier-1 feature data hub.

Provides HA event queries (InfluxDB), device/entity browsing,
integration management, sports data, analytics, and HA automation.
All sensitive routes require Bearer authentication via AuthManager.

Modules:
    _service.py   — DataAPIService class (config, auth, lifecycle)
    _app_setup.py — middleware and router registration
    _models.py    — Pydantic response models
"""

from __future__ import annotations

import os
import pathlib
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from homeiq_observability.logging_config import setup_logging

from ._models import APIResponse, ErrorResponse
from ._service import DataAPIService
from .cache import cache
from .database import check_db_health, init_db

try:
    from homeiq_data.error_handler import register_error_handlers
except ImportError:
    register_error_handlers = None  # type: ignore[assignment]

load_dotenv()
logger = setup_logging("data-api")

# -- app factory --------------------------------------------------------------

data_api_service = DataAPIService()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifecycle: DB init, service start/stop."""
    try:
        from homeiq_ha.deployment_validation import log_deployment_info
        log_deployment_info("data-api")
    except ImportError:
        pass
    pathlib.Path("./data").mkdir(exist_ok=True)
    await init_db()
    await data_api_service.startup()
    yield
    await data_api_service.shutdown()


app = FastAPI(
    title=data_api_service.api_title, version=data_api_service.api_version,
    description=data_api_service.api_description, lifespan=lifespan,
    docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
)

from ._app_setup import configure_middleware, register_routers  # noqa: E402

configure_middleware(app, data_api_service)
register_routers(app, data_api_service)


# -- endpoints ----------------------------------------------------------------

@app.get("/", response_model=APIResponse)
async def root() -> APIResponse:
    """Root endpoint."""
    svc = data_api_service
    return APIResponse(success=True, message="Data API is running", data={
        "service": svc.api_title, "version": svc.api_version,
        "status": "running", "timestamp": datetime.now().isoformat()})


@app.get("/health")
async def health_check() -> dict:
    """Health check with dependencies and error-rate metrics."""
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


# -- error handlers -----------------------------------------------------------

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
    uvicorn.run("src.main:app", host=data_api_service.api_host,
                port=data_api_service.api_port,
                reload=os.getenv("RELOAD", "false").lower() == "true",
                log_level=os.getenv("LOG_LEVEL", "info").lower())
