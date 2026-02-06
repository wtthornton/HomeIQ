"""
Data API Service
Feature Data Hub for Home Assistant Ingestor

This service provides access to feature data including:
- HA event queries from InfluxDB
- Device and entity browsing
- Integration management
- Sports data and analytics
- Home Assistant automation endpoints
"""

import logging
import os
import secrets
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Early logger for use before setup_logging() is called
_early_logger = logging.getLogger("data-api.startup")

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.auth import AuthManager
from shared.correlation_middleware import FastAPICorrelationMiddleware
from shared.influxdb_query_client import InfluxDBQueryClient
from shared.logging_config import setup_logging

# Import shared error handler
try:
    from shared.error_handler import register_error_handlers
except ImportError:
    _early_logger.warning("Shared error handler not available, using default error handling")
    register_error_handlers = None

# Import observability modules
try:
    from shared.observability import CorrelationMiddleware as ObservabilityCorrelationMiddleware
    from shared.observability import instrument_fastapi, setup_tracing
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    _early_logger.warning("Observability modules not available")
    OBSERVABILITY_AVAILABLE = False

# Story 22.1: SQLite database
import pathlib

# Load environment variables
from dotenv import load_dotenv

from shared.endpoints import create_integration_router

# WebSocket endpoints removed - using HTTP polling only
from shared.monitoring import alerting_service, metrics_service
from shared.rate_limiter import RateLimiter, rate_limit_middleware

from .alert_endpoints import AlertEndpoints

# Story 21.4: Analytics Endpoints
from .analytics_endpoints import router as analytics_router

# MCP Code Execution Tools
from .api.mcp_router import router as mcp_router
from .cache import cache
from .config_manager import config_manager
from .database import check_db_health, init_db
from .devices_endpoints import router as devices_router

# Energy Correlation Endpoints (Phase 4)
from .energy_endpoints import router as energy_router

# Import endpoint routers (Stories 13.2-13.4)
from .events_endpoints import EventsEndpoints
from .ha_automation_endpoints import router as ha_automation_router
from .ha_automation_endpoints import start_webhook_detector, stop_webhook_detector
from .hygiene_endpoints import router as hygiene_router
from .metrics_endpoints import create_metrics_router

# Story 13.4: Sports & HA Automation (Epic 12 Integration)
from .sports_endpoints import router as sports_router
from .sports_influxdb_writer import get_sports_writer

load_dotenv()

# Configure logging
logger = setup_logging("data-api")

# Story 24.1: Track service start time for accurate uptime calculation
SERVICE_START_TIME = datetime.utcnow()


class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = Field(description="Whether the request was successful")
    data: Any | None = Field(default=None, description="Response data")
    message: str | None = Field(default=None, description="Response message")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(default=False)
    error: str = Field(description="Error message")
    error_code: str | None = Field(default=None)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class DataAPIService:
    """Main Data API service"""

    def __init__(self):
        """Initialize Data API service"""
        # Configuration - Configurable via environment variables
        self.api_host = os.getenv('DATA_API_HOST', '0.0.0.0')
        self.api_port = int(os.getenv('DATA_API_PORT', '8006'))
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))  # seconds
        self.db_query_timeout = int(os.getenv('DB_QUERY_TIMEOUT', '10'))  # seconds
        self.api_title = 'Data API - Feature Data Hub'
        self.api_version = '1.0.0'
        self.api_description = 'Feature data access for HA Ingestor (events, devices, sports, analytics, HA automation)'

        # Security - authentication always enforced
        self.api_key = os.getenv('DATA_API_API_KEY') or os.getenv('DATA_API_KEY') or os.getenv('API_KEY')
        self.allow_anonymous = os.getenv('DATA_API_ALLOW_ANONYMOUS', 'false').lower() == 'true'
        rate_limit_per_minute = int(os.getenv('DATA_API_RATE_LIMIT_PER_MIN', '100'))
        burst = int(os.getenv('DATA_API_RATE_LIMIT_BURST', '20'))
        self.rate_limiter = RateLimiter(rate=rate_limit_per_minute, per=60, burst=burst)

        if not self.api_key:
            if not self.allow_anonymous:
                raise RuntimeError("DATA_API_API_KEY (or API_KEY) must be configured for data-api")
            self.api_key = secrets.token_urlsafe(48)
            logger.warning(
                "Data API started in anonymous mode for local testing only. "
                "Set DATA_API_API_KEY to enforce authentication."
            )

        # CORS settings - default to localhost only; never use wildcard in production
        self.cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

        # Initialize components
        self.auth_manager = AuthManager(
            api_key=self.api_key,
            allow_anonymous=self.allow_anonymous,
        )
        self.influxdb_client = InfluxDBQueryClient()

        # Service state
        self.start_time = datetime.now()
        self.is_running = False

        # Error tracking for metrics
        self.total_requests = 0
        self.failed_requests = 0

        logger.info("Data API Service initialized (anonymous=%s)", self.allow_anonymous)

    async def startup(self):
        """Start the Data API service"""
        logger.info("Starting Data API service...")

        # Start monitoring services (Story 13.3)
        await alerting_service.start()
        await metrics_service.start()

        # Connect to InfluxDB FIRST (before webhook detector)
        try:
            logger.info("Connecting to InfluxDB...")
            connected = await self.influxdb_client.connect()
            if connected:
                logger.info("InfluxDB connection established successfully")

                # Connect sports InfluxDB writer (Epic 12 Story 12.1)
                sports_writer = get_sports_writer()
                await sports_writer.connect()
                if sports_writer.is_connected:
                    logger.info("Sports InfluxDB writer connected successfully")
                else:
                    logger.warning("Sports InfluxDB writer connection failed - writes disabled")

                # Start webhook event detector AFTER InfluxDB connection (Story 13.4)
                # This ensures InfluxDB client is ready before detector queries it
                start_webhook_detector()
                logger.info("Webhook event detector started (InfluxDB ready)")
            else:
                logger.warning("InfluxDB connection failed - webhook detector disabled")
        except Exception as e:
            logger.error(f"Error connecting to InfluxDB: {e}")
            logger.warning("Service will start without InfluxDB connection")

        self.is_running = True
        logger.info(f"Data API service started on {self.api_host}:{self.api_port}")

    async def shutdown(self):
        """Stop the Data API service"""
        logger.info("Shutting down Data API service...")

        # Stop webhook detector (Story 13.4)
        stop_webhook_detector()

        # Stop monitoring services (Story 13.3)
        await alerting_service.stop()
        await metrics_service.stop()

        # Close InfluxDB connection
        try:
            await self.influxdb_client.close()
        except Exception as e:
            logger.error(f"Error closing InfluxDB connection: {e}")

        self.is_running = False
        logger.info("Data API service stopped")


