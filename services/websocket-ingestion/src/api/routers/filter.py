"""
Entity filter router for websocket-ingestion service.
"""

from fastapi import APIRouter, Request

from ...api.models import FilterStatsResponse

router = APIRouter(prefix="/api/v1/filter", tags=["filter"])


@router.get("/stats", response_model=FilterStatsResponse)
async def get_filter_stats(request: Request):
    """
    Get entity filter statistics.
    
    Returns statistics about the entity filter if configured.
    """
    service = request.app.state.service
    if not service.entity_filter:
        return {
            "enabled": False,
            "message": "Entity filter not configured"
        }
    
    stats = service.entity_filter.get_statistics()
    return {
        "enabled": True,
        "statistics": stats
    }

