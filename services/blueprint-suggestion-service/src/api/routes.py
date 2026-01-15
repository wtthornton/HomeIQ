"""API routes for Blueprint Suggestion Service."""

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import check_schema_version, get_db
from ..models.suggestion import BlueprintSuggestion
from ..services.suggestion_service import SuggestionService
from .schemas import (
    AcceptSuggestionResponse,
    BlueprintSuggestionListResponse,
    BlueprintSuggestionResponse,
    DeviceMatch,
    GenerateSuggestionsRequest,
    GenerateSuggestionsResponse,
    SuggestionStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/blueprint-suggestions", tags=["blueprint-suggestions"])

service = SuggestionService()


def _suggestion_to_response(suggestion: BlueprintSuggestion) -> BlueprintSuggestionResponse:
    """Convert database model to response schema."""
    # Use stored blueprint name/description, or empty string if not available
    blueprint_name = suggestion.blueprint_name or ""
    blueprint_description = suggestion.blueprint_description
    
    return BlueprintSuggestionResponse(
        id=suggestion.id,
        blueprint_id=suggestion.blueprint_id,
        blueprint_name=blueprint_name,
        blueprint_description=blueprint_description,
        suggestion_score=suggestion.suggestion_score,
        matched_devices=[
            DeviceMatch(**device) if isinstance(device, dict) else DeviceMatch(**device)
            for device in suggestion.matched_devices
        ],
        use_case=suggestion.use_case,
        status=suggestion.status,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
        accepted_at=suggestion.accepted_at,
        declined_at=suggestion.declined_at,
        conversation_id=suggestion.conversation_id,
    )


@router.delete("/delete-all", name="delete_all_suggestions")
async def delete_all_suggestions(db: AsyncSession = Depends(get_db)):
    """
    Delete all blueprint suggestions from the database.
    
    This endpoint removes all suggestions regardless of status.
    Use with caution - this action cannot be undone.
    """
    try:
        from sqlalchemy import delete
        
        delete_stmt = delete(BlueprintSuggestion)
        result = await db.execute(delete_stmt)
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} suggestions")
        
        return {"deleted": deleted_count, "status": "success"}
    except Exception as e:
        logger.error(f"Delete all suggestions failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete all suggestions failed: {str(e)}")


@router.get("/health/schema")
async def check_schema_health(db: AsyncSession = Depends(get_db)):
    """
    Check if database schema is up to date.
    
    Returns schema health status including:
    - schema_version: Current schema version
    - schema_ok: Whether schema matches model
    - status: Overall health status
    """
    try:
        schema_ok = await check_schema_version(db)
        return {
            "schema_version": "1.0.0",
            "schema_ok": schema_ok,
            "status": "healthy" if schema_ok else "schema_mismatch",
            "message": "Schema is up to date" if schema_ok else "Schema mismatch detected - migrations may be required"
        }
    except Exception as e:
        logger.error(f"Schema health check failed: {e}", exc_info=True)
        return {
            "schema_version": "unknown",
            "schema_ok": False,
            "status": "error",
            "message": f"Failed to check schema: {str(e)}"
        }


