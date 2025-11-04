"""
Synergy Opportunity Router

API endpoints for browsing and querying synergy opportunities.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.8: Frontend Synergy Tab
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import logging

from ..database import get_db
from ..database.crud import get_synergy_opportunities, get_synergy_stats
from ..database.models import SynergyOpportunity

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/synergies", tags=["Synergies"])


@router.get("/")
async def list_synergies(
    synergy_type: Optional[str] = Query(default=None, description="Filter by synergy type"),
    min_confidence: float = Query(default=0.7, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum results"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List synergy opportunities.
    
    Story AI3.8: Frontend Synergy Tab
    
    Returns:
        List of synergy opportunities with metadata
    """
    try:
        logger.info(f"Listing synergies: type={synergy_type}, min_confidence={min_confidence}")
        
        synergies = await get_synergy_opportunities(
            db,
            synergy_type=synergy_type,
            min_confidence=min_confidence,
            limit=limit
        )
        
        # Convert to dict format for JSON response
        synergies_list = [
            {
                'id': s.id,
                'synergy_id': s.synergy_id,
                'synergy_type': s.synergy_type,
                'device_ids': s.device_ids,
                'opportunity_metadata': s.opportunity_metadata,
                'impact_score': s.impact_score,
                'complexity': s.complexity,
                'confidence': s.confidence,
                'area': s.area,
                'created_at': s.created_at.isoformat() if s.created_at else None
            }
            for s in synergies
        ]
        
        return {
            'success': True,
            'data': {
                'synergies': synergies_list,
                'count': len(synergies_list)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list synergies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve synergies: {str(e)}")


@router.get("/stats")
async def synergy_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get synergy opportunity statistics.
    
    Story AI3.8: Frontend Synergy Tab
    
    Returns:
        Statistics about detected synergies
    """
    try:
        stats = await get_synergy_stats(db)
        
        return {
            'success': True,
            'data': stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get synergy stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


@router.get("/{synergy_id}")
async def get_synergy_detail(
    synergy_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get single synergy opportunity by ID.
    
    Story AI3.8: Frontend Synergy Tab
    
    Args:
        synergy_id: Synergy UUID
    
    Returns:
        Synergy opportunity details
    """
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(SynergyOpportunity).where(SynergyOpportunity.synergy_id == synergy_id)
        )
        synergy = result.scalar_one_or_none()
        
        if not synergy:
            raise HTTPException(status_code=404, detail=f"Synergy {synergy_id} not found")
        
        return {
            'success': True,
            'data': {
                'synergy': {
                    'id': synergy.id,
                    'synergy_id': synergy.synergy_id,
                    'synergy_type': synergy.synergy_type,
                    'device_ids': synergy.device_ids,
                    'opportunity_metadata': synergy.opportunity_metadata,
                    'impact_score': synergy.impact_score,
                    'complexity': synergy.complexity,
                    'confidence': synergy.confidence,
                    'area': synergy.area,
                    'created_at': synergy.created_at.isoformat() if synergy.created_at else None
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get synergy {synergy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve synergy: {str(e)}")

