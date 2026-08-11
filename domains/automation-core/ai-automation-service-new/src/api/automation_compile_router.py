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
from ..services.yaml_compiler import CompilationError, YAMLCompiler
from ..templates.template_library import TemplateLibrary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])

# M7 fix: Cache template library as module-level singleton (same pattern as plan_router)
_template_library: TemplateLibrary | None = None


class CompileRequest(BaseModel):
    """Request to compile automation plan to YAML."""

    plan_id: str = Field(..., description="Plan identifier")
    template_id: str = Field(..., description="Template identifier")
    template_version: int = Field(..., description="Template version")
    parameters: dict[str, Any] = Field(..., description="Template parameters")
    resolved_context: dict[str, Any] = Field(
        default_factory=dict, description="Resolved context from validator"
    )


class CompileResponse(BaseModel):
    """Response with compiled YAML artifact."""

    compiled_id: str
    plan_id: str
    yaml: str
    human_summary: str
    diff_summary: list[dict[str, Any]] = Field(default_factory=list)
    risk_notes: list[dict[str, Any]] = Field(default_factory=list)


def get_template_library() -> TemplateLibrary:
    """Get or create template library instance (cached)."""
    global _template_library
    if _template_library is None:
        from pathlib import Path

        current_file = Path(__file__)
        templates_dir = current_file.parent.parent / "templates" / "templates"
        _template_library = TemplateLibrary(templates_dir=templates_dir)
    return _template_library


def get_yaml_compiler(
    _db: DatabaseSession, template_library: TemplateLibrary = Depends(get_template_library)
) -> YAMLCompiler:
    """Get YAML compiler instance."""
    data_api_client = DataAPIClient(base_url=settings.data_api_url)
    return YAMLCompiler(template_library=template_library, data_api_client=data_api_client)


@router.post("/compile", response_model=CompileResponse)
@handle_route_errors("compile automation plan")
async def compile_plan(
    request: CompileRequest,
    db: DatabaseSession,
    compiler: YAMLCompiler = Depends(get_yaml_compiler),
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
            db=db,
        )

        return CompileResponse(**result)

    except CompilationError as e:
        logger.error(f"Compilation error: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "compilation_incomplete",
                "message": str(e),
                "suggestion": "Check that all required parameters are provided and the target area has the necessary devices.",
            },
        ) from e
    except Exception as e:
        logger.error(f"Failed to compile plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to compile plan. Check server logs for details."
        ) from e


class RegisterExternalRequest(BaseModel):
    """Register an externally-compiled automation artifact for deployment.

    The AgentForge author->judge pipeline is an external compiler: it produces
    finished HA YAML that must flow through the same deploy/version/rollback
    machinery as template-compiled artifacts.
    """

    yaml: str = Field(..., min_length=1, description="Complete HA automation YAML")
    human_summary: str = Field(..., min_length=1, description="Human-readable summary")
    source: str = Field(..., description="Producing system, e.g. 'agentforge'")
    source_run_id: str = Field(default="", description="Producer run id for provenance")
    area_id: str | None = Field(default=None, description="Target area")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    safety_class: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


@router.post("/compiled/register", response_model=CompileResponse)
@handle_route_errors("register external compiled artifact")
async def register_external_artifact(
    request: RegisterExternalRequest,
    db: DatabaseSession,
) -> CompileResponse:
    """Register externally-authored YAML as a compiled artifact.

    Creates the provenance Plan row (template_id 'external:<source>') and the
    CompiledArtifact row, returning a compiled_id accepted by
    POST /api/deploy/automation/deploy.
    """
    import uuid

    from ..database.models import CompiledArtifact, Plan

    plan_id = f"p_{uuid.uuid4().hex[:8]}"
    compiled_id = f"c_{uuid.uuid4().hex[:8]}"

    plan = Plan(
        plan_id=plan_id,
        template_id=f"external:{request.source}",
        template_version=0,
        parameters={"source_run_id": request.source_run_id},
        confidence=request.confidence,
        safety_class=request.safety_class,
        explanation=f"Externally compiled by {request.source} run {request.source_run_id}",
    )
    artifact = CompiledArtifact(
        compiled_id=compiled_id,
        plan_id=plan_id,
        template_id=f"external:{request.source}",
        area_id=request.area_id,
        yaml=request.yaml,
        human_summary=request.human_summary,
        diff_summary=[],
        risk_notes=[],
    )
    db.add(plan)
    await db.flush()  # plan row must exist before the artifact's FK insert
    db.add(artifact)
    await db.commit()

    logger.info(
        "Registered external compiled artifact %s (plan %s, source %s)",
        compiled_id,
        plan_id,
        request.source,
    )

    return CompileResponse(
        compiled_id=compiled_id,
        plan_id=plan_id,
        yaml=request.yaml,
        human_summary=request.human_summary,
        diff_summary=[],
        risk_notes=[],
    )
