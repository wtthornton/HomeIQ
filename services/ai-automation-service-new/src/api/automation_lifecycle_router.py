"""
Automation Lifecycle Router

Hybrid Flow Implementation: Lifecycle tracking endpoints
Query full lifecycle: conversation → plan → compiled → deployed
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..api.dependencies import DatabaseSession
from ..api.error_handlers import handle_route_errors
from ..database.models import CompiledArtifact, Deployment, Plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])


class LifecycleResponse(BaseModel):
    """Response with full automation lifecycle."""
    conversation_id: str | None
    plan: dict[str, Any] | None
    compiled: dict[str, Any] | None
    deployment: dict[str, Any] | None


@router.get("/plans/{plan_id}")
@handle_route_errors("get plan")
async def get_plan(
    plan_id: str,
    db: DatabaseSession
) -> dict[str, Any]:
    """
    Get plan details by plan_id.
    """
    query = select(Plan).where(Plan.plan_id == plan_id)
    result = await db.execute(query)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found")
    
    return {
        "plan_id": plan.plan_id,
        "conversation_id": plan.conversation_id,
        "template_id": plan.template_id,
        "template_version": plan.template_version,
        "parameters": plan.parameters,
        "confidence": plan.confidence,
        "clarifications_needed": plan.clarifications_needed,
        "safety_class": plan.safety_class,
        "explanation": plan.explanation,
        "created_at": plan.created_at.isoformat() if plan.created_at else None
    }


@router.get("/compiled/{compiled_id}")
@handle_route_errors("get compiled artifact")
async def get_compiled(
    compiled_id: str,
    db: DatabaseSession
) -> dict[str, Any]:
    """
    Get compiled artifact details by compiled_id.
    """
    query = select(CompiledArtifact).where(CompiledArtifact.compiled_id == compiled_id)
    result = await db.execute(query)
    compiled = result.scalar_one_or_none()
    
    if not compiled:
        raise HTTPException(status_code=404, detail=f"Compiled artifact '{compiled_id}' not found")
    
    return {
        "compiled_id": compiled.compiled_id,
        "plan_id": compiled.plan_id,
        "yaml": compiled.yaml,
        "human_summary": compiled.human_summary,
        "diff_summary": compiled.diff_summary,
        "risk_notes": compiled.risk_notes,
        "created_at": compiled.created_at.isoformat() if compiled.created_at else None
    }


@router.get("/deployments/{deployment_id}")
@handle_route_errors("get deployment")
async def get_deployment(
    deployment_id: str,
    db: DatabaseSession
) -> dict[str, Any]:
    """
    Get deployment details by deployment_id.
    """
    query = select(Deployment).where(Deployment.deployment_id == deployment_id)
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")
    
    return {
        "deployment_id": deployment.deployment_id,
        "compiled_id": deployment.compiled_id,
        "ha_automation_id": deployment.ha_automation_id,
        "status": deployment.status,
        "version": deployment.version,
        "approved_by": deployment.approved_by,
        "ui_source": deployment.ui_source,
        "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
        "audit_data": deployment.audit_data
    }


@router.get("/conversations/{conversation_id}/lifecycle")
@handle_route_errors("get lifecycle")
async def get_lifecycle(
    conversation_id: str,
    db: DatabaseSession
) -> LifecycleResponse:
    """
    Get full automation lifecycle for a conversation.
    
    Returns plan, compiled artifact, and deployment (if available).
    """
    # Get plan
    plan_query = select(Plan).where(Plan.conversation_id == conversation_id).order_by(Plan.created_at.desc())
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one_or_none()
    
    plan_data = None
    compiled_data = None
    deployment_data = None
    
    if plan:
        plan_data = {
            "plan_id": plan.plan_id,
            "template_id": plan.template_id,
            "template_version": plan.template_version,
            "parameters": plan.parameters,
            "confidence": plan.confidence,
            "safety_class": plan.safety_class,
            "created_at": plan.created_at.isoformat() if plan.created_at else None
        }
        
        # Get compiled artifact
        compiled_query = select(CompiledArtifact).where(CompiledArtifact.plan_id == plan.plan_id)
        compiled_result = await db.execute(compiled_query)
        compiled = compiled_result.scalar_one_or_none()
        
        if compiled:
            compiled_data = {
                "compiled_id": compiled.compiled_id,
                "human_summary": compiled.human_summary,
                "risk_notes": compiled.risk_notes,
                "created_at": compiled.created_at.isoformat() if compiled.created_at else None
            }
            
            # Get deployment
            deployment_query = select(Deployment).where(Deployment.compiled_id == compiled.compiled_id)
            deployment_result = await db.execute(deployment_query)
            deployment = deployment_result.scalar_one_or_none()
            
            if deployment:
                deployment_data = {
                    "deployment_id": deployment.deployment_id,
                    "ha_automation_id": deployment.ha_automation_id,
                    "status": deployment.status,
                    "version": deployment.version,
                    "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None
                }
    
    return LifecycleResponse(
        conversation_id=conversation_id,
        plan=plan_data,
        compiled=compiled_data,
        deployment=deployment_data
    )
