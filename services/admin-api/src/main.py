"""
Admin REST API Service
"""

import asyncio
import os
import secrets
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import aiohttp
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.correlation_middleware import FastAPICorrelationMiddleware
from shared.logging_config import setup_logging

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Configure enhanced logging (must be done before any logger usage)
logger = setup_logging("admin-api")

# Import shared error handler
try:
    from shared.error_handler import register_error_handlers
except ImportError:
    logger.warning("Shared error handler not available, using default error handling")
    register_error_handlers = None

# Import observability modules
try:
    from shared.observability import CorrelationMiddleware as ObservabilityCorrelationMiddleware
    from shared.observability import instrument_fastapi, setup_tracing
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    logger.warning("Observability modules not available")
    OBSERVABILITY_AVAILABLE = False

from shared.auth import AuthManager  # Moved to shared

# WebSocket endpoints removed - using HTTP polling only
from shared.endpoints import create_integration_router
from shared.monitoring import (
    MonitoringEndpoints,
    StatsEndpoints,
    alerting_service,
    logging_service,
    metrics_service,
)
from shared.rate_limiter import RateLimiter, rate_limit_middleware

from .config_endpoints import ConfigEndpoints
from .config_manager import config_manager
from .docker_endpoints import DockerEndpoints
from .ha_proxy_endpoints import router as ha_proxy_router
from .health_endpoints import HealthEndpoints
from .mqtt_config_endpoints import router as mqtt_config_router, public_router as mqtt_config_public_router


class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = Field(description="Whether the request was successful")
    data: Any | None = Field(default=None, description="Response data")
    message: str | None = Field(default=None, description="Response message")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Response timestamp")
    request_id: str | None = Field(default=None, description="Request ID for tracking")


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error message")
    error_code: str | None = Field(default=None, description="Error code")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Error timestamp")
    request_id: str | None = Field(default=None, description="Request ID for tracking")


_start_time = time.time()
_request_count = 0
_error_count = 0


