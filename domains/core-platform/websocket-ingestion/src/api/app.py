"""FastAPI application setup for websocket-ingestion service.

Uses the shared ``create_app`` factory, ``ServiceLifespan``, and
``StandardHealthCheck`` from homeiq-resilience while preserving
all existing routers and WebSocket handling.
"""

import logging

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from ..config import settings
from .routers import discovery, event_rate, filter, health, websocket

logger = logging.getLogger(__name__)


# -- lifecycle hooks --------------------------------------------------------

async def _startup_service() -> None:
    """Start the WebSocketIngestionService and store on app state."""
    # Lazy import to avoid circular dependency
    from ..main import WebSocketIngestionService

    service = WebSocketIngestionService()
    _startup_service._service = service  # type: ignore[attr-defined]
    await service.start()
    logger.info("WebSocket Ingestion Service started")


async def _shutdown_service() -> None:
    """Shut down the WebSocketIngestionService."""
    service = getattr(_startup_service, "_service", None)
    if service:
        await service.stop()
    logger.info("WebSocket Ingestion Service stopped")


# -- ServiceLifespan --------------------------------------------------------

_lifespan = ServiceLifespan(settings.service_name)
_lifespan.on_startup(_startup_service, name="ws-ingestion")
_lifespan.on_shutdown(_shutdown_service, name="ws-ingestion")

# -- StandardHealthCheck ----------------------------------------------------

_health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)

# -- App creation -----------------------------------------------------------

app = create_app(
    title="WebSocket Ingestion Service",
    description="Service for ingesting Home Assistant WebSocket events",
    version="1.0.0",
    lifespan=_lifespan.handler,
    health_check=_health,
    cors_origins=settings.get_cors_origins_list(),
)


# Store service reference on app state after startup
_orig_lifespan = app.router.lifespan_context


async def _wire_state_lifespan(app_instance):
    """Wrap lifespan to wire service onto app.state after startup."""
    async with _orig_lifespan(app_instance) as state:
        service = getattr(_startup_service, "_service", None)
        if service:
            app_instance.state.service = service
        yield state


app.router.lifespan_context = _wire_state_lifespan

# Include existing routers (health router provides /health/detailed)
app.include_router(health.router)
app.include_router(event_rate.router)
app.include_router(discovery.router)
app.include_router(filter.router)
app.include_router(websocket.router)
