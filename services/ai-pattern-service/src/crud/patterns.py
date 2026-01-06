"""
Pattern CRUD Operations for Pattern Service

Epic 39, Story 39.6: Daily Scheduler Migration
Simplified pattern storage operations (full history tracking in later stories).
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Note: Pattern model is defined in shared database (ai-automation-service)
# We'll import it when needed, or use raw SQL if models aren't available
logger = logging.getLogger(__name__)


async def store_patterns(
    db: AsyncSession,
    patterns: list[dict],
    time_window_days: int = 30,
    automation_validator: Any | None = None
) -> int:
    """
    Store detected patterns in database.
    
    Simplified version for Story 39.6 - full history tracking in later stories.
    
    Args:
        db: Database session
        patterns: List of pattern dictionaries from detector
        time_window_days: Time window in days (for future use)
    
    Returns:
        Number of patterns stored/updated
    """
    if not patterns:
        logger.warning("No patterns to store")
        return 0

    try:
        # Import Pattern model (from shared database)
        # Note: This assumes the models are available via import or shared module
        try:
            from ...database.models import Pattern
        except ImportError:
            # Fallback: Use raw SQL if models aren't available
            logger.warning("Pattern model not available, using raw SQL")
            return await _store_patterns_raw_sql(db, patterns)
        
        stored_count = 0
        now = datetime.now(timezone.utc)
        
        # Validate external data patterns against automations if validator provided
        if automation_validator:
            try:
                await automation_validator.load_automation_entities()
                for pattern_data in patterns:
                    pattern_data = automation_validator.validate_pattern(pattern_data)
            except Exception as e:
                logger.warning(f"Failed to validate patterns against automations: {e}")

        for pattern_data in patterns:
            # Check if pattern already exists (same type and device)
            query = select(Pattern).where(
                Pattern.pattern_type == pattern_data['pattern_type'],
                Pattern.device_id == pattern_data['device_id']
            )
            result = await db.execute(query)
            existing_pattern = result.scalar_one_or_none()

            if existing_pattern:
                # Update existing pattern
                existing_pattern.confidence = max(existing_pattern.confidence, pattern_data['confidence'])
                existing_pattern.occurrences = pattern_data.get('occurrences', existing_pattern.occurrences)
                existing_pattern.pattern_metadata = pattern_data.get('metadata', existing_pattern.pattern_metadata)
                if hasattr(existing_pattern, 'last_seen'):
                    existing_pattern.last_seen = now
                existing_pattern.updated_at = now
                logger.debug(f"Updated existing pattern {existing_pattern.id} for {existing_pattern.device_id}")
            else:
                # Create new pattern
                pattern = Pattern(
                    pattern_type=pattern_data['pattern_type'],
                    device_id=pattern_data['device_id'],
                    pattern_metadata=pattern_data.get('metadata', {}),
                    confidence=pattern_data['confidence'],
                    occurrences=pattern_data.get('occurrences', 0),
                    created_at=now,
                    updated_at=now,
                )
                # Set history tracking fields if they exist
                if hasattr(pattern, 'first_seen'):
                    pattern.first_seen = now
                if hasattr(pattern, 'last_seen'):
                    pattern.last_seen = now
                if hasattr(pattern, 'confidence_history_count'):
                    pattern.confidence_history_count = 1
                
                db.add(pattern)
                logger.debug(f"Created new pattern for {pattern.device_id}")

            stored_count += 1

        await db.commit()
        logger.info(f"✅ Stored {stored_count} patterns in database")
        return stored_count

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to store patterns: {e}", exc_info=True)
        raise


async def _store_patterns_raw_sql(db: AsyncSession, patterns: list[dict]) -> int:
    """Fallback: Store patterns using raw SQL if models aren't available"""
    from sqlalchemy import text
    
    stored_count = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for pattern_data in patterns:
        try:
            # Check if pattern exists
            check_query = text("""
                SELECT id FROM patterns 
                WHERE pattern_type = :pattern_type AND device_id = :device_id
            """)
            result = await db.execute(
                check_query,
                {
                    "pattern_type": pattern_data['pattern_type'],
                    "device_id": pattern_data['device_id']
                }
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update
                update_query = text("""
                    UPDATE patterns 
                    SET confidence = MAX(confidence, :confidence),
                        occurrences = :occurrences,
                        pattern_metadata = :metadata,
                        updated_at = :updated_at
                    WHERE id = :id
                """)
                await db.execute(
                    update_query,
                    {
                        "id": existing,
                        "confidence": pattern_data['confidence'],
                        "occurrences": pattern_data.get('occurrences', 0),
                        "metadata": str(pattern_data.get('metadata', {})),
                        "updated_at": now
                    }
                )
            else:
                # Insert
                insert_query = text("""
                    INSERT INTO patterns 
                    (pattern_type, device_id, pattern_metadata, confidence, occurrences, created_at, updated_at)
                    VALUES (:pattern_type, :device_id, :metadata, :confidence, :occurrences, :created_at, :updated_at)
                """)
                await db.execute(
                    insert_query,
                    {
                        "pattern_type": pattern_data['pattern_type'],
                        "device_id": pattern_data['device_id'],
                        "metadata": str(pattern_data.get('metadata', {})),
                        "confidence": pattern_data['confidence'],
                        "occurrences": pattern_data.get('occurrences', 0),
                        "created_at": now,
                        "updated_at": now
                    }
                )
            
            stored_count += 1
        except Exception as e:
            logger.warning(f"Failed to store pattern {pattern_data.get('device_id')}: {e}")
            continue
    
    await db.commit()
    return stored_count


async def get_patterns(
    db: AsyncSession,
    pattern_type: str | None = None,
    device_id: str | None = None,
    min_confidence: float | None = None,
    limit: int = 100
) -> list[Any]:
    """
    Retrieve patterns from database with optional filters.
    
    Args:
        db: Database session
        pattern_type: Filter by pattern type
        device_id: Filter by device ID
        min_confidence: Minimum confidence threshold
        limit: Maximum number of patterns to return
    
    Returns:
        List of Pattern objects
    """
    try:
        try:
            from ...database.models import Pattern
        except ImportError:
            logger.warning("Pattern model not available, using raw SQL")
            return await _get_patterns_raw_sql(db, pattern_type, device_id, min_confidence, limit)
        
        query = select(Pattern)

        if pattern_type:
            query = query.where(Pattern.pattern_type == pattern_type)

        if device_id:
            query = query.where(Pattern.device_id == device_id)

        if min_confidence is not None:
            query = query.where(Pattern.confidence >= min_confidence)

        query = query.order_by(Pattern.confidence.desc()).limit(limit)

        result = await db.execute(query)
        patterns = result.scalars().all()

        logger.info(f"Retrieved {len(patterns)} patterns from database")
        return list(patterns)

    except Exception as e:
        # Check if this is a database corruption error
        from ..database.integrity import is_database_corruption_error, DatabaseIntegrityError
        
        if is_database_corruption_error(e):
            logger.error(f"Database corruption detected while retrieving patterns: {e}", exc_info=True)
            raise DatabaseIntegrityError(f"Database corruption detected: {e}") from e
        else:
            logger.error(f"Failed to retrieve patterns: {e}", exc_info=True)
            raise


async def _get_patterns_raw_sql(
    db: AsyncSession,
    pattern_type: str | None,
    device_id: str | None,
    min_confidence: float | None,
    limit: int
) -> list[dict]:
    """Fallback: Get patterns using raw SQL"""
    from sqlalchemy import text
    
    conditions = []
    params = {}
    
    if pattern_type:
        conditions.append("pattern_type = :pattern_type")
        params["pattern_type"] = pattern_type
    if device_id:
        conditions.append("device_id = :device_id")
        params["device_id"] = device_id
    if min_confidence is not None:
        conditions.append("confidence >= :min_confidence")
        params["min_confidence"] = min_confidence
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = text(f"""
        SELECT * FROM patterns 
        WHERE {where_clause}
        ORDER BY confidence DESC
        LIMIT :limit
    """)
    params["limit"] = limit
    
    result = await db.execute(query, params)
    rows = result.fetchall()
    
    # Convert rows to dicts
    patterns = []
    for row in rows:
        patterns.append(dict(row._mapping))
    
    return patterns

