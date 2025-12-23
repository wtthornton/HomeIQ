"""Validation API router"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..clients.data_api_client import DataAPIClient
from ..config import settings
from ..yaml_validation_service import ValidationPipeline, ValidationResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


class ValidationRequest(BaseModel):
    """Validation request model."""
    yaml_content: str = Field(..., description="YAML content to validate")
    normalize: bool = Field(True, description="Whether to normalize YAML")
    validate_entities: bool = Field(True, description="Whether to validate entities")
    validate_services: bool = Field(False, description="Whether to validate services")


class ValidationResponse(BaseModel):
    """Validation response model."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    score: float
    fixed_yaml: str | None = None
    fixes_applied: list[str] = []
    summary: str | None = None


@router.post("/validate", response_model=ValidationResponse)
async def validate_yaml(request: ValidationRequest) -> ValidationResponse:
    """
    Validate Home Assistant automation YAML.
    
    Performs multi-stage validation:
    1. Syntax validation
    2. Schema validation
    3. Referential integrity (entities, areas)
    4. Service schema validation
    5. Safety checks
    6. Style/maintainability checks
    """
    try:
        # Initialize clients
        data_api_client = None
        if request.validate_entities and settings.enable_entity_validation:
            data_api_client = DataAPIClient(base_url=settings.data_api_url)
        
        ha_client = None  # TODO: Initialize HA client if validate_services
        
        # Create validation pipeline
        pipeline = ValidationPipeline(
            data_api_client=data_api_client,
            ha_client=ha_client,
            validation_level=settings.validation_level
        )
        
        # Validate
        result: ValidationResult = await pipeline.validate(
            request.yaml_content,
            normalize=request.normalize and settings.enable_normalization
        )
        
        return ValidationResponse(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings,
            score=result.score,
            fixed_yaml=result.fixed_yaml,
            fixes_applied=result.fixes_applied,
            summary=result.summary
        )
    
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.post("/normalize")
async def normalize_yaml(yaml_content: str) -> dict[str, Any]:
    """
    Normalize YAML to canonical format.
    
    Fixes:
    - triggers: → trigger:
    - actions: → action:
    - action: → service: in action items
    - trigger: → platform: in trigger items
    - continue_on_error → error
    """
    try:
        from ..yaml_validation_service import YAMLNormalizer
        
        normalizer = YAMLNormalizer()
        normalized_yaml, fixes = normalizer.normalize(yaml_content)
        
        return {
            "normalized_yaml": normalized_yaml,
            "fixes_applied": fixes
        }
    
    except Exception as e:
        logger.error(f"Normalization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Normalization error: {str(e)}")

