"""
Device Context Classifier Service
Phase 2.1: Classify devices based on entity patterns

Analyzes entities to infer device types (fridge, car, 3D printer, etc.)
"""

import os

import uvicorn
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from src.classifier import DeviceContextClassifier
from src.patterns import DEVICE_PATTERNS, DOMAIN_TO_DEVICE_TYPE, get_device_category

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


# --- Shared state ---

_classifier: DeviceContextClassifier | None = None


# --- Lifespan ---

async def _startup() -> None:
    global _classifier
    ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
    if not ha_url:
        logger.warning("HA_URL not configured - classification will return empty results")
    _classifier = DeviceContextClassifier()
    logger.info("DeviceContextClassifier initialized")


async def _shutdown() -> None:
    if _classifier:
        await _classifier.close()
    logger.info("Classifier session closed")


lifespan = ServiceLifespan("Device Context Classifier Service")
lifespan.on_startup(_startup, name="classifier")
lifespan.on_shutdown(_shutdown, name="classifier")


# --- Health check ---

async def _check_ha_config() -> bool:
    ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
    ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
    return bool(ha_url and ha_token)


health = StandardHealthCheck(service_name="device-context-classifier", version="1.0.0")
health.register_check("ha-config", _check_ha_config)


# --- App ---

app = create_app(
    title="Device Context Classifier Service",
    version="1.0.0",
    description="Device type classification based on entity patterns",
    lifespan=lifespan.handler,
    health_check=health,
)


# --- Endpoints ---

@app.post("/api/v1/classify", response_model=ClassifyResponse)
async def classify_device(request: ClassifyRequest) -> ClassifyResponse:
    """Classify a device based on its entity IDs."""
    result = await _classifier.classify_device(request.device_id, request.entity_ids)
    return ClassifyResponse(**result)


@app.get("/api/v1/patterns")
async def get_patterns() -> dict:
    """Return all device patterns."""
    return DEVICE_PATTERNS


@app.get("/api/v1/categories")
async def get_categories() -> dict:
    """Return device-type to category mapping."""
    all_device_types = set(DOMAIN_TO_DEVICE_TYPE.values())
    all_device_types.update(DEVICE_PATTERNS.keys())

    category_map = {}
    for dt in sorted(all_device_types):
        cat = get_device_category(dt)
        if cat:
            category_map[dt] = cat

    return category_map


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_CONTEXT_CLASSIFIER_PORT", "8020"))
    host = os.getenv("HOST", "0.0.0.0")  # noqa: S104 - Docker container binding
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
