"""
API Routes for Automation Miner

Implements corpus query endpoints.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..miner.database import get_db_session
from ..miner.repository import CorpusRepository
from .schemas import AutomationResponse, SearchResponse, StatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["corpus"])


@router.get("/corpus/search", response_model=SearchResponse)
async def search_corpus(
    device: str | None = Query(None, description="Filter by device type (e.g., 'light', 'motion_sensor')"),
    integration: str | None = Query(None, description="Filter by integration (e.g., 'mqtt', 'zigbee2mqtt')"),
    use_case: str | None = Query(None, description="Filter by use case (energy/comfort/security/convenience)"),
    min_quality: float = Query(0.7, ge=0.0, le=1.0, description="Minimum quality score"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Search community automation corpus
    
    Query automations by device type, integration, use case, and quality threshold.
    
    Example:
        GET /api/automation-miner/corpus/search?device=motion_sensor&use_case=security&min_quality=0.8
    """
    logger.info(
        f"Search request: device={device}, integration={integration}, "
        f"use_case={use_case}, min_quality={min_quality}, limit={limit}"
    )

    repo = CorpusRepository(db)

    filters = {
        'device': device,
        'integration': integration,
        'use_case': use_case,
        'min_quality': min_quality,
        'limit': limit
    }

    try:
        automations = await repo.search(filters)

        logger.info(f"Search returned {len(automations)} results")

        return SearchResponse(
            automations=automations,
            count=len(automations),
            filters=filters
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corpus/blueprints", response_model=SearchResponse)
async def search_blueprints(
    device: str | None = Query(None, description="Filter by device type (e.g., 'light', 'motion_sensor')"),
    integration: str | None = Query(None, description="Filter by integration (e.g., 'mqtt', 'zigbee2mqtt')"),
    use_case: str | None = Query(None, description="Filter by use case (energy/comfort/security/convenience)"),
    min_quality: float = Query(0.7, ge=0.0, le=1.0, description="Minimum quality score"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Search for Home Assistant automation blueprints
    
    Returns only automations that are blueprints (have blueprint metadata).
    Blueprints are reusable automation templates with configurable inputs.
    
    Example:
        GET /api/automation-miner/corpus/blueprints?device=light&use_case=comfort&min_quality=0.8
    """
    logger.info(
        f"Blueprint search request: device={device}, integration={integration}, "
        f"use_case={use_case}, min_quality={min_quality}, limit={limit}"
    )

    repo = CorpusRepository(db)

    filters = {
        'device': device,
        'integration': integration,
        'use_case': use_case,
        'min_quality': min_quality,
        'limit': limit
    }

    try:
        blueprints = await repo.search_blueprints(filters)

        logger.info(f"Blueprint search returned {len(blueprints)} results")

        return SearchResponse(
            automations=blueprints,
            count=len(blueprints),
            filters=filters
        )

    except Exception as e:
        logger.error(f"Blueprint search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corpus/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get corpus statistics
    
    Returns:
        - Total automation count
        - Average quality score
        - Device type coverage
        - Integration coverage
        - Breakdown by use case and complexity
        - Blueprint count
        - Last crawl timestamp
    """
    logger.info("Stats request")

    repo = CorpusRepository(db)

    try:
        stats = await repo.get_stats()

        logger.info(
            f"Stats: {stats['total']} automations, "
            f"avg quality {stats['avg_quality']}, "
            f"blueprints: {stats.get('blueprint_count', 0)}"
        )

        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"Stats request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corpus/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get single automation by ID
    
    Args:
        automation_id: Database ID of automation
    
    Returns:
        Full automation details
    """
    logger.info(f"Get automation: {automation_id}")

    repo = CorpusRepository(db)

    try:
        automation = await repo.get_by_id(automation_id)

        if not automation:
            raise HTTPException(status_code=404, detail="Automation not found")

        return AutomationResponse(**automation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get automation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

