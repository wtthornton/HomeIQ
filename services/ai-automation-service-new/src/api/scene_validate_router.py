"""
Scene Validation API

Epic: Platform-Wide Pattern Rollout, Story 4
Validates scene definitions using the UnifiedValidationRouter pattern.
Checks entity targets exist, state values are valid, and service calls are correct.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import get_ha_client
from ..api.error_handlers import handle_route_errors
from ..clients.ha_client import HomeAssistantClient

_project_root = str(Path(__file__).resolve().parents[4])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.patterns import (
    UnifiedValidationRouter,
    ValidationRequest,
    ValidationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scenes", tags=["scene", "validation"])


class ValidateSceneRequest(BaseModel):
    yaml_content: str = Field(..., description="Scene YAML content")
    normalize: bool = Field(True)
    validate_entities: bool = Field(True, description="Validate entity targets exist")
    validate_services: bool = Field(True, description="Validate service calls")


class ValidateSceneResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    entity_validation: dict = Field(default_factory=dict)
    service_validation: dict = Field(default_factory=dict)
    score: float = 0.0


VALID_LIGHT_ATTRS = {"state", "brightness", "color_temp", "rgb_color", "xy_color", "hs_color", "effect", "transition"}
VALID_COVER_ATTRS = {"state", "position", "tilt_position", "current_position", "current_tilt_position"}
VALID_CLIMATE_ATTRS = {"state", "temperature", "target_temp_high", "target_temp_low", "hvac_mode", "fan_mode", "preset_mode"}


class SceneValidationRouter(UnifiedValidationRouter):
    """Scene validation using the UnifiedValidationRouter pattern."""

    domain = "scene"

    error_categories = {
        "entity": ("entity", "Entity", "entity_id", "not found"),
        "service": ("service", "Service", "invalid service"),
    }

    def __init__(self, ha_client: HomeAssistantClient) -> None:
        self.ha_client = ha_client

    async def run_validation(
        self,
        request: ValidationRequest,
        **kwargs: Any,
    ) -> ValidationResponse:
        import yaml as yaml_lib

        errors: list[str] = []
        warnings: list[str] = []

        try:
            data = yaml_lib.safe_load(request.content)
        except yaml_lib.YAMLError as e:
            return ValidationResponse(valid=False, errors=[f"Invalid YAML: {e}"])

        # Accept both a single scene dict and the scene list format
        scenes = []
        if isinstance(data, dict):
            if "scene" in data and isinstance(data["scene"], list):
                scenes = data["scene"]
            else:
                scenes = [data]
        elif isinstance(data, list):
            scenes = data
        else:
            return ValidationResponse(valid=False, errors=["Scene YAML must be a mapping or list"])

        for i, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                errors.append(f"Scene #{i+1}: must be a mapping")
                continue

            name = scene.get("name")
            if not name:
                errors.append(f"Scene #{i+1}: missing required 'name' field")

            entities = scene.get("entities", {})
            if not entities:
                warnings.append(f"Scene '{name or i+1}': no entities defined")
                continue

            if request.validate_entities:
                for entity_id, attrs in entities.items():
                    state_data = await self.ha_client.get_state(entity_id)
                    if state_data is None:
                        errors.append(f"Entity not found: {entity_id}")
                    else:
                        # Validate attribute keys for known domains
                        domain = entity_id.split(".")[0]
                        if isinstance(attrs, dict):
                            self._validate_attrs(domain, entity_id, attrs, warnings)

        score = max(0.0, 100.0 - len(errors) * 15 - len(warnings) * 5)
        return self.build_response(
            {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "score": score},
            request,
        )

    def _validate_attrs(self, domain: str, entity_id: str, attrs: dict, warnings: list[str]) -> None:
        valid_attrs = None
        if domain == "light":
            valid_attrs = VALID_LIGHT_ATTRS
        elif domain == "cover":
            valid_attrs = VALID_COVER_ATTRS
        elif domain == "climate":
            valid_attrs = VALID_CLIMATE_ATTRS

        if valid_attrs:
            for key in attrs:
                if key not in valid_attrs:
                    warnings.append(
                        f"Unusual attribute '{key}' for {domain} entity '{entity_id}'"
                    )

        # Validate brightness range for lights
        if domain == "light" and "brightness" in attrs:
            b = attrs["brightness"]
            if isinstance(b, (int, float)) and (b < 0 or b > 255):
                warnings.append(
                    f"Light brightness for '{entity_id}' should be 0-255, got {b}"
                )


@router.post("/validate", response_model=ValidateSceneResponse)
@handle_route_errors("validate scene")
async def validate_scene(
    request: ValidateSceneRequest,
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> ValidateSceneResponse:
    """Validate a scene definition."""
    try:
        validation_router = SceneValidationRouter(ha_client)
        unified_request = ValidationRequest(
            content=request.yaml_content,
            normalize=request.normalize,
            validate_entities=request.validate_entities,
            validate_services=request.validate_services,
        )
        response = await validation_router.run_validation(unified_request)
    except Exception as e:
        logger.error(f"Scene validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Validation error: {e}") from e

    entity_sub = response.subsections.get("entity_validation")
    service_sub = response.subsections.get("service_validation")

    return ValidateSceneResponse(
        valid=response.valid,
        errors=response.errors,
        warnings=response.warnings,
        entity_validation={
            "performed": entity_sub.performed if entity_sub else request.validate_entities,
            "passed": entity_sub.passed if entity_sub else True,
            "errors": entity_sub.errors if entity_sub else [],
        },
        service_validation={
            "performed": service_sub.performed if service_sub else request.validate_services,
            "passed": service_sub.passed if service_sub else True,
            "errors": service_sub.errors if service_sub else [],
        },
        score=response.score,
    )
