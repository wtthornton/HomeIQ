"""
Automation Validate Router

Hybrid Flow Implementation: Validate plan endpoint
Deterministic validation of automation plans against templates.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import DatabaseSession
from ..api.error_handlers import handle_route_errors
from ..clients.data_api_client import DataAPIClient
from ..config import settings
from ..services.template_validator import TemplateValidator, ValidationError
from ..templates.template_library import TemplateLibrary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])

# M7 fix: Cache template library as module-level singleton (same pattern as plan_router)
_template_library: TemplateLibrary | None = None


class ValidateRequest(BaseModel):
    """Request to validate automation plan."""
    plan_id: str = Field(..., description="Plan identifier")
    template_id: str = Field(..., description="Template identifier")
    template_version: int = Field(..., description="Template version")
    parameters: dict[str, Any] = Field(..., description="Template parameters")


class ValidateResponse(BaseModel):
    """Response with validation result."""
    valid: bool
    validation_errors: list[dict[str, str]] = Field(default_factory=list)
    resolved_context: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=dict)


def get_template_library() -> TemplateLibrary:
    """Get or create template library instance (cached)."""
    global _template_library
    if _template_library is None:
        from pathlib import Path
        current_file = Path(__file__)
        templates_dir = current_file.parent.parent / "templates" / "templates"
        _template_library = TemplateLibrary(templates_dir=templates_dir)
    return _template_library


def get_template_validator(
    db: DatabaseSession,
    template_library: TemplateLibrary = Depends(get_template_library)
) -> TemplateValidator:
    """Get template validator instance."""
    data_api_client = DataAPIClient(base_url=settings.data_api_url)
    return TemplateValidator(
        template_library=template_library,
        data_api_client=data_api_client
    )


@router.post("/validate", response_model=ValidateResponse)
@handle_route_errors("validate automation plan")
async def validate_plan(
    request: ValidateRequest,
    validator: TemplateValidator = Depends(get_template_validator)
) -> ValidateResponse:
    """
    Validate automation plan against template.
    
    Validates:
    - Template exists and version matches
    - Parameters match schema (types, enums, bounds)
    - Context can be resolved (room → area_id, device → entity_id)
    - Safety checks pass
    """
    try:
        result = await validator.validate_plan(
            plan_id=request.plan_id,
            template_id=request.template_id,
            template_version=request.template_version,
            parameters=request.parameters
        )
        
        return ValidateResponse(**result)
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail="Validation error. Check server logs for details.")
    except Exception as e:
        logger.error(f"Failed to validate plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate plan. Check server logs for details.")
