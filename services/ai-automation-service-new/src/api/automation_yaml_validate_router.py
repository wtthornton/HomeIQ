"""
Unified Automation YAML Validation API

Epic: HomeIQ Automation Improvements, Story 4
Single endpoint that orchestrates yaml-validation-service and returns
unified result with entity_validation and service_validation.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import get_yaml_validation_client
from ..api.error_handlers import handle_route_errors
from ..clients.yaml_validation_client import YAMLValidationClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/automations", tags=["automation", "validation"])


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


def _categorize_errors(errors: list[str]) -> tuple[list[str], list[str]]:
    """Split errors into entity-related and service-related."""
    entity_errors: list[str] = []
    service_errors: list[str] = []
    entity_keywords = ("entity", "Entity", "invalid entity", "entity_id")
    service_keywords = ("service", "Service", "invalid service")
    for e in errors:
        if any(kw in e for kw in entity_keywords):
            entity_errors.append(e)
        elif any(kw in e for kw in service_keywords):
            service_errors.append(e)
    return entity_errors, service_errors


@router.post("/validate", response_model=ValidateYAMLResponse)
@handle_route_errors("validate automation YAML")
async def validate_automation_yaml(
    request: ValidateYAMLRequest,
    yaml_client: YAMLValidationClient = Depends(get_yaml_validation_client)
) -> ValidateYAMLResponse:
    """
    Unified validation endpoint for automation YAML.

    Orchestrates yaml-validation-service (schema, entities, services)
    and returns structured result with entity_validation and service_validation.
    """
    try:
        result = await yaml_client.validate_yaml(
            yaml_content=request.yaml_content,
            normalize=request.normalize,
            validate_entities=request.validate_entities,
            validate_services=request.validate_services
        )
    except Exception as e:
        logger.error(f"YAML validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Validation service error: {str(e)}"
        ) from e

    errors = result.get("errors", [])
    entity_errors, service_errors = _categorize_errors(errors)
    valid = result.get("valid", False)

    if not valid and errors:
        logger.warning("Validation returned invalid: %s", errors[:3])

    return ValidateYAMLResponse(
        valid=valid,
        errors=errors,
        warnings=result.get("warnings", []),
        entity_validation=EntityValidationResult(
            performed=request.validate_entities,
            passed=len(entity_errors) == 0,
            errors=entity_errors
        ),
        service_validation=ServiceValidationResult(
            performed=request.validate_services,
            passed=len(service_errors) == 0,
            errors=service_errors
        ),
        score=result.get("score", 0.0),
        fixed_yaml=result.get("fixed_yaml"),
        fixes_applied=result.get("fixes_applied", [])
    )