@router.get("/suggestions", response_model=BlueprintSuggestionListResponse)
async def get_suggestions(
    min_score: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    use_case: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    blueprint_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get blueprint suggestions with filters.
    
    Query params:
    - min_score: Minimum suggestion score (0.0-1.0)
    - use_case: Filter by use case
    - status: Filter by status (pending, accepted, declined)
    - blueprint_id: Filter by blueprint ID
    - limit: Maximum results (1-200)
    - offset: Pagination offset
    """
    try:
        # Check schema before querying
        schema_ok = await check_schema_version(db)
        if not schema_ok:
            logger.error("Schema mismatch detected - required columns may be missing")
            raise HTTPException(
                status_code=503,
                detail="Database schema mismatch. Please restart the service to run migrations or contact support."
            )
        
        suggestions, total = await service.get_suggestions(
            db=db,
            min_score=min_score,
            use_case=use_case,
            status=status,
            blueprint_id=blueprint_id,
            limit=limit,
            offset=offset,
        )
        
        # Enrich suggestions with blueprint details if name/description missing
        from ..clients.blueprint_client import BlueprintClient
        
        response_suggestions = []
        async with BlueprintClient() as blueprint_client:
            for s in suggestions:
                # If blueprint name is missing, fetch from blueprint service (fallback)
                if not s.blueprint_name:
                    try:
                        blueprint_data = await blueprint_client.get_blueprint(s.blueprint_id)
                        if blueprint_data:
                            s.blueprint_name = blueprint_data.get("name", "")
                            s.blueprint_description = blueprint_data.get("description")
                            # Update in database for future requests
                            db.add(s)
                    except Exception as e:
                        logger.warning(f"Failed to fetch blueprint {s.blueprint_id} for enrichment: {e}")
                
                response_suggestions.append(_suggestion_to_response(s))
        
        await db.commit()  # Commit any updates from enrichment
        
        return BlueprintSuggestionListResponse(
            suggestions=response_suggestions,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Get suggestions failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get suggestions failed: {str(e)}")


@router.post("/{suggestion_id}/accept", response_model=AcceptSuggestionResponse)
async def accept_suggestion(
    suggestion_id: str,
    conversation_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a blueprint suggestion.
    
    This will:
    - Update suggestion status to 'accepted'
    - Set accepted_at timestamp
    - Optionally link to a conversation_id
    """
    try:
        suggestion = await service.accept_suggestion(
            db=db,
            suggestion_id=suggestion_id,
            conversation_id=conversation_id,
        )
        
        if not suggestion:
            raise HTTPException(status_code=404, detail=f"Suggestion not found: {suggestion_id}")
        
        # Fetch blueprint details for response
        from ..clients.blueprint_client import BlueprintClient
        
        blueprint_data = None
        async with BlueprintClient() as blueprint_client:
            blueprint_data = await blueprint_client.get_blueprint(suggestion.blueprint_id)
        
        return AcceptSuggestionResponse(
            id=suggestion.id,
            status=suggestion.status,
            blueprint_id=suggestion.blueprint_id,
            blueprint_yaml=blueprint_data.get("yaml_content") if blueprint_data else None,
            blueprint_inputs=blueprint_data.get("blueprint_inputs", {}) if blueprint_data else {},
            matched_devices=[
                DeviceMatch(**device) if isinstance(device, dict) else DeviceMatch(**device)
                for device in suggestion.matched_devices
            ],
            suggestion_score=suggestion.suggestion_score,
            conversation_id=suggestion.conversation_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Accept suggestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Accept suggestion failed: {str(e)}")


@router.post("/{suggestion_id}/decline")
async def decline_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Decline a blueprint suggestion.
    
    This will:
    - Update suggestion status to 'declined'
    - Set declined_at timestamp
    """
    try:
        suggestion = await service.decline_suggestion(
            db=db,
            suggestion_id=suggestion_id,
        )
        
        if not suggestion:
            raise HTTPException(status_code=404, detail=f"Suggestion not found: {suggestion_id}")
        
        return {"id": suggestion.id, "status": suggestion.status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Decline suggestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Decline suggestion failed: {str(e)}")


@router.get("/stats", response_model=SuggestionStatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get statistics about blueprint suggestions.
    
    Returns:
    - Total suggestions count
    - Counts by status (pending, accepted, declined)
    - Score statistics (average, min, max)
    """
    try:
        stats = await service.get_stats(db=db)
        return SuggestionStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Get stats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get stats failed: {str(e)}")


@router.post("/generate", response_model=GenerateSuggestionsResponse)
async def generate_suggestions(
    request: GenerateSuggestionsRequest = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate blueprint suggestions with user-defined parameters.
    
    This endpoint generates suggestions based on:
    - Device selection (specific devices or all)
    - Complexity filter (simple, medium, high, or all)
    - Use case filter (convenience, security, energy, comfort, or all)
    - Quality threshold
    - Number of suggestions to generate
    
    Note: This may take a while depending on the parameters.
    """
    try:
        count = await service.generate_suggestions_with_params(
            db=db,
            device_ids=request.device_ids,
            complexity=request.complexity,
            use_case=request.use_case,
            min_score=request.min_score,
            max_suggestions=request.max_suggestions,
            min_quality_score=request.min_quality_score,
            domain=request.domain,
        )
        return GenerateSuggestionsResponse(
            generated=count,
            status="success",
            message=f"Generated {count} suggestions based on your parameters",
        )
    except Exception as e:
        logger.error(f"Generate suggestions failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generate suggestions failed: {str(e)}")
