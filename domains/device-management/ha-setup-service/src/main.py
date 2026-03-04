"""HA Setup Service - Main FastAPI Application.

Provides setup wizards, health monitoring, performance optimization
and Zigbee2MQTT bridge management for Home Assistant environments.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from .schemas import HealthCheckResponse
from .setup_wizard import MQTTSetupWizard, Zigbee2MQTTSetupWizard
from .validation_service import ValidationService
from .zigbee_bridge_manager import ZigbeeBridgeManager
from .zigbee_setup_wizard import Zigbee2MQTTSetupWizard as ZigbeeSetupWizard

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for service initialization and cleanup."""
    logger.info("HA Setup Service Starting")
    db_ok = await init_db()
    if db_ok:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable - starting in degraded mode")

    app.state.monitor = HealthMonitoringService()
    app.state.integration_checker = IntegrationHealthChecker()
    continuous_monitor = ContinuousHealthMonitor(app.state.monitor, app.state.integration_checker)
    app.state.continuous_monitor = continuous_monitor
    await continuous_monitor.start()

    app.state.zigbee2mqtt_wizard = Zigbee2MQTTSetupWizard()
    app.state.mqtt_wizard = MQTTSetupWizard()
    app.state.performance_analyzer = PerformanceAnalysisEngine()
    app.state.recommendation_engine = RecommendationEngine()
    app.state.bridge_manager = ZigbeeBridgeManager()
    app.state.zigbee_setup_wizard = ZigbeeSetupWizard()
    app.state.validation_service = ValidationService()

    logger.info("HA Setup Service Ready - Listening on port %s", settings.service_port)
    yield

    logger.info("Stopping continuous monitoring...")
    await continuous_monitor.stop()
    await close_http_session()
    logger.info("HA Setup Service Shutting Down")


app = FastAPI(
    title="HA Setup & Recommendation Service",
    description="Automated setup, health monitoring, and optimization for Home Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include extracted route modules
app.include_router(bridge_router)
app.include_router(setup_router)
app.include_router(health_router)
app.include_router(optimization_router)
app.include_router(validation_router)


@app.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check() -> HealthCheckResponse:
    """Simple health check endpoint for container orchestration."""
    return HealthCheckResponse(
        status="healthy", service=settings.service_name,
        timestamp=datetime.now(UTC), version="1.0.0",
    )


@app.post("/api/setup/wizard/{integration_type}/start", tags=["setup"])
async def start_setup_wizard(request: Any, integration_type: str) -> dict[str, Any]:
    """Start a setup wizard for the specified integration type."""
    from fastapi import HTTPException, Request
    req: Request = request
    try:
        if integration_type == "zigbee2mqtt":
            wizard = getattr(req.app.state, "zigbee2mqtt_wizard", None)
            if not wizard:
                raise HTTPException(status_code=503, detail="Setup wizard not initialized")
            session_id = await wizard.start_zigbee2mqtt_setup()
        elif integration_type == "mqtt":
            wizard = getattr(req.app.state, "mqtt_wizard", None)
            if not wizard:
                raise HTTPException(status_code=503, detail="Setup wizard not initialized")
            session_id = await wizard.start_mqtt_setup()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported integration type: {integration_type}")
        return {"session_id": session_id, "integration_type": integration_type,
                "status": "started", "timestamp": datetime.now(UTC)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error starting setup wizard")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/setup/wizard/{session_id}/step/{step_number}", tags=["setup"])
async def execute_wizard_step(
    request: Any, session_id: str, step_number: int,
    step_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a specific step in the setup wizard."""
    from fastapi import HTTPException, Request
    req: Request = request
    try:
        zigbee_wizard = getattr(req.app.state, "zigbee2mqtt_wizard", None)
        mqtt_wizard = getattr(req.app.state, "mqtt_wizard", None)
        session = zigbee_wizard.get_session_status(session_id) or mqtt_wizard.get_session_status(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        wizard = zigbee_wizard if session["integration_type"] == "zigbee2mqtt" else mqtt_wizard
        return await wizard.execute_step(session_id, step_number, step_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing wizard step")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/", tags=["info"])
async def root() -> dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": "HA Setup & Recommendation Service",
        "version": "1.0.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("BIND_HOST", "0.0.0.0"),  # noqa: S104 - Intentional for Docker container
        port=settings.service_port,
        reload=True,
    )
