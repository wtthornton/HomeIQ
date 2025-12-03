"""
Deployment Router
Deploy approved automations to Home Assistant
Story AI1.11: Home Assistant Integration
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..clients.ha_client import HomeAssistantClient
from ..config import settings
from ..database.models import Suggestion, get_db_session
from ..observability.trace import create_trace, write_trace
from ..rollback import get_versions, rollback_to_previous, store_version
from ..safety_validator import SafetyResult, get_safety_validator
from .dependencies.auth import require_authenticated_user

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
async def deploy_suggestion(
    suggestion_id: int,
    request: DeployRequest = DeployRequest(),
    auth=Depends(require_authenticated_user)
):
    """
    Deploy an approved automation suggestion to Home Assistant with comprehensive safety validation.
    
    This is the core deployment function that orchestrates the entire deployment pipeline,
    including safety validation, conflict detection, version management, and learning system
    integration. It ensures that only safe, validated automations are deployed to production.
    
    The function performs the following major phases:
    
    Phase 1: Authentication & Authorization
    - Validates user authentication (via dependency injection)
    - Checks admin privileges for skip_validation and force_deploy options
    - Enforces role-based access control
    
    Phase 2: Suggestion Retrieval & Status Validation
    - Retrieves suggestion from database by ID
    - Validates suggestion exists (404 if not found)
    - Checks suggestion status (must be 'approved' or 'deployed' unless skip_validation)
    - Enforces admin-only access for skip_validation
    
    Phase 3: Safety Validation & Conflict Detection
    - Fetches existing automations from Home Assistant for conflict detection
    - Runs comprehensive safety validation (Story AI1.19) using SafetyValidator
    - Validates automation YAML against safety rules (climate extremes, security, etc.)
    - Calculates safety score (0-100)
    - Detects conflicts with existing automations
    
    Phase 4: Admin Override Handling (if validation fails)
    - Allows admin override via force_deploy flag (if enabled in config)
    - Requires admin role and safety_allow_override configuration
    - Logs comprehensive security audit trail for all overrides
    - Tracks override details (safety score, issue count, admin role) for compliance
    
    Phase 5: Deployment to Home Assistant
    - Calls Home Assistant API to deploy automation YAML
    - Receives automation_id from Home Assistant upon successful deployment
    - Handles deployment failures with detailed error messages
    
    Phase 6: Version Management & Rollback Support (Story AI1.20)
    - Stores automation version for rollback capability
    - Records safety score with version for historical tracking
    - Enables rollback to previous versions if needed
    
    Phase 7: Observability & Tracing
    - Creates decision trace for observability system
    - Records validation results and safety scores
    - Generates trace_id for request tracking
    
    Phase 8: Database Updates
    - Updates suggestion status to 'deployed'
    - Records automation_id and deployment timestamp
    - Commits transaction to database
    
    Phase 9: Learning System Integration (if enabled)
    - Links automation to clarification session (Q&A outcome tracking)
    - Updates question quality metrics (marks questions as successful)
    - Feeds successful deployment to RL confidence calibrator
    - Tracks automation creation outcomes for continuous learning
    - All learning operations are non-blocking (failures logged but don't stop deployment)
    
    Phase 10: Response Building
    - Builds comprehensive response with deployment details
    - Includes safety score and warnings (if validation was run)
    - Returns automation_id, trace_id, and status information
    
    Args:
        suggestion_id (int): Database ID of the suggestion to deploy (must exist and be approved)
        request (DeployRequest): Deployment options containing:
            - skip_validation (bool): Skip status validation (admin only, default: False)
            - force_deploy (bool): Override safety checks (admin only, requires config, default: False)
        auth (AuthenticatedUser): Authenticated user object from dependency injection
            - Must have valid authentication token
            - Admin role required for skip_validation and force_deploy
    
    Returns:
        dict[str, Any]: Deployment result containing:
            - success (bool): True if deployment succeeded
            - message (str): Human-readable success message
            - data (dict): Deployment details:
                - suggestion_id (int): ID of deployed suggestion
                - automation_id (str): Home Assistant automation entity ID
                - status (str): "deployed"
                - title (str): Suggestion title
                - trace_id (str): Observability trace ID
                - safety_score (int): Safety validation score (0-100, if validation ran)
                - safety_warnings (list): List of warning/info issues (if any)
    
    Raises:
        HTTPException 404: If suggestion not found in database
        HTTPException 400: If suggestion status invalid or safety validation failed
        HTTPException 403: If user lacks admin privileges for requested operation
        HTTPException 500: If deployment fails or internal error occurs
    
    Examples:
        >>> # Standard deployment (approved suggestion)
        >>> result = await deploy_suggestion(
        ...     suggestion_id=123,
        ...     request=DeployRequest(),
        ...     auth=admin_user
        ... )
        >>> result['success']
        True
        >>> result['data']['automation_id']
        'automation.morning_lights'
        
        >>> # Admin override (safety validation failed but force_deploy=True)
        >>> result = await deploy_suggestion(
        ...     suggestion_id=456,
        ...     request=DeployRequest(force_deploy=True),
        ...     auth=admin_user
        ... )
        >>> # Security audit log created, deployment proceeds
    
    Security Considerations:
        - All admin overrides are logged with comprehensive audit trail
        - Safety validation cannot be bypassed without admin role
        - force_deploy requires explicit configuration flag (safety_allow_override)
        - All deployment operations are traced for observability
    
    Complexity: C (15) - High complexity due to multiple phases, conditional logic,
                 learning system integration, and comprehensive error handling.
    Note: This function handles critical production deployment operations. Consider
          refactoring learning system integration into separate service to reduce
          function length and improve testability. The function is well-structured
          but could benefit from extracting Phase 9 (learning integration) into
          a dedicated service method.
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
            if request.skip_validation and auth.role != "admin":
                raise HTTPException(status_code=403, detail="skip_validation is restricted to admin users")

            logger.info(f"🚀 Deploying suggestion {suggestion_id}: {suggestion.title}")

            # SAFETY VALIDATION (AI1.19)
            logger.info(f"🛡️ Running safety validation for suggestion {suggestion_id}")

            # Get existing automations for conflict detection
            existing_automations = await ha_client.list_automations()

            # Run safety validation
            safety_result: SafetyResult = await safety_validator.validate(
                suggestion.automation_yaml,
                existing_automations
            )

            if not safety_result.passed:
                if request.force_deploy:
                    if auth.role != "admin":
                        raise HTTPException(
                            status_code=403,
                            detail="force_deploy requires admin privileges"
                        )
                    if not getattr(settings, "safety_allow_override", False):
                        raise HTTPException(
                            status_code=400,
                            detail="force_deploy overrides are disabled by configuration"
                        )
                    # CRITICAL: Audit log all force_deploy overrides for security monitoring
                    logger.warning(
                        f"⚠️ SECURITY AUDIT - Admin override: Safety validation failed for suggestion {suggestion_id} "
                        f"(score={safety_result.safety_score}). Admin user {auth.role} bypassed safety checks via force_deploy. "
                        f"Automation: {suggestion.title[:50]}..."
                    )
                    # Log detailed audit trail
                    logger.info(
                        f"🔒 FORCE_DEPLOY_AUDIT: suggestion_id={suggestion_id}, "
                        f"admin_role={auth.role}, safety_score={safety_result.safety_score}, "
                        f"issues_count={len(safety_result.issues)}, "
                        f"can_override={safety_result.can_override}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Safety validation failed for suggestion {suggestion_id}: "
                        f"{safety_result.summary}"
                    )
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
                            "suggestion": "Review issues and fix automation, or request an admin override"
                        }
                    )
            else:
                logger.info(
                    f"✅ Safety validation passed: score={safety_result.safety_score}/100, "
                    f"issues={len(safety_result.issues)}"
                )

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
                logger.info("📝 Version stored for rollback capability")

                # Create decision trace
                trace = create_trace(
                    final_plan={"automation_id": automation_id, "yaml": suggestion.automation_yaml},
                    validation_results={
                        "safety_score": safety_result.safety_score if safety_result else 100,
                        "safety_passed": safety_result.passed if safety_result else True
                    } if safety_result else None
                )
                trace_id = write_trace(trace)

                # Update suggestion status
                suggestion.status = 'deployed'
                suggestion.ha_automation_id = automation_id
                suggestion.deployed_at = datetime.now(timezone.utc)
                suggestion.updated_at = datetime.now(timezone.utc)
                await db.commit()

                # Track Q&A outcome for learning (link automation to clarification session)
                try:
                    from ...services.learning.qa_outcome_tracker import QAOutcomeTracker
                    from ...database.models import SystemSettings, AskAIQuery, ClarificationSessionDB
                    from sqlalchemy import select
                    
                    # Check if learning is enabled
                    settings_result = await db.execute(select(SystemSettings).limit(1))
                    settings = settings_result.scalar_one_or_none()
                    if settings and getattr(settings, 'enable_qa_learning', True):
                        # Find clarification session through AskAIQuery
                        # Suggestions are stored in AskAIQuery.suggestions JSON, need to find query
                        # that contains this suggestion_id
                        query_result = await db.execute(
                            select(AskAIQuery).where(
                                AskAIQuery.suggestions.contains([{"id": suggestion_id}])
                            )
                        )
                        ask_query = query_result.scalar_one_or_none()
                        
                        if ask_query:
                            # Find clarification session linked to this query
                            session_result = await db.execute(
                                select(ClarificationSessionDB).where(
                                    ClarificationSessionDB.clarification_query_id == ask_query.query_id
                                )
                            )
                            clarification_session = session_result.scalar_one_or_none()
                            
                            if clarification_session:
                                outcome_tracker = QAOutcomeTracker()
                                await outcome_tracker.update_automation_outcome(
                                    db=db,
                                    session_id=clarification_session.session_id,
                                    automation_id=automation_id,
                                    outcome_type='automation_created'
                                )
                                logger.debug(f"✅ Updated Q&A outcome with automation_id for session {clarification_session.session_id}")
                                
                                # Update question quality metrics (mark questions as successful)
                                try:
                                    from ...services.learning.question_quality_tracker import QuestionQualityTracker
                                    quality_tracker = QuestionQualityTracker()
                                    
                                    # Get questions from session
                                    questions = clarification_session.questions or []
                                    for question in questions:
                                        question_id = question.get('id') if isinstance(question, dict) else getattr(question, 'id', None)
                                        if question_id:
                                            await quality_tracker.update_question_quality(
                                                db=db,
                                                question_id=question_id,
                                                outcome='success',
                                                confidence_impact=None  # Already tracked earlier
                                            )
                                    logger.debug(f"✅ Updated question quality for {len(questions)} questions")
                                    
                                    # Feed successful deployment to RL calibrator
                                    try:
                                        from ...services.clarification.rl_calibrator import RLConfidenceCalibrator
                                        from ...database.models import ClarificationSessionDB
                                        
                                        # Get session to find confidence
                                        session_result = await db.execute(
                                            select(ClarificationSessionDB).where(
                                                ClarificationSessionDB.session_id == clarification_session.session_id
                                            )
                                        )
                                        session = session_result.scalar_one_or_none()
                                        
                                        if session:
                                            rl_calibrator = RLConfidenceCalibrator()
                                            
                                            # Feed successful automation creation
                                            rl_calibrator.add_feedback(
                                                predicted_confidence=session.current_confidence,
                                                actual_outcome=True,  # Automation was created and deployed
                                                ambiguity_count=len(session.ambiguities) if session.ambiguities else 0,
                                                critical_ambiguity_count=len([a for a in (session.ambiguities or []) if isinstance(a, dict) and a.get('severity') == 'critical']),
                                                rounds=session.rounds_completed,
                                                answer_count=len(session.answers) if session.answers else 0,
                                                auto_train=True
                                            )
                                            logger.debug(f"✅ Fed successful deployment to RL calibrator")
                                    except Exception as e:
                                        logger.warning(f"⚠️ Failed to feed deployment to RL calibrator: {e}")
                                        # Non-critical: continue
                                except Exception as e:
                                    logger.warning(f"⚠️ Failed to update question quality: {e}")
                                    # Non-critical: continue
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update Q&A outcome with automation: {e}")
                    # Non-critical: continue even if tracking fails

                logger.info(f"✅ Successfully deployed suggestion {suggestion_id}")

                response_data = {
                    "success": True,
                    "message": "Automation deployed successfully to Home Assistant",
                    "data": {
                        "suggestion_id": suggestion_id,
                        "automation_id": automation_id,
                        "status": "deployed",
                        "title": suggestion.title,
                        "trace_id": trace_id
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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e

