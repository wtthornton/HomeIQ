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

from ..clients.data_api_client import DataAPIClient
from ..crud.patterns import get_patterns
from ..database import get_db
from ..services.device_activity import DeviceActivityService
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])


@router.get("/list")
async def list_patterns(
    pattern_type: str | None = Query(default=None, description="Filter by pattern type"),
    device_id: str | None = Query(default=None, description="Filter by device ID"),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum patterns to return"),
    include_inactive: bool = Query(default=False, description="Include patterns for inactive devices"),
    activity_window_days: int = Query(default=30, ge=1, le=365, description="Activity window in days"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    List detected patterns with optional filters.
    
    Returns patterns with safely parsed metadata.
    Optionally filters by device activity (default: only active devices).
    """
    try:
        patterns = await get_patterns(
            db,
            pattern_type=pattern_type,
            device_id=device_id,
            min_confidence=min_confidence,
            limit=limit
        )
        
        # Filter by device activity if requested
        if not include_inactive:
            try:
                async with DataAPIClient(base_url=settings.data_api_url) as data_client:
                    activity_service = DeviceActivityService(data_api_client=data_client)
                    active_devices = await activity_service.get_active_devices(
                        window_days=activity_window_days,
                        data_api_client=data_client
                    )
                    
                    if active_devices:
                        # Convert patterns to dict format for filtering
                        patterns_dict = []
                        for p in patterns:
                            if isinstance(p, dict):
                                patterns_dict.append(p)
                            else:
                                patterns_dict.append({
                                    "id": p.id,
                                    "pattern_type": p.pattern_type,
                                    "device_id": p.device_id,
                                    "metadata": p.pattern_metadata,
                                    "confidence": p.confidence,
                                    "occurrences": p.occurrences,
                                })
                        
                        # Filter patterns by activity
                        filtered_patterns = activity_service.filter_patterns_by_activity(
                            patterns_dict,
                            active_devices
                        )
                        
                        # Convert back to original format (keep original objects if possible)
                        active_pattern_ids = {p.get("id") if isinstance(p, dict) else p.id for p in filtered_patterns}
                        patterns = [p for p in patterns if (p.id if hasattr(p, 'id') else p.get("id")) in active_pattern_ids]
                        
                        logger.info(
                            f"Filtered patterns by activity: {len(patterns_dict)} → {len(filtered_patterns)} "
                            f"(window: {activity_window_days} days)"
                        )
                    else:
                        logger.warning("No active devices found, returning all patterns")
            except Exception as e:
                logger.warning(f"Failed to filter patterns by activity: {e}, returning all patterns")
                # Continue with all patterns if filtering fails

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
        # Check for database corruption errors
        from ..database.integrity import (
            DatabaseIntegrityError,
            is_database_corruption_error,
            attempt_database_repair,
            check_database_integrity
        )
        from ..config import settings
        from pathlib import Path
        
        if is_database_corruption_error(e):
            logger.error(f"Database corruption detected while listing patterns: {e}", exc_info=True)
            # Attempt automatic repair
            try:
                db_path = Path(settings.database_path)
                repair_success = await attempt_database_repair(db_path)
                if repair_success:
                    logger.info("Database repair successful, retrying pattern list")
                    # Retry the query after repair
                    try:
                        patterns = await get_patterns(db, pattern_type=pattern_type, device_id=device_id, min_confidence=min_confidence, limit=limit)
                        # Return empty list with message if repair succeeded but no patterns
                        return {
                            "success": True,
                            "data": {
                                "patterns": [],
                                "count": 0
                            },
                            "message": "Database repaired successfully. Please refresh to see patterns."
                        }
                    except Exception as retry_error:
                        logger.error(f"Query failed after repair: {retry_error}")
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Database corruption detected. Repair attempted but query still fails. Please use the repair endpoint. Error: {str(e)}"
                        ) from e
                else:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Database corruption detected. Automatic repair failed. Please use the repair endpoint at /api/v1/patterns/repair. Error: {str(e)}"
                    ) from e
            except HTTPException:
                raise
            except Exception as repair_error:
                logger.error(f"Repair attempt failed: {repair_error}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Database corruption detected. Repair attempt failed. Please use the repair endpoint at /api/v1/patterns/repair. Error: {str(e)}"
                ) from e
        else:
            logger.error(f"Failed to list patterns: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list patterns: {str(e)}"
            ) from e


def _calculate_pattern_stats(patterns: list) -> dict[str, Any]:
    """
    Calculate statistics from a list of patterns.

    Extracted as a helper to eliminate duplication in error recovery branches.

    Args:
        patterns: List of Pattern objects or dicts

    Returns:
        Stats dictionary with total_patterns, by_type, avg_confidence, unique_devices, total_occurrences
    """
    total_patterns = len(patterns)
    by_type: dict[str, int] = {}
    total_confidence = 0.0
    total_occurrences = 0
    unique_device_set: set[str] = set()

    for p in patterns:
        if isinstance(p, dict):
            pattern_type = p.get("pattern_type", "unknown")
            confidence = p.get("confidence", 0.0)
            occurrences = p.get("occurrences", 0)
            device_id = p.get("device_id")
        else:
            pattern_type = p.pattern_type
            confidence = p.confidence
            occurrences = p.occurrences
            device_id = p.device_id

        by_type[pattern_type] = by_type.get(pattern_type, 0) + 1
        total_confidence += confidence
        total_occurrences += occurrences

        if device_id:
            individual_devices = device_id.split('+')
            unique_device_set.update(individual_devices)

    avg_confidence = total_confidence / total_patterns if total_patterns > 0 else 0.0

    return {
        "total_patterns": total_patterns,
        "by_type": by_type,
        "avg_confidence": round(avg_confidence, 3),
        "unique_devices": len(unique_device_set),
        "total_occurrences": total_occurrences
    }


@router.get("/stats")
async def get_pattern_stats(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get pattern statistics.

    Returns summary statistics about detected patterns.
    Handles database corruption gracefully with automatic recovery attempts.
    """
    from ..database.integrity import (
        DatabaseIntegrityError,
        is_database_corruption_error,
        check_database_integrity,
        attempt_database_repair
    )
    from ..config import settings
    from pathlib import Path

    _empty_stats = {
        "total_patterns": 0,
        "by_type": {},
        "avg_confidence": 0.0,
        "unique_devices": 0,
        "total_occurrences": 0
    }

    async def _fetch_patterns_for_stats():
        """Inner function to fetch patterns for stats calculation"""
        try:
            return await get_patterns(db, limit=10000)
        except Exception as e:
            if is_database_corruption_error(e):
                logger.warning(f"Failed to fetch all patterns due to corruption, trying smaller limit: {e}")
                try:
                    return await get_patterns(db, limit=1000)
                except Exception as e2:
                    if is_database_corruption_error(e2):
                        logger.warning(f"Smaller limit also failed, trying minimal limit: {e2}")
                        return await get_patterns(db, limit=100)
                    else:
                        raise
            else:
                raise

    async def _attempt_repair_and_retry():
        """Attempt database repair and retry query"""
        logger.info("Attempting automatic database repair...")
        db_path = Path(settings.database_path)
        repair_success = await attempt_database_repair(db_path)

        if repair_success:
            logger.info("Database repair successful, retrying query")
            is_healthy, error_msg = await check_database_integrity(db)
            if is_healthy:
                try:
                    return await _fetch_patterns_for_stats()
                except Exception as retry_error:
                    logger.error(f"Query failed after repair: {retry_error}")
                    raise DatabaseIntegrityError("Query failed after database repair") from retry_error
            else:
                logger.error(f"Database still unhealthy after repair: {error_msg}")
                raise DatabaseIntegrityError(f"Database repair completed but integrity check still fails: {error_msg}")
        else:
            logger.error("Database repair failed")
            raise DatabaseIntegrityError("Database repair failed")

    def _stats_response(patterns, message_suffix=""):
        """Build a successful stats response."""
        stats = _calculate_pattern_stats(patterns)
        msg = "Pattern statistics retrieved successfully"
        if message_suffix:
            msg += f" ({message_suffix})"
        return {"success": True, "data": stats, "message": msg}

    def _corruption_fallback(error_msg):
        """Return safe fallback for corruption errors."""
        return {
            "success": False,
            "data": _empty_stats,
            "message": "Database corruption detected. Automatic repair attempted but failed. Please use the repair endpoint.",
            "error": str(error_msg),
            "repair_available": True
        }

    try:
        try:
            patterns = await _fetch_patterns_for_stats()
        except Exception as query_error:
            if is_database_corruption_error(query_error):
                logger.warning(f"Query failed due to corruption: {query_error}")
                is_healthy, error_msg = await check_database_integrity(db)

                if not is_healthy:
                    logger.warning(f"Database integrity check failed: {error_msg}")
                    try:
                        patterns = await _attempt_repair_and_retry()
                    except DatabaseIntegrityError:
                        return _corruption_fallback(error_msg)
                else:
                    raise
            else:
                raise

        return _stats_response(patterns)

    except DatabaseIntegrityError as integrity_error:
        logger.error(f"Database integrity error in get_pattern_stats: {integrity_error}", exc_info=True)
        try:
            patterns = await _attempt_repair_and_retry()
            return _stats_response(patterns, "after database repair")
        except DatabaseIntegrityError:
            return _corruption_fallback(integrity_error)
        except Exception as repair_error:
            logger.error(f"Repair attempt failed: {repair_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database corruption detected. Repair attempt failed. Error: {str(integrity_error)}"
            ) from integrity_error
    except Exception as e:
        if is_database_corruption_error(e):
            logger.error(f"Database corruption detected (unhandled): {e}", exc_info=True)
            try:
                patterns = await _attempt_repair_and_retry()
                return _stats_response(patterns, "after database repair")
            except (DatabaseIntegrityError, Exception) as repair_error:
                if isinstance(repair_error, DatabaseIntegrityError):
                    return _corruption_fallback(e)
                logger.error(f"Repair attempt failed: {repair_error}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Database corruption detected. Repair attempt failed. Error: {str(e)}"
                ) from e
        else:
            logger.error(f"Failed to get pattern stats: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get pattern stats: {str(e)}"
            ) from e


@router.post("/repair")
async def repair_database(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Repair corrupted database.
    
    Attempts to repair database corruption by dumping and recreating the database.
    Creates a backup before attempting repair.
    
    Returns:
        Repair status and result
    """
    from ..database.integrity import (
        attempt_database_repair,
        check_database_integrity
    )
    from ..config import settings
    from pathlib import Path
    
    try:
        # Check current integrity status
        is_healthy, error_msg = await check_database_integrity(db)
        
        if is_healthy:
            return {
                "success": True,
                "message": "Database integrity check passed. No repair needed.",
                "data": {
                    "integrity_status": "healthy",
                    "repair_performed": False
                }
            }
        
        logger.info(f"Database integrity check failed: {error_msg}. Attempting repair...")
        
        # Attempt repair
        db_path = Path(settings.database_path)
        repair_success = await attempt_database_repair(db_path)
        
        if repair_success:
            # Verify repair
            is_healthy_after, error_msg_after = await check_database_integrity(db)
            
            if is_healthy_after:
                return {
                    "success": True,
                    "message": "Database repair completed successfully. Integrity check passed.",
                    "data": {
                        "integrity_status": "healthy",
                        "repair_performed": True,
                        "before_repair_error": error_msg,
                        "after_repair_status": "ok"
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Database repair completed but integrity check still fails.",
                    "data": {
                        "integrity_status": "unhealthy",
                        "repair_performed": True,
                        "before_repair_error": error_msg,
                        "after_repair_error": error_msg_after
                    },
                    "error": f"Repair completed but database still unhealthy: {error_msg_after}"
                }
        else:
            return {
                "success": False,
                "message": "Database repair failed.",
                "data": {
                    "integrity_status": "unhealthy",
                    "repair_performed": False,
                    "before_repair_error": error_msg
                },
                "error": "Repair operation failed. Database may need manual intervention."
            }
            
    except Exception as e:
        logger.error(f"Failed to repair database: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to repair database: {str(e)}"
        ) from e

