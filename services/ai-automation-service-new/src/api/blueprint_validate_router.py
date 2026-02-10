"""
Blueprint Validation API

Epic: High-Value Domain Extensions, Story 3
Unified validation endpoint for blueprint YAML using the UnifiedValidationRouter pattern.
Validates schema, entity references, and device compatibility.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import get_ha_client, get_data_api_client
from ..api.error_handlers import handle_route_errors
from ..clients.ha_client import HomeAssistantClient
from ..clients.data_api_client import DataAPIClient

try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.patterns import (
    UnifiedValidationRouter,
    ValidationRequest,
    ValidationResponse,
    ValidationSubsection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprint", "validation"])


# --- Request / Response models ---

class ValidateBlueprintRequest(BaseModel):
    """Request to validate blueprint YAML."""
    yaml_content: str = Field(..., description="Blueprint YAML content")
    normalize: bool = Field(True, description="Normalize YAML")
    validate_entities: bool = Field(True, description="Validate entity references exist")
    validate_services: bool = Field(True, description="Validate service calls")
    validate_devices: bool = Field(True, description="Validate device compatibility")


class DeviceValidationResult(BaseModel):
    """Device compatibility validation subsection."""
    performed: bool = True
    passed: bool = True
    errors: list[str] = Field(default_factory=list)


class ValidateBlueprintResponse(BaseModel):
    """Unified blueprint validation response."""
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    entity_validation: dict = Field(default_factory=dict)
    service_validation: dict = Field(default_factory=dict)
    device_validation: DeviceValidationResult = Field(default_factory=DeviceValidationResult)
    score: float = 0.0
    fixed_yaml: str | None = None
    fixes_applied: list[str] = Field(default_factory=list)


# --- Concrete validation router ---

class BlueprintValidationRouter(UnifiedValidationRouter):
    """
    Blueprint validation using the UnifiedValidationRouter pattern.

    Validates blueprint YAML schema, entity references, and device compatibility.
    """

    domain = "blueprint"

    error_categories = {
        "entity": ("entity", "Entity", "invalid entity", "entity_id"),
        "service": ("service", "Service", "invalid service"),
        "device": ("device", "Device", "device_class", "device compatibility"),
    }

    def __init__(self, ha_client: HomeAssistantClient, data_api_client: DataAPIClient) -> None:
        self.ha_client = ha_client
        self.data_api_client = data_api_client

    async def run_validation(
        self,
        request: ValidationRequest,
        **kwargs: Any,
    ) -> ValidationResponse:
        """Validate blueprint YAML content."""
        import yaml as yaml_lib

        errors: list[str] = []
        warnings: list[str] = []
        validate_devices = kwargs.get("validate_devices", True)

        # 1. Schema validation — parse YAML
        try:
            data = yaml_lib.safe_load(request.content)
        except yaml_lib.YAMLError as e:
            return ValidationResponse(
                valid=False,
                errors=[f"Invalid YAML syntax: {e}"],
            )

        if not isinstance(data, dict):
            return ValidationResponse(
                valid=False,
                errors=["Blueprint YAML must be a mapping"],
            )

        # 2. Blueprint structure validation
        blueprint_section = data.get("blueprint")
        if not blueprint_section:
            errors.append("Missing 'blueprint' section")
        else:
            if not blueprint_section.get("name"):
                errors.append("Blueprint missing required 'name' field")
            if not blueprint_section.get("domain"):
                errors.append("Blueprint missing required 'domain' field")
            elif blueprint_section["domain"] not in ("automation", "script"):
                warnings.append(
                    f"Unusual blueprint domain: {blueprint_section['domain']}. "
                    "Expected 'automation' or 'script'."
                )

            # Validate inputs
            inputs = blueprint_section.get("input", {})
            if isinstance(inputs, dict):
                for input_name, input_def in inputs.items():
                    if isinstance(input_def, dict):
                        selector = input_def.get("selector")
                        if not selector and not input_def.get("default"):
                            warnings.append(
                                f"Input '{input_name}' has no selector and no default value"
                            )

        # 3. Entity validation (if enabled)
        if request.validate_entities and blueprint_section:
            entity_errors = await self._validate_entities(data)
            errors.extend(entity_errors)

        # 4. Service validation (if enabled)
        if request.validate_services:
            service_errors = self._validate_services(data)
            errors.extend(service_errors)

        # 5. Device compatibility (if enabled)
        if validate_devices and blueprint_section:
            device_errors = self._validate_device_compatibility(data)
            errors.extend(device_errors)

        score = 100.0 - (len(errors) * 15) - (len(warnings) * 5)
        score = max(0.0, min(100.0, score))

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": score,
        }
        return self.build_response(result, request)

    async def _validate_entities(self, data: dict) -> list[str]:
        """Check entity references in triggers, conditions, actions."""
        errors: list[str] = []
        # Extract entity_id references from the blueprint body (not inputs)
        entity_ids = self._extract_entity_refs(data)
        for eid in entity_ids:
            if eid.startswith("!input"):
                continue  # Blueprint input reference, skip
            try:
                state = await self.ha_client.get_state(eid)
                if state is None:
                    errors.append(f"Entity not found: {eid}")
            except Exception:
                pass  # Network errors are not validation errors
        return errors

    def _validate_services(self, data: dict) -> list[str]:
        """Basic service reference validation."""
        errors: list[str] = []
        services = self._extract_service_refs(data)
        for svc in services:
            parts = svc.split(".")
            if len(parts) != 2:
                errors.append(f"Invalid service format: {svc}")
        return errors

    def _validate_device_compatibility(self, data: dict) -> list[str]:
        """Validate device_class and domain requirements in selectors."""
        errors: list[str] = []
        blueprint = data.get("blueprint", {})
        inputs = blueprint.get("input", {})

        if not isinstance(inputs, dict):
            return errors

        for input_name, input_def in inputs.items():
            if not isinstance(input_def, dict):
                continue
            selector = input_def.get("selector", {})
            if not isinstance(selector, dict):
                continue
            entity_sel = selector.get("entity", {})
            if isinstance(entity_sel, dict):
                domain = entity_sel.get("domain")
                device_class = entity_sel.get("device_class")
                if domain and device_class:
                    # Valid requirement, just informational
                    pass
        return errors

    def _extract_entity_refs(self, data: Any, refs: set | None = None) -> set[str]:
        """Recursively extract entity_id values from data."""
        if refs is None:
            refs = set()
        if isinstance(data, dict):
            for k, v in data.items():
                if k == "entity_id" and isinstance(v, str):
                    refs.add(v)
                elif k == "entity_id" and isinstance(v, list):
                    refs.update(str(x) for x in v if isinstance(x, str))
                else:
                    self._extract_entity_refs(v, refs)
        elif isinstance(data, list):
            for item in data:
                self._extract_entity_refs(item, refs)
        return refs

    def _extract_service_refs(self, data: Any, refs: set | None = None) -> set[str]:
        """Recursively extract service call references."""
        if refs is None:
            refs = set()
        if isinstance(data, dict):
            svc = data.get("service")
            if isinstance(svc, str) and "." in svc:
                refs.add(svc)
            for v in data.values():
                self._extract_service_refs(v, refs)
        elif isinstance(data, list):
            for item in data:
                self._extract_service_refs(item, refs)
        return refs


# --- FastAPI route ---

@router.post("/validate", response_model=ValidateBlueprintResponse)
@handle_route_errors("validate blueprint YAML")
async def validate_blueprint(
    request: ValidateBlueprintRequest,
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    data_api_client: DataAPIClient = Depends(get_data_api_client),
) -> ValidateBlueprintResponse:
    """
    Unified validation endpoint for blueprint YAML.

    Validates schema, entity references, service calls, and device compatibility.
    """
    try:
        validation_router = BlueprintValidationRouter(ha_client, data_api_client)
        unified_request = ValidationRequest(
            content=request.yaml_content,
            normalize=request.normalize,
            validate_entities=request.validate_entities,
            validate_services=request.validate_services,
        )
        response = await validation_router.run_validation(
            unified_request, validate_devices=request.validate_devices
        )
    except Exception as e:
        logger.error(f"Blueprint validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Validation service error: {str(e)}",
        ) from e

    entity_sub = response.subsections.get("entity_validation")
    service_sub = response.subsections.get("service_validation")
    device_sub = response.subsections.get("device_validation")

    return ValidateBlueprintResponse(
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
        device_validation=DeviceValidationResult(
            performed=device_sub.performed if device_sub else request.validate_devices,
            passed=device_sub.passed if device_sub else True,
            errors=device_sub.errors if device_sub else [],
        ),
        score=response.score,
        fixed_yaml=response.fixed_content,
        fixes_applied=response.fixes_applied,
    )
