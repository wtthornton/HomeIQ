"""Admin REST API Service.

FastAPI-based administration API for the HomeIQ platform.
Provides health checks, configuration management, Docker management,
real-time metrics, and monitoring endpoints on port 8004.
"""

import asyncio
import contextlib
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from homeiq_observability.logging_config import setup_logging

from .config import AdminAPIConfig
from .endpoints import register_public_endpoints
from .middleware import (
    register_logging_middleware,
    register_rate_limit_middleware,
    setup_cors,
    setup_observability,
)
from .models import ErrorResponse
from .routes import register_root_endpoints, register_routers

load_dotenv()
logger = setup_logging("admin-api")

try:
    from homeiq_data.error_handler import register_error_handlers
except ImportError:
    register_error_handlers = None

from homeiq_data.auth import AuthManager
from homeiq_data.rate_limiter import RateLimiter
from homeiq_observability.monitoring import (
    MonitoringEndpoints,
    StatsEndpoints,
    alerting_service,
    logging_service,
    metrics_service,
)

from .config_endpoints import ConfigEndpoints
from .docker_endpoints import DockerEndpoints
from .health_endpoints import HealthEndpoints

_start_time: float = time.time()
_counters: list[int] = [0, 0]


class AdminAPIService:
    """Main Admin API service managing FastAPI lifecycle."""

    def __init__(self, cfg: AdminAPIConfig | None = None) -> None:
        """Initialize service from *cfg* (defaults to env-based config)."""
        self.cfg: AdminAPIConfig = cfg or AdminAPIConfig()
        c = self.cfg
        self.rate_limiter: RateLimiter = RateLimiter(
            rate=c.rate_limit_per_min, per=60, burst=c.rate_limit_burst,
        )
        self.auth_manager: AuthManager = AuthManager(
            api_key=c.api_key, allow_anonymous=c.allow_anonymous,
        )
        self.health_endpoints: HealthEndpoints = HealthEndpoints()
        self.stats_endpoints: StatsEndpoints = StatsEndpoints()
        self.config_endpoints: ConfigEndpoints = ConfigEndpoints()
        self.docker_endpoints: DockerEndpoints = DockerEndpoints(
            self.auth_manager
        )
        self.monitoring_endpoints: MonitoringEndpoints = MonitoringEndpoints(
            self.auth_manager
        )
        self.app: FastAPI | None = None
        self.server_task: asyncio.Task[None] | None = None
        self.is_running: bool = False

    async def start(self) -> None:
        """Start the Admin API including monitoring and HTTP server."""
        if self.is_running:
            logger.warning("Admin API is already running")
            return
        if self.app is None:
            self.app = self._create_app()
        await self._start_monitoring()
        await self._init_influxdb()
        self.setup_app(self.app)
        c = self.cfg
        config = uvicorn.Config(
            app=self.app, host=c.api_host, port=c.api_port,
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
        )
        self.server_task = asyncio.create_task(
            uvicorn.Server(config).serve()
        )
        self.is_running = True
        logger.info(f"Admin API started on {c.api_host}:{c.api_port}")

    async def stop(self) -> None:
        """Stop the service and release resources."""
        if not self.is_running:
            return
        self.is_running = False
        if self.server_task:
            self.server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.server_task
        try:
            await self.stats_endpoints.close()
        except Exception as e:
            logger.error(f"Error closing InfluxDB: {e}")
        await alerting_service.stop()
        await metrics_service.stop()
        await logging_service.stop()

    def get_app(self) -> FastAPI | None:
        """Return the FastAPI app instance."""
        return self.app

    def setup_app(self, app: FastAPI) -> None:
        """Wire middleware, routes, and exception handlers onto *app*."""
        global _counters
        c = self.cfg
        setup_observability(app)
        setup_cors(
            app, origins=c.cors_origins,
            methods=c.cors_methods, headers=c.cors_headers,
        )
        register_rate_limit_middleware(app, self.rate_limiter)
        _counters = register_logging_middleware(app)
        register_public_endpoints(
            app, stats_endpoints=self.stats_endpoints,
            allow_anonymous=c.allow_anonymous,
            docs_enabled=c.docs_enabled,
            rate_limiter=self.rate_limiter,
            start_time=_start_time, counters=_counters,
        )
        register_routers(
            app, auth_manager=self.auth_manager,
            health_endpoints=self.health_endpoints,
            stats_endpoints=self.stats_endpoints,
            config_endpoints=self.config_endpoints,
            docker_endpoints=self.docker_endpoints,
            monitoring_endpoints=self.monitoring_endpoints,
        )
        register_root_endpoints(
            app, api_title=c.api_title, api_version=c.api_version,
            api_description=c.api_description,
            allow_anonymous=c.allow_anonymous,
            docs_enabled=c.docs_enabled,
            rate_limiter=self.rate_limiter,
            health_endpoints=self.health_endpoints,
        )
        _add_exception_handlers(app)

    def _create_app(self) -> FastAPI:
        """Create a new FastAPI application instance."""
        c = self.cfg
        return FastAPI(
            title=c.api_title, version=c.api_version,
            description=c.api_description,
            docs_url="/docs" if c.docs_enabled else None,
            redoc_url="/redoc" if c.docs_enabled else None,
            openapi_url=(
                "/openapi.json"
                if (c.docs_enabled or c.openapi_enabled) else None
            ),
        )

    @staticmethod
    async def _start_monitoring() -> None:
        """Start background monitoring services."""
        await logging_service.start()
        await metrics_service.start()
        await alerting_service.start()

    async def _init_influxdb(self) -> None:
        """Initialize InfluxDB connection for stats."""
        try:
            await self.stats_endpoints.initialize()
        except Exception as e:
            logger.warning(f"Failed to initialize InfluxDB: {e}")


def _add_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers on the FastAPI app."""
    if register_error_handlers:
        register_error_handlers(app)
        return
    from fastapi import HTTPException, Request, status
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exc(
        request: Request, exc: HTTPException,
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail,
                error_code=f"HTTP_{exc.status_code}",
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exc(
        request: Request, exc: Exception,
    ) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal server error",
                error_code="INTERNAL_ERROR",
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )


# ---------------------------------------------------------------------------
# Module-level app setup
# ---------------------------------------------------------------------------

admin_api_service = AdminAPIService()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Manage application startup and shutdown lifecycle."""
    logger.info("Starting Admin API service...")
    await AdminAPIService._start_monitoring()
    await admin_api_service._init_influxdb()
    logger.info("Admin API started on 0.0.0.0:8004")
    yield
    logger.info("Shutting down Admin API service...")
    try:
        await admin_api_service.stats_endpoints.close()
    except Exception as e:
        logger.error(f"Error closing InfluxDB: {e}")
    await alerting_service.stop()
    await metrics_service.stop()
    await logging_service.stop()


c = admin_api_service.cfg
app = FastAPI(
    title=c.api_title, version=c.api_version,
    description=c.api_description,
    docs_url="/docs" if c.docs_enabled else None,
    redoc_url="/redoc" if c.docs_enabled else None,
    openapi_url=(
        "/openapi.json"
        if (c.docs_enabled or c.openapi_enabled) else None
    ),
    lifespan=lifespan,
)
admin_api_service.app = app
admin_api_service.setup_app(app)

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", host=c.api_host, port=c.api_port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
