"""
YAML Validation Router - Consolidated YAML Validation Endpoint

Provides a single, comprehensive endpoint for validating Home Assistant automation YAML.
Used by ha-ai-agent-service and self-correct functionality.

Validates:
- YAML syntax
- HA automation structure
- Entity existence (via HA API)
- Safety rules
"""

import logging
from typing import Any

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException

from pydantic import BaseModel, Field

from ..api.common.dependencies import get_ha_client_optional
from ..clients.ha_client import HomeAssistantClient
from ..config import settings
from ..safety_validator import SafetyValidator, get_safety_validator
from ..services.automation.yaml_validator import AutomationYAMLValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/yaml", tags=["yaml-validation"])


class YAMLValidationRequest(BaseModel):
    """Request to validate YAML"""
    yaml: str = Field(..., description="Home Assistant automation YAML to validate")
    validate_entities: bool = Field(
        default=True,
        description="Validate entities exist in Home Assistant (requires HA client)"
    )
    validate_safety: bool = Field(
        default=True,
        description="Run safety validation checks"
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Optional context (validated entities, etc.)"
    )


class ValidationError(BaseModel):
    """Individual validation error"""
    stage: str
    severity: str  # "error" or "warning"
    message: str
    fix: str | None = None


class EntityValidationResult(BaseModel):
    """Entity validation result"""
    entity_id: str
    exists: bool
    alternatives: list[str] | None = None


class YAMLValidationResponse(BaseModel):
    """Response from YAML validation"""
    valid: bool
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    stages: dict[str, bool] = {}
    entity_results: list[EntityValidationResult] = []
    safety_score: int | None = None
    fixed_yaml: str | None = None
    summary: str = ""


