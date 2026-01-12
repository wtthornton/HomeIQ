"""
Synergy CRUD Operations for Pattern Service

Epic 39, Story 39.6: Daily Scheduler Migration
Simplified synergy storage operations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def store_synergy_opportunities(
    db: AsyncSession,
    synergies: list[dict],
    validate_with_patterns: bool = False,  # Disabled for Story 39.6
    min_pattern_confidence: float = 0.7,
    calculate_quality: bool = True,  # 2025 Enhancement: Calculate quality scores
    filter_low_quality: bool = True,  # 2025 Enhancement: Filter low-quality synergies
    min_quality_score: float = 0.50,  # 2025 Enhancement: Minimum quality score threshold (medium+ quality)
    deduplicate: bool = True  # 2025 Enhancement: Remove duplicates
) -> tuple[int, int]:
    """
    Store multiple synergy opportunities in database with quality scoring and filtering.
    
    2025 Enhancement: Added quality scoring, filtering, and deduplication.
    
    Args:
        db: Database session
        synergies: List of synergy dictionaries from detector
        validate_with_patterns: Whether to validate against patterns (disabled for Story 39.6)
        min_pattern_confidence: Minimum pattern confidence for validation
        calculate_quality: Calculate quality_score for each synergy (default: True)
        filter_low_quality: Filter synergies below min_quality_score (default: True)
        min_quality_score: Minimum quality score threshold (default: 0.50, medium+ quality)
        deduplicate: Remove duplicate synergies before storage (default: True)
    
    Returns:
        Tuple of (stored_count, filtered_count)
    """
    if not synergies:
        logger.warning("No synergies to store")
        return 0, 0

    try:
        # Import SynergyOpportunity model
        try:
            from ...database.models import SynergyOpportunity
        except ImportError:
            logger.warning("SynergyOpportunity model not available, using raw SQL")
            stored = await _store_synergies_raw_sql(db, synergies)
            return stored, 0
        
        # 2025 Enhancement: Quality scoring and filtering
        from ...services.synergy_quality_scorer import SynergyQualityScorer
        from ...services.synergy_deduplicator import SynergyDeduplicator
        
        quality_scorer = SynergyQualityScorer()
        deduplicator = SynergyDeduplicator()
        
        # Step 1: Deduplicate if enabled
        if deduplicate:
            original_count = len(synergies)
            synergies = deduplicator.deduplicate(synergies, keep_highest_quality=True)
            logger.info(f"Deduplication: {original_count} → {len(synergies)} synergies")
        
        # Step 2: Calculate quality scores and filter
        filtered_count = 0
        filtered_synergies = []
        
        for synergy in synergies:
            # Calculate quality score if enabled
            if calculate_quality:
                try:
                    quality_result = quality_scorer.calculate_quality_score(synergy)
                    synergy['quality_score'] = quality_result['quality_score']
                    synergy['quality_tier'] = quality_result['quality_tier']
                except Exception as e:
                    logger.warning(f"Failed to calculate quality score for synergy {synergy.get('synergy_id')}: {e}")
                    synergy['quality_score'] = 0.0
                    synergy['quality_tier'] = 'poor'
            
            # Check if should filter
            if filter_low_quality:
                quality_score = synergy.get('quality_score', 0.0)
                should_filter, filter_reason = quality_scorer.should_filter_synergy(
                    synergy,
                    quality_score,
                    config={
                        'min_quality_score': min_quality_score,
                        'min_confidence': 0.50,
                        'min_impact': 0.30,
                        'filter_unvalidated_high_complexity': True
                    }
                )
                
                if should_filter:
                    synergy['filter_reason'] = filter_reason
                    filtered_count += 1
                    logger.debug(f"Filtered synergy {synergy.get('synergy_id')}: {filter_reason}")
                    continue
            
            filtered_synergies.append(synergy)
        
        if filter_low_quality and filtered_count > 0:
            logger.info(f"Quality filtering: {len(synergies)} → {len(filtered_synergies)} synergies ({filtered_count} filtered)")
        
        # Use filtered synergies for storage
        synergies = filtered_synergies
        
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
                    'rationale': synergy_data.get('rationale'),
                    'context_metadata': synergy_data.get('context_metadata')
                }
                
                # 2025 Enhancement: Store XAI explanation and context breakdown as separate fields
                explanation = synergy_data.get('explanation')
                context_breakdown = synergy_data.get('context_breakdown')

                # Extract n-level synergy fields
                synergy_depth = synergy_data.get('synergy_depth', 2)
                chain_devices = synergy_data.get('chain_devices', synergy_data.get('devices', []))

                # 2025 Enhancement: Extract quality fields
                quality_score = synergy_data.get('quality_score')
                quality_tier = synergy_data.get('quality_tier')
                filter_reason = synergy_data.get('filter_reason')
                
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
                    # 2025 Enhancement: Update explanation and context_breakdown if fields exist
                    if hasattr(existing_synergy, 'explanation'):
                        existing_synergy.explanation = explanation
                    if hasattr(existing_synergy, 'context_breakdown'):
                        existing_synergy.context_breakdown = context_breakdown
                    # 2025 Enhancement: Update quality fields if they exist
                    if hasattr(existing_synergy, 'quality_score') and quality_score is not None:
                        existing_synergy.quality_score = quality_score
                    if hasattr(existing_synergy, 'quality_tier') and quality_tier is not None:
                        existing_synergy.quality_tier = quality_tier
                    if hasattr(existing_synergy, 'last_validated_at'):
                        existing_synergy.last_validated_at = now
                    if hasattr(existing_synergy, 'filter_reason'):
                        existing_synergy.filter_reason = filter_reason
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
                    # 2025 Enhancement: Set explanation and context_breakdown if fields exist
                    if hasattr(synergy, 'explanation'):
                        synergy.explanation = explanation
                    if hasattr(synergy, 'context_breakdown'):
                        synergy.context_breakdown = context_breakdown
                    # 2025 Enhancement: Set quality fields if they exist
                    if hasattr(synergy, 'quality_score') and quality_score is not None:
                        synergy.quality_score = quality_score
                    if hasattr(synergy, 'quality_tier') and quality_tier is not None:
                        synergy.quality_tier = quality_tier
                    if hasattr(synergy, 'last_validated_at'):
                        synergy.last_validated_at = now
                    if hasattr(synergy, 'filter_reason') and filter_reason is not None:
                        synergy.filter_reason = filter_reason
                    
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
                + (f", filtered {filtered_count} low-quality" if filter_low_quality and filtered_count > 0 else "")
            )
            return stored_count + updated_count, filtered_count
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error during commit: {e}", exc_info=True)
            return stored_count + updated_count, filtered_count
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit synergy opportunities: {e}", exc_info=True)
            raise

    except Exception as e:
        logger.error(f"Failed to store synergy opportunities: {e}", exc_info=True)
        raise
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
                'context_metadata': synergy_data.get('context_metadata')
            }
            
            # 2025 Enhancement: Extract explanation and context_breakdown
            explanation = synergy_data.get('explanation')
            context_breakdown = synergy_data.get('context_breakdown')
            
            # Epic AI-4: Extract n-level synergy fields
            synergy_depth = synergy_data.get('synergy_depth', 2)
            chain_devices = synergy_data.get('chain_devices', synergy_data.get('devices', []))
            
            if existing:
                # Update - include 2025 enhancement fields and n-level synergy fields
                update_query = text("""
                    UPDATE synergy_opportunities 
                    SET synergy_type = :synergy_type,
                        device_ids = :device_ids,
                        opportunity_metadata = :metadata,
                        impact_score = :impact_score,
                        complexity = :complexity,
                        confidence = :confidence,
                        area = :area,
                        pattern_support_score = :pattern_support_score,
                        validated_by_patterns = :validated_by_patterns,
                        synergy_depth = :synergy_depth,
                        chain_devices = :chain_devices
                    WHERE synergy_id = :synergy_id
                """)
                params = {
                    "synergy_id": synergy_id,
                    "synergy_type": synergy_data['synergy_type'],
                    "device_ids": json.dumps(synergy_data['devices']),
                    "metadata": json.dumps(metadata),
                    "impact_score": synergy_data['impact_score'],
                    "complexity": synergy_data['complexity'],
                    "confidence": synergy_data['confidence'],
                    "area": synergy_data.get('area', ''),
                    "pattern_support_score": synergy_data.get('pattern_support_score', 0.0),
                    "validated_by_patterns": synergy_data.get('validated_by_patterns', False),
                    "synergy_depth": synergy_depth,
                    "chain_devices": json.dumps(chain_devices) if chain_devices else None
                }
                
                # Try to update explanation and context_breakdown if columns exist
                if explanation is not None:
                    try:
                        update_explanation_query = text("""
                            UPDATE synergy_opportunities 
                            SET explanation = :explanation
                            WHERE synergy_id = :synergy_id
                        """)
                        await db.execute(update_explanation_query, {"synergy_id": synergy_id, "explanation": json.dumps(explanation)})
                    except Exception:
                        pass  # Column may not exist yet, migration will add it
                
                if context_breakdown is not None:
                    try:
                        update_context_query = text("""
                            UPDATE synergy_opportunities 
                            SET context_breakdown = :context_breakdown
                            WHERE synergy_id = :synergy_id
                        """)
                        await db.execute(update_context_query, {"synergy_id": synergy_id, "context_breakdown": json.dumps(context_breakdown)})
                    except Exception:
                        pass  # Column may not exist yet, migration will add it
                
                await db.execute(update_query, params)
            else:
                # Insert - include 2025 enhancement fields and n-level synergy fields
                insert_query = text("""
                    INSERT INTO synergy_opportunities 
                    (synergy_id, synergy_type, device_ids, opportunity_metadata, impact_score, complexity, confidence, area, created_at, pattern_support_score, validated_by_patterns, synergy_depth, chain_devices)
                    VALUES (:synergy_id, :synergy_type, :device_ids, :metadata, :impact_score, :complexity, :confidence, :area, :created_at, :pattern_support_score, :validated_by_patterns, :synergy_depth, :chain_devices)
                """)
                params = {
                    "synergy_id": synergy_id,
                    "synergy_type": synergy_data['synergy_type'],
                    "device_ids": json.dumps(synergy_data['devices']),
                    "metadata": json.dumps(metadata),
                    "impact_score": synergy_data['impact_score'],
                    "complexity": synergy_data['complexity'],
                    "confidence": synergy_data['confidence'],
                    "area": synergy_data.get('area', ''),
                    "created_at": now,
                    "pattern_support_score": synergy_data.get('pattern_support_score', 0.0),
                    "validated_by_patterns": synergy_data.get('validated_by_patterns', False),
                    "synergy_depth": synergy_depth,
                    "chain_devices": json.dumps(chain_devices) if chain_devices else None
                }
                await db.execute(insert_query, params)
                
                # Try to update explanation and context_breakdown if columns exist (added via migration)
                if explanation is not None:
                    try:
                        update_explanation_query = text("""
                            UPDATE synergy_opportunities 
                            SET explanation = :explanation
                            WHERE synergy_id = :synergy_id
                        """)
                        await db.execute(update_explanation_query, {"synergy_id": synergy_id, "explanation": json.dumps(explanation)})
                    except Exception:
                        pass  # Column may not exist yet, migration will add it
                
                if context_breakdown is not None:
                    try:
                        update_context_query = text("""
                            UPDATE synergy_opportunities 
                            SET context_breakdown = :context_breakdown
                            WHERE synergy_id = :synergy_id
                        """)
                        await db.execute(update_context_query, {"synergy_id": synergy_id, "context_breakdown": json.dumps(context_breakdown)})
                    except Exception:
                        pass  # Column may not exist yet, migration will add it
            
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
    order_by_priority: bool = False,
    min_quality_score: float | None = None,  # 2025 Enhancement: Quality filter
    quality_tier: str | None = None,  # 2025 Enhancement: Filter by tier ('high', 'medium', 'low')
    exclude_filtered: bool = True  # 2025 Enhancement: Exclude filtered synergies
) -> list[Any]:
    """
    Retrieve synergy opportunities from database with quality filtering.
    
    2025 Enhancement: Added quality score and tier filtering.
    
    Args:
        db: Database session
        synergy_type: Optional filter by synergy type
        min_confidence: Minimum confidence threshold
        synergy_depth: Optional filter by synergy depth
        limit: Maximum number of results
        order_by_priority: If True, order by priority score
        min_quality_score: Minimum quality score (None = no filter)
        quality_tier: Filter by quality tier ('high', 'medium', 'low')
        exclude_filtered: Exclude synergies with filter_reason set (default: True)
    
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
        
        # 2025 Enhancement: Quality filters
        if min_quality_score is not None:
            if hasattr(SynergyOpportunity, 'quality_score'):
                conditions.append(SynergyOpportunity.quality_score >= min_quality_score)
        
        if quality_tier:
            if hasattr(SynergyOpportunity, 'quality_tier'):
                conditions.append(SynergyOpportunity.quality_tier == quality_tier)
        
        if exclude_filtered:
            if hasattr(SynergyOpportunity, 'filter_reason'):
                conditions.append(
                    or_(
                        SynergyOpportunity.filter_reason.is_(None),
                        SynergyOpportunity.filter_reason == ''
                    )
                )

        query = select(SynergyOpportunity).where(and_(*conditions))

        if order_by_priority:
            # 2025 Enhancement: Enhanced priority score calculation
            # Check if quality_score column exists (for backward compatibility)
            if hasattr(SynergyOpportunity, 'quality_score'):
                # Enhanced priority score with quality_score and validation bonus
                priority_score = (
                    SynergyOpportunity.impact_score * 0.30 +
                    SynergyOpportunity.confidence * 0.20 +
                    func.coalesce(SynergyOpportunity.pattern_support_score, 0.0) * 0.20 +
                    func.coalesce(SynergyOpportunity.quality_score, 0.0) * 0.20 +
                    case(
                        (SynergyOpportunity.validated_by_patterns == True, 0.10),
                        else_=0.0
                    )
                )
            else:
                # Fallback to original priority score (backward compatibility)
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

