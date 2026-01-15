"""
Suggestions API Router for Proactive Agent Service

REST API endpoints for managing proactive automation suggestions.
Enhanced with invalid suggestion reporting for user feedback.

Epic: Proactive Suggestions Device Validation
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.suggestion_storage_service import SuggestionStorageService
from ..clients.ha_agent_client import HAAgentClient
from ..models import Suggestion, InvalidSuggestionReport, InvalidReportReason

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/suggestions",
    tags=["suggestions"],
)


# Pydantic models for request/response
class SuggestionResponse(BaseModel):
    """Suggestion response model"""

    id: str
    prompt: str
    context_type: str
    status: str
    quality_score: float
    context_metadata: dict[str, Any] = Field(default_factory=dict)
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)
    agent_response: dict[str, Any] | None = None
    created_at: str
    sent_at: str | None = None
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Convert datetime fields to ISO strings before validation"""
        from datetime import datetime as dt

        if hasattr(obj, "__dict__"):
            data = {}
            for key in ["id", "prompt", "context_type", "status", "quality_score",
                       "context_metadata", "prompt_metadata", "agent_response",
                       "created_at", "sent_at", "updated_at"]:
                value = getattr(obj, key, None)
                if isinstance(value, dt):
                    data[key] = value.isoformat()
                else:
                    data[key] = value
            return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


class UpdateSuggestionRequest(BaseModel):
    """Request model for updating suggestion status"""

    status: str = Field(..., pattern="^(pending|sent|approved|rejected)$")


class SuggestionStatsResponse(BaseModel):
    """Suggestion statistics response model"""

    total: int
    by_status: dict[str, int]
    by_context_type: dict[str, int]


class SuggestionListResponse(BaseModel):
    """List suggestions response model"""

    suggestions: list[SuggestionResponse]
    total: int
    limit: int
    offset: int


class InvalidSuggestionReportRequest(BaseModel):
    """Request model for reporting an invalid suggestion."""
    
    reason: str = Field(
        ...,
        description="Reason for reporting",
        pattern="^(device_not_found|not_relevant|already_automated|other)$",
    )
    feedback: str | None = Field(
        None,
        max_length=500,
        description="Optional user feedback",
    )


class InvalidSuggestionReportResponse(BaseModel):
    """Response model for invalid suggestion report."""
    
    success: bool
    report_id: str
    message: str


class InvalidReportItem(BaseModel):
    """Item in invalid reports list."""
    
    id: str
    suggestion_id: str
    reason: str
    feedback: str | None
    reported_at: str
    suggestion_prompt: str | None = None


class InvalidReportsListResponse(BaseModel):
    """Response for listing invalid reports."""
    
    reports: list[InvalidReportItem]
    total: int
    by_reason: dict[str, int]


# Dependency for storage service
def get_storage_service() -> SuggestionStorageService:
    """Get suggestion storage service instance"""
    return SuggestionStorageService()