async def _check_dependency(name: str, url: str, timeout: float = 5.0) -> dict:
    """Check the health of a dependency service."""
    try:
        start = time.time()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(f"{url}/health") as response:
                elapsed = (time.time() - start) * 1000
                return {
                    "name": name,
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "response_time_ms": round(elapsed, 2),
                    "last_check": datetime.now().isoformat()
                }
    except Exception as e:
        return {
            "name": name,
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


class AdminAPIService:
    """Main Admin API service"""

    def __init__(self):
        """Initialize Admin API service"""
        # Configuration
        self.api_host = os.getenv('API_HOST', '0.0.0.0')
        self.api_port = int(os.getenv('API_PORT', '8000'))
        self.api_title = os.getenv('API_TITLE', 'Home Assistant Ingestor Admin API')
        self.api_version = os.getenv('API_VERSION', '1.0.0')
        self.api_description = os.getenv('API_DESCRIPTION', 'Admin API for Home Assistant Ingestor')

        # Security
        self.api_key = os.getenv('ADMIN_API_API_KEY') or os.getenv('API_KEY')
        self.allow_anonymous = os.getenv('ADMIN_API_ALLOW_ANONYMOUS', 'false').lower() == 'true'
        self.docs_enabled = os.getenv('ADMIN_API_ENABLE_DOCS', 'false').lower() == 'true'
        self.openapi_enabled = os.getenv('ADMIN_API_ENABLE_OPENAPI', 'false').lower() == 'true'
        rate_limit_per_minute = int(os.getenv('ADMIN_API_RATE_LIMIT_PER_MIN', '60'))
        burst = int(os.getenv('ADMIN_API_RATE_LIMIT_BURST', '20'))
        self.rate_limiter = RateLimiter(rate=rate_limit_per_minute, per=60, burst=burst)

        if not self.api_key:
            if not self.allow_anonymous:
                raise RuntimeError(
                    "API_KEY (or ADMIN_API_API_KEY) must be set before starting admin-api"
                )
            self.api_key = secrets.token_urlsafe(48)
            logger.warning(
                "Admin API started in anonymous mode for local testing only. "
                "Set ADMIN_API_API_KEY to enforce authentication."
            )

        # CORS settings
        self.cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
        self.cors_methods = os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE').split(',')
        self.cors_headers = os.getenv('CORS_HEADERS', '*').split(',')

        # Initialize components
        self.start_time = datetime.now()  # Add start time for uptime calculation
        self.auth_manager = AuthManager(
            api_key=self.api_key,
            allow_anonymous=self.allow_anonymous,
        )
        self.health_endpoints = HealthEndpoints()
        self.stats_endpoints = StatsEndpoints()
        self.config_endpoints = ConfigEndpoints()
        self.docker_endpoints = DockerEndpoints(self.auth_manager)
        self.monitoring_endpoints = MonitoringEndpoints(self.auth_manager)
        # Integration router removed - migrated to data-api (Epic 13 Story 13.3)
        # WebSocket endpoints removed - using HTTP polling only

        # FastAPI app
        self.app: FastAPI | None = None
        self.server_task: asyncio.Task | None = None
        self.is_running = False

    async def start(self):
        """Start the Admin API service"""
        if self.is_running:
            logger.warning("Admin API service is already running")
            return

        # Create FastAPI app if it doesn't exist
        if self.app is None:
            self.app = FastAPI(
                title=self.api_title,
                version=self.api_version,
                description=self.api_description,
                docs_url="/docs" if self.docs_enabled else None,
                redoc_url="/redoc" if self.docs_enabled else None,
                openapi_url="/openapi.json" if (self.docs_enabled or self.openapi_enabled) else None,
            )

        # Start monitoring services
        await logging_service.start()
        await metrics_service.start()
        await alerting_service.start()

        # Initialize InfluxDB connection for stats endpoints
        try:
            logger.info("Initializing InfluxDB connection for statistics...")
            await self.stats_endpoints.initialize()
            logger.info("InfluxDB connection initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize InfluxDB: {e}")
            logger.warning("Statistics will fall back to direct service calls")

        # Add middleware
        self._add_middleware()

        # Add routes
        self._add_routes()

        # Add exception handlers
        self._add_exception_handlers()

        # Start server
        config = uvicorn.Config(
            app=self.app,
            host=self.api_host,
            port=self.api_port,
            log_level=os.getenv('LOG_LEVEL', 'info').lower()
        )
        server = uvicorn.Server(config)

        self.server_task = asyncio.create_task(server.serve())
        self.is_running = True

        logger.info(f"Admin API service started on {self.api_host}:{self.api_port}")

    async def stop(self):
        """Stop the Admin API service"""
        if not self.is_running:
            return

        self.is_running = False

        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass

        # Close InfluxDB connection
        try:
            logger.info("Closing InfluxDB connection...")
            await self.stats_endpoints.close()
        except Exception as e:
            logger.error(f"Error closing InfluxDB connection: {e}")

        # Stop monitoring services
        await alerting_service.stop()
        await metrics_service.stop()
        await logging_service.stop()

        logger.info("Admin API service stopped")

    def _add_middleware(self):
        """Add middleware to FastAPI app"""
        if self.app is None:
            logger.error("Cannot add middleware: FastAPI app is not initialized")
            return

        # Observability setup (tracing and correlation ID)
        if OBSERVABILITY_AVAILABLE:
            # Set up OpenTelemetry tracing
            otlp_endpoint = os.getenv('OTLP_ENDPOINT')
            if setup_tracing("admin-api", otlp_endpoint):
                logger.info("✅ OpenTelemetry tracing configured")

            # Instrument FastAPI app
            if instrument_fastapi(self.app, "admin-api"):
                logger.info("✅ FastAPI app instrumented for tracing")

            # Add correlation ID middleware (should be early in middleware stack)
            self.app.add_middleware(ObservabilityCorrelationMiddleware)
            logger.info("✅ Correlation ID middleware added")
        else:
            # Fallback to existing correlation middleware
            self.app.add_middleware(FastAPICorrelationMiddleware)

        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=self.cors_methods,
            allow_headers=self.cors_headers
        )

        # Rate limiting middleware
        @self.app.middleware("http")
        async def apply_rate_limit(request, call_next):
            return await rate_limit_middleware(request, call_next, self.rate_limiter)

        # Request logging middleware
        @self.app.middleware("http")
        async def log_requests(request, call_next):
            global _request_count, _error_count
            start_time = datetime.now()

            # Process request
            response = await call_next(request)

            # Track request and error counts for health metrics
            _request_count += 1
            if response.status_code >= 500:
                _error_count += 1

            # Log request
            process_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )

            return response

    def _add_routes(self):
        """Add routes to FastAPI app"""
        if self.app is None:
            logger.error("Cannot add routes: FastAPI app is not initialized")
            return

        # Simple health endpoint that always works
        @self.app.get("/api/health")
        async def simple_health():
            """Simple health endpoint that always works"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "admin-api"
            }

        # Enhanced health endpoint with dependency information
        @self.app.get("/api/v1/health")
        async def enhanced_health():
            """Enhanced health endpoint with actual dependency checks"""
            global _request_count, _error_count
            try:
                uptime_seconds = time.time() - _start_time

                # Perform actual dependency health checks concurrently
                influxdb_url = os.getenv("INFLUXDB_URL", "http://homeiq-influxdb:8086")
                websocket_url = os.getenv("WEBSOCKET_INGESTION_URL", "http://homeiq-websocket:8001")
                data_api_url = os.getenv("DATA_API_URL", "http://homeiq-data-api:8006")

                dep_checks = await asyncio.gather(
                    _check_dependency("InfluxDB", influxdb_url),
                    _check_dependency("WebSocket Ingestion", websocket_url),
                    _check_dependency("Data API", data_api_url),
                    return_exceptions=True
                )

                dependencies = []
                for check in dep_checks:
                    if isinstance(check, Exception):
                        dependencies.append({
                            "name": "unknown",
                            "status": "unhealthy",
                            "error": str(check),
                            "last_check": datetime.now().isoformat()
                        })
                    else:
                        dependencies.append(check)

                # Determine overall status from dependency checks
                all_healthy = all(d.get("status") == "healthy" for d in dependencies)
                overall_status = "healthy" if all_healthy else "degraded"

                rate_limiter_stats = self.rate_limiter.get_stats()

                # Calculate uptime percentage from actual start time
                uptime_human = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s"

                # Calculate error rate from actual counts
                total_requests = _request_count if _request_count > 0 else 1
                error_rate = round((_error_count / total_requests) * 100, 2)

                return {
                    "status": overall_status,
                    "service": "admin-api",
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": round(uptime_seconds, 2),
                    "uptime_human": uptime_human,
                    "dependencies": dependencies,
                    "security": {
                        "api_key_required": not self.allow_anonymous,
                        "docs_enabled": self.docs_enabled,
                        "rate_limit": rate_limiter_stats,
                    },
                    "metrics": {
                        "uptime_human": uptime_human,
                        "uptime_seconds": round(uptime_seconds, 2),
                        "total_requests": _request_count,
                        "error_rate": error_rate
                    }
                }
            except Exception as e:
                logger.error(f"Enhanced health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "service": "admin-api",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }

        # Simple metrics endpoint that always works
        @self.app.get("/api/metrics/realtime")
        async def simple_metrics():
            """Simple metrics endpoint that always works"""
            return {
                "success": True,
                "events_per_second": 0.0,
                "active_api_calls": 0,
                "active_sources": [],
                "timestamp": datetime.now().isoformat()
            }

        # Public real-time metrics endpoint for dashboard (no authentication required)
        @self.app.get("/api/v1/real-time-metrics")
        async def public_real_time_metrics():
            """Get consolidated real-time metrics for dashboard - public endpoint"""
            try:
                # Call the stats endpoint methods directly
                event_rate = await self.stats_endpoints._get_current_event_rate()
                api_stats = await self.stats_endpoints._get_all_api_metrics()
                data_sources = await self.stats_endpoints._get_active_data_sources()
                
                return {
                    "events_per_hour": event_rate * 3600,
                    "api_calls_active": api_stats["active_calls"],
                    "data_sources_active": data_sources,
                    "api_metrics": api_stats["api_metrics"],
                    "inactive_apis": api_stats["inactive_apis"],
                    "error_apis": api_stats["error_apis"],
                    "total_apis": api_stats["total_apis"],
                    "health_summary": {
                        "healthy": api_stats["active_calls"],
                        "unhealthy": api_stats["inactive_apis"] + api_stats["error_apis"],
                        "total": api_stats["total_apis"],
                        "health_percentage": round((api_stats["active_calls"] / api_stats["total_apis"]) * 100, 1) if api_stats["total_apis"] > 0 else 0
                    },
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error getting real-time metrics: {e}")
                return {
                    "events_per_hour": 0,
                    "api_calls_active": 0,
                    "data_sources_active": [],
                    "api_metrics": [],
                    "inactive_apis": 0,
                    "error_apis": 0,
                    "total_apis": 0,
                    "health_summary": {
                        "healthy": 0,
                        "unhealthy": 0,
                        "total": 0,
                        "health_percentage": 0
                    },
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }

        secure_dependency = [Depends(self.auth_manager.get_current_user)]

        # Health endpoints
        self.app.include_router(
            self.health_endpoints.router,
            prefix="/api/v1",
            tags=["Health"]
        )

        # Statistics endpoints
        self.app.include_router(
            self.stats_endpoints.router,
            prefix="/api/v1",
            tags=["Statistics"],
            dependencies=secure_dependency
        )

        # Configuration endpoints
        self.app.include_router(
            self.config_endpoints.router,
            prefix="/api/v1",
            tags=["Configuration"],
            dependencies=secure_dependency
        )

        # MQTT/Zigbee configuration endpoints
        # GET is public (no auth) - allows dashboard to load config
        self.app.include_router(
            mqtt_config_public_router,
            prefix="/api/v1",
            tags=["Integrations"]
        )

        # PUT requires authentication - configuration changes must be secured
        self.app.include_router(
            mqtt_config_router,
            prefix="/api/v1",
            tags=["Integrations"],
            dependencies=secure_dependency
        )

        # Docker management endpoints
        self.app.include_router(
            self.docker_endpoints.router,
            tags=["Docker Management"],
            dependencies=secure_dependency
        )

        # Events endpoints removed - migrated to data-api (Epic 13 Story 13.2)

        # Monitoring endpoints
        self.app.include_router(
            self.monitoring_endpoints.router,
            prefix="/api/v1/monitoring",
            tags=["Monitoring"],
            dependencies=secure_dependency
        )

        # WebSocket endpoints removed - dashboard uses HTTP polling for simplicity

        # Integration Management endpoints removed - migrated to data-api (Epic 13 Story 13.3)

        # Devices & Entities endpoints removed - migrated to data-api (Epic 13 Story 13.2)

        # Home Assistant proxy endpoints
        self.app.include_router(
            ha_proxy_router,
            tags=["Home Assistant Proxy"],
            dependencies=secure_dependency
        )

        # Metrics endpoints removed - migrated to data-api (Epic 13 Story 13.3)

        # Alert endpoints removed - migrated to data-api (Epic 13 Story 13.3)

        # Root health endpoint (for Docker health checks)
        @self.app.get("/health")
        async def root_health():
            """Simple health check endpoint for Docker and monitoring"""
            if self.health_endpoints is None:
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "service": "admin-api",
                    "uptime_seconds": 0
                }
            uptime = (datetime.now() - self.health_endpoints.start_time).total_seconds()
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "admin-api",
                "uptime_seconds": uptime
            }

        # Root endpoint
        @self.app.get("/", response_model=APIResponse)
        async def root():
            """Root endpoint"""
            return APIResponse(
                success=True,
                data={
                    "service": self.api_title,
                    "version": self.api_version,
                    "status": "running",
                    "timestamp": datetime.now().isoformat()
                },
                message="Admin API is running"
            )

        # API info endpoint
        @self.app.get("/api/info", response_model=APIResponse)
        async def api_info():
            """API information endpoint"""
            return APIResponse(
                success=True,
                data={
                    "title": self.api_title,
                    "version": self.api_version,
                    "description": self.api_description,
                    "endpoints": {
                        "health": "/api/v1/health",
                        "stats": "/api/v1/stats",
                        "config": "/api/v1/config",
                        "events": "/api/v1/events"
                    },
                  "authentication": {
                      "api_key_required": not self.allow_anonymous,
                      "docs_enabled": self.docs_enabled
                  },
                  "rate_limit": {
                      "requests_per_minute": self.rate_limiter.rate,
                      "burst": self.rate_limiter.burst
                  },
                  "cors_enabled": True
                },
                message="API information retrieved successfully"
            )

    def _add_exception_handlers(self):
        """Add exception handlers to FastAPI app"""
        if self.app is None:
            logger.error("Cannot add exception handlers: FastAPI app is not initialized")
            return

        # Register shared error handlers if available
        if register_error_handlers:
            register_error_handlers(self.app)
            logger.info("✅ Shared error handlers registered")
        else:
            # Fallback to local error handlers
            @self.app.exception_handler(HTTPException)
            async def http_exception_handler(request, exc: HTTPException):
                """Handle HTTP exceptions"""
                return JSONResponse(
                    status_code=exc.status_code,
                    content=ErrorResponse(
                        error=exc.detail,
                        error_code=f"HTTP_{exc.status_code}",
                        request_id=getattr(request.state, 'request_id', None)
                    ).model_dump()
                )

            @self.app.exception_handler(Exception)
            async def general_exception_handler(request, exc: Exception):
                """Handle general exceptions"""
                logger.error(f"Unhandled exception: {exc}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content=ErrorResponse(
                        error="Internal server error",
                        error_code="INTERNAL_ERROR",
                        request_id=getattr(request.state, 'request_id', None)
                    ).model_dump()
                )

    def get_app(self) -> FastAPI:
        """Get FastAPI app instance"""
        return self.app


# Global service instance
admin_api_service = AdminAPIService()


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("Starting Admin API service...")

    # Start monitoring services
    await logging_service.start()
    await metrics_service.start()
    await alerting_service.start()

    # Initialize InfluxDB connection for stats endpoints
    try:
        logger.info("Initializing InfluxDB connection for statistics...")
        await admin_api_service.stats_endpoints.initialize()
        logger.info("InfluxDB connection initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize InfluxDB: {e}")
        logger.warning("Statistics will fall back to direct service calls")

    # WebSocket broadcast loop removed - using HTTP polling only

    logger.info("Admin API service started on 0.0.0.0:8004")

    yield

    # Shutdown
    logger.info("Shutting down Admin API service...")

    # WebSocket broadcast loop removed - using HTTP polling only

    # Close InfluxDB connection
    try:
        await admin_api_service.stats_endpoints.close()
    except Exception as e:
        logger.error(f"Error closing InfluxDB connection: {e}")

    # Stop monitoring services
    await alerting_service.stop()
    await metrics_service.stop()
    await logging_service.stop()

    logger.info("Admin API service stopped")


# Create FastAPI app for external use
app = FastAPI(
    title=admin_api_service.api_title,
    version=admin_api_service.api_version,
    description=admin_api_service.api_description,
    docs_url="/docs" if admin_api_service.docs_enabled else None,
    redoc_url="/redoc" if admin_api_service.docs_enabled else None,
    openapi_url="/openapi.json" if (admin_api_service.docs_enabled or admin_api_service.openapi_enabled) else None,
    lifespan=lifespan
)

# Initialize the app in the service
admin_api_service.app = app

# Add middleware and routes
admin_api_service._add_middleware()
admin_api_service._add_routes()
admin_api_service._add_exception_handlers()


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "src.main:app",
        host=admin_api_service.api_host,
        port=admin_api_service.api_port,
        reload=os.getenv('RELOAD', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )
