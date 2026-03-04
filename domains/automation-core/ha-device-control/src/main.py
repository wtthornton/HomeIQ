"""HA Device Control Service -- main entry point.

FastAPI app providing direct Home Assistant device control via REST API.
Supports lights, switches, climate, scenes, notifications, and house
status snapshots.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from . import __version__
from .config import settings

if TYPE_CHECKING:
    from .services.blacklist import BlacklistService
    from .services.climate_controller import ClimateController
    from .services.entity_resolver import EntityResolver
    from .services.ha_rest_client import HARestClient
    from .services.light_controller import LightController
    from .services.notification_service import NotificationService
    from .services.scene_controller import SceneController
    from .services.status_service import StatusService
    from .services.switch_controller import SwitchController

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    """Configure logging for the service."""
    try:
        from homeiq_observability.logging_config import setup_logging

        setup_logging(settings.service_name)
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


_configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global service components (initialized in _startup)
# ---------------------------------------------------------------------------

ha_client: "HARestClient | None" = None  # noqa: UP037
blacklist_service: "BlacklistService | None" = None  # noqa: UP037
entity_resolver: "EntityResolver | None" = None  # noqa: UP037
light_controller: "LightController | None" = None  # noqa: UP037
switch_controller: "SwitchController | None" = None  # noqa: UP037
climate_controller: "ClimateController | None" = None  # noqa: UP037
scene_controller: "SceneController | None" = None  # noqa: UP037
status_service: "StatusService | None" = None  # noqa: UP037
notification_service: "NotificationService | None" = None  # noqa: UP037


async def _startup() -> None:
    """Initialize all service components."""
    global ha_client, blacklist_service, entity_resolver  # noqa: PLW0603
    global light_controller, switch_controller, climate_controller  # noqa: PLW0603
    global scene_controller, status_service, notification_service  # noqa: PLW0603

    from .services.blacklist import BlacklistService
    from .services.climate_controller import ClimateController
    from .services.entity_resolver import EntityResolver
    from .services.ha_rest_client import HARestClient
    from .services.light_controller import LightController
    from .services.notification_service import NotificationService
    from .services.scene_controller import SceneController
    from .services.status_service import StatusService
    from .services.switch_controller import SwitchController

    logger.info("Starting %s v%s", settings.service_name, __version__)

    # HA REST client
    token = settings.ha_token.get_secret_value() if settings.ha_token else ""
    ha_client = HARestClient(
        base_url=settings.ha_url,
        token=token,
        timeout=settings.ha_timeout,
    )
    await ha_client.startup()

    # Verify HA connectivity
    if token:
        connected = await ha_client.check_connection()
        if connected:
            logger.info("HA connection verified: %s", settings.ha_url)
        else:
            logger.warning("Could not connect to HA at %s -- will retry on first request", settings.ha_url)
    else:
        logger.warning("No HA_TOKEN configured -- HA API calls will fail")

    # Blacklist
    blacklist_service = BlacklistService()
    blacklist_service.load_from_config(settings.blacklist_patterns)

    # Entity resolver
    entity_resolver = EntityResolver(
        ha_client=ha_client,
        blacklist=blacklist_service,
        cache_ttl=settings.entity_cache_ttl_seconds,
    )

    # Controllers
    light_controller = LightController(ha_client, entity_resolver)
    switch_controller = SwitchController(ha_client, entity_resolver)
    climate_controller = ClimateController(ha_client, entity_resolver)
    scene_controller = SceneController(ha_client, entity_resolver)
    status_service = StatusService(entity_resolver)
    notification_service = NotificationService(
        ha_client=ha_client,
        default_service=settings.default_notify_service,
    )

    # Pre-warm entity cache if HA is available
    if token:
        try:
            count = await entity_resolver.refresh_cache()
            logger.info("Entity cache pre-warmed: %d entities", count)
        except Exception:
            logger.warning("Failed to pre-warm entity cache -- will retry on first request")

    logger.info("%s v%s ready on port %d", settings.service_name, __version__, settings.service_port)


async def _shutdown() -> None:
    """Graceful shutdown."""
    logger.info("Shutting down %s", settings.service_name)
    if ha_client:
        await ha_client.shutdown()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup, name="device_control")
lifespan.on_shutdown(_shutdown, name="device_control")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version=__version__,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="HA Device Control Service",
    version=__version__,
    description="Direct Home Assistant device control via REST API",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

from .api.admin_router import router as admin_router  # noqa: E402
from .api.control_router import router as control_router  # noqa: E402
from .api.notify_router import router as notify_router  # noqa: E402
from .api.status_router import router as status_router  # noqa: E402

app.include_router(control_router)
app.include_router(status_router)
app.include_router(notify_router)
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Detailed health endpoint
# ---------------------------------------------------------------------------


@app.get("/health/details")
async def health_details() -> dict:
    """Detailed health check with component-level status."""
    ha_ok = ha_client.is_connected if ha_client else False
    cache_size = entity_resolver.cache_size if entity_resolver else 0
    cache_age = entity_resolver.cache_age_seconds if entity_resolver else -1
    bl_count = len(blacklist_service.list_all()) if blacklist_service else 0

    overall = "healthy" if ha_ok else "degraded"
    return {
        "status": overall,
        "version": __version__,
        "components": {
            "ha_client": "connected" if ha_ok else "disconnected",
            "entity_cache_size": cache_size,
            "entity_cache_age_seconds": round(cache_age, 1),
            "blacklist_patterns": bl_count,
        },
    }


# ---------------------------------------------------------------------------
# Run with uvicorn
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        log_level="info",
    )
