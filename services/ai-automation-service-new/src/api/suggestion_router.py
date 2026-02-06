"""
Suggestion Generation Router

Epic 39, Story 39.10: Automation Service Foundation
Extracted from ai-automation-service for independent scaling.
"""

import logging
from typing import Any

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
    suggestion_svc: SuggestionService = Depends(get_suggestion_service)
) -> dict[str, Any]:
    """
    Generate automation suggestions from patterns.
    """
    suggestions = await suggestion_svc.generate_suggestions(
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
    suggestion_svc: SuggestionService = Depends(get_suggestion_service)
) -> dict[str, Any]:
    """
    List automation suggestions with filtering and pagination.
    """
    result = await suggestion_svc.list_suggestions(
        limit=limit,
        offset=offset,
        status=status
    )
    return result


@router.get("/usage/stats")
@handle_route_errors("get usage stats")
async def get_usage_stats(
    suggestion_svc: SuggestionService = Depends(get_suggestion_service)
) -> dict[str, Any]:
    """
    Get suggestion usage statistics.
    """
    stats = await suggestion_svc.get_usage_stats()
    return stats


@router.post("/refresh")
@handle_route_errors("refresh suggestions")
async def refresh_suggestions(
    db: DatabaseSession,
    suggestion_svc: SuggestionService = Depends(get_suggestion_service)
) -> dict[str, Any]:
    """
    Manually trigger suggestion generation.

    Generates new automation suggestions and stores them in the database
    with status="draft" for user review.

    Returns:
        {
            "success": True/False,
            "message": "Status message",
            "count": <number_of_suggestions_generated>,
            "suggestions": [<suggestion_dicts>],
            "error_code": "<error_code>" (if failed)
        }
    """
    try:
        # Generate suggestions synchronously (Option 1 from analysis)
        # Default: 10 suggestions, 30 days of data
        suggestions = await suggestion_svc.generate_suggestions(limit=10, days=30)

        if len(suggestions) == 0:
            return {
                "success": False,
                "message": "No suggestions generated. Possible reasons: No events available (need at least 100 events), Data API not responding, or OpenAI API key not configured. Check service logs for details.",
                "count": 0,
                "suggestions": [],
                "error_code": "NO_SUGGESTIONS_GENERATED"
            }

        return {
            "success": True,
            "message": f"Suggestion generation completed. Generated {len(suggestions)} suggestions.",
            "count": len(suggestions),
            "suggestions": suggestions
        }
    except ValueError as e:
        # Handle validation errors (e.g., OpenAI not configured, Data API errors)
        error_msg = str(e)
        logger.error(f"Suggestion generation failed: {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "count": 0,
            "suggestions": [],
            "error_code": "VALIDATION_ERROR"
        }
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error during suggestion generation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "count": 0,
            "suggestions": [],
            "error_code": "GENERATION_ERROR"
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


@router.get("/health")
@handle_route_errors("health check")
async def get_suggestions_health(
    suggestion_svc: SuggestionService = Depends(get_suggestion_service)
) -> dict[str, Any]:
    """
    Health check endpoint for suggestion generation prerequisites.

    Checks:
    - Database connectivity
    - Data API connectivity
    - Event count availability
    - OpenAI API key configuration

    Returns:
        {
            "healthy": True/False,
            "checks": {
                "database": True/False,
                "data_api": True/False,
                "openai": True/False,
                "events_available": True/False
            },
            "details": {
                "event_count": <number>,
                "can_generate": <number_of_suggestions>,
                "openai_configured": True/False
            },
            "issues": ["<issue1>", "<issue2>"]
        }
    """
    issues = []
    checks = {
        "database": False,
        "data_api": False,
        "openai": False,
        "events_available": False
    }
    details = {
        "event_count": 0,
        "can_generate": 0,
        "openai_configured": False
    }

    # Check database connectivity
    try:
        from sqlalchemy import select, func
        count_query = select(func.count()).select_from(Suggestion)
        result = await suggestion_svc.db.execute(count_query)
        total_suggestions = result.scalar() or 0
        checks["database"] = True
    except Exception as e:
        issues.append(f"Database connection failed: {str(e)}")

    # Check OpenAI configuration
    if suggestion_svc.openai_client and suggestion_svc.openai_client.client:
        checks["openai"] = True
        details["openai_configured"] = True
    else:
        issues.append("OpenAI API key not configured")

    # Check Data API connectivity and event count
    try:
        if await suggestion_svc.data_api_client.health_check():
            checks["data_api"] = True
            # Try to fetch events (with small limit for health check)
            try:
                events = await suggestion_svc.data_api_client.fetch_events(limit=100)
                event_count = len(events) if events else 0
                details["event_count"] = event_count
                details["can_generate"] = event_count // 100

                if event_count >= 100:
                    checks["events_available"] = True
                else:
                    issues.append(f"Insufficient events: {event_count} available, need at least 100 (can generate {details['can_generate']} suggestions)")
            except Exception as e:
                issues.append(f"Failed to fetch events from Data API: {str(e)}")
        else:
            issues.append("Data API service not responding")
    except Exception as e:
        issues.append(f"Data API health check failed: {str(e)}")

    healthy = all(checks.values())

    return {
        "healthy": healthy,
        "checks": checks,
        "details": details,
        "issues": issues,
        "message": "All checks passed" if healthy else f"Found {len(issues)} issue(s). See 'issues' array for details."
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
    from_yaml: bool = Query(False, description="Rebuild from YAML instead of description"),
    rebuilder: JSONRebuilder = Depends(get_json_rebuilder)
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
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    query_svc: JSONQueryService = Depends(get_json_query_service)
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
    matching_automations = query_svc.query(automations, filters)

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
