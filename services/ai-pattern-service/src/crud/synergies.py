"""
Synergy CRUD Operations for Pattern Service

Epic 39, Story 39.6: Daily Scheduler Migration
Simplified synergy storage operations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def store_synergy_opportunities(
    db: AsyncSession,
    synergies: list[dict],
    validate_with_patterns: bool = False,  # Disabled for Story 39.6
    min_pattern_confidence: float = 0.7
) -> int:
    """
    Store multiple synergy opportunities in database.
    
    Simplified version for Story 39.6 - pattern validation in later stories.
    
    Args:
        db: Database session
        synergies: List of synergy dictionaries from detector
        validate_with_patterns: Whether to validate against patterns (disabled for Story 39.6)
        min_pattern_confidence: Minimum pattern confidence for validation
    
    Returns:
        Number of synergies stored
    """
    if not synergies:
        logger.warning("No synergies to store")
        return 0

    try:
        # Import SynergyOpportunity model
        try:
            from ...database.models import SynergyOpportunity
        except ImportError:
            logger.warning("SynergyOpportunity model not available, using raw SQL")
            return await _store_synergies_raw_sql(db, synergies)
        
        stored_count = 0
        updated_count = 0
        skipped_count = 0
        now = datetime.now(timezone.utc)

        for synergy_data in synergies:
            try:
                synergy_id = synergy_data['synergy_id']

                # Check if synergy already exists (upsert pattern)
                query = select(SynergyOpportunity).where(
                    SynergyOpportunity.synergy_id == synergy_id
                )
                result = await db.execute(query)
                existing_synergy = result.scalar_one_or_none()

                # Create metadata dict from synergy data
                metadata = {
                    'trigger_entity': synergy_data.get('trigger_entity'),
                    'trigger_name': synergy_data.get('trigger_name'),
                    'action_entity': synergy_data.get('action_entity'),
                    'action_name': synergy_data.get('action_name'),
                    'relationship': synergy_data.get('relationship'),
                    'rationale': synergy_data.get('rationale')
                }

                # Extract n-level synergy fields
                synergy_depth = synergy_data.get('synergy_depth', 2)
                chain_devices = synergy_data.get('chain_devices', synergy_data.get('devices', []))

                if existing_synergy:
                    # Update existing synergy
                    existing_synergy.synergy_type = synergy_data['synergy_type']
                    existing_synergy.device_ids = json.dumps(synergy_data['devices'])
                    existing_synergy.opportunity_metadata = metadata
                    existing_synergy.impact_score = synergy_data['impact_score']
                    existing_synergy.complexity = synergy_data['complexity']
                    existing_synergy.confidence = synergy_data['confidence']
                    existing_synergy.area = synergy_data.get('area')
                    # Update n-level fields if they exist
                    if hasattr(existing_synergy, 'synergy_depth'):
                        existing_synergy.synergy_depth = synergy_depth
                    if hasattr(existing_synergy, 'chain_devices'):
                        existing_synergy.chain_devices = json.dumps(chain_devices) if chain_devices else None
                    updated_count += 1
                    logger.debug(f"Updated existing synergy: {synergy_id}")
                else:
                    # Create new synergy
                    synergy = SynergyOpportunity(
                        synergy_id=synergy_id,
                        synergy_type=synergy_data['synergy_type'],
                        device_ids=json.dumps(synergy_data['devices']),
                        opportunity_metadata=metadata,
                        impact_score=synergy_data['impact_score'],
                        complexity=synergy_data['complexity'],
                        confidence=synergy_data['confidence'],
                        area=synergy_data.get('area'),
                        created_at=now,
                    )
                    # Set n-level fields if they exist
                    if hasattr(synergy, 'synergy_depth'):
                        synergy.synergy_depth = synergy_depth
                    if hasattr(synergy, 'chain_devices'):
                        synergy.chain_devices = json.dumps(chain_devices) if chain_devices else None
                    
                    db.add(synergy)
                    stored_count += 1
                    logger.debug(f"Added new synergy: {synergy_id}")

            except IntegrityError as e:
                # Handle duplicate key errors gracefully
                await db.rollback()
                skipped_count += 1
                logger.warning(f"Skipped duplicate synergy {synergy_data.get('synergy_id')}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing synergy {synergy_data.get('synergy_id')}: {e}")
                skipped_count += 1
                try:
                    await db.rollback()
                except Exception:
                    pass
                continue

        # Commit all changes
        try:
            await db.commit()
            logger.info(
                f"✅ Stored {stored_count} new, updated {updated_count} existing synergy opportunities"
                + (f", skipped {skipped_count} duplicates/errors" if skipped_count > 0 else "")
            )
            return stored_count + updated_count
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error during commit: {e}", exc_info=True)
            return stored_count + updated_count
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit synergy opportunities: {e}", exc_info=True)
            raise

    except Exception as e:
        logger.error(f"Failed to store synergy opportunities: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        raise


async def _store_synergies_raw_sql(db: AsyncSession, synergies: list[dict]) -> int:
    """Fallback: Store synergies using raw SQL if models aren't available"""
    from sqlalchemy import text
    
    stored_count = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for synergy_data in synergies:
        try:
            synergy_id = synergy_data['synergy_id']
            
            # Check if exists
            check_query = text("SELECT id FROM synergy_opportunities WHERE synergy_id = :synergy_id")
            result = await db.execute(check_query, {"synergy_id": synergy_id})
            existing = result.scalar_one_or_none()
            
            metadata = {
                'trigger_entity': synergy_data.get('trigger_entity'),
                'action_entity': synergy_data.get('action_entity'),
                'relationship': synergy_data.get('relationship'),
            }
            
            if existing:
                # Update
                update_query = text("""
                    UPDATE synergy_opportunities 
                    SET synergy_type = :synergy_type,
                        device_ids = :device_ids,
                        opportunity_metadata = :metadata,
                        impact_score = :impact_score,
                        complexity = :complexity,
                        confidence = :confidence,
                        area = :area
                    WHERE synergy_id = :synergy_id
                """)
                await db.execute(
                    update_query,
                    {
                        "synergy_id": synergy_id,
                        "synergy_type": synergy_data['synergy_type'],
                        "device_ids": json.dumps(synergy_data['devices']),
                        "metadata": json.dumps(metadata),
                        "impact_score": synergy_data['impact_score'],
                        "complexity": synergy_data['complexity'],
                        "confidence": synergy_data['confidence'],
                        "area": synergy_data.get('area', '')
                    }
                )
            else:
                # Insert
                insert_query = text("""
                    INSERT INTO synergy_opportunities 
                    (synergy_id, synergy_type, device_ids, opportunity_metadata, impact_score, complexity, confidence, area, created_at)
                    VALUES (:synergy_id, :synergy_type, :device_ids, :metadata, :impact_score, :complexity, :confidence, :area, :created_at)
                """)
                await db.execute(
                    insert_query,
                    {
                        "synergy_id": synergy_id,
                        "synergy_type": synergy_data['synergy_type'],
                        "device_ids": json.dumps(synergy_data['devices']),
                        "metadata": json.dumps(metadata),
                        "impact_score": synergy_data['impact_score'],
                        "complexity": synergy_data['complexity'],
                        "confidence": synergy_data['confidence'],
                        "area": synergy_data.get('area', ''),
                        "created_at": now
                    }
                )
            
            stored_count += 1
        except Exception as e:
            logger.warning(f"Failed to store synergy {synergy_data.get('synergy_id')}: {e}")
            continue
    
    await db.commit()
    return stored_count


