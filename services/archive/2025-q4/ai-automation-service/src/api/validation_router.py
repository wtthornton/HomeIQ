"""
Validation Router - POST /validate endpoint
"""

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from ..clients.data_api_client import DataAPIClient
from ..config import settings
from ..policy.engine import PolicyEngine
from ..safety_validator import get_safety_validator
from ..validation.resolver import EntityResolver
from ..validation.validator import AutomationValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/validate", tags=["validation"])

# Initialize validator components
data_api_client = DataAPIClient(base_url=settings.data_api_url)
entity_resolver = EntityResolver(data_api_client=data_api_client)
policy_engine = PolicyEngine()
safety_validator = get_safety_validator(getattr(settings, 'safety_level', 'moderate'))
validator = AutomationValidator(
    entity_resolver=entity_resolver,
    policy_engine=policy_engine,
    safety_validator=safety_validator
)


class ValidateRequest(BaseModel):
    """Request to validate automation plan"""
    automation: Any  # Can be dict, YAML string, or AutomationPlan
    original_automation: Any | None = None  # Optional original for diff
    overrides: dict[str, bool] | None = None  # Policy overrides


class ValidateResponse(BaseModel):
    """Response from validation"""
    ok: bool
    verdict: str  # "allow", "warn", "deny"
    reasons: list[str]
    fixes: list[str]
    diff: dict[str, Any] | None = None
    entity_resolutions: dict[str, Any] | None = None
    safety_score: int | None = None
    schema_valid: bool = False


@router.post("", response_model=ValidateResponse)
async def validate_automation(request: ValidateRequest = Body(...)):
    """
    Validate automation plan through validation wall.
    
    Validates:
    - Schema conformance
    - Entity resolution
    - Capability checks
    - Policy rules
    - Safety constraints
    
    Returns:
        ValidationResult with verdict, reasons, fixes, and diff
    """
    try:
        result = await validator.validate(
            automation_input=request.automation,
            original_automation=request.original_automation,
            overrides=request.overrides
        )

        # Convert entity resolutions to dict for JSON serialization
        entity_resolutions_dict = {}
        if result.entity_resolutions:
            for text, resolution in result.entity_resolutions.items():
                entity_resolutions_dict[text] = {
                    "canonical_entity_id": resolution.canonical_entity_id,
                    "resolved": resolution.resolved,
                    "confidence": resolution.confidence,
                    "alternatives": resolution.alternatives,
                    "resolution_method": resolution.resolution_method
                }

        return ValidateResponse(
            ok=result.ok,
            verdict=result.verdict,
            reasons=result.reasons,
            fixes=result.fixes,
            diff=result.diff,
            entity_resolutions=entity_resolutions_dict,
            safety_score=result.safety_score,
            schema_valid=result.schema_valid
        )

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

