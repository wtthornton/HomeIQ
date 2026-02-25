"""
Deployment Router

Epic 39, Story 39.10: Automation Service Foundation
Extracted from ai-automation-service for independent scaling.
Handles deployment of automations to Home Assistant.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..api.dependencies import DatabaseSession, get_deployment_service
from ..api.error_handlers import handle_route_errors
from ..database.models import CompiledArtifact, Deployment

if TYPE_CHECKING:
    from ..services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deploy", tags=["deployment"])


class DeployRequest(BaseModel):
    """Request to deploy an automation"""

    skip_validation: bool = False
    force_deploy: bool = False


@router.post("/batch")
@handle_route_errors("batch deploy")
async def batch_deploy(
    suggestion_ids: list[int], deployment_svc: DeploymentService = Depends(get_deployment_service)
) -> dict[str, Any]:
    """
    Deploy multiple automations in batch.
    """
    result = await deployment_svc.batch_deploy(suggestion_ids)
    return result


@router.post("/{suggestion_id}")
@handle_route_errors("deploy suggestion")
async def deploy_suggestion(
    suggestion_id: int,
    request: DeployRequest = DeployRequest(),
    deployment_svc: DeploymentService = Depends(get_deployment_service),
) -> dict[str, Any]:
    """
    Deploy an approved automation suggestion to Home Assistant.
    """
    result = await deployment_svc.deploy_suggestion(
        suggestion_id=suggestion_id,
        skip_validation=request.skip_validation,
        force_deploy=request.force_deploy,
    )
    return result


@router.get("/automations")
@handle_route_errors("list automations")
async def list_deployed_automations(
    deployment_svc: DeploymentService = Depends(get_deployment_service),
) -> dict[str, Any]:
    """
    List all deployed automations.
    """
    automations = await deployment_svc.list_deployed_automations()
    return {"automations": automations}


@router.get("/automations/{automation_id}")
@handle_route_errors("get automation status")
async def get_automation_status(
    automation_id: str, deployment_svc: DeploymentService = Depends(get_deployment_service)
) -> dict[str, Any]:
    """
    Get status of a deployed automation.
    """
    status = await deployment_svc.get_automation_status(automation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Automation not found")
    return status


@router.post("/automations/{automation_id}/enable")
@handle_route_errors("enable automation")
async def enable_automation(
    automation_id: str, deployment_svc: DeploymentService = Depends(get_deployment_service)
) -> dict[str, Any]:
    """Enable a deployed automation."""
    success = await deployment_svc.enable_automation(automation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enable automation")
    return {"automation_id": automation_id, "status": "enabled", "success": True}


@router.post("/automations/{automation_id}/disable")
@handle_route_errors("disable automation")
async def disable_automation(
    automation_id: str, deployment_svc: DeploymentService = Depends(get_deployment_service)
) -> dict[str, Any]:
    """Disable a deployed automation."""
    success = await deployment_svc.disable_automation(automation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disable automation")
    return {"automation_id": automation_id, "status": "disabled", "success": True}


@router.post("/automations/{automation_id}/trigger")
@handle_route_errors("trigger automation")
async def trigger_automation(
    automation_id: str, deployment_svc: DeploymentService = Depends(get_deployment_service)
) -> dict[str, Any]:
    """Trigger a deployed automation."""
    success = await deployment_svc.trigger_automation(automation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger automation")
    return {"automation_id": automation_id, "status": "triggered", "success": True}


@router.get("/test-connection")
async def test_ha_connection(_db: DatabaseSession) -> dict[str, Any]:
    """
    Test connection to Home Assistant.

    Note: Full implementation will be migrated from ai-automation-service
    in Story 39.10 completion phase.
    """
    # TODO: Epic 39, Story 39.10 - Migrate HA connection testing from archived service
    # Current: Placeholder endpoint
    # Future: Full HA connectivity check with health status reporting
    return {"status": "unknown", "message": "Test connection endpoint - implementation in progress"}


@router.post("/{automation_id}/rollback")
@handle_route_errors("rollback automation")
async def rollback_automation(
    automation_id: str, deployment_svc: DeploymentService = Depends(get_deployment_service)
) -> dict[str, Any]:
    """
    Rollback automation to previous version.
    """
    result = await deployment_svc.rollback_automation(automation_id)
    return result


@router.get("/{automation_id}/versions")
@handle_route_errors("get automation versions")
async def get_automation_versions(
    automation_id: str, deployment_svc: DeploymentService = Depends(get_deployment_service)
) -> dict[str, Any]:
    """
    Get version history for an automation.
    """
    versions = await deployment_svc.get_automation_versions(automation_id)
    return {"automation_id": automation_id, "versions": versions}


# Hybrid Flow: Deploy compiled artifact
class DeployCompiledRequest(BaseModel):
    """Request to deploy a compiled automation artifact."""

    compiled_id: str = Field(..., description="Compiled artifact identifier")
    approved_by: str | None = None
    ui_source: str | None = None
    audit_data: dict[str, Any] | None = None
    ha_automation_id: str | None = Field(
        None,
        description="Existing HA automation ID to update. If provided, updates instead of creating new.",
    )


@router.post("/automation/deploy")
async def deploy_compiled_automation(
    payload: DeployCompiledRequest,
    db: DatabaseSession,
    _deployment_svc: DeploymentService = Depends(get_deployment_service),
) -> dict[str, Any]:
    """
    Deploy a compiled automation artifact to Home Assistant.

    Hybrid Flow Implementation: Deploys from compiled_id (template-based flow).
    Supports update-or-create: if an existing deployment matches the same
    template + area, it updates instead of creating a duplicate.
    """
    import uuid
    from datetime import datetime, timezone

    compiled_id = payload.compiled_id

    # Get compiled artifact
    query = select(CompiledArtifact).where(CompiledArtifact.compiled_id == compiled_id)
    result = await db.execute(query)
    compiled_artifact = result.scalar_one_or_none()

    if not compiled_artifact:
        raise HTTPException(status_code=404, detail=f"Compiled artifact '{compiled_id}' not found")

    # Determine ha_automation_id: explicit > lookup by template+area > new from HA
    ha_automation_id = payload.ha_automation_id
    existing_deployment = None

    if (
        not ha_automation_id
        and getattr(compiled_artifact, "template_id", None)
        and getattr(compiled_artifact, "area_id", None)
    ):
        # Look up existing deployment for same template + area
        lookup_query = (
            select(Deployment)
            .where(
                Deployment.template_id == compiled_artifact.template_id,
                Deployment.area_id == compiled_artifact.area_id,
                Deployment.status == "deployed",
            )
            .order_by(Deployment.deployed_at.desc())
            .limit(1)
        )
        lookup_result = await db.execute(lookup_query)
        existing_deployment = lookup_result.scalar_one_or_none()
        if existing_deployment:
            ha_automation_id = existing_deployment.ha_automation_id
            logger.info(
                f"Found existing deployment for template={compiled_artifact.template_id}, "
                f"area={compiled_artifact.area_id}: {ha_automation_id}"
            )

    # Safety validation on compiled YAML before deployment
    from ..services.safety_validator import SafetyValidator

    safety_validator = SafetyValidator()
    safety_result = await safety_validator.validate(compiled_artifact.yaml)

    if not safety_result.passed:
        issue_msgs = [
            f"[{i.severity.value}] {i.message}" for i in safety_result.issues
        ]
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Safety validation failed",
                "safety_score": safety_result.score,
                "issues": issue_msgs,
            },
        )

    # Deploy to HA using existing deployment service
    from ..api.dependencies import get_ha_client

    ha_client = get_ha_client()

    try:
        # Inject existing automation ID into YAML for update-vs-create
        deploy_yaml = compiled_artifact.yaml
        if ha_automation_id:
            import yaml as _yaml

            auto_data = _yaml.safe_load(deploy_yaml)
            if isinstance(auto_data, dict):
                auto_data["id"] = ha_automation_id
                deploy_yaml = _yaml.dump(auto_data, default_flow_style=False, sort_keys=False)
                logger.info(f"Updating existing automation {ha_automation_id}")

        # Deploy YAML to HA
        deployment_result = await ha_client.deploy_automation(deploy_yaml)

        # Use HA-returned ID if we didn't have one from lookup
        final_ha_id = (
            ha_automation_id
            or deployment_result.get("automation_id")
            or deployment_result.get("entity_id")
        )
        if not final_ha_id:
            raise HTTPException(
                status_code=500, detail="Failed to extract automation ID from deployment"
            )

        # Compute version number
        version = 1
        if existing_deployment:
            version = existing_deployment.version + 1

        # Create deployment record
        deployment_id = f"d_{uuid.uuid4().hex[:8]}"
        deployment = Deployment(
            deployment_id=deployment_id,
            compiled_id=compiled_id,
            ha_automation_id=final_ha_id,
            template_id=getattr(compiled_artifact, "template_id", None),
            area_id=getattr(compiled_artifact, "area_id", None),
            status="deployed",
            version=version,
            approved_by=payload.approved_by,
            ui_source=payload.ui_source or "api",
            deployed_at=datetime.now(timezone.utc),
            audit_data=payload.audit_data
            or {
                "compiled_id": compiled_id,
                "plan_id": compiled_artifact.plan_id,
                "deployed_at": datetime.now(timezone.utc).isoformat(),
                "is_update": existing_deployment is not None,
                "previous_deployment_id": existing_deployment.deployment_id
                if existing_deployment
                else None,
                "safety_score": safety_result.score,
            },
        )

        db.add(deployment)

        # Mark previous deployment as superseded
        if existing_deployment:
            existing_deployment.status = "superseded"

        await db.commit()
        await db.refresh(deployment)

        logger.info(
            f"Deployed automation {final_ha_id} from compiled artifact {compiled_id} (version={version})"
        )

        deploy_result: dict[str, Any] = {
            "deployment_id": deployment_id,
            "compiled_id": compiled_id,
            "ha_automation_id": final_ha_id,
            "status": "deployed",
            "version": version,
            "is_update": existing_deployment is not None,
            "safety_score": safety_result.score,
        }
        # Story 7: Include state and last_triggered in deploy response
        if deployment_result.get("state"):
            deploy_result["state"] = deployment_result["state"]
        if deployment_result.get("attributes"):
            attrs = deployment_result["attributes"]
            if attrs.get("last_triggered"):
                deploy_result["last_triggered"] = attrs["last_triggered"]
        if deployment_result.get("verification_warning"):
            deploy_result["verification_warning"] = deployment_result["verification_warning"]
        return deploy_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deploy compiled automation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to deploy automation. Check server logs for details."
        ) from e