async def get_synergy_opportunities(
    db: AsyncSession,
    synergy_type: str | None = None,
    min_confidence: float = 0.0,
    synergy_depth: int | None = None,
    limit: int = 100,
    order_by_priority: bool = False
) -> list[Any]:
    """
    Retrieve synergy opportunities from database.
    
    Args:
        db: Database session
        synergy_type: Optional filter by synergy type
        min_confidence: Minimum confidence threshold
        synergy_depth: Optional filter by synergy depth
        limit: Maximum number of results
        order_by_priority: If True, order by priority score
    
    Returns:
        List of SynergyOpportunity instances
    """
    try:
        try:
            from ...database.models import SynergyOpportunity
        except ImportError:
            logger.warning("SynergyOpportunity model not available, using raw SQL")
            return await _get_synergies_raw_sql(db, synergy_type, min_confidence, synergy_depth, limit)
        
        conditions = [SynergyOpportunity.confidence >= min_confidence]

        if synergy_depth is not None:
            if hasattr(SynergyOpportunity, 'synergy_depth'):
                conditions.append(SynergyOpportunity.synergy_depth == synergy_depth)

        if synergy_type:
            conditions.append(SynergyOpportunity.synergy_type == synergy_type)

        query = select(SynergyOpportunity).where(and_(*conditions))

        if order_by_priority:
            # Calculate priority score
            priority_score = (
                SynergyOpportunity.impact_score * 0.40 +
                SynergyOpportunity.confidence * 0.25 +
                func.coalesce(SynergyOpportunity.pattern_support_score, 0.0) * 0.25
            )
            query = query.order_by(priority_score.desc()).limit(limit)
        else:
            query = query.order_by(SynergyOpportunity.impact_score.desc()).limit(limit)

        result = await db.execute(query)
        synergies = result.scalars().all()

        logger.info(f"Retrieved {len(synergies)} synergy opportunities")
        return list(synergies)

    except Exception as e:
        logger.error(f"Failed to get synergies: {e}", exc_info=True)
        raise


async def _get_synergies_raw_sql(
    db: AsyncSession,
    synergy_type: str | None,
    min_confidence: float,
    synergy_depth: int | None,
    limit: int
) -> list[dict]:
    """Fallback: Get synergies using raw SQL"""
    from sqlalchemy import text
    
    conditions = ["confidence >= :min_confidence"]
    params = {"min_confidence": min_confidence}
    
    if synergy_type:
        conditions.append("synergy_type = :synergy_type")
        params["synergy_type"] = synergy_type
    if synergy_depth is not None:
        conditions.append("synergy_depth = :synergy_depth")
        params["synergy_depth"] = synergy_depth
    
    where_clause = " AND ".join(conditions)
    
    query = text(f"""
        SELECT * FROM synergy_opportunities 
        WHERE {where_clause}
        ORDER BY impact_score DESC
        LIMIT :limit
    """)
    params["limit"] = limit
    
    result = await db.execute(query, params)
    rows = result.fetchall()
    
    synergies = []
    for row in rows:
        synergies.append(dict(row._mapping))
    
    return synergies

