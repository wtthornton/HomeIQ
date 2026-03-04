"""Admin REST API Service.

FastAPI-based administration API for the HomeIQ platform.
Provides health checks, configuration management, Docker management,
real-time metrics, and monitoring endpoints on port 8004.
"""

import os
import time

import uvicorn
from dotenv import load_dotenv
from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .config import Settings, settings
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

    def __init__(self, cfg: Settings | None = None) -> None:
        """Initialize service from *cfg* (defaults to env-based config)."""
        self.cfg: Settings = cfg or settings
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

    def setup_app(self, app):
        """Wire middleware, routes, and exception handlers onto *app*."""
        global _counters
        c = self.cfg
        setup_observability(app)
        setup_cors(
            app, origins=c.get_cors_origins_list(),
            methods=c.get_cors_methods_list(), headers=c.get_cors_headers_list(),
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


def _add_exception_handlers(app) -> None:
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
        logger.error("Unhandled exception: %s", exc, exc_info=True)
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
c = admin_api_service.cfg


async def _start_monitoring() -> None:
    """Start background monitoring services."""
    await logging_service.start()
    await metrics_service.start()
    await alerting_service.start()


async def _init_influxdb() -> None:
    """Initialize InfluxDB connection for stats."""
    try:
        await admin_api_service.stats_endpoints.initialize()
    except Exception as e:
        logger.warning("Failed to initialize InfluxDB: %s", e)


async def _stop_monitoring() -> None:
    """Stop monitoring and close InfluxDB."""
    try:
        await admin_api_service.stats_endpoints.close()
    except Exception as e:
        logger.error("Error closing InfluxDB: %s", e)
    await alerting_service.stop()
    await metrics_service.stop()
    await logging_service.stop()


# -- ServiceLifespan (replaces manual asynccontextmanager lifespan) ---------

_lifespan = ServiceLifespan(c.service_name)
_lifespan.on_startup(_start_monitoring, name="monitoring")
_lifespan.on_startup(_init_influxdb, name="influxdb")
_lifespan.on_shutdown(_stop_monitoring, name="monitoring")

# -- StandardHealthCheck (provides consistent /health) ----------------------

_health = StandardHealthCheck(service_name=c.service_name, version=c.api_version)

# -- App creation -----------------------------------------------------------

app = create_app(
    title=c.api_title,
    version=c.api_version,
    description=c.api_description,
    lifespan=_lifespan.handler,
    health_check=_health,
    cors_origins=c.get_cors_origins_list(),
)

# Wire all admin-api specific middleware, routes, and exception handlers
admin_api_service.setup_app(app)

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", host="0.0.0.0",  # noqa: S104
        port=c.service_port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=c.log_level.lower(),
    )
