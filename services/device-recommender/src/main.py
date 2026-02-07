"""
Device Recommender Service
Phase 3.3: Device recommendations and comparisons

Recommends devices based on user requirements, compares devices,
and provides device ratings from Device Database.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from shared.logging_config import setup_logging
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
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Device Recommender Service starting up...")

    # Create shared clients and engines
    ha_client = HAClient()
    recommender = DeviceRecommender()
    comparison_engine = DeviceComparisonEngine()

    app.state.ha_client = ha_client
    app.state.recommender = recommender
    app.state.comparison_engine = comparison_engine

    yield

    logger.info("Device Recommender Service shutting down...")
    await ha_client.close()


app = FastAPI(
    title="Device Recommender Service",
    version="1.0.0",
    description="Device recommendations and comparisons",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check(request: Request) -> dict:
    """Health check endpoint"""
    ha_client: HAClient = request.app.state.ha_client
    if not ha_client.ha_url:
        raise HTTPException(
            status_code=503,
            detail="Home Assistant URL not configured",
        )
    return {
        "status": "healthy",
        "service": "device-recommender",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": "device-recommender",
        "version": "1.0.0",
        "status": "running",
    }


@app.post("/api/v1/recommend", response_model=RecommendResponse)
async def recommend(request: Request, body: RecommendRequest) -> RecommendResponse:
    """Recommend devices based on requirements."""
    recommender: DeviceRecommender = request.app.state.recommender
    recommendations = await recommender.recommend_devices(
        device_type=body.device_type,
        requirements=body.requirements,
        user_devices=body.user_devices,
    )
    return RecommendResponse(
        recommendations=recommendations,
        total=len(recommendations),
    )


@app.post("/api/v1/compare", response_model=CompareResponse)
async def compare(request: Request, body: CompareRequest) -> CompareResponse:
    """Compare multiple devices side-by-side."""
    comparison_engine: DeviceComparisonEngine = request.app.state.comparison_engine

    if len(body.device_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 devices to compare")

    try:
        result = comparison_engine.compare_devices(
            device_ids=body.device_ids,
            devices=body.devices,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CompareResponse(**result)


@app.get("/api/v1/devices")
async def get_devices(request: Request) -> list[dict]:
    """Get user's devices from Home Assistant."""
    ha_client: HAClient = request.app.state.ha_client
    return await ha_client.get_user_devices()


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