# Create service instance
data_api_service = DataAPIService()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    # Epic 40: Deployment mode validation and logging
    try:
        from shared.deployment_validation import log_deployment_info, get_deployment_mode
        log_deployment_info("data-api")
        logger.info(f"Deployment Mode: {get_deployment_mode()}")
    except ImportError:
        # Fallback if shared module not available
        import os
        deployment_mode = os.getenv("DEPLOYMENT_MODE", "production")
        logger.info(f"Data API starting in {deployment_mode} mode")
    
    # Startup
    # Ensure data directory exists
    pathlib.Path("./data").mkdir(exist_ok=True)

    # Initialize SQLite database
    try:
        await init_db()
        logger.info("SQLite database initialized")
    except Exception as e:
        logger.error(f"SQLite initialization failed: {e}")
        # Don't crash - service can run without SQLite initially

    await data_api_service.startup()
    yield
    # Shutdown
    await data_api_service.shutdown()


# Create FastAPI app
app = FastAPI(
    title=data_api_service.api_title,
    version=data_api_service.api_version,
    description=data_api_service.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Observability setup (tracing and correlation ID)
if OBSERVABILITY_AVAILABLE:
    # Set up OpenTelemetry tracing
    otlp_endpoint = os.getenv('OTLP_ENDPOINT')
    if setup_tracing("data-api", otlp_endpoint):
        logger.info("✅ OpenTelemetry tracing configured")

    # Instrument FastAPI app
    if instrument_fastapi(app, "data-api"):
        logger.info("✅ FastAPI app instrumented for tracing")

    # Add correlation ID middleware (should be early in middleware stack)
    app.add_middleware(ObservabilityCorrelationMiddleware)
    logger.info("✅ Correlation ID middleware added")
else:
    # Fallback to existing correlation middleware
    app.add_middleware(FastAPICorrelationMiddleware)

# Add CORS middleware
# HIGH-03: Do not use allow_credentials=True with wildcard origins
_cors_allow_credentials = "*" not in data_api_service.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=data_api_service.cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
@app.middleware("http")
async def apply_rate_limit(request, call_next):
    return await rate_limit_middleware(request, call_next, data_api_service.rate_limiter)


# CRIT-06: Auth dependency for sensitive routes
# All sensitive routers require authentication via the shared AuthManager.
# Health and root endpoints remain public for monitoring/load-balancer probes.
_auth_dependency = [Depends(data_api_service.auth_manager.get_current_user)]

# Register endpoint routers (Stories 13.2-13.3)
# Story 13.2: Events & Devices
events_endpoints = EventsEndpoints()
app.include_router(
    events_endpoints.router,
    prefix="/api/v1",
    tags=["Events"],
    dependencies=_auth_dependency
)

app.include_router(
    devices_router,
    tags=["Devices & Entities"],
    dependencies=_auth_dependency
)

# Story 13.3: Alerts, Metrics, Integrations, WebSockets
alert_endpoints = AlertEndpoints()
app.include_router(
    alert_endpoints.router,
    prefix="/api/v1",
    tags=["Alerts"],
    dependencies=_auth_dependency
)

app.include_router(
    create_metrics_router(),
    prefix="/api/v1",
    tags=["Metrics"],
    dependencies=_auth_dependency
)

# Create integration router with service-specific config_manager
integration_router = create_integration_router(config_manager)
app.include_router(
    integration_router,
    prefix="/api/v1",
    tags=["Integrations"],
    dependencies=_auth_dependency
)

# WebSocket endpoints removed - dashboard uses HTTP polling for simplicity

# Story 13.4: Sports Data & HA Automation (Epic 12 + 13 Convergence)
app.include_router(
    sports_router,
    prefix="/api/v1",
    tags=["Sports Data"],
    dependencies=_auth_dependency
)

app.include_router(
    ha_automation_router,
    prefix="/api/v1",
    tags=["Home Assistant Automation"],
    dependencies=_auth_dependency
)

# Story 21.4: Analytics Endpoints (Real-time metrics aggregation)
app.include_router(
    analytics_router,
    prefix="/api/v1",
    tags=["Analytics"],
    dependencies=_auth_dependency
)

# Phase 4: Energy Correlation Endpoints
app.include_router(
    energy_router,
    prefix="/api/v1",
    tags=["Energy"],
    dependencies=_auth_dependency
)

app.include_router(
    hygiene_router,
    tags=["Device Hygiene"],
    dependencies=_auth_dependency
)

# MCP Code Execution Tools
app.include_router(
    mcp_router,
    tags=["MCP Tools"],
    dependencies=_auth_dependency
)


# Root endpoint
@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint"""
    return APIResponse(
        success=True,
        data={
            "service": data_api_service.api_title,
            "version": data_api_service.api_version,
            "status": "running",
            "timestamp": datetime.now().isoformat()
        },
        message="Data API is running"
    )


# Health endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns service health status including InfluxDB and SQLite connections
    Plus error rate metrics for monitoring
    """
    uptime = (datetime.now() - data_api_service.start_time).total_seconds()
    influxdb_status = data_api_service.influxdb_client.get_connection_status()
    sqlite_status = await check_db_health()

    # Calculate error rate
    error_rate = 0.0
    if data_api_service.total_requests > 0:
        error_rate = (data_api_service.failed_requests / data_api_service.total_requests) * 100

    return {
        "status": "healthy" if data_api_service.is_running else "unhealthy",
        "service": "data-api",
        "version": data_api_service.api_version,
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime,
        "metrics": {
            "total_requests": data_api_service.total_requests,
            "failed_requests": data_api_service.failed_requests,
            "error_rate_percent": round(error_rate, 2)
        },
        "cache": cache.get_stats(),
        "rate_limiter": data_api_service.rate_limiter.get_stats(),
        "dependencies": {
            "influxdb": {
                "status": "connected" if influxdb_status["is_connected"] else "disconnected",
                "url": influxdb_status["url"],
                "query_count": influxdb_status["query_count"],
                "avg_query_time_ms": influxdb_status["avg_query_time_ms"],
                "success_rate": influxdb_status["success_rate"]
            },
            "sqlite": sqlite_status
        },
        "authentication": {
            "api_key_required": not data_api_service.allow_anonymous
        }
    }


# API info endpoint
@app.get("/api/info", response_model=APIResponse)
async def api_info():
    """API information endpoint"""
    return APIResponse(
        success=True,
        data={
            "title": data_api_service.api_title,
            "version": data_api_service.api_version,
            "description": data_api_service.api_description,
            "endpoints": {
                "health": "/health",
                "events": "/api/v1/events (Coming in Story 13.2)",
                "devices": "/api/v1/devices (Coming in Story 13.2)",
                "sports": "/api/v1/sports (Coming in Story 13.4)",
                "ha_automation": "/api/v1/ha (Coming in Story 13.4)"
            },
            "authentication": {"api_key_required": not data_api_service.allow_anonymous}
        },
        message="Data API information retrieved successfully"
    )


# Register shared error handlers if available
if register_error_handlers:
    register_error_handlers(app)
    logger.info("✅ Shared error handlers registered")
else:
    # Fallback to local error handlers with request tracking
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        """Handle HTTP exceptions and track error metrics"""
        data_api_service.total_requests += 1
        if exc.status_code >= 400:
            data_api_service.failed_requests += 1

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail,
                error_code=f"HTTP_{exc.status_code}"
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        """Handle general exceptions and track error metrics"""
        data_api_service.total_requests += 1
        data_api_service.failed_requests += 1

        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal server error",
                error_code="INTERNAL_ERROR"
            ).model_dump()
        )


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "src.main:app",
        host=data_api_service.api_host,
        port=data_api_service.api_port,
        reload=os.getenv('RELOAD', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )

