"""
Device Recommender Service
Phase 3.3: Device recommendations and comparisons

Recommends devices based on user requirements, compares devices,
and provides device ratings from Device Database.
"""

import os

import uvicorn
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from src.comparison_engine import DeviceComparisonEngine
from src.ha_client import HAClient
from src.recommender import DeviceRecommender

logger = setup_logging("device-recommender")


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    device_type: str
    requirements: dict | None = None
    user_devices: list[dict] | None = None


class RecommendResponse(BaseModel):
    recommendations: list[dict]
    total: int


class CompareRequest(BaseModel):
    device_ids: list[str] = Field(..., min_length=2)
    devices: list[dict]


class CompareResponse(BaseModel):
    devices: list[dict]
    comparison_points: dict
    recommendation: dict


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_ha_client: HAClient | None = None
_recommender: DeviceRecommender | None = None
_comparison_engine: DeviceComparisonEngine | None = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

async def _startup() -> None:
    global _ha_client, _recommender, _comparison_engine
    _ha_client = HAClient()
    _recommender = DeviceRecommender()
    _comparison_engine = DeviceComparisonEngine()
    logger.info("Device Recommender components initialized")


async def _shutdown() -> None:
    global _ha_client
    if _ha_client:
        await _ha_client.close()
    logger.info("Device Recommender shut down")


lifespan = ServiceLifespan("Device Recommender Service")
lifespan.on_startup(_startup, name="init-components")
lifespan.on_shutdown(_shutdown, name="close-ha-client")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def _check_ha() -> bool:
    return _ha_client is not None and bool(_ha_client.ha_url)


health = StandardHealthCheck(service_name="device-recommender", version="1.0.0")
health.register_check("ha-config", _check_ha)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Device Recommender Service",
    version="1.0.0",
    description="Device recommendations and comparisons",
    lifespan=lifespan.handler,
    health_check=health,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/recommend", response_model=RecommendResponse)
async def recommend(body: RecommendRequest) -> RecommendResponse:
    """Recommend devices based on requirements."""
    recommendations = await _recommender.recommend_devices(
        device_type=body.device_type,
        requirements=body.requirements,
        user_devices=body.user_devices,
    )
    return RecommendResponse(
        recommendations=recommendations,
        total=len(recommendations),
    )


@app.post("/api/v1/compare", response_model=CompareResponse)
async def compare(body: CompareRequest) -> CompareResponse:
    """Compare multiple devices side-by-side."""
    if len(body.device_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 devices to compare")

    try:
        result = _comparison_engine.compare_devices(
            device_ids=body.device_ids,
            devices=body.devices,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CompareResponse(**result)


@app.get("/api/v1/devices")
async def get_devices() -> list[dict]:
    """Get user's devices from Home Assistant."""
    return await _ha_client.get_user_devices()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("DEVICE_RECOMMENDER_PORT", "8023"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
