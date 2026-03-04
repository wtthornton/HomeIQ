"""RAG Service - Main FastAPI Application.

Standalone RAG (Retrieval-Augmented Generation) microservice.
Uses shared library pattern: create_app + ServiceLifespan + StandardHealthCheck.
"""

import logging
import sys
from typing import Any

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .api import metrics_router, rag_router
from .clients.openvino_client import OpenVINOClient
from .config import settings
from .database.session import init_db


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# Configure logging
_configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton resources managed via app.state (set during startup)
# ---------------------------------------------------------------------------
_openvino_client: OpenVINOClient | None = None


async def _startup_db() -> None:
    """Initialize database connection."""
    db_ok = await init_db()
    if db_ok:
        logger.info("RAG Service database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")


async def _startup_openvino() -> None:
    """Create singleton OpenVINO client."""
    global _openvino_client  # noqa: PLW0603
    _openvino_client = OpenVINOClient(base_url=settings.openvino_service_url)
    logger.info("OpenVINO client initialized (url=%s)", settings.openvino_service_url)


async def _shutdown_openvino() -> None:
    """Close the OpenVINO HTTP client."""
    if _openvino_client is not None:
        await _openvino_client.close()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_db, name="database")
lifespan.on_startup(_startup_openvino, name="openvino-client")
lifespan.on_shutdown(_shutdown_openvino, name="openvino-client")


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
    title="RAG Service",
    version="1.0.0",
    description="Semantic knowledge storage and retrieval service with embeddings",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Include API routes (health is auto-included by create_app)
app.include_router(rag_router.router)
app.include_router(metrics_router.router)


# Expose openvino_client on app.state for route handlers
@app.middleware("http")
async def _inject_openvino_state(request: Any, call_next: Any) -> Any:
    """Ensure app.state.openvino_client is set for route dependencies."""
    if _openvino_client is not None and not hasattr(request.app.state, "openvino_client"):
        request.app.state.openvino_client = _openvino_client
        request.app.state.embedding_cache: dict[str, Any] = {}
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
