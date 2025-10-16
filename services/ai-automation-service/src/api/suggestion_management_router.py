"""
Suggestion Management Router
CRUD operations for managing automation suggestions
Story AI1.10: Suggestion Management API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import logging

from ..database.crud import get_suggestions, store_suggestion
from ..database.models import get_db_session, Suggestion
from sqlalchemy import select, update, delete

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suggestions", tags=["suggestion-management"])


class UpdateSuggestionRequest(BaseModel):
    """Request to update a suggestion"""
    title: Optional[str] = None
    description: Optional[str] = None
    automation_yaml: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|approved|deployed|rejected)$")
    category: Optional[str] = None
    priority: Optional[str] = None


class FeedbackRequest(BaseModel):
    """User feedback on a suggestion"""
    action: str = Field(..., pattern="^(approved|rejected|modified)$")
    feedback_text: Optional[str] = None


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
async def reject_suggestion(suggestion_id: int, feedback: Optional[FeedbackRequest] = None):
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
                suggestion.description = update_data.description
            if update_data.automation_yaml is not None:
                suggestion.automation_yaml = update_data.automation_yaml
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

