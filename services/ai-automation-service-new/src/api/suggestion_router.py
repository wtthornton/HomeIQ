"""
Suggestion Generation Router

Epic 39, Story 39.10: Automation Service Foundation
Extracted from ai-automation-service for independent scaling.
"""

import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..api.dependencies import (
    DatabaseSession,
    get_automation_combiner,
    get_json_query_service,
    get_json_rebuilder,
    get_json_verification_service,
    get_suggestion_service,
)
from ..api.error_handlers import handle_route_errors
from ..database import get_db
from ..database.models import Suggestion
from ..services.automation_combiner import AutomationCombiner
from ..services.json_query_service import JSONQueryService
from ..services.json_rebuilder import JSONRebuilder
from ..services.json_verification_service import JSONVerificationService
from ..services.suggestion_service import SuggestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


class GenerateRequest(BaseModel):
    """Request to generate suggestions."""
    pattern_ids: list[str] | None = None
    days: int = 30
    limit: int = 10


@router.post("/generate")
@handle_route_errors("generate suggestions")
async def generate_suggestions(
    request: GenerateRequest,
    db: DatabaseSession,
    service: Annotated[SuggestionService, Depends(get_suggestion_service)]
) -> dict[str, Any]:
    """
    Generate automation suggestions from patterns.
    """
    suggestions = await service.generate_suggestions(
        pattern_ids=request.pattern_ids,
        days=request.days,
        limit=request.limit
    )
    return {
        "success": True,
        "suggestions": suggestions,
        "count": len(suggestions)
    }


@router.get("/list")
@handle_route_errors("list suggestions")
async def list_suggestions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    db: DatabaseSession = None,
    service: Annotated[SuggestionService, Depends(get_suggestion_service)] = None
) -> dict[str, Any]:
    """
    List automation suggestions with filtering and pagination.
    """
    result = await service.list_suggestions(
        limit=limit,
        offset=offset,
        status=status
    )
    return result


@router.get("/usage/stats")
@handle_route_errors("get usage stats")
async def get_usage_stats(
    service: Annotated[SuggestionService, Depends(get_suggestion_service)]
) -> dict[str, Any]:
    """
    Get suggestion usage statistics.
    """
    stats = await service.get_usage_stats()
    return stats


@router.post("/refresh")
async def refresh_suggestions(
    db: DatabaseSession
) -> dict[str, Any]:
    """
    Manually trigger suggestion refresh.
    
    Note: Full implementation will be migrated from ai-automation-service
    in Story 39.10 completion phase.
    """
    # TODO: Epic 39, Story 39.10 - Migrate suggestion refresh functionality from archived service
    # Current: Placeholder endpoint
    # Future: Background job processing, status tracking, progress reporting
    return {
        "message": "Refresh endpoint - implementation in progress",
        "status": "queued"
    }


@router.get("/refresh/status")
async def get_refresh_status(
    db: DatabaseSession
) -> dict[str, Any]:
    """
    Get status of suggestion refresh operation.
    
    Note: Full implementation will be migrated from ai-automation-service
    in Story 39.10 completion phase.
    """
    # TODO: Epic 39, Story 39.10 - Migrate refresh status tracking from archived service
    # Current: Placeholder endpoint
    # Future: Real-time status updates, job queue management
    return {
        "status": "idle",
        "message": "Refresh status endpoint - implementation in progress"
    }


@router.get("/{suggestion_id}/json")
@handle_route_errors("get suggestion JSON")
async def get_suggestion_json(
    suggestion_id: int,
    db: DatabaseSession
) -> dict[str, Any]:
    """
    Get HomeIQ JSON Automation for a suggestion.
    
    Returns the stored automation_json if available, otherwise returns error.
    """
    suggestion = await db.get(Suggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if not suggestion.automation_json:
        raise HTTPException(
            status_code=404,
            detail="HomeIQ JSON not available for this suggestion"
        )
    
    return {
        "success": True,
        "suggestion_id": suggestion_id,
        "automation_json": suggestion.automation_json,
        "json_schema_version": suggestion.json_schema_version,
        "ha_version": suggestion.ha_version
    }


@router.post("/{suggestion_id}/rebuild-json")
@handle_route_errors("rebuild suggestion JSON")
async def rebuild_suggestion_json(
    suggestion_id: int,
    db: DatabaseSession,
    rebuilder: Annotated[JSONRebuilder, Depends(get_json_rebuilder)],
    from_yaml: bool = Query(False, description="Rebuild from YAML instead of description")
) -> dict[str, Any]:
    """
    Rebuild HomeIQ JSON Automation for a suggestion.
    
    Can rebuild from YAML (if automation_yaml exists) or from description.
    """
    suggestion = await db.get(Suggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    try:
        if from_yaml and suggestion.automation_yaml:
            # Rebuild from YAML
            automation_json = await rebuilder.rebuild_from_yaml(
                yaml_content=suggestion.automation_yaml,
                suggestion_id=suggestion_id,
                pattern_id=suggestion.pattern_id
            )
        else:
            # Rebuild from description
            automation_json = await rebuilder.rebuild_from_description(
                description=suggestion.description or "",
                title=suggestion.title,
                suggestion_id=suggestion_id,
                pattern_id=suggestion.pattern_id
            )
        
        # Update suggestion with rebuilt JSON
        suggestion.automation_json = automation_json
        suggestion.json_schema_version = automation_json.get("version", "1.0.0")
        await db.commit()
        
        return {
            "success": True,
            "suggestion_id": suggestion_id,
            "automation_json": automation_json,
            "message": "JSON rebuilt successfully"
        }
    
    except Exception as e:
        logger.error(f"Failed to rebuild JSON for suggestion {suggestion_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rebuild JSON: {e}")


@router.post("/query")
@handle_route_errors("query suggestions")
async def query_suggestions(
    filters: dict[str, Any],
    db: DatabaseSession,
    query_service: Annotated[JSONQueryService, Depends(get_json_query_service)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> dict[str, Any]:
    """
    Query suggestions by JSON properties.
    
    Filters can include:
    - device_id: str | list[str]
    - entity_id: str | list[str]
    - area_id: str | list[str]
    - pattern_type: str
    - use_case: str (energy, comfort, security, convenience)
    - complexity: str (low, medium, high)
    - min_energy_impact_w: float
    - requires_confirmation: bool
    - tags: str | list[str]
    """
    # Fetch all suggestions with JSON
    from sqlalchemy import select
    stmt = select(Suggestion).where(Suggestion.automation_json.isnot(None))
    result = await db.execute(stmt)
    suggestions = result.scalars().all()
    
    # Extract JSON from suggestions
    automations = [s.automation_json for s in suggestions if s.automation_json]
    
    # Query using JSONQueryService
    matching_automations = query_service.query(automations, filters)
    
    # Apply pagination
    total = len(matching_automations)
    paginated = matching_automations[offset:offset + limit]
    
    # Map back to suggestions
    automation_aliases = {a.get("alias"): a for a in paginated}
    matching_suggestions = [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "automation_json": s.automation_json,
            "status": s.status
        }
        for s in suggestions
        if s.automation_json and s.automation_json.get("alias") in automation_aliases
    ]
    
    return {
        "success": True,
        "suggestions": matching_suggestions,
        "count": len(matching_suggestions),
        "total": total,
        "limit": limit,
        "offset": offset
    }

