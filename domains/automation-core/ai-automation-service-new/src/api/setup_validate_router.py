"""
Device Setup Validation API

Epic: High-Value Domain Extensions, Story 8
Unified validation endpoint for device setup steps using the UnifiedValidationRouter pattern.
Validates configuration format, connectivity, and integration health.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from homeiq_patterns import (
    UnifiedValidationRouter,
    ValidationRequest,
    ValidationResponse,
)
from pydantic import BaseModel, Field

from ..api.dependencies import get_ha_client
from ..api.error_handlers import handle_route_errors
from ..clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/setup", tags=["setup", "validation"])


# --- Request / Response models ---


class SetupValidationRequest(BaseModel):
    """Request to validate a device setup step."""

    yaml_content: str = Field("", description="Configuration content (YAML/JSON)")
    integration_type: str = Field(
        "", description="Integration type (zigbee, mqtt, hue, zwave, matter)"
    )
    step: str = Field(
        "config", description="Wizard step to validate (config, connectivity, health)"
    )
    normalize: bool = Field(True, description="Normalize content")
    validate_entities: bool = Field(True, description="Validate entity references")
    validate_services: bool = Field(False, description="Validate service calls")
    validate_connectivity: bool = Field(True, description="Validate connectivity")
    validate_health: bool = Field(True, description="Validate integration health")


class ConnectivityValidationResult(BaseModel):
    """Connectivity validation subsection."""

    performed: bool = True
    passed: bool = True
    errors: list[str] = Field(default_factory=list)


class HealthValidationResult(BaseModel):
    """Integration health validation subsection."""

    performed: bool = True
    passed: bool = True
    errors: list[str] = Field(default_factory=list)


class SetupValidationResponse(BaseModel):
    """Unified setup validation response."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    entity_validation: dict = Field(default_factory=dict)
    connectivity_validation: ConnectivityValidationResult = Field(
        default_factory=ConnectivityValidationResult
    )
    health_validation: HealthValidationResult = Field(default_factory=HealthValidationResult)
    score: float = 0.0
    step: str = "config"


# --- Concrete validation router ---

SUPPORTED_INTEGRATIONS = {
    "zigbee",
    "zigbee2mqtt",
    "z2m",
    "zwave",
    "z-wave",
    "mqtt",
    "mosquitto",
    "hue",
    "philips_hue",
    "matter",
    "thread",
}

INTEGRATION_REQUIRED_FIELDS: dict[str, list[str]] = {
    "mqtt": ["host", "port"],
    "mosquitto": ["host", "port"],
    "zigbee2mqtt": ["mqtt_host"],
    "z2m": ["mqtt_host"],
    "hue": ["host"],
    "philips_hue": ["host"],
    "zwave": ["usb_path"],
    "z-wave": ["usb_path"],
}


