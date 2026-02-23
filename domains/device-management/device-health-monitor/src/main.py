"""
Device Health Monitor Service
Phase 1.2: Monitor device health and provide maintenance insights

Analyzes device response times, battery levels, power consumption, and generates health reports.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from homeiq_observability.logging_config import setup_logging
from src.clients.data_api_client import DataAPIClient
from src.clients.device_intelligence_client import DeviceIntelligenceClient
from src.ha_client import HAClient
from src.health_analyzer import HealthAnalyzer

try:
    from homeiq_resilience import GroupHealthCheck, wait_for_dependency
except ImportError:
    GroupHealthCheck = None  # type: ignore[assignment,misc]
    wait_for_dependency = None  # type: ignore[assignment]

logger = setup_logging("device-health-monitor", group_name="device-management")

# Global group health check
_group_health: GroupHealthCheck | None = None


class AnalyzeRequest(BaseModel):
    """Request body for device health analysis"""
    device_id: str = Field(description="Device identifier")
    device_name: str = Field(description="Device display name")
    entity_ids: list[str] = Field(description="List of HA entity IDs for this device")
    power_spec_w: Optional[float] = Field(default=None, description="Expected power consumption in watts")
    actual_power_w: Optional[float] = Field(default=None, description="Actual power consumption in watts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    global _group_health

    # Startup
    logger.info("Device Health Monitor Service starting up...")

    # Probe cross-group dependencies (non-fatal)
    if wait_for_dependency is not None:
        await wait_for_dependency(url="http://data-api:8006", name="data-api", max_retries=10)
        await wait_for_dependency(
            url="http://device-intelligence-service:8019", name="device-intelligence",
            max_retries=10,
        )

    # Initialize group health check
    if GroupHealthCheck is not None:
        _group_health = GroupHealthCheck(
            group_name="device-management", version="1.0.0",
        )
        _group_health.register_dependency("data-api", "http://data-api:8006")
        _group_health.register_dependency(
            "device-intelligence", "http://device-intelligence-service:8019",
        )

    # Cross-group clients
    app.state.data_api_client = DataAPIClient()
    app.state.device_intel_client = DeviceIntelligenceClient()

    ha_url = os.getenv("HA_URL", "")
    ha_token = os.getenv("HA_TOKEN", "")

    if ha_url and ha_token:
        ha_client = HAClient(ha_url, ha_token)
        app.state.ha_client = ha_client
        app.state.analyzer = HealthAnalyzer(ha_client)
        app.state.ha_configured = True
        logger.info("Home Assistant client configured (url=%s)", ha_url)
    else:
        app.state.ha_client = None
        app.state.analyzer = None
        app.state.ha_configured = False
        logger.warning("HA_URL or HA_TOKEN not set - service running in degraded mode")

    yield

    # Shutdown
    logger.info("Device Health Monitor Service shutting down...")
    if app.state.ha_client is not None:
        await app.state.ha_client.close()
        logger.info("HA client session closed")


app = FastAPI(
    title="Device Health Monitor Service",
    version="1.0.0",
    description="Device health monitoring and maintenance insights",
    lifespan=lifespan
)


@app.get("/health")
async def health_check() -> dict:
    """Health check with group-level status."""
    if _group_health is not None:
        response = await _group_health.to_dict()
    else:
        response = {
            "status": "healthy",
            "service": "device-health-monitor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    response["ha_configured"] = getattr(app.state, "ha_configured", False)
    if not response["ha_configured"]:
        response["status"] = "degraded"
        response["error"] = "Home Assistant not configured (HA_URL/HA_TOKEN missing)"

    return response


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": "device-health-monitor",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/api/v1/health/analyze")
async def analyze_device_health(request: AnalyzeRequest) -> dict:
    """Analyze health for a specific device"""
    if not app.state.ha_configured or app.state.analyzer is None:
        raise HTTPException(
            status_code=503,
            detail="Home Assistant not configured - cannot analyze device health"
        )

    try:
        report = await app.state.analyzer.analyze_device_health(
            device_id=request.device_id,
            device_name=request.device_name,
            device_entities=request.entity_ids,
            power_spec_w=request.power_spec_w,
            actual_power_w=request.actual_power_w
        )
        return report
    except Exception as e:
        logger.error("Error analyzing device health for %s: %s", request.device_id, e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.get("/api/v1/health/summary")
async def health_summary() -> dict:
    """Return basic health summary status"""
    return {
        "status": "healthy" if app.state.ha_configured else "degraded",
        "service": "device-health-monitor",
        "ha_configured": app.state.ha_configured,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_HEALTH_MONITOR_PORT", "8019"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
