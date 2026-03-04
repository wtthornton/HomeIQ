"""
Device Health Monitor Service
Phase 1.2: Monitor device health and provide maintenance insights

Analyzes device response times, battery levels, power consumption, and generates health reports.
"""

import os
from datetime import UTC, datetime

import uvicorn
from fastapi import HTTPException
from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import (
    GroupHealthCheck,
    ServiceLifespan,
    StandardHealthCheck,
    create_app,
    wait_for_dependency,
)
from pydantic import BaseModel, Field

from src.clients.data_api_client import DataAPIClient
from src.clients.device_intelligence_client import DeviceIntelligenceClient
from src.ha_client import HAClient
from src.health_analyzer import HealthAnalyzer

logger = setup_logging("device-health-monitor", group_name="device-management")


class AnalyzeRequest(BaseModel):
    """Request body for device health analysis"""
    device_id: str = Field(description="Device identifier")
    device_name: str = Field(description="Device display name")
    entity_ids: list[str] = Field(description="List of HA entity IDs for this device")
    power_spec_w: float | None = Field(default=None, description="Expected power consumption in watts")
    actual_power_w: float | None = Field(default=None, description="Actual power consumption in watts")


# --- Shared state ---

_data_api_client: DataAPIClient | None = None
_device_intel_client: DeviceIntelligenceClient | None = None
_ha_client: HAClient | None = None
_analyzer: HealthAnalyzer | None = None
_ha_configured: bool = False
_group_health: GroupHealthCheck | None = None


# --- Lifespan ---

async def _startup() -> None:
    global _data_api_client, _device_intel_client, _ha_client, _analyzer, _ha_configured, _group_health

    # Probe cross-group dependencies (non-fatal)
    await wait_for_dependency(url="http://data-api:8006", name="data-api", max_retries=10)
    await wait_for_dependency(
        url="http://device-intelligence-service:8019", name="device-intelligence",
        max_retries=10,
    )

    # Initialize group health check
    _group_health = GroupHealthCheck(group_name="device-management", version="1.0.0")
    _group_health.register_dependency("data-api", "http://data-api:8006")
    _group_health.register_dependency("device-intelligence", "http://device-intelligence-service:8019")

    # Cross-group clients
    _data_api_client = DataAPIClient()
    _device_intel_client = DeviceIntelligenceClient()

    ha_url = os.getenv("HA_URL", "")
    ha_token = os.getenv("HA_TOKEN", "")

    if ha_url and ha_token:
        _ha_client = HAClient(ha_url, ha_token)
        _analyzer = HealthAnalyzer(_ha_client)
        _ha_configured = True
        logger.info("Home Assistant client configured (url=%s)", ha_url)
    else:
        _ha_configured = False
        logger.warning("HA_URL or HA_TOKEN not set - service running in degraded mode")


async def _shutdown() -> None:
    if _ha_client is not None:
        await _ha_client.close()
        logger.info("HA client session closed")


lifespan = ServiceLifespan("Device Health Monitor Service")
lifespan.on_startup(_startup, name="init-components")
lifespan.on_shutdown(_shutdown, name="close-ha-client")


# --- Health check ---

async def _check_ha() -> bool:
    return _ha_configured


health = StandardHealthCheck(service_name="device-health-monitor", version="1.0.0")
health.register_check("ha-config", _check_ha)


# --- App ---

app = create_app(
    title="Device Health Monitor Service",
    version="1.0.0",
    description="Device health monitoring and maintenance insights",
    lifespan=lifespan.handler,
    health_check=health,
)


# --- Endpoints ---

@app.post("/api/v1/health/analyze")
async def analyze_device_health(request: AnalyzeRequest) -> dict:
    """Analyze health for a specific device"""
    if not _ha_configured or _analyzer is None:
        raise HTTPException(
            status_code=503,
            detail="Home Assistant not configured - cannot analyze device health"
        )

    try:
        report = await _analyzer.analyze_device_health(
            device_id=request.device_id,
            device_name=request.device_name,
            device_entities=request.entity_ids,
            power_spec_w=request.power_spec_w,
            actual_power_w=request.actual_power_w
        )
        return report
    except Exception as e:
        logger.error("Error analyzing device health for %s: %s", request.device_id, e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}") from e


@app.get("/api/v1/health/summary")
async def health_summary() -> dict:
    """Return basic health summary status"""
    return {
        "status": "healthy" if _ha_configured else "degraded",
        "service": "device-health-monitor",
        "ha_configured": _ha_configured,
        "timestamp": datetime.now(UTC).isoformat()
    }


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_HEALTH_MONITOR_PORT", "8019"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