@router.post("/validate", response_model=YAMLValidationResponse)
async def validate_yaml(
    request: YAMLValidationRequest = Body(...),
    ha_client: HomeAssistantClient | None = Depends(get_ha_client_optional)
) -> YAMLValidationResponse:
    """
    Comprehensive YAML validation endpoint.
    
    Validates Home Assistant automation YAML through multiple stages:
    1. Syntax validation (YAML parsing)
    2. Structure validation (HA format with auto-fixes)
    3. Entity existence validation (via HA API)
    4. Safety validation (7 safety rules)
    
    Returns detailed validation report with errors, warnings, fixes, and suggestions.
    """
    errors = []
    warnings = []
    stages = {}
    entity_results = []
    fixed_yaml = None
    safety_score = None
    all_valid = True
    
    logger.info(f"🔍 Validating YAML (validate_entities={request.validate_entities}, validate_safety={request.validate_safety})")
    
    # Determine if we can actually validate entities (need HA client)
    can_validate_entities = request.validate_entities and ha_client is not None
    
    # Check if entity validation is requested but HA client is not available
    if request.validate_entities and not ha_client:
        warnings.append(ValidationError(
            stage="entities",
            severity="warning",
            message="Entity validation requested but Home Assistant client not initialized. Skipping entity validation.",
            fix="Ensure Home Assistant URL and token are configured"
        ))
        logger.warning("⚠️ Entity validation requested but HA client not available - skipping entity validation")
    
    # Initialize validators
    yaml_validator = AutomationYAMLValidator(ha_client=ha_client if can_validate_entities else None)
    safety_validator = get_safety_validator(getattr(settings, 'safety_level', 'moderate')) if request.validate_safety else None
    
    # Stage 1-3: Use AutomationYAMLValidator for core validation
    try:
        validation_result = await yaml_validator.validate(request.yaml, context=request.context)
        
        # Extract results from validation pipeline
        for stage in validation_result.stages:
            stage_name = stage.name
            stages[stage_name] = stage.valid
            
            # Convert stage errors to ValidationError format
            for error_msg in stage.errors:
                errors.append(ValidationError(
                    stage=stage_name,
                    severity="error",
                    message=error_msg,
                    fix=None
                ))
                if stage.valid is False:
                    all_valid = False
            
            # Convert stage warnings to ValidationError format
            for warning_msg in stage.warnings:
                warnings.append(ValidationError(
                    stage=stage_name,
                    severity="warning",
                    message=warning_msg,
                    fix=None
                ))
        
        # Get fixed YAML if available
        fixed_yaml = validation_result.fixed_yaml
        
        # Extract entity validation details if entity validation ran
        if can_validate_entities and "entities" in stages:
            try:
                parsed_yaml = yaml.safe_load(fixed_yaml if fixed_yaml else request.yaml)
                if parsed_yaml:
                    from ..services.entity_id_validator import EntityIDValidator
                    entity_id_extractor = EntityIDValidator()
                    entity_id_tuples = entity_id_extractor._extract_all_entity_ids(parsed_yaml)
                    
                    if entity_id_tuples:
                        from ..clients.data_api_client import DataAPIClient
                        from ..services.entity.validator import EntityValidator
                        
                        data_api_client = DataAPIClient(base_url=settings.data_api_url)
                        entity_validator_service = EntityValidator(
                            ha_client=ha_client,
                            data_api_client=data_api_client
                        )
                        
                        entity_ids = [eid for eid, _ in entity_id_tuples]
                        validation_results = await entity_validator_service.validate_entities(entity_ids)
                        
                        for entity_id in entity_ids:
                            result = validation_results.get(entity_id, {})
                            if isinstance(result, dict):
                                exists = result.get('exists', False)
                                alternatives = result.get('alternatives')
                            else:
                                exists = bool(result) if result else False
                                alternatives = None
                            
                            entity_results.append(EntityValidationResult(
                                entity_id=entity_id,
                                exists=exists,
                                alternatives=alternatives
                            ))
            except Exception as e:
                logger.warning(f"Could not extract entity validation details: {e}")
        
        # Update all_valid based on validation result
        if not validation_result.all_checks_passed:
            all_valid = False
            
    except Exception as e:
        logger.error(f"❌ Validation error: {e}", exc_info=True)
        errors.append(ValidationError(
            stage="validation",
            severity="error",
            message=f"Validation error: {str(e)}",
            fix="Check YAML format and structure"
        ))
        all_valid = False
        stages["validation"] = False
    
    # Stage 4: Safety Validation (if requested)
    if request.validate_safety and safety_validator:
        try:
            yaml_to_check = fixed_yaml if fixed_yaml else request.yaml
            safety_result = await safety_validator.validate(yaml_to_check)
            safety_score = safety_result.safety_score
            stages["safety"] = safety_result.passed
            
            if not safety_result.passed:
                all_valid = False
                for issue in safety_result.issues:
                    errors.append(ValidationError(
                        stage="safety",
                        severity=issue.severity,
                        message=issue.message,
                        fix=issue.suggested_fix
                    ))
                logger.warning(f"⚠️ Safety validation found {len(safety_result.issues)} issues (score: {safety_score})")
            else:
                logger.debug(f"✅ Safety validation passed (score: {safety_score})")
        except Exception as e:
            warnings.append(ValidationError(
                stage="safety",
                severity="warning",
                message=f"Safety validation error: {str(e)}",
                fix="Safety validation unavailable"
            ))
            stages["safety"] = False
            logger.warning(f"⚠️ Safety validation failed: {e}")
    
    # Generate summary
    if all_valid:
        summary = "✅ All validation checks passed"
    else:
        error_count = len([e for e in errors if e.severity == "error"])
        warning_count = len([w for w in warnings if w.severity == "warning"])
        summary = f"❌ Validation failed: {error_count} error(s), {warning_count} warning(s)"
    
    logger.info(f"🔍 Validation complete: valid={all_valid}, errors={len(errors)}, warnings={len(warnings)}")
    
    return YAMLValidationResponse(
        valid=all_valid,
        errors=errors,
        warnings=warnings,
        stages=stages,
        entity_results=entity_results,
        safety_score=safety_score,
        fixed_yaml=fixed_yaml,
        summary=summary
    )
