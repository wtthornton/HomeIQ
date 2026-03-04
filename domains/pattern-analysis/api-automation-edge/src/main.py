"""Main FastAPI application for API Automation Edge Service."""

import logging
import sys
import threading
import time

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api.execution_router import router as execution_router
from .api.observability_router import router as observability_router
from .api.spec_router import router as spec_router
from .capability.capability_graph import CapabilityGraph
from .clients.ha_rest_client import HARestClient
from .clients.ha_websocket_client import HAWebSocketClient
from .config import settings


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()
logger = logging.getLogger(__name__)


# Global components
rest_client: HARestClient | None = None
websocket_client: HAWebSocketClient | None = None
capability_graph: CapabilityGraph | None = None


# ---------------------------------------------------------------------------
# Startup / Shutdown helpers
# ---------------------------------------------------------------------------

def _start_huey_consumer() -> None:
    """Initialize Huey in-memory task queue."""
    try:
        logger.info("Huey in-memory backend ready (no external consumer needed)")
    except Exception:
        logger.exception("Failed to initialize Huey")


async def _startup_service() -> None:
    """Initialize HA clients and capability graph."""
    global rest_client, websocket_client, capability_graph  # noqa: PLW0603

    rest_client = HARestClient()

    try:
        websocket_client = HAWebSocketClient()
        await websocket_client.connect()

        capability_graph = CapabilityGraph(rest_client, websocket_client)
        await capability_graph.initialize()
        await capability_graph.start(websocket_client)
    except Exception:
        logger.warning(
            "HA unavailable at startup -- running in degraded mode",
            exc_info=True,
        )
        logger.info(
            "Service will start without live HA data; "
            "endpoints requiring HA will return 503"
        )

    if settings.use_task_queue:
        try:
            consumer_thread = threading.Thread(
                target=_start_huey_consumer, daemon=True
            )
            consumer_thread.start()
            time.sleep(0.1)
            logger.info("Huey task queue consumer thread started")
        except ImportError:
            logger.warning("Huey not available - task queue disabled")
        except Exception:
            logger.exception("Failed to start Huey consumer")
            logger.warning("Service will continue without task queue")


async def _shutdown_service() -> None:
    """Gracefully shut down HA clients and task queue."""
    if settings.use_task_queue:
        try:
            from .task_queue.huey_config import huey  # noqa: F811

            huey.flush()
            logger.info("Huey in-memory queue flushed")
        except Exception:
            logger.warning("Error cleaning up Huey queue", exc_info=True)

    if capability_graph:
        await capability_graph.stop()

    if websocket_client:
        await websocket_client.disconnect()

    logger.info("API Automation Edge Service stopped")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_service, name="ha-clients")
lifespan.on_shutdown(_shutdown_service, name="ha-clients")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="HomeIQ API Automation Edge Service",
    version="1.0.0",
    description="API-driven automation engine for HomeIQ",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Include routers
app.include_router(spec_router)
app.include_router(execution_router)
app.include_router(observability_router)

# Include task and schedule routers if Huey is available
try:
    from .api.schedule_router import router as schedule_router
    from .api.task_router import router as task_router

    app.include_router(task_router)
    app.include_router(schedule_router)
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
    )
