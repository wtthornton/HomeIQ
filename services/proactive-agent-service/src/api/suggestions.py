"""
Suggestions API Router for Proactive Agent Service

REST API endpoints for managing proactive automation suggestions.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.suggestion_storage_service import SuggestionStorageService
from ..models import Suggestion

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
