"""
Device Setup Assistant Service
Phase 2.3: Provide setup guides and detect setup issues for new devices
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from shared.logging_config import setup_logging
from src.ha_client import HAClient
from src.issue_detector import SetupIssueDetector
from src.setup_guide_generator import SetupGuideGenerator

logger = setup_logging("device-setup-assistant")


# --- Pydantic Request/Response Models ---

class SetupStep(BaseModel):
    step: int
    title: str
    description: str
    type: str


class SetupGuideRequest(BaseModel):
    device_id: str
    device_name: str
    device_type: str | None = None
    integration: str | None = None
    setup_instructions_url: str | None = None

    @field_validator("setup_instructions_url")
    @classmethod
    def validate_url_scheme(cls, v: str | None) -> str | None:
        if v is not None:
            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("setup_instructions_url must use http or https scheme")
        return v


class SetupGuideResponse(BaseModel):
    device_id: str
    device_name: str
    device_type: str | None
    integration: str | None
    steps: list[SetupStep]
    estimated_time_minutes: int


class IssueDetectionRequest(BaseModel):
    device_id: str
    device_name: str
    entity_ids: list[str]
    expected_entities: list[str] | None = None


class IssueDetectionResponse(BaseModel):
    device_id: str
    issues: list[dict[str, Any]]
    total_issues: int


# --- Application Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Device Setup Assistant Service starting up...")

    # Create HAClient - fail fast if HA_URL not set
    ha_configured = True
    try:
        ha_client = HAClient()
        app.state.ha_client = ha_client
    except ValueError as e:
        logger.warning(f"Home Assistant not configured: {e}")
        ha_configured = False
        app.state.ha_client = None

    app.state.ha_configured = ha_configured

    # Create SetupIssueDetector using shared HAClient (no duplicate session)
    if ha_configured:
        app.state.issue_detector = SetupIssueDetector(ha_client)
    else:
        app.state.issue_detector = None

    # Create SetupGuideGenerator
    app.state.setup_guide_generator = SetupGuideGenerator()

    yield

    # Shutdown: close HAClient session only
    logger.info("Device Setup Assistant Service shutting down...")
    if app.state.ha_client is not None:
        await app.state.ha_client.close()


app = FastAPI(
    title="Device Setup Assistant Service",
    version="1.0.0",
    description="Device setup guides and issue detection",
    lifespan=lifespan
)


# --- Endpoints ---

@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint - returns 503 if HA not configured"""
    if not app.state.ha_configured:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "service": "device-setup-assistant",
                "reason": "Home Assistant not configured",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "device-setup-assistant",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": "device-setup-assistant",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/api/v1/setup-guide", response_model=SetupGuideResponse)
async def generate_setup_guide(request: SetupGuideRequest):
    """Generate a setup guide for a device"""
    generator: SetupGuideGenerator = app.state.setup_guide_generator
    result = generator.generate_setup_guide(
        device_id=request.device_id,
        device_name=request.device_name,
        device_type=request.device_type,
        integration=request.integration,
        setup_instructions_url=request.setup_instructions_url
    )
    return result


@app.post("/api/v1/detect-issues", response_model=IssueDetectionResponse)
async def detect_issues(request: IssueDetectionRequest):
    """Detect setup issues for a device"""
    if not app.state.ha_configured or app.state.issue_detector is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Home Assistant not configured"}
        )

    detector: SetupIssueDetector = app.state.issue_detector
    issues = await detector.detect_setup_issues(
        device_id=request.device_id,
        device_name=request.device_name,
        entity_ids=request.entity_ids,
        expected_entities=request.expected_entities
    )
    return IssueDetectionResponse(
        device_id=request.device_id,
        issues=issues,
        total_issues=len(issues)
    )


@app.get("/api/v1/device-registry")
async def get_device_registry():
    """Get device registry from Home Assistant"""
    if not app.state.ha_configured or app.state.ha_client is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Home Assistant not configured"}
        )

    ha_client: HAClient = app.state.ha_client
    registry = await ha_client.get_device_registry()
    return {"devices": registry, "total": len(registry)}


@app.get("/api/v1/entity-registry")
async def get_entity_registry():
    """Get entity registry from Home Assistant"""
    if not app.state.ha_configured or app.state.ha_client is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Home Assistant not configured"}
        )

    ha_client: HAClient = app.state.ha_client
    registry = await ha_client.get_entity_registry()
    return {"entities": registry, "total": len(registry)}


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_SETUP_ASSISTANT_PORT", "8021"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
