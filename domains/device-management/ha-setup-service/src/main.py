"""HA Setup Service - Main FastAPI Application.

Provides setup wizards, health monitoring, performance optimization
and Zigbee2MQTT bridge management for Home Assistant environments.
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
from .routes_zigbee import bridge_router, setup_router
from .validation_service import ValidationService
from .zigbee_bridge_manager import ZigbeeBridgeManager
from .zigbee_setup_wizard import Zigbee2MQTTSetupWizard as ZigbeeSetupWizard

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
        app.state.monitor, app.state.integration_checker,
    )
    app.state.continuous_monitor = _continuous_monitor
    await _continuous_monitor.start()

    app.state.performance_analyzer = PerformanceAnalysisEngine()
    app.state.recommendation_engine = RecommendationEngine()
    app.state.bridge_manager = ZigbeeBridgeManager()
    app.state.zigbee_setup_wizard = ZigbeeSetupWizard()
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
app.include_router(bridge_router)
app.include_router(setup_router)
app.include_router(health_router)
app.include_router(optimization_router)
app.include_router(validation_router)


# The generic /api/setup/wizard/* endpoints are gone along with the wizard
# framework module. They fronted an MQTT wizard that declared five steps and
# never implemented any of them, plus a second Zigbee2MQTT wizard competing
# with the one behind /api/zigbee2mqtt/setup/*. That router is now the single
# setup surface.


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
