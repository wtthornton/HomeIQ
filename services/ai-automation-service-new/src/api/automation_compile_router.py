"""
Automation Compile Router

Hybrid Flow Implementation: Compile plan → YAML endpoint
Deterministic YAML compilation from templates (no LLM).
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import DatabaseSession
from ..api.error_handlers import handle_route_errors
from ..clients.data_api_client import DataAPIClient
from ..config import settings
from ..services.template_validator import TemplateValidator
from ..services.yaml_compiler import CompilationError, YAMLCompiler
from ..templates.template_library import TemplateLibrary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])


class CompileRequest(BaseModel):
    """Request to compile automation plan to YAML."""
    plan_id: str = Field(..., description="Plan identifier")
    template_id: str = Field(..., description="Template identifier")
    template_version: int = Field(..., description="Template version")
    parameters: dict[str, Any] = Field(..., description="Template parameters")
    resolved_context: dict[str, Any] = Field(default_factory=dict, description="Resolved context from validator")


class CompileResponse(BaseModel):
    """Response with compiled YAML artifact."""
    compiled_id: str
    plan_id: str
    yaml: str
    human_summary: str
    diff_summary: list[dict[str, Any]] = Field(default_factory=list)
    risk_notes: list[dict[str, Any]] = Field(default_factory=list)


def get_template_library() -> TemplateLibrary:
    """Get or create template library instance."""
    from pathlib import Path
    current_file = Path(__file__)
    templates_dir = current_file.parent.parent / "templates" / "templates"
    return TemplateLibrary(templates_dir=templates_dir)


def get_yaml_compiler(
    template_library: TemplateLibrary = Depends(get_template_library),
    db: DatabaseSession = Depends()
) -> YAMLCompiler:
    """Get YAML compiler instance."""
    data_api_client = DataAPIClient(base_url=settings.data_api_url)
    return YAMLCompiler(
        template_library=template_library,
        data_api_client=data_api_client
    )


@router.post("/compile", response_model=CompileResponse)
@handle_route_errors("compile automation plan")
async def compile_plan(
    request: CompileRequest,
    compiler: YAMLCompiler = Depends(get_yaml_compiler),
    db: DatabaseSession = Depends()
) -> CompileResponse:
    """
    Compile automation plan to YAML.
    
    Deterministic compilation from template + plan + resolved context.
    NEVER calls LLM - pure deterministic compilation.
    """
    try:
        result = await compiler.compile_plan(
            plan_id=request.plan_id,
            template_id=request.template_id,
            template_version=request.template_version,
            parameters=request.parameters,
            resolved_context=request.resolved_context,
            db=db
        )
        
        return CompileResponse(**result)
        
    except CompilationError as e:
        logger.error(f"Compilation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to compile plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compile plan: {str(e)}")
