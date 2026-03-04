"""
Device Setup Assistant Service.

Phase 2.3: Provide setup guides and detect setup issues for new devices.
"""

from __future__ import annotations

import logging
import sys
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from pydantic import BaseModel, field_validator

from .config import settings
from .ha_client import HAClient
from .issue_detector import SetupIssueDetector
from .setup_guide_generator import SetupGuideGenerator


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()
logger = logging.getLogger(__name__)

# Module-level references for shutdown access
_ha_client: HAClient | None = None


# --- Pydantic Request/Response Models ---


class SetupStep(BaseModel):
    """A single step in a device setup guide."""

    step: int
    title: str
    description: str
    type: str


class SetupGuideRequest(BaseModel):
    """Request body for generating a device setup guide."""

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
                msg = "setup_instructions_url must use http or https scheme"
                raise ValueError(msg)
        return v


class SetupGuideResponse(BaseModel):
    """Response containing a generated device setup guide."""

    device_id: str
    device_name: str
    device_type: str | None
    integration: str | None
    steps: list[SetupStep]
    estimated_time_minutes: int


class IssueDetectionRequest(BaseModel):
    """Request body for detecting device setup issues."""

    device_id: str
    device_name: str
    entity_ids: list[str]
    expected_entities: list[str] | None = None


class IssueDetectionResponse(BaseModel):
    """Response containing detected device setup issues."""

    device_id: str
    issues: list[dict[str, Any]]
    total_issues: int


# ---------------------------------------------------------------------------
# Lifespan hooks
# ---------------------------------------------------------------------------


async def _startup_services() -> None:
    """Initialize HA client and service components on startup."""
    global _ha_client  # noqa: PLW0603

    ha_configured = True
    try:
        _ha_client = HAClient()
        app.state.ha_client = _ha_client
    except ValueError as e:
        logger.warning("Home Assistant not configured: %s", e)
        ha_configured = False
        app.state.ha_client = None

    app.state.ha_configured = ha_configured

    if ha_configured and _ha_client is not None:
        app.state.issue_detector = SetupIssueDetector(_ha_client)
    else:
        app.state.issue_detector = None

    app.state.setup_guide_generator = SetupGuideGenerator()


async def _shutdown_services() -> None:
    """Close HA client session on shutdown."""
    if _ha_client is not None:
        await _ha_client.close()


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_services, name="services")
lifespan.on_shutdown(_shutdown_services, name="services")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def _check_ha() -> bool:
    """Return True if HA client is configured and available."""
    return bool(getattr(app.state, "ha_configured", False))


health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)
health.register_check("home_assistant", _check_ha)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Device Setup Assistant Service",
    version="1.0.0",
    description="Device setup guides and issue detection",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/v1/setup-guide", response_model=SetupGuideResponse)
async def generate_setup_guide(request: SetupGuideRequest) -> SetupGuideResponse:
    """Generate a setup guide for a device."""
    generator: SetupGuideGenerator = app.state.setup_guide_generator
    return generator.generate_setup_guide(
        device_id=request.device_id,
        device_name=request.device_name,
        device_type=request.device_type,
        integration=request.integration,
        setup_instructions_url=request.setup_instructions_url,
    )


@app.post("/api/v1/detect-issues", response_model=IssueDetectionResponse)
async def detect_issues(request: IssueDetectionRequest) -> IssueDetectionResponse:
    """Detect setup issues for a device."""
    if not app.state.ha_configured or app.state.issue_detector is None:
        raise HTTPException(status_code=503, detail="Home Assistant not configured")

    detector: SetupIssueDetector = app.state.issue_detector
    issues = await detector.detect_setup_issues(
        device_id=request.device_id,
        device_name=request.device_name,
        entity_ids=request.entity_ids,
        expected_entities=request.expected_entities,
    )
    return IssueDetectionResponse(
        device_id=request.device_id,
        issues=issues,
        total_issues=len(issues),
    )


@app.get("/api/v1/device-registry")
async def get_device_registry() -> dict[str, Any]:
    """Get device registry from Home Assistant."""
    if not app.state.ha_configured or app.state.ha_client is None:
        raise HTTPException(status_code=503, detail="Home Assistant not configured")

    ha_client: HAClient = app.state.ha_client
    registry = await ha_client.get_device_registry()
    return {"devices": registry, "total": len(registry)}


@app.get("/api/v1/entity-registry")
async def get_entity_registry() -> dict[str, Any]:
    """Get entity registry from Home Assistant."""
    if not app.state.ha_configured or app.state.ha_client is None:
        raise HTTPException(status_code=503, detail="Home Assistant not configured")

    ha_client: HAClient = app.state.ha_client
    registry = await ha_client.get_entity_registry()
    return {"entities": registry, "total": len(registry)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
