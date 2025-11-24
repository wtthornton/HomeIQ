"""
API endpoints for device name enhancement.

Provides endpoints for:
- Getting name suggestions for devices
- Accepting/rejecting suggestions
- Batch name enhancement
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..models.database import Device, DeviceEntity, NameSuggestion
from ..services.name_enhancement import DeviceNameGenerator, NameUniquenessValidator
from ..config import Settings

router = APIRouter(prefix="/api/name-enhancement", tags=["Name Enhancement"])


class NameSuggestionResponse(BaseModel):
    """Name suggestion response"""
    name: str
    confidence: float
    source: str
    reasoning: str | None = None


class NameSuggestionsResponse(BaseModel):
    """Response with multiple name suggestions"""
    device_id: str
    current_name: str
    suggestions: list[NameSuggestionResponse]


class AcceptNameRequest(BaseModel):
    """Request to accept a name suggestion"""
    suggested_name: str
    sync_to_ha: bool = Field(default=False, description="Sync name back to Home Assistant")


class AcceptNameResponse(BaseModel):
    """Response after accepting a name"""
    success: bool
    device_id: str
    old_name: str
    new_name: str


class BatchEnhanceRequest(BaseModel):
    """Request for batch name enhancement"""
    device_ids: list[str] | None = Field(default=None, description="Specific device IDs, or None for all")
    use_ai: bool = Field(default=False, description="Use AI generation (slower, costs money)")
    auto_accept_high_confidence: bool = Field(
        default=False,
        description="Auto-accept suggestions with confidence > 0.9"
    )


class BatchEnhanceResponse(BaseModel):
    """Response for batch enhancement"""
    success: bool
    job_id: str
    status: str
    estimated_duration: str


@router.get("/devices/{device_id}/suggestions", response_model=NameSuggestionsResponse)
async def get_name_suggestions(
    device_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get name suggestions for a device.
    
    Returns all pending suggestions for the device, ordered by confidence.
    """
    try:
        # Get device
        result = await session.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )

        # Get pending suggestions
        result = await session.execute(
            select(NameSuggestion)
            .where(
                NameSuggestion.device_id == device_id,
                NameSuggestion.status == "pending"
            )
            .order_by(NameSuggestion.confidence_score.desc())
        )
        suggestions = result.scalars().all()

        return NameSuggestionsResponse(
            device_id=device_id,
            current_name=device.name_by_user or device.name or "Unknown",
            suggestions=[
                NameSuggestionResponse(
                    name=s.suggested_name,
                    confidence=s.confidence_score or 0.0,
                    source=s.suggestion_source,
                    reasoning=s.reasoning
                )
                for s in suggestions
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting name suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get name suggestions: {str(e)}"
        )


@router.post("/devices/{device_id}/accept", response_model=AcceptNameResponse)
async def accept_suggested_name(
    device_id: str,
    request: AcceptNameRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Accept a suggested name (updates name_by_user).
    
    This updates the device's name_by_user field and marks the suggestion as accepted.
    Optionally syncs the name back to Home Assistant.
    """
    try:
        # Get device
        result = await session.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )

        old_name = device.name_by_user or device.name or "Unknown"

        old_name = device.name_by_user or device.name or "Unknown"

        # Update device name_by_user
        device.name_by_user = request.suggested_name
        device.updated_at = datetime.utcnow()

        # Mark suggestion as accepted
        result = await session.execute(
            select(NameSuggestion).where(
                NameSuggestion.device_id == device_id,
                NameSuggestion.suggested_name == request.suggested_name,
                NameSuggestion.status == "pending"
            )
        )
        suggestion = result.scalar_one_or_none()
        if suggestion:
            suggestion.status = "accepted"
            suggestion.reviewed_at = datetime.utcnow()
            
            # Learn from this customization
            try:
                from ..api.discovery import get_discovery_service
                discovery_service = await get_discovery_service()
                if discovery_service and hasattr(discovery_service, 'preference_learner') and discovery_service.preference_learner:
                # Get primary entity
                entity_result = await session.execute(
                    select(DeviceEntity).where(
                        DeviceEntity.device_id == device_id
                    ).limit(1)
                )
                entity = entity_result.scalar_one_or_none()
                
                    await discovery_service.preference_learner.learn_from_customization(
                        original_name=suggestion.original_name,
                        user_customized_name=request.suggested_name,
                        device=device,
                        entity=entity,
                        db_session=session
                    )
            except Exception as e:
                logger.warning(f"Failed to learn from customization: {e}")

        # Reject other pending suggestions for this device
        result = await session.execute(
            select(NameSuggestion).where(
                NameSuggestion.device_id == device_id,
                NameSuggestion.status == "pending",
                NameSuggestion.suggested_name != request.suggested_name
            )
        )
        for other_suggestion in result.scalars().all():
            other_suggestion.status = "rejected"
            other_suggestion.reviewed_at = datetime.utcnow()

        await session.commit()

        # TODO: Sync to Home Assistant if requested
        # if request.sync_to_ha:
        #     await sync_name_to_ha(device_id, request.suggested_name)

        return AcceptNameResponse(
            success=True,
            device_id=device_id,
            old_name=old_name,
            new_name=request.suggested_name
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error accepting name: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept name: {str(e)}"
        )


@router.post("/devices/{device_id}/reject")
async def reject_suggested_name(
    device_id: str,
    suggested_name: str = Query(..., description="Name suggestion to reject"),
    reason: str | None = Query(default=None, description="Optional rejection reason"),
    session: AsyncSession = Depends(get_db_session)
):
    """Reject a name suggestion"""
    try:
        result = await session.execute(
            select(NameSuggestion).where(
                NameSuggestion.device_id == device_id,
                NameSuggestion.suggested_name == suggested_name,
                NameSuggestion.status == "pending"
            )
        )
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found"
            )

        suggestion.status = "rejected"
        suggestion.reviewed_at = datetime.utcnow()
        if reason:
            suggestion.user_feedback = reason

        await session.commit()

        return {"success": True, "message": "Suggestion rejected"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error rejecting name: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject name: {str(e)}"
        )


@router.post("/batch-enhance", response_model=BatchEnhanceResponse)
async def batch_enhance_names(
    request: BatchEnhanceRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Trigger batch name enhancement (background job).
    
    This generates name suggestions for multiple devices.
    The actual processing happens in the background.
    """
    try:
        import uuid
        job_id = str(uuid.uuid4())

        # Get batch processor from discovery service
        from ..api.discovery import get_discovery_service
        try:
            discovery_service = await get_discovery_service()
            
            if not discovery_service or not discovery_service.batch_processor:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Name enhancement batch processor not available. Enable AUTO_GENERATE_NAME_SUGGESTIONS in settings."
                )

            # Trigger batch processing in background
            asyncio.create_task(
                discovery_service.batch_processor.process_pending_devices(
                    use_ai=request.use_ai,
                    auto_accept_high_confidence=request.auto_accept_high_confidence
                )
            )
        except Exception as e:
            logger.error(f"Error accessing discovery service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Name enhancement service not available: {str(e)}"
            )

        return BatchEnhanceResponse(
            success=True,
            job_id=job_id,
            status="running",
            estimated_duration="2-5 minutes" if request.use_ai else "10-30 seconds"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering batch enhancement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger batch enhancement: {str(e)}"
        )

# Import asyncio
import asyncio


@router.get("/status")
async def get_enhancement_status(
    status_filter: str | None = Query(default=None, description="Filter by status"),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    session: AsyncSession = Depends(get_db_session)
):
    """Get name enhancement status statistics"""
    try:
        from sqlalchemy import func, case

        # Count by status
        result = await session.execute(
            select(
                NameSuggestion.status,
                func.count(NameSuggestion.id).label('count')
            )
            .group_by(NameSuggestion.status)
        )
        by_status = {row.status: row.count for row in result}

        # Count by confidence
        result = await session.execute(
            select(
                func.count(NameSuggestion.id).label('total'),
                func.sum(
                    case((NameSuggestion.confidence_score > 0.8, 1), else_=0)
                ).label('high'),
                func.sum(
                    case(
                        (
                            (NameSuggestion.confidence_score >= 0.5) &
                            (NameSuggestion.confidence_score <= 0.8),
                            1
                        ),
                        else_=0
                    )
                ).label('medium'),
                func.sum(
                    case((NameSuggestion.confidence_score < 0.5, 1), else_=0)
                ).label('low')
            )
        )
        confidence_stats = result.one()

        return {
            "total_suggestions": confidence_stats.total or 0,
            "by_status": by_status,
            "by_confidence": {
                "high": confidence_stats.high or 0,
                "medium": confidence_stats.medium or 0,
                "low": confidence_stats.low or 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting enhancement status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/devices/pending")
async def get_pending_suggestions(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get all devices with pending name suggestions (bulk endpoint for UI).
    
    Returns devices grouped by device_id with their suggestions.
    """
    try:
        import json
        
        # Get all pending suggestions
        result = await session.execute(
            select(NameSuggestion, Device.name, Device.name_by_user)
            .join(Device, NameSuggestion.device_id == Device.id)
            .where(NameSuggestion.status == "pending")
            .order_by(NameSuggestion.device_id, NameSuggestion.confidence_score.desc())
            .limit(limit * 5)  # Get more to account for multiple suggestions per device
        )

        # Group by device_id
        devices_dict: dict[str, dict[str, Any]] = {}
        
        for row in result:
            suggestion = row[0]
            device_name = row[1]
            name_by_user = row[2]
            
            device_id = suggestion.device_id
            if device_id not in devices_dict:
                devices_dict[device_id] = {
                    "device_id": device_id,
                    "current_name": name_by_user or device_name or "Unknown",
                    "suggestions": []
                }
            
            devices_dict[device_id]["suggestions"].append({
                "name": suggestion.suggested_name,
                "confidence": suggestion.confidence_score or 0.0,
                "source": suggestion.suggestion_source,
                "reasoning": suggestion.reasoning
            })

        # Convert to list and limit
        devices = list(devices_dict.values())[:limit]

        return {
            "devices": devices,
            "count": len(devices)
        }
    except Exception as e:
        logger.error(f"Error getting pending suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending suggestions: {str(e)}"
        )


# Import logger
import logging
logger = logging.getLogger(__name__)

