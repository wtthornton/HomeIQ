"""
Pattern Router - API endpoints for pattern data

Epic 39: Pattern Service API endpoints
Provides REST API for querying patterns from the database.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.patterns import get_patterns
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])


@router.get("/list")
async def list_patterns(
    pattern_type: str | None = Query(default=None, description="Filter by pattern type"),
    device_id: str | None = Query(default=None, description="Filter by device ID"),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum patterns to return"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    List detected patterns with optional filters.
    
    Returns patterns with safely parsed metadata.
    """
    try:
        patterns = await get_patterns(
            db,
            pattern_type=pattern_type,
            device_id=device_id,
            min_confidence=min_confidence,
            limit=limit
        )

        # Convert to dictionaries with safe JSON parsing
        # Handle both Pattern objects and dicts (from raw SQL queries)
        patterns_list = []
        for p in patterns:
            # Check if p is a dict (from raw SQL) or Pattern object
            if isinstance(p, dict):
                # Already a dictionary, use it directly but ensure metadata is parsed
                pattern_dict = p.copy()
                metadata = pattern_dict.get("pattern_metadata")
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse pattern_metadata for pattern {pattern_dict.get('id')}: {e}")
                        metadata = {}
                pattern_dict["metadata"] = metadata if metadata is not None else {}
                # Ensure all expected fields exist
                patterns_list.append({
                    "id": pattern_dict.get("id"),
                    "pattern_type": pattern_dict.get("pattern_type"),
                    "device_id": pattern_dict.get("device_id"),
                    "metadata": pattern_dict.get("metadata", {}),
                    "confidence": pattern_dict.get("confidence", 0.0),
                    "occurrences": pattern_dict.get("occurrences", 0),
                    "created_at": pattern_dict.get("created_at"),
                    "first_seen": pattern_dict.get("first_seen"),
                    "last_seen": pattern_dict.get("last_seen"),
                    "trend_direction": pattern_dict.get("trend_direction"),
                    "trend_strength": pattern_dict.get("trend_strength"),
                    "confidence_history_count": pattern_dict.get("confidence_history_count", 0)
                })
            else:
                # Pattern object, access attributes
                metadata = p.pattern_metadata
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse pattern_metadata for pattern {p.id}: {e}")
                        metadata = {}
                elif not isinstance(metadata, dict) and metadata is not None:
                    logger.warning(f"Unexpected pattern_metadata type for pattern {p.id}: {type(metadata)}")
                    metadata = {}
                elif metadata is None:
                    metadata = {}
                
                patterns_list.append({
                    "id": p.id,
                    "pattern_type": p.pattern_type,
                    "device_id": p.device_id,
                    "metadata": metadata,
                    "confidence": p.confidence,
                    "occurrences": p.occurrences,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    # History tracking fields
                    "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                    "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                    "trend_direction": p.trend_direction,
                    "trend_strength": p.trend_strength,
                    "confidence_history_count": p.confidence_history_count
                })

        return {
            "success": True,
            "data": {
                "patterns": patterns_list,
                "count": len(patterns_list)
            },
            "message": f"Retrieved {len(patterns_list)} patterns"
        }

    except Exception as e:
        logger.error(f"Failed to list patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list patterns: {str(e)}"
        ) from e


@router.get("/stats")
async def get_pattern_stats(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get pattern statistics.
    
    Returns summary statistics about detected patterns.
    """
    try:
        # Get all patterns for stats
        patterns = await get_patterns(db, limit=10000)
        
        total_patterns = len(patterns)
        pattern_types = {}
        total_confidence = 0.0
        total_occurrences = 0
        
        for p in patterns:
            # Handle both dict and Pattern object
            if isinstance(p, dict):
                pattern_type = p.get("pattern_type", "unknown")
                confidence = p.get("confidence", 0.0)
                occurrences = p.get("occurrences", 0)
            else:
                pattern_type = p.pattern_type
                confidence = p.confidence
                occurrences = p.occurrences
            
            pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
            total_confidence += confidence
            total_occurrences += occurrences
        
        avg_confidence = total_confidence / total_patterns if total_patterns > 0 else 0.0
        
        return {
            "success": True,
            "data": {
                "total_patterns": total_patterns,
                "pattern_types": pattern_types,
                "average_confidence": round(avg_confidence, 3),
                "total_occurrences": total_occurrences
            },
            "message": "Pattern statistics retrieved successfully"
        }
    
    except Exception as e:
        logger.error(f"Failed to get pattern stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pattern stats: {str(e)}"
        ) from e

