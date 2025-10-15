"""
Pattern Detection Router

Endpoints for detecting and managing automation patterns.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import logging
import time

from ..clients.data_api_client import DataAPIClient
from ..pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from ..database import get_db, store_patterns, get_patterns, get_pattern_stats, delete_old_patterns
from ..config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/patterns", tags=["Patterns"])

# Initialize clients
data_api_client = DataAPIClient(base_url=settings.data_api_url)


@router.post("/detect/time-of-day")
async def detect_time_of_day_patterns(
    days: int = Query(default=30, ge=1, le=90, description="Number of days of history to analyze"),
    min_occurrences: int = Query(default=3, ge=1, le=10, description="Minimum pattern occurrences"),
    min_confidence: float = Query(default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    limit: int = Query(default=10000, ge=100, le=50000, description="Maximum events to fetch"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Detect time-of-day patterns from historical data.
    
    This endpoint:
    1. Fetches historical events from Data API
    2. Runs time-of-day pattern detection using KMeans clustering
    3. Stores detected patterns in database
    4. Returns pattern summary and performance metrics
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting time-of-day pattern detection: days={days}, min_occurrences={min_occurrences}, min_confidence={min_confidence}")
        
        # Step 1: Fetch historical events
        logger.info(f"Fetching events from Data API (last {days} days)")
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)
        
        events_df = await data_api_client.fetch_events(
            start_time=start_dt,
            end_time=end_dt,
            limit=limit
        )
        
        if events_df.empty:
            return {
                "success": False,
                "message": f"No events found for the last {days} days",
                "data": {
                    "patterns_detected": 0,
                    "patterns_stored": 0,
                    "events_analyzed": 0
                }
            }
        
        # Ensure required columns
        if 'entity_id' in events_df.columns and 'device_id' not in events_df.columns:
            events_df['device_id'] = events_df['entity_id']
        
        logger.info(f"✅ Fetched {len(events_df)} events from {events_df['device_id'].nunique()} devices")
        
        # Step 2: Detect patterns
        logger.info("Running time-of-day pattern detection")
        detector = TimeOfDayPatternDetector(
            min_occurrences=min_occurrences,
            min_confidence=min_confidence
        )
        
        patterns = detector.detect_patterns(events_df)
        logger.info(f"✅ Detected {len(patterns)} patterns")
        
        # Step 3: Store patterns in database
        patterns_stored = 0
        if patterns:
            logger.info(f"Storing {len(patterns)} patterns in database")
            patterns_stored = await store_patterns(db, patterns)
            logger.info(f"✅ Stored {patterns_stored} patterns")
        
        # Step 4: Get summary
        pattern_summary = detector.get_pattern_summary(patterns)
        
        # Calculate performance metrics
        duration = time.time() - start_time
        
        logger.info(f"✅ Pattern detection completed in {duration:.2f}s")
        
        return {
            "success": True,
            "message": f"Detected and stored {patterns_stored} time-of-day patterns",
            "data": {
                "patterns_detected": len(patterns),
                "patterns_stored": patterns_stored,
                "events_analyzed": len(events_df),
                "unique_devices": int(events_df['device_id'].nunique()),
                "time_range": {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "days": days
                },
                "summary": pattern_summary,
                "performance": {
                    "duration_seconds": round(duration, 2),
                    "events_per_second": int(len(events_df) / duration) if duration > 0 else 0
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Pattern detection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pattern detection failed: {str(e)}"
        )


@router.get("/list")
async def list_patterns(
    pattern_type: Optional[str] = Query(default=None, description="Filter by pattern type"),
    device_id: Optional[str] = Query(default=None, description="Filter by device ID"),
    min_confidence: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum patterns to return"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List detected patterns with optional filters.
    """
    try:
        patterns = await get_patterns(
            db,
            pattern_type=pattern_type,
            device_id=device_id,
            min_confidence=min_confidence,
            limit=limit
        )
        
        # Convert to dictionaries
        patterns_list = [
            {
                "id": p.id,
                "pattern_type": p.pattern_type,
                "device_id": p.device_id,
                "metadata": p.pattern_metadata,
                "confidence": p.confidence,
                "occurrences": p.occurrences,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in patterns
        ]
        
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
        )


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get pattern statistics.
    """
    try:
        stats = await get_pattern_stats(db)
        
        return {
            "success": True,
            "data": stats,
            "message": "Pattern statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get pattern stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pattern stats: {str(e)}"
        )


@router.delete("/cleanup")
async def cleanup_old_patterns(
    days_old: int = Query(default=30, ge=7, le=365, description="Delete patterns older than this many days"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Delete old patterns to manage database size.
    """
    try:
        deleted_count = await delete_old_patterns(db, days_old=days_old)
        
        return {
            "success": True,
            "data": {
                "deleted_count": deleted_count,
                "days_old": days_old
            },
            "message": f"Deleted {deleted_count} patterns older than {days_old} days"
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup patterns: {str(e)}"
        )


@router.on_event("shutdown")
async def shutdown_pattern_client():
    """Close Data API client on shutdown"""
    await data_api_client.close()
    logger.info("Pattern detection client closed")

