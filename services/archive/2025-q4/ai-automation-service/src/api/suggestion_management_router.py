"""
Suggestion Management Router
CRUD operations for managing automation suggestions
Story AI1.10: Suggestion Management API
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from ..config import settings
from ..database.models import ClarificationOutcome, Suggestion, get_db_session
from ..safety_validator import get_safety_validator
from .dependencies.auth import require_admin_user

logger = logging.getLogger(__name__)

safety_validator = get_safety_validator(getattr(settings, 'safety_level', 'moderate'))

router = APIRouter(
    prefix="/api/suggestions",
    tags=["suggestion-management"],
    dependencies=[Depends(require_admin_user)]
)


class UpdateSuggestionRequest(BaseModel):
    """Request to update a suggestion"""
    title: str | None = None
    description: str | None = None
    automation_yaml: str | None = None
    status: str | None = Field(None, pattern="^(pending|approved|deployed|rejected)$")
    category: str | None = None
    priority: str | None = None


class FeedbackRequest(BaseModel):
    """User feedback on a suggestion"""
    action: str = Field(..., pattern="^(approved|rejected|modified)$")
    feedback_text: str | None = None


@router.patch("/{suggestion_id}/approve")
async def approve_suggestion(suggestion_id: int):
    """
    Approve a suggestion.
    
    Changes status from 'pending' to 'approved', making it ready for deployment.
    
    Args:
        suggestion_id: ID of the suggestion to approve
    
    Returns:
        Updated suggestion
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

            # Update status
            suggestion.status = 'approved'
            suggestion.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(suggestion)

            # Update clarification outcome if linked (Phase 2.1)
            try:
                # Find outcome by suggestion_id
                outcome_result = await db.execute(
                    select(ClarificationOutcome).where(
                        ClarificationOutcome.suggestion_id == suggestion_id
                    )
                )
                outcome = outcome_result.scalar_one_or_none()
                if outcome:
                    outcome.suggestion_approved = True
                    await db.commit()
                    logger.debug(f"Updated clarification outcome for suggestion {suggestion_id}: approved")
            except Exception as e:
                logger.debug(f"Failed to update clarification outcome: {e}")
                # Non-blocking: continue even if outcome update fails

            logger.info(f"✅ Approved suggestion {suggestion_id}: {suggestion.title}")

            return {
                "success": True,
                "message": "Suggestion approved successfully",
                "data": {
                    "id": suggestion.id,
                    "title": suggestion.title,
                    "status": suggestion.status,
                    "updated_at": suggestion.updated_at.isoformat()
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: int, feedback: FeedbackRequest | None = None):
    """
    Reject a suggestion.
    
    Changes status to 'rejected' and optionally stores feedback for learning.
    
    Args:
        suggestion_id: ID of the suggestion to reject
        feedback: Optional feedback about why it was rejected
    
    Returns:
        Updated suggestion
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

            # Update status
            suggestion.status = 'rejected'
            suggestion.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(suggestion)

            # Store feedback if provided
            if feedback:
                from ..database.crud import store_feedback
                await store_feedback(db, {
                    'suggestion_id': suggestion_id,
                    'action': 'rejected',
                    'feedback_text': feedback.feedback_text
                })

            # Update clarification outcome if linked (Phase 2.1)
            try:
                # Find outcome by suggestion_id
                outcome_result = await db.execute(
                    select(ClarificationOutcome).where(
                        ClarificationOutcome.suggestion_id == suggestion_id
                    )
                )
                outcome = outcome_result.scalar_one_or_none()
                if outcome:
                    outcome.suggestion_approved = False
                    await db.commit()
                    logger.debug(f"Updated clarification outcome for suggestion {suggestion_id}: rejected")
            except Exception as e:
                logger.debug(f"Failed to update clarification outcome: {e}")
                # Non-blocking: continue even if outcome update fails

            # Track Q&A outcome for learning (rejected suggestion)
            try:
                from ...services.learning.qa_outcome_tracker import QAOutcomeTracker
                from ...database.models import SystemSettings, AskAIQuery, ClarificationSessionDB
                
                # Check if learning is enabled
                settings_result = await db.execute(select(SystemSettings).limit(1))
                settings = settings_result.scalar_one_or_none()
                if settings and getattr(settings, 'enable_qa_learning', True):
                    # Find clarification session through AskAIQuery
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
                                outcome_type='rejected'
                            )
                            logger.debug(f"✅ Updated Q&A outcome to rejected for session {clarification_session.session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update Q&A outcome for rejection: {e}")
                # Non-critical: continue even if tracking fails

            logger.info(f"❌ Rejected suggestion {suggestion_id}: {suggestion.title}")

            return {
                "success": True,
                "message": "Suggestion rejected successfully",
                "data": {
                    "id": suggestion.id,
                    "title": suggestion.title,
                    "status": suggestion.status,
                    "updated_at": suggestion.updated_at.isoformat()
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{suggestion_id}")
async def update_suggestion(suggestion_id: int, update_data: UpdateSuggestionRequest):
    """
    Update a suggestion (edit YAML, change status, etc.).
    
    Args:
        suggestion_id: ID of the suggestion to update
        update_data: Fields to update
    
    Returns:
        Updated suggestion
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

            # Update fields
            if update_data.title is not None:
                suggestion.title = update_data.title
            if update_data.description is not None:
                suggestion.description_only = update_data.description
            if update_data.automation_yaml is not None:
                safety_result = await safety_validator.validate(update_data.automation_yaml)
                if not safety_result.passed:
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
                            ]
                        }
                    )
                suggestion.automation_yaml = update_data.automation_yaml
                suggestion.safety_score = safety_result.safety_score
                suggestion.yaml_edited_at = datetime.now(timezone.utc)
                suggestion.yaml_edit_count = (suggestion.yaml_edit_count or 0) + 1
            if update_data.status is not None:
                suggestion.status = update_data.status
            if update_data.category is not None:
                suggestion.category = update_data.category
            if update_data.priority is not None:
                suggestion.priority = update_data.priority

            suggestion.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(suggestion)

            logger.info(f"✏️ Updated suggestion {suggestion_id}: {suggestion.title}")

            return {
                "success": True,
                "message": "Suggestion updated successfully",
                "data": {
                    "id": suggestion.id,
                    "title": suggestion.title,
                    "status": suggestion.status,
                    "updated_at": suggestion.updated_at.isoformat()
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{suggestion_id}")
async def delete_suggestion(suggestion_id: int):
    """
    Delete a suggestion.
    
    Args:
        suggestion_id: ID of the suggestion to delete
    
    Returns:
        Success message
    """
    try:
        async with get_db_session() as db:
            # Check if exists
            result = await db.execute(
                select(Suggestion).where(Suggestion.id == suggestion_id)
            )
            suggestion = result.scalar_one_or_none()

            if not suggestion:
                raise HTTPException(status_code=404, detail="Suggestion not found")

            # Delete
            await db.execute(
                delete(Suggestion).where(Suggestion.id == suggestion_id)
            )
            await db.commit()

            logger.info(f"🗑️ Deleted suggestion {suggestion_id}: {suggestion.title}")

            return {
                "success": True,
                "message": "Suggestion deleted successfully",
                "data": {
                    "id": suggestion_id,
                    "title": suggestion.title
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/approve")
async def batch_approve_suggestions(suggestion_ids: list[int]):
    """
    Approve multiple suggestions at once.
    
    Args:
        suggestion_ids: List of suggestion IDs to approve
    
    Returns:
        Summary of batch operation
    """
    try:
        async with get_db_session() as db:
            approved_count = 0
            failed_count = 0

            for suggestion_id in suggestion_ids:
                try:
                    result = await db.execute(
                        select(Suggestion).where(Suggestion.id == suggestion_id)
                    )
                    suggestion = result.scalar_one_or_none()

                    if suggestion:
                        suggestion.status = 'approved'
                        suggestion.updated_at = datetime.now(timezone.utc)
                        approved_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Failed to approve suggestion {suggestion_id}: {e}")
                    failed_count += 1

            await db.commit()

            logger.info(f"✅ Batch approved {approved_count} suggestions ({failed_count} failed)")

            return {
                "success": True,
                "message": f"Batch approved {approved_count} suggestions",
                "data": {
                    "approved_count": approved_count,
                    "failed_count": failed_count,
                    "total_requested": len(suggestion_ids)
                }
            }

    except Exception as e:
        logger.error(f"Batch approve failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/reject")
async def batch_reject_suggestions(suggestion_ids: list[int]):
    """
    Reject multiple suggestions at once.
    
    Args:
        suggestion_ids: List of suggestion IDs to reject
    
    Returns:
        Summary of batch operation
    """
    try:
        async with get_db_session() as db:
            rejected_count = 0
            failed_count = 0

            for suggestion_id in suggestion_ids:
                try:
                    result = await db.execute(
                        select(Suggestion).where(Suggestion.id == suggestion_id)
                    )
                    suggestion = result.scalar_one_or_none()

                    if suggestion:
                        suggestion.status = 'rejected'
                        suggestion.updated_at = datetime.now(timezone.utc)
                        rejected_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Failed to reject suggestion {suggestion_id}: {e}")
                    failed_count += 1

            await db.commit()

            logger.info(f"❌ Batch rejected {rejected_count} suggestions ({failed_count} failed)")

            return {
                "success": True,
                "message": f"Batch rejected {rejected_count} suggestions",
                "data": {
                    "rejected_count": rejected_count,
                    "failed_count": failed_count,
                    "total_requested": len(suggestion_ids)
                }
            }

    except Exception as e:
        logger.error(f"Batch reject failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