@router.get("", response_model=SuggestionListResponse)
async def list_suggestions(
    status: str | None = Query(None, description="Filter by status (pending, sent, approved, rejected)"),
    context_type: str | None = Query(None, description="Filter by context type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    List suggestions with optional filters.

    Args:
        status: Filter by status
        context_type: Filter by context type
        limit: Maximum number of results
        offset: Offset for pagination
        db: Database session
        storage_service: Storage service instance

    Returns:
        List of suggestions with pagination info
    """
    try:
        suggestions = await storage_service.list_suggestions(
            status=status,
            context_type=context_type,
            limit=limit,
            offset=offset,
            db=db,
        )

        # Get total count using efficient COUNT query
        total = await storage_service.count_suggestions(
            status=status,
            context_type=context_type,
            db=db,
        )

        return SuggestionListResponse(
            suggestions=[SuggestionResponse.model_validate(s) for s in suggestions],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Failed to list suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list suggestions") from e


@router.get("/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    Get a suggestion by ID.

    Args:
        suggestion_id: Suggestion ID
        db: Database session
        storage_service: Storage service instance

    Returns:
        Suggestion details
    """
    try:
        suggestion = await storage_service.get_suggestion(suggestion_id, db=db)

        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        return SuggestionResponse.model_validate(suggestion)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get suggestion") from e


@router.patch("/{suggestion_id}", response_model=SuggestionResponse)
async def update_suggestion(
    suggestion_id: str,
    update_data: UpdateSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    Update suggestion status.

    Args:
        suggestion_id: Suggestion ID
        update_data: Update request data
        db: Database session
        storage_service: Storage service instance

    Returns:
        Updated suggestion
    """
    try:
        suggestion = await storage_service.update_suggestion_status(
            suggestion_id,
            status=update_data.status,
            db=db,
        )

        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        return SuggestionResponse.model_validate(suggestion)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update suggestion") from e


@router.delete("/{suggestion_id}")
async def delete_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    Delete a suggestion.

    Args:
        suggestion_id: Suggestion ID
        db: Database session
        storage_service: Storage service instance

    Returns:
        Success message
    """
    try:
        deleted = await storage_service.delete_suggestion(suggestion_id, db=db)

        if not deleted:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        return {"success": True, "message": "Suggestion deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete suggestion") from e


@router.post("/{suggestion_id}/send", response_model=SuggestionResponse)
async def send_suggestion_to_agent(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    Send a suggestion to the HA AI Agent Service.

    Args:
        suggestion_id: Suggestion ID
        db: Database session
        storage_service: Storage service instance

    Returns:
        Updated suggestion with agent response
    """
    try:
        # Get the suggestion
        suggestion = await storage_service.get_suggestion(suggestion_id, db=db)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        # Only send if status is pending
        if suggestion.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send suggestion with status '{suggestion.status}'. Only pending suggestions can be sent."
            )

        # Initialize HA Agent client
        agent_client = HAAgentClient()
        
        try:
            # Generate title from context type for conversation
            title = f"💡 {suggestion.context_type.title()} suggestion"
            
            # Build hidden context from automation_hints (if available)
            hidden_context = None
            automation_hints = suggestion.prompt_metadata.get("automation_hints") or \
                             suggestion.context_metadata.get("automation_hints")
            if automation_hints:
                hidden_context = {
                    "context_type": suggestion.context_type,
                    **automation_hints
                }
                logger.debug(f"Passing hidden context to HA Agent: {hidden_context}")
            
            # Send message to HA AI Agent Service
            agent_response = await agent_client.send_message(
                suggestion.prompt,
                title=title,
                source="proactive",
                hidden_context=hidden_context,
            )

            if agent_response:
                # Update suggestion with agent response and mark as sent
                updated_suggestion = await storage_service.update_suggestion_status(
                    suggestion_id,
                    status="sent",
                    agent_response={
                        "message": agent_response.get("message", ""),
                        "conversation_id": agent_response.get("conversation_id"),
                        "tool_calls": agent_response.get("tool_calls", []),
                        "metadata": agent_response.get("metadata", {}),
                    },
                    db=db,
                )
                logger.info(f"Successfully sent suggestion {suggestion_id} to HA AI Agent")
                return SuggestionResponse.model_validate(updated_suggestion)
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to send suggestion to HA AI Agent Service"
                )
        finally:
            # Close the agent client
            await agent_client.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send suggestion {suggestion_id} to agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send suggestion: {str(e)}") from e


@router.get("/stats/summary", response_model=SuggestionStatsResponse)
async def get_suggestion_stats(
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    Get suggestion statistics.

    Args:
        db: Database session
        storage_service: Storage service instance

    Returns:
        Suggestion statistics
    """
    try:
        stats = await storage_service.get_suggestion_stats(db=db)
        return SuggestionStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get suggestion stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get suggestion stats") from e


# Global scheduler service reference (set by main.py)
_scheduler_service: Any = None


def set_scheduler_service(service: Any):
    """Set scheduler service reference (called from main.py)"""
    global _scheduler_service
    _scheduler_service = service


@router.post("/trigger")
async def trigger_suggestion_generation():
    """
    Manually trigger suggestion generation (for testing/debugging).

    Returns:
        Job results
    """
    try:
        if not _scheduler_service:
            raise HTTPException(status_code=503, detail="Scheduler service not available")

        results = await _scheduler_service.trigger_manual()
        return {"success": True, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger suggestion generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger suggestion generation") from e


@router.get("/debug/context")
async def debug_context_analysis():
    """
    Debug endpoint to analyze context without creating suggestions.

    Returns context analysis results to help diagnose why no suggestions are generated.
    """
    from ..services.context_analysis_service import ContextAnalysisService

    try:
        context_service = ContextAnalysisService()
        context_analysis = await context_service.analyze_all_context()
        await context_service.close()

        return {
            "success": True,
            "context_analysis": context_analysis,
            "summary": {
                "weather_available": context_analysis.get("weather", {}).get("available", False),
                "sports_available": context_analysis.get("sports", {}).get("available", False),
                "energy_available": context_analysis.get("energy", {}).get("available", False),
                "historical_available": context_analysis.get("historical_patterns", {}).get("available", False),
                "total_insights": len(context_analysis.get("summary", {}).get("insights", [])),
            },
        }
    except Exception as e:
        logger.error(f"Failed to analyze context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze context: {str(e)}") from e


@router.post("/sample")
async def create_sample_suggestion(
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    Create a sample suggestion for testing the UI.

    This endpoint is for debugging purposes to verify the API and UI integration.
    """
    try:
        # Create a sample suggestion
        suggestion = await storage_service.create_suggestion(
            prompt="It's going to be 90°F today. Should I create an automation to pre-cool your home before you arrive?",
            context_type="weather",
            quality_score=0.85,
            context_metadata={
                "weather": {
                    "available": True,
                    "current": {"temperature": 90, "condition": "sunny", "humidity": 45},
                },
                "timestamp": "2025-01-07T12:00:00Z",
            },
            prompt_metadata={
                "trigger": "high_temperature",
                "temperature": 90,
            },
            db=db,
        )

        return {
            "success": True,
            "message": "Sample suggestion created",
            "suggestion_id": suggestion.id,
        }
    except Exception as e:
        logger.error(f"Failed to create sample suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create sample suggestion: {str(e)}") from e


@router.post("/{suggestion_id}/report", response_model=InvalidSuggestionReportResponse)
async def report_invalid_suggestion(
    suggestion_id: str,
    report_data: InvalidSuggestionReportRequest,
    db: AsyncSession = Depends(get_db),
    storage_service: SuggestionStorageService = Depends(get_storage_service),
):
    """
    Report a suggestion as invalid.
    
    Allows users to report suggestions that reference non-existent devices,
    are not relevant, or have other issues.
    
    Epic: Proactive Suggestions Device Validation
    Story: User Feedback for Invalid Suggestions (P2)
    
    Args:
        suggestion_id: ID of the suggestion to report
        report_data: Report details (reason, feedback)
        db: Database session
        storage_service: Storage service instance
        
    Returns:
        Report confirmation with report ID
    """
    try:
        # Verify suggestion exists
        suggestion = await storage_service.get_suggestion(suggestion_id, db=db)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        # Create report
        report = InvalidSuggestionReport(
            suggestion_id=suggestion_id,
            reason=report_data.reason,
            feedback=report_data.feedback,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        logger.info(
            f"Invalid suggestion reported: suggestion_id={suggestion_id}, "
            f"reason={report_data.reason}, report_id={report.id}"
        )
        
        return InvalidSuggestionReportResponse(
            success=True,
            report_id=report.id,
            message=f"Thank you for reporting. This helps improve our suggestions.",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to report suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to submit report"
        ) from e


@router.get("/reports/invalid", response_model=InvalidReportsListResponse)
async def list_invalid_reports(
    reason: str | None = Query(None, description="Filter by reason"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """
    List invalid suggestion reports (admin endpoint).
    
    Returns reports with aggregated statistics by reason.
    
    Epic: Proactive Suggestions Device Validation
    
    Args:
        reason: Optional filter by reason
        limit: Maximum number of results
        db: Database session
        
    Returns:
        List of reports with statistics
    """
    try:
        # Build query
        query = select(InvalidSuggestionReport).order_by(
            InvalidSuggestionReport.reported_at.desc()
        ).limit(limit)
        
        if reason:
            query = query.where(InvalidSuggestionReport.reason == reason)
        
        result = await db.execute(query)
        reports = result.scalars().all()
        
        # Get totals by reason
        count_query = select(
            InvalidSuggestionReport.reason,
            sql_func.count().label("count")
        ).group_by(InvalidSuggestionReport.reason)
        
        count_result = await db.execute(count_query)
        by_reason = {row.reason: row.count for row in count_result.all()}
        
        # Get suggestion prompts for context
        report_items = []
        for report in reports:
            # Fetch suggestion prompt
            suggestion_query = select(Suggestion.prompt).where(
                Suggestion.id == report.suggestion_id
            )
            suggestion_result = await db.execute(suggestion_query)
            suggestion_prompt = suggestion_result.scalar_one_or_none()
            
            report_items.append(InvalidReportItem(
                id=report.id,
                suggestion_id=report.suggestion_id,
                reason=report.reason,
                feedback=report.feedback,
                reported_at=report.reported_at.isoformat() if report.reported_at else "",
                suggestion_prompt=suggestion_prompt[:100] + "..." if suggestion_prompt and len(suggestion_prompt) > 100 else suggestion_prompt,
            ))
        
        total = sum(by_reason.values())
        
        return InvalidReportsListResponse(
            reports=report_items,
            total=total,
            by_reason=by_reason,
        )
        
    except Exception as e:
        logger.error(f"Failed to list invalid reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to list reports"
        ) from e
