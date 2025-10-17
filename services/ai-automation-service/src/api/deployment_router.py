"""
Deployment Router
Deploy approved automations to Home Assistant
Story AI1.11: Home Assistant Integration
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

from ..config import settings
from ..clients.ha_client import HomeAssistantClient
from ..database.models import get_db_session, Suggestion
from ..safety_validator import get_safety_validator, SafetyResult
from ..rollback import store_version, rollback_to_previous, get_versions
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deploy", tags=["deployment"])

# Initialize HA client and safety validator
ha_client = HomeAssistantClient(settings.ha_url, settings.ha_token)
safety_validator = get_safety_validator(getattr(settings, 'safety_level', 'moderate'))


class DeployRequest(BaseModel):
    """Request to deploy an automation"""
    skip_validation: bool = False
    force_deploy: bool = False  # Override safety checks (for admins)


@router.post("/{suggestion_id}")
async def deploy_suggestion(suggestion_id: int, request: DeployRequest = DeployRequest()):
    """
    Deploy an approved suggestion to Home Assistant.
    
    Args:
        suggestion_id: ID of the suggestion to deploy
        request: Deployment options
    
    Returns:
        Deployment result with automation ID
    """
    try:
        async with get_db_session() as db:
            # Get suggestion
            result = await db.execute(
                select(Suggestion).where(Suggestion.id == suggestion_id)
            )
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                raise HTTPException(status_code=404, detail="Suggestion not found")
            
            # Validate status
            if suggestion.status not in ['approved', 'deployed'] and not request.skip_validation:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot deploy suggestion with status '{suggestion.status}'. Must be 'approved'."
                )
            
            logger.info(f"🚀 Deploying suggestion {suggestion_id}: {suggestion.title}")
            
            # SAFETY VALIDATION (AI1.19)
            if not request.force_deploy:
                logger.info(f"🛡️ Running safety validation for suggestion {suggestion_id}")
                
                # Get existing automations for conflict detection
                existing_automations = await ha_client.list_automations()
                
                # Run safety validation
                safety_result: SafetyResult = await safety_validator.validate(
                    suggestion.automation_yaml,
                    existing_automations
                )
                
                if not safety_result.passed:
                    logger.warning(
                        f"⚠️ Safety validation failed for suggestion {suggestion_id}: "
                        f"{safety_result.summary}"
                    )
                    
                    # Return detailed safety validation error
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "Safety validation failed",
                            "safety_score": safety_result.safety_score,
                            "issues": [
                                {
                                    "rule": issue.rule,
                                    "severity": issue.severity,
                                    "message": issue.message,
                                    "suggested_fix": issue.suggested_fix
                                }
                                for issue in safety_result.issues
                            ],
                            "can_override": safety_result.can_override,
                            "summary": safety_result.summary,
                            "suggestion": "Review issues and fix automation, or use force_deploy=true to override (if allowed)"
                        }
                    )
                
                logger.info(
                    f"✅ Safety validation passed: score={safety_result.safety_score}/100, "
                    f"issues={len(safety_result.issues)}"
                )
            else:
                logger.warning(f"⚠️ FORCE DEPLOY: Skipping safety validation for suggestion {suggestion_id}")
                safety_result = None
            
            # Deploy to Home Assistant
            deployment_result = await ha_client.deploy_automation(
                automation_yaml=suggestion.automation_yaml
            )
            
            if deployment_result.get('success'):
                automation_id = deployment_result.get('automation_id')
                
                # Store version for rollback (AI1.20)
                await store_version(
                    db,
                    automation_id,
                    suggestion.automation_yaml,
                    safety_result.safety_score if safety_result else 100
                )
                logger.info(f"📝 Version stored for rollback capability")
                
                # Update suggestion status
                suggestion.status = 'deployed'
                suggestion.ha_automation_id = automation_id
                suggestion.deployed_at = datetime.now(timezone.utc)
                suggestion.updated_at = datetime.now(timezone.utc)
                await db.commit()
                
                logger.info(f"✅ Successfully deployed suggestion {suggestion_id}")
                
                response_data = {
                    "success": True,
                    "message": "Automation deployed successfully to Home Assistant",
                    "data": {
                        "suggestion_id": suggestion_id,
                        "automation_id": automation_id,
                        "status": "deployed",
                        "title": suggestion.title
                    }
                }
                
                # Include safety score if validation was run
                if safety_result:
                    response_data["data"]["safety_score"] = safety_result.safety_score
                    if safety_result.issues:
                        response_data["data"]["safety_warnings"] = [
                            {
                                "severity": issue.severity,
                                "message": issue.message
                            }
                            for issue in safety_result.issues
                            if issue.severity in ['warning', 'info']
                        ]
                
                return response_data
            else:
                # Deployment failed
                error_msg = deployment_result.get('error', 'Unknown error')
                logger.error(f"❌ Deployment failed for suggestion {suggestion_id}: {error_msg}")
                
                raise HTTPException(
                    status_code=500,
                    detail=f"Deployment failed: {error_msg}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_deploy_suggestions(suggestion_ids: list[int]):
    """
    Deploy multiple approved suggestions at once.
    
    Args:
        suggestion_ids: List of suggestion IDs to deploy
    
    Returns:
        Summary of batch deployment
    """
    try:
        deployed_count = 0
        failed_count = 0
        failed_ids = []
        
        for suggestion_id in suggestion_ids:
            try:
                result = await deploy_suggestion(suggestion_id, DeployRequest())
                if result.get('success'):
                    deployed_count += 1
                else:
                    failed_count += 1
                    failed_ids.append(suggestion_id)
            except Exception as e:
                logger.error(f"Failed to deploy suggestion {suggestion_id}: {e}")
                failed_count += 1
                failed_ids.append(suggestion_id)
        
        logger.info(f"📊 Batch deployment: {deployed_count} succeeded, {failed_count} failed")
        
        return {
            "success": True,
            "message": f"Deployed {deployed_count} of {len(suggestion_ids)} automations",
            "data": {
                "deployed_count": deployed_count,
                "failed_count": failed_count,
                "failed_ids": failed_ids,
                "total_requested": len(suggestion_ids)
            }
        }
        
    except Exception as e:
        logger.error(f"Batch deployment error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automations")
async def list_deployed_automations():
    """
    List all automations currently in Home Assistant.
    
    Returns:
        List of deployed automations
    """
    try:
        automations = await ha_client.list_automations()
        
        return {
            "success": True,
            "data": automations,
            "count": len(automations)
        }
        
    except Exception as e:
        logger.error(f"Error listing automations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automations/{automation_id}")
async def get_automation_status(automation_id: str):
    """
    Get status of a specific automation in Home Assistant.
    
    Args:
        automation_id: Automation entity ID (e.g., "automation.morning_lights")
    
    Returns:
        Automation status
    """
    try:
        automation = await ha_client.get_automation(automation_id)
        
        if automation:
            return {
                "success": True,
                "data": automation
            }
        else:
            raise HTTPException(status_code=404, detail="Automation not found in HA")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting automation {automation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automations/{automation_id}/enable")
async def enable_automation(automation_id: str):
    """
    Enable/turn on an automation in Home Assistant.
    
    Args:
        automation_id: Automation entity ID
    
    Returns:
        Success status
    """
    try:
        success = await ha_client.enable_automation(automation_id)
        
        if success:
            return {
                "success": True,
                "message": f"Automation {automation_id} enabled"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to enable automation")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling automation {automation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automations/{automation_id}/disable")
async def disable_automation(automation_id: str):
    """
    Disable/turn off an automation in Home Assistant.
    
    Args:
        automation_id: Automation entity ID
    
    Returns:
        Success status
    """
    try:
        success = await ha_client.disable_automation(automation_id)
        
        if success:
            return {
                "success": True,
                "message": f"Automation {automation_id} disabled"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to disable automation")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling automation {automation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automations/{automation_id}/trigger")
async def trigger_automation(automation_id: str):
    """
    Manually trigger an automation in Home Assistant.
    
    Args:
        automation_id: Automation entity ID
    
    Returns:
        Success status
    """
    try:
        success = await ha_client.trigger_automation(automation_id)
        
        if success:
            return {
                "success": True,
                "message": f"Automation {automation_id} triggered"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to trigger automation")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering automation {automation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-connection")
async def test_ha_connection():
    """
    Test connection to Home Assistant.
    
    Returns:
        Connection status
    """
    try:
        is_connected = await ha_client.test_connection()
        
        if is_connected:
            return {
                "success": True,
                "message": "Successfully connected to Home Assistant",
                "ha_url": settings.ha_url
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to Home Assistant. Check HA_URL and HA_TOKEN."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HA connection test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Story AI1.20: Simple Rollback Endpoints
# ============================================================================

@router.post("/{automation_id}/rollback")
async def rollback_automation(automation_id: str):
    """
    Rollback automation to previous version.
    Simple: just restores the last version with safety validation.
    
    Args:
        automation_id: HA automation ID (e.g., "automation.morning_lights")
    
    Returns:
        Rollback result
    """
    try:
        async with get_db_session() as db:
            result = await rollback_to_previous(
                db,
                automation_id,
                ha_client,
                safety_validator
            )
            
            logger.info(f"✅ Rollback completed for {automation_id}")
            
            return {
                "success": True,
                "message": f"Automation {automation_id} rolled back successfully",
                "data": result
            }
            
    except ValueError as e:
        # Expected errors (no previous version, safety failure)
        logger.warning(f"Rollback rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{automation_id}/versions")
async def get_version_history(automation_id: str):
    """
    Get version history for automation (last 3 versions).
    
    Args:
        automation_id: HA automation ID
    
    Returns:
        List of versions (most recent first)
    """
    try:
        async with get_db_session() as db:
            versions = await get_versions(db, automation_id)
            
            return {
                "success": True,
                "automation_id": automation_id,
                "versions": [
                    {
                        "id": v.id,
                        "deployed_at": v.deployed_at.isoformat(),
                        "safety_score": v.safety_score,
                        "yaml_preview": v.yaml_content[:100] + "..." if len(v.yaml_content) > 100 else v.yaml_content,
                        "is_current": i == 0  # First is current
                    }
                    for i, v in enumerate(versions)
                ],
                "count": len(versions),
                "can_rollback": len(versions) >= 2
            }
            
    except Exception as e:
        logger.error(f"Error getting versions for {automation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

