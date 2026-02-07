"""
Device Context Classifier Service
Phase 2.1: Classify devices based on entity patterns

Analyzes entities to infer device types (fridge, car, 3D printer, etc.)
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from shared.logging_config import setup_logging

from src.classifier import DeviceContextClassifier
from src.patterns import DEVICE_PATTERNS, get_device_category, DOMAIN_TO_DEVICE_TYPE

logger = setup_logging("device-context-classifier")


# --- Pydantic request/response models ---

class ClassifyRequest(BaseModel):
    """Request model for device classification."""
    device_id: str = Field(..., min_length=1, description="Device identifier")
    entity_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of entity IDs for this device (max 50)"
    )


class ClassifyResponse(BaseModel):
    """Response model for device classification."""
    device_id: str
    device_type: str | None
    device_category: str | None
    confidence: float
    matched_entities: int


# --- Application lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle."""
    logger.info("Device Context Classifier Service starting up...")

    # Validate HA configuration - fail fast if missing
    ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
    if not ha_url:
        logger.warning("HA_URL not configured - classification will return empty results")

    # Create classifier and store on app state
    classifier = DeviceContextClassifier()
    app.state.classifier = classifier
    logger.info("DeviceContextClassifier initialized")

    yield

    # Shutdown: close classifier session
    logger.info("Device Context Classifier Service shutting down...")
    await classifier.close()
    logger.info("Classifier session closed")


app = FastAPI(
    title="Device Context Classifier Service",
    version="1.0.0",
    description="Device type classification based on entity patterns",
    lifespan=lifespan
)


# --- Endpoints ---

@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint. Returns 503 if HA is not configured."""
    ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
    ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")

    if not ha_url or not ha_token:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "service": "device-context-classifier",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "HA_URL or HA_TOKEN not configured"
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "device-context-classifier",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": "device-context-classifier",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/api/v1/classify", response_model=ClassifyResponse)
async def classify_device(request: ClassifyRequest) -> ClassifyResponse:
    """Classify a device based on its entity IDs."""
    classifier: DeviceContextClassifier = app.state.classifier
    result = await classifier.classify_device(request.device_id, request.entity_ids)
    return ClassifyResponse(**result)


@app.get("/api/v1/patterns")
async def get_patterns() -> dict:
    """Return all device patterns."""
    return DEVICE_PATTERNS


@app.get("/api/v1/categories")
async def get_categories() -> dict:
    """Return device-type to category mapping."""
    # Build the full category map by calling get_device_category for each known device type
    all_device_types = set(DOMAIN_TO_DEVICE_TYPE.values())
    # Also include pattern-based device types
    all_device_types.update(DEVICE_PATTERNS.keys())

    category_map = {}
    for dt in sorted(all_device_types):
        cat = get_device_category(dt)
        if cat:
            category_map[dt] = cat

    return category_map


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_CONTEXT_CLASSIFIER_PORT", "8020"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
