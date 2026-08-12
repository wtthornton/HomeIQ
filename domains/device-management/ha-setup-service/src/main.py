"""HA Setup Service - Main FastAPI Application.

Provides health monitoring, performance optimization and setup validation
for Home Assistant environments. Zigbee onboarding now lives in the
libs/homeiq-ha init agent (ZHA recipe), not here.
"""

from __future__ import annotations

import logging
import sys

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .config import get_settings
from .database import init_db
from .health_service import HealthMonitoringService
from .http_client import close_http_session
from .integration_checker import IntegrationHealthChecker
from .monitoring_service import ContinuousHealthMonitor
from .optimization_engine import PerformanceAnalysisEngine, RecommendationEngine
from .routes_health import health_router
from .routes_validation import optimization_router, validation_router
from .validation_service import ValidationService

settings = get_settings()


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()
logger = logging.getLogger(__name__)

# Reference to continuous monitor for shutdown
_continuous_monitor: ContinuousHealthMonitor | None = None


# ---------------------------------------------------------------------------
# Lifespan hooks
# ---------------------------------------------------------------------------


async def _startup_db() -> None:
    """Initialize database on startup."""
    db_ok = await init_db()
    if db_ok:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable - starting in degraded mode")


async def _startup_services() -> None:
    """Initialize service components on startup."""
    global _continuous_monitor  # noqa: PLW0603

    app.state.monitor = HealthMonitoringService()
    app.state.integration_checker = IntegrationHealthChecker()
    _continuous_monitor = ContinuousHealthMonitor(
        app.state.monitor,
        app.state.integration_checker,
    )
    app.state.continuous_monitor = _continuous_monitor
    await _continuous_monitor.start()

    app.state.performance_analyzer = PerformanceAnalysisEngine()
    app.state.recommendation_engine = RecommendationEngine()
    app.state.validation_service = ValidationService()


async def _shutdown_services() -> None:
    """Stop services and close connections on shutdown."""
    if _continuous_monitor is not None:
        await _continuous_monitor.stop()
    await close_http_session()


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_db, name="database")
lifespan.on_startup(_startup_services, name="services")
lifespan.on_shutdown(_shutdown_services, name="services")


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
    title="HA Setup & Recommendation Service",
    version="1.0.0",
    description="Automated setup, health monitoring, and optimization for Home Assistant",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Include extracted route modules
app.include_router(health_router)
app.include_router(optimization_router)
app.include_router(validation_router)


# The Zigbee2MQTT wizard, bridge manager and their routers are gone: they
# called two Home Assistant services that do not exist and hit WS-only
# registries over REST (docs/ha-init-agent-design.md). Zigbee onboarding is
# the libs/homeiq-ha init agent's ZHA recipe now.


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