class SetupValidationRouter(UnifiedValidationRouter):
    """
    Device setup validation using the UnifiedValidationRouter pattern.

    Validates configuration format, connectivity, and integration health
    for each wizard step.
    """

    domain = "setup"

    error_categories = {
        "entity": ("entity", "Entity", "entity_id"),
        "connectivity": ("connect", "Connect", "unreachable", "timeout", "refused"),
        "health": ("health", "Health", "unhealthy", "integration"),
    }

    def __init__(self, ha_client: HomeAssistantClient) -> None:
        self.ha_client = ha_client

    async def run_validation(
        self,
        request: ValidationRequest,
        **kwargs: Any,
    ) -> ValidationResponse:
        """Validate a device setup step."""
        import yaml as yaml_lib

        integration_type = kwargs.get("integration_type", "")
        step = kwargs.get("step", "config")
        validate_connectivity = kwargs.get("validate_connectivity", True)
        validate_health = kwargs.get("validate_health", True)

        errors: list[str] = []
        warnings: list[str] = []

        # 1. Config format validation
        if step in ("config", "all") and request.content.strip():
            try:
                config_data = yaml_lib.safe_load(request.content)
                if not isinstance(config_data, dict):
                    errors.append("Configuration must be a YAML mapping")
                else:
                    # Check required fields for the integration type
                    required = INTEGRATION_REQUIRED_FIELDS.get(integration_type, [])
                    for field in required:
                        if field not in config_data:
                            errors.append(
                                f"Missing required field '{field}' for {integration_type}"
                            )
            except yaml_lib.YAMLError as e:
                errors.append(f"Invalid YAML configuration: {e}")

        # 2. Integration type validation
        if integration_type and integration_type not in SUPPORTED_INTEGRATIONS:
            warnings.append(
                f"Unknown integration type '{integration_type}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_INTEGRATIONS))}"
            )

        # 3. Connectivity validation
        if step in ("connectivity", "all") and validate_connectivity:
            connectivity_errors = await self._validate_connectivity(integration_type)
            errors.extend(connectivity_errors)

        # 4. Health validation
        if step in ("health", "all") and validate_health:
            health_errors = await self._validate_health()
            errors.extend(health_errors)

        score = 100.0 - (len(errors) * 20) - (len(warnings) * 5)
        score = max(0.0, min(100.0, score))

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": score,
        }
        return self.build_response(result, request)

    async def _validate_connectivity(self, _integration_type: str) -> list[str]:
        """Validate connectivity for the integration type."""
        errors: list[str] = []
        # Check HA is reachable (proxy for integration connectivity)
        try:
            healthy = await self.ha_client.health_check()
            if not healthy:
                errors.append(
                    "Home Assistant is unreachable. Cannot validate integration connectivity."
                )
        except Exception as e:
            errors.append(f"Connectivity check failed: {e}")
        return errors

    async def _validate_health(self) -> list[str]:
        """Validate integration health via HA API."""
        errors: list[str] = []
        try:
            healthy = await self.ha_client.health_check()
            if not healthy:
                errors.append(
                    "Home Assistant health check failed. Integration health cannot be verified."
                )
        except Exception as e:
            errors.append(f"Health validation failed: {e}")
        return errors


# --- FastAPI route ---


@router.post("/validate", response_model=SetupValidationResponse)
@handle_route_errors("validate device setup")
async def validate_setup(
    request: SetupValidationRequest,
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> SetupValidationResponse:
    """
    Unified validation endpoint for device setup steps.

    Validates configuration format, connectivity, and integration health.
    Supports step-by-step validation for setup wizards.
    """
    try:
        validation_router = SetupValidationRouter(ha_client)
        unified_request = ValidationRequest(
            content=request.yaml_content,
            normalize=request.normalize,
            validate_entities=request.validate_entities,
            validate_services=request.validate_services,
        )
        response = await validation_router.run_validation(
            unified_request,
            integration_type=request.integration_type,
            step=request.step,
            validate_connectivity=request.validate_connectivity,
            validate_health=request.validate_health,
        )
    except Exception as e:
        logger.error(f"Setup validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Validation service error: {str(e)}",
        ) from e

    connectivity_sub = response.subsections.get("connectivity_validation")
    health_sub = response.subsections.get("health_validation")

    return SetupValidationResponse(
        valid=response.valid,
        errors=response.errors,
        warnings=response.warnings,
        entity_validation={
            "performed": request.validate_entities,
            "passed": not any("entity" in e.lower() for e in response.errors),
            "errors": [e for e in response.errors if "entity" in e.lower()],
        },
        connectivity_validation=ConnectivityValidationResult(
            performed=connectivity_sub.performed
            if connectivity_sub
            else request.validate_connectivity,
            passed=connectivity_sub.passed if connectivity_sub else True,
            errors=connectivity_sub.errors if connectivity_sub else [],
        ),
        health_validation=HealthValidationResult(
            performed=health_sub.performed if health_sub else request.validate_health,
            passed=health_sub.passed if health_sub else True,
            errors=health_sub.errors if health_sub else [],
        ),
        score=response.score,
        step=request.step,
    )
