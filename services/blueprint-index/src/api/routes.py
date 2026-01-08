"""API routes for Blueprint Index Service."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..search.search_engine import BlueprintSearchEngine
from .schemas import (
    BlueprintResponse,
    BlueprintSearchRequest,
    BlueprintSearchResponse,
    BlueprintSummary,
    IndexingJobResponse,
    IndexingStatusResponse,
    PatternMatchRequest,
    PatternMatchResponse,
    TriggerIndexingRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/blueprints", tags=["blueprints"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "blueprint-index"}


@router.get("/status", response_model=IndexingStatusResponse)
async def get_indexing_status(db: AsyncSession = Depends(get_db)):
    """
    Get current indexing status and statistics.
    """
    try:
        search_engine = BlueprintSearchEngine(db)
        status = await search_engine.get_indexing_status()
        return status
        
    except Exception as e:
        logger.error(f"Get status failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get status failed: {str(e)}")


@router.get("/search", response_model=BlueprintSearchResponse)
async def search_blueprints(
    domains: Optional[str] = Query(default=None, description="Comma-separated required domains"),
    device_classes: Optional[str] = Query(default=None, description="Comma-separated device classes"),
    trigger_domain: Optional[str] = Query(default=None),
    action_domain: Optional[str] = Query(default=None),
    use_case: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None, description="Text search query"),
    min_quality_score: float = Query(default=0.5, ge=0.0, le=1.0),
    min_community_rating: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="quality_score"),
    sort_order: str = Query(default="desc"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search blueprints by device requirements, use case, and text query.
    
    Examples:
    - GET /api/blueprints/search?domains=binary_sensor,light&device_classes=motion
    - GET /api/blueprints/search?use_case=security&min_quality_score=0.7
    - GET /api/blueprints/search?query=motion%20light
    """
    try:
        search_engine = BlueprintSearchEngine(db)
        
        # Parse comma-separated values
        domain_list = domains.split(",") if domains else None
        device_class_list = device_classes.split(",") if device_classes else None
        
        request = BlueprintSearchRequest(
            domains=domain_list,
            device_classes=device_class_list,
            trigger_domain=trigger_domain,
            action_domain=action_domain,
            use_case=use_case,
            query=query,
            min_quality_score=min_quality_score,
            min_community_rating=min_community_rating,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        results = await search_engine.search(request)
        return results
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/by-pattern", response_model=PatternMatchResponse)
async def find_by_pattern(
    trigger_domain: str = Query(..., description="Trigger entity domain"),
    action_domain: str = Query(..., description="Action entity domain"),
    trigger_device_class: Optional[str] = Query(default=None),
    action_device_class: Optional[str] = Query(default=None),
    min_quality_score: float = Query(default=0.7, ge=0.0, le=1.0),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Find blueprints matching a trigger-action pattern.
    
    This endpoint is optimized for synergy-to-blueprint matching.
    
    Examples:
    - GET /api/blueprints/by-pattern?trigger_domain=binary_sensor&action_domain=light
    - GET /api/blueprints/by-pattern?trigger_domain=binary_sensor&trigger_device_class=motion&action_domain=light
    """
    try:
        search_engine = BlueprintSearchEngine(db)
        
        request = PatternMatchRequest(
            trigger_domain=trigger_domain,
            action_domain=action_domain,
            trigger_device_class=trigger_device_class,
            action_device_class=action_device_class,
            min_quality_score=min_quality_score,
            limit=limit,
        )
        
        results = await search_engine.find_by_pattern(request)
        return results
        
    except Exception as e:
        logger.error(f"Pattern match failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pattern match failed: {str(e)}")


@router.get("/{blueprint_id}", response_model=BlueprintResponse)
async def get_blueprint(
    blueprint_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full blueprint details by ID.
    """
    try:
        search_engine = BlueprintSearchEngine(db)
        blueprint = await search_engine.get_by_id(blueprint_id)
        
        if not blueprint:
            raise HTTPException(status_code=404, detail=f"Blueprint not found: {blueprint_id}")
        
        return blueprint
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get blueprint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get blueprint failed: {str(e)}")


@router.post("/index/refresh", response_model=IndexingJobResponse)
async def trigger_indexing(
    request: TriggerIndexingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a new indexing job.
    
    Job types:
    - 'github': Index from GitHub repositories
    - 'discourse': Index from Home Assistant Community forums
    - 'full': Index from all sources
    """
    try:
        # Import here to avoid circular imports
        from ..indexer.index_manager import IndexManager
        
        index_manager = IndexManager(db)
        job = await index_manager.start_indexing_job(
            job_type=request.job_type,
            force_refresh=request.force_refresh
        )
        
        return IndexingJobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            total_items=job.total_items,
            processed_items=job.processed_items,
            indexed_items=job.indexed_items,
            failed_items=job.failed_items,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
        
    except Exception as e:
        logger.error(f"Trigger indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trigger indexing failed: {str(e)}")


@router.get("/index/job/{job_id}", response_model=IndexingJobResponse)
async def get_indexing_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific indexing job.
    """
    try:
        from ..indexer.index_manager import IndexManager
        
        index_manager = IndexManager(db)
        job = await index_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        return IndexingJobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            total_items=job.total_items,
            processed_items=job.processed_items,
            indexed_items=job.indexed_items,
            failed_items=job.failed_items,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get job failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get job failed: {str(e)}")
