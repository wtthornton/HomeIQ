"""
Automation Plan Router

Hybrid Flow Implementation: Intent → Plan endpoint
LLM generates structured plan (template_id + parameters), never YAML.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import DatabaseSession
from ..api.error_handlers import handle_route_errors
from ..clients.data_api_client import DataAPIClient
from ..clients.openai_client import OpenAIClient
from ..config import settings
from ..services.intent_planner import IntentPlanner
from ..templates.template_library import TemplateLibrary

# Agent Evaluation Framework: SessionTracer wiring (E3.S6)
try:
    from homeiq_patterns.evaluation.session_tracer import InMemorySink, trace_session
    _eval_sink = InMemorySink()  # TODO: replace with persistent sink when E4 is implemented
    _TRACING_AVAILABLE = True
except ImportError:
    _TRACING_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])


class PlanRequest(BaseModel):
    """Request to create automation plan."""

    conversation_id: str | None = Field(None, description="Conversation ID for tracking")
    user_text: str = Field(..., description="User's natural language request")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (selected devices, room, timezone, etc.)",
    )


class PlanResponse(BaseModel):
    """Response with automation plan."""

    plan_id: str
    intent_type: str = "automation_request"
    template_id: str
    template_version: int
    parameters: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    clarifications_needed: list[dict[str, Any]] = Field(default_factory=list)
    safety_class: str
    promotion_recommended: bool
    explanation: str


# Global instances (initialized in dependency)
_template_library: TemplateLibrary | None = None


def get_template_library() -> TemplateLibrary:
    """Get or create template library instance."""
    global _template_library
    if _template_library is None:
        from pathlib import Path

        current_file = Path(__file__)
        templates_dir = current_file.parent.parent / "templates" / "templates"
        _template_library = TemplateLibrary(templates_dir=templates_dir)
        logger.info(
            f"Initialized template library with {len(_template_library.list_templates())} templates"
        )
    return _template_library


def get_intent_planner(
    _db: DatabaseSession, template_library: TemplateLibrary = Depends(get_template_library)
) -> IntentPlanner:
    """Get intent planner instance."""
    openai_client = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
    data_api_client = DataAPIClient(base_url=settings.data_api_url)

    return IntentPlanner(
        openai_client=openai_client,
        template_library=template_library,
        data_api_client=data_api_client,
    )


@router.post("/plan", response_model=PlanResponse)
@(trace_session(agent_name="ai-automation-service", sink=_eval_sink, model="gpt-4o") if _TRACING_AVAILABLE else lambda f: f)
@handle_route_errors("create automation plan")
async def create_plan(
    request: PlanRequest, db: DatabaseSession, planner: IntentPlanner = Depends(get_intent_planner)
) -> PlanResponse:
    """
    Create automation plan from user intent.

    LLM selects appropriate template and fills in parameters.
    Returns structured plan (template_id + parameters), never YAML.
    """
    try:
        plan = await planner.create_plan(
            user_text=request.user_text,
            conversation_id=request.conversation_id,
            context=request.context,
            db=db,
        )

        # Coerce clarifications_needed: LLM sometimes returns list[str]
        # instead of list[dict], which fails Pydantic validation.
        raw_clarifications = plan.get("clarifications_needed", [])
        plan["clarifications_needed"] = [
            c if isinstance(c, dict) else {"question": c} for c in raw_clarifications
        ]

        return PlanResponse(**plan)

    except ValueError as e:
        logger.error(f"Invalid plan creation request: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create plan: {str(e)}") from e
