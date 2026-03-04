"""Route registration for the Admin API service.

Organizes public endpoints, authenticated sub-routers,
and root-level endpoints into separate registration functions.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import Depends

from .config_endpoints import ConfigEndpoints
from .docker_endpoints import DockerEndpoints
from .ha_proxy_endpoints import router as ha_proxy_router
from .health_endpoints import HealthEndpoints
from .models import APIResponse
from .mqtt_config_endpoints import public_router as mqtt_config_public_router
from .mqtt_config_endpoints import router as mqtt_config_router

if TYPE_CHECKING:
    from fastapi import FastAPI
    from homeiq_data.auth import AuthManager
    from homeiq_data.rate_limiter import RateLimiter
    from homeiq_observability.monitoring import MonitoringEndpoints, StatsEndpoints


def register_routers(
    app: "FastAPI",
    *,
    auth_manager: "AuthManager",
    health_endpoints: HealthEndpoints,
    stats_endpoints: "StatsEndpoints",
    config_endpoints: ConfigEndpoints,
    docker_endpoints: DockerEndpoints,
    monitoring_endpoints: "MonitoringEndpoints",
) -> None:
    """Include all sub-routers with appropriate auth dependencies.

    Args:
        app: The FastAPI application instance.
        auth_manager: Auth manager providing user dependency.
        health_endpoints: Health router (public).
        stats_endpoints: Statistics router (authenticated).
        config_endpoints: Configuration router (authenticated).
        docker_endpoints: Docker management router (authenticated).
        monitoring_endpoints: Monitoring router (authenticated).
    """
    secure = [Depends(auth_manager.get_current_user)]

    app.include_router(
        health_endpoints.router, prefix="/api/v1", tags=["Health"]
    )
    app.include_router(
        stats_endpoints.router,
        prefix="/api/v1", tags=["Statistics"], dependencies=secure,
    )
    app.include_router(
        config_endpoints.router,
        prefix="/api/v1", tags=["Configuration"], dependencies=secure,
    )
    app.include_router(
        mqtt_config_public_router, prefix="/api/v1", tags=["Integrations"]
    )
    app.include_router(
        mqtt_config_router,
        prefix="/api/v1", tags=["Integrations"], dependencies=secure,
    )
    app.include_router(
        docker_endpoints.router,
        tags=["Docker Management"], dependencies=secure,
    )
    app.include_router(
        monitoring_endpoints.router,
        prefix="/api/v1/monitoring", tags=["Monitoring"], dependencies=secure,
    )
    app.include_router(
        ha_proxy_router, tags=["Home Assistant Proxy"], dependencies=secure,
    )


def register_root_endpoints(
    app: "FastAPI",
    *,
    api_title: str,
    api_version: str,
    api_description: str,
    allow_anonymous: bool,
    docs_enabled: bool,
    rate_limiter: "RateLimiter",
    health_endpoints: HealthEndpoints,
) -> None:
    """Register root-level endpoints (Docker health, root info, API info).

    Args:
        app: The FastAPI application instance.
        api_title: Service title for display.
        api_version: Service version string.
        api_description: Service description.
        allow_anonymous: Whether anonymous access is allowed.
        docs_enabled: Whether API docs are enabled.
        rate_limiter: Rate limiter instance for stats.
        health_endpoints: Health endpoints for uptime tracking.
    """

    @app.get("/health")
    async def root_health() -> dict[str, Any]:
        """Return minimal health for Docker HEALTHCHECK and monitoring probes."""
        uptime = 0.0
        if health_endpoints is not None:
            uptime = (
                datetime.now(UTC) - health_endpoints.start_time
            ).total_seconds()
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "admin-api",
            "uptime_seconds": uptime,
        }

    @app.get("/", response_model=APIResponse)
    async def root() -> APIResponse:
        """Return service identity and running status."""
        return APIResponse(
            success=True,
            data={
                "service": api_title,
                "version": api_version,
                "status": "running",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            message="Admin API is running",
        )

    @app.get("/api/info", response_model=APIResponse)
    async def api_info() -> APIResponse:
        """Return API metadata: endpoints, auth settings, rate limits, CORS."""
        return APIResponse(
            success=True,
            data={
                "title": api_title,
                "version": api_version,
                "description": api_description,
                "endpoints": {
                    "health": "/api/v1/health",
                    "stats": "/api/v1/stats",
                    "config": "/api/v1/config",
                    "events": "/api/v1/events",
                },
                "authentication": {
                    "api_key_required": not allow_anonymous,
                    "docs_enabled": docs_enabled,
                },
                "rate_limit": {
                    "requests_per_minute": rate_limiter.rate,
                    "burst": rate_limiter.burst,
                },
                "cors_enabled": True,
            },
            message="API information retrieved successfully",
        )
