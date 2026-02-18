"""
Unified Automation YAML Validation API

Epic: HomeIQ Automation Improvements, Story 4
Epic: Reusable Pattern Framework, Story 3 (refactored to use UnifiedValidationRouter)

Single endpoint that orchestrates yaml-validation-service and returns
unified result with entity_validation and service_validation.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import get_yaml_validation_client
from ..api.error_handlers import handle_route_errors
from ..clients.yaml_validation_client import YAMLValidationClient

# Ensure shared modules are importable
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
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/automations", tags=["automation", "validation"])


# --- Backward-compatible response models ---
# These preserve the existing API contract while the internal logic
# now uses the shared UnifiedValidationRouter pattern.


class ValidateYAMLRequest(BaseModel):
    """Request to validate automation YAML."""

    yaml_content: str = Field(..., description="Home Assistant automation YAML")
    normalize: bool = Field(True, description="Normalize YAML to canonical format")
    validate_entities: bool = Field(True, description="Validate entity IDs exist")
    validate_services: bool = Field(True, description="Validate service calls")


class EntityValidationResult(BaseModel):
    """Entity validation subsection."""

    performed: bool = True
    passed: bool = True
    errors: list[str] = Field(default_factory=list)


class ServiceValidationResult(BaseModel):
    """Service validation subsection."""

    performed: bool = True
    passed: bool = True
    errors: list[str] = Field(default_factory=list)


class ValidateYAMLResponse(BaseModel):
    """Unified validation response."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    entity_validation: EntityValidationResult = Field(default_factory=EntityValidationResult)
    service_validation: ServiceValidationResult = Field(default_factory=ServiceValidationResult)
    score: float = 0.0
    fixed_yaml: str | None = None
    fixes_applied: list[str] = Field(default_factory=list)


# --- Concrete validation router using shared pattern ---


class AutomationYAMLValidationRouter(UnifiedValidationRouter):
    """
    Automation YAML validation using the UnifiedValidationRouter pattern.

    Orchestrates yaml-validation-service and categorizes errors
    into entity and service validation subsections.
    """

    domain = "automation"

    error_categories = {
        "entity": ("entity", "Entity", "invalid entity", "entity_id"),
        "service": ("service", "Service", "invalid service"),
    }

    def __init__(self, yaml_client: YAMLValidationClient) -> None:
        self.yaml_client = yaml_client

    async def run_validation(
        self,
        request: ValidationRequest,
        **kwargs: Any,
    ) -> ValidationResponse:
        """Orchestrate yaml-validation-service and return unified response."""
        result = await self.yaml_client.validate_yaml(
            yaml_content=request.content,
            normalize=request.normalize,
            validate_entities=request.validate_entities,
            validate_services=request.validate_services,
        )
        return self.build_response(result, request)


# Singleton-ish: created per-request via dependency injection
def _build_router(yaml_client: YAMLValidationClient) -> AutomationYAMLValidationRouter:
    return AutomationYAMLValidationRouter(yaml_client)


@router.post("/validate", response_model=ValidateYAMLResponse)
@handle_route_errors("validate automation YAML")
async def validate_automation_yaml(
    request: ValidateYAMLRequest,
    yaml_client: YAMLValidationClient = Depends(get_yaml_validation_client),
) -> ValidateYAMLResponse:
    """
    Unified validation endpoint for automation YAML.

    Orchestrates yaml-validation-service (schema, entities, services)
    and returns structured result with entity_validation and service_validation.
    """
    try:
        # Use the shared UnifiedValidationRouter pattern
        validation_router = _build_router(yaml_client)
        unified_request = ValidationRequest(
            content=request.yaml_content,
            normalize=request.normalize,
            validate_entities=request.validate_entities,
            validate_services=request.validate_services,
        )
        response = await validation_router.run_validation(unified_request)
    except Exception as e:
        logger.error(f"YAML validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Validation service error: {str(e)}") from e

    if not response.valid and response.errors:
        logger.warning("Validation returned invalid: %s", response.errors[:3])

    # Map shared ValidationResponse → backward-compatible ValidateYAMLResponse
    entity_sub = response.subsections.get("entity_validation")
    service_sub = response.subsections.get("service_validation")

    return ValidateYAMLResponse(
        valid=response.valid,
        errors=response.errors,
        warnings=response.warnings,
        entity_validation=EntityValidationResult(
            performed=entity_sub.performed if entity_sub else request.validate_entities,
            passed=entity_sub.passed if entity_sub else True,
            errors=entity_sub.errors if entity_sub else [],
        ),
        service_validation=ServiceValidationResult(
            performed=service_sub.performed if service_sub else request.validate_services,
            passed=service_sub.passed if service_sub else True,
            errors=service_sub.errors if service_sub else [],
        ),
        score=response.score,
        fixed_yaml=response.fixed_content,
        fixes_applied=response.fixes_applied,
    )
