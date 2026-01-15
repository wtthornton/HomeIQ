"""
Deployment Router

Epic 39, Story 39.10: Automation Service Foundation
Extracted from ai-automation-service for independent scaling.
Handles deployment of automations to Home Assistant.
"""

import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..api.dependencies import DatabaseSession, get_deployment_service
from ..api.error_handlers import handle_route_errors
from ..services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deploy", tags=["deployment"])


class DeployRequest(BaseModel):
    """Request to deploy an automation"""
    skip_validation: bool = False
    force_deploy: bool = False


@router.post("/{suggestion_id}")
@handle_route_errors("deploy suggestion")
async def deploy_suggestion(
    suggestion_id: int,
    request: DeployRequest = DeployRequest(),
    service: Annotated[DeploymentService, Depends(get_deployment_service)] = None
) -> dict[str, Any]:
    """
    Deploy an approved automation suggestion to Home Assistant.
    """
    result = await service.deploy_suggestion(
        suggestion_id=suggestion_id,
        skip_validation=request.skip_validation,
        force_deploy=request.force_deploy
    )
    return result


@router.post("/batch")
@handle_route_errors("batch deploy")
async def batch_deploy(
    suggestion_ids: list[int],
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """
    Deploy multiple automations in batch.
    """
    result = await service.batch_deploy(suggestion_ids)
    return result


@router.get("/automations")
@handle_route_errors("list automations")
async def list_deployed_automations(
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """
    List all deployed automations.
    """
    automations = await service.list_deployed_automations()
    return {"automations": automations}


@router.get("/automations/{automation_id}")
@handle_route_errors("get automation status")
async def get_automation_status(
    automation_id: str,
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """
    Get status of a deployed automation.
    """
    status = await service.get_automation_status(automation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Automation not found")
    return status


@router.post("/automations/{automation_id}/enable")
@handle_route_errors("enable automation")
async def enable_automation(
    automation_id: str,
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """Enable a deployed automation."""
    success = await service.enable_automation(automation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enable automation")
    return {
        "automation_id": automation_id,
        "status": "enabled",
        "success": True
    }


@router.post("/automations/{automation_id}/disable")
@handle_route_errors("disable automation")
async def disable_automation(
    automation_id: str,
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """Disable a deployed automation."""
    success = await service.disable_automation(automation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disable automation")
    return {
        "automation_id": automation_id,
        "status": "disabled",
        "success": True
    }


@router.post("/automations/{automation_id}/trigger")
@handle_route_errors("trigger automation")
async def trigger_automation(
    automation_id: str,
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """Trigger a deployed automation."""
    success = await service.trigger_automation(automation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger automation")
    return {
        "automation_id": automation_id,
        "status": "triggered",
        "success": True
    }


@router.get("/test-connection")
async def test_ha_connection(
    db: DatabaseSession
) -> dict[str, Any]:
    """
    Test connection to Home Assistant.
    
    Note: Full implementation will be migrated from ai-automation-service
    in Story 39.10 completion phase.
    """
    # TODO: Epic 39, Story 39.10 - Migrate HA connection testing from archived service
    # Current: Placeholder endpoint
    # Future: Full HA connectivity check with health status reporting
    return {
        "status": "unknown",
        "message": "Test connection endpoint - implementation in progress"
    }


@router.post("/{automation_id}/rollback")
@handle_route_errors("rollback automation")
async def rollback_automation(
    automation_id: str,
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """
    Rollback automation to previous version.
    """
    result = await service.rollback_automation(automation_id)
    return result


@router.get("/{automation_id}/versions")
@handle_route_errors("get automation versions")
async def get_automation_versions(
    automation_id: str,
    service: Annotated[DeploymentService, Depends(get_deployment_service)]
) -> dict[str, Any]:
    """
    Get version history for an automation.
    """
    versions = await service.get_automation_versions(automation_id)
    return {"automation_id": automation_id, "versions": versions}

