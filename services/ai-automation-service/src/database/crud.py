"""
CRUD operations for AI Automation Service database
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import logging

from .models import Pattern, Suggestion, UserFeedback, DeviceCapability, DeviceFeatureUsage, SynergyOpportunity

logger = logging.getLogger(__name__)


# ============================================================================
# Pattern CRUD Operations
# ============================================================================

async def store_patterns(db: AsyncSession, patterns: List[Dict]) -> int:
    """
    Store detected patterns in database.
    
    Args:
        db: Database session
        patterns: List of pattern dictionaries from detector
    
    Returns:
        Number of patterns stored
    """
    if not patterns:
        logger.warning("No patterns to store")
        return 0
    
    try:
        stored_count = 0
        
        for pattern_data in patterns:
            pattern = Pattern(
                pattern_type=pattern_data['pattern_type'],
                device_id=pattern_data['device_id'],
                pattern_metadata=pattern_data.get('metadata', {}),
                confidence=pattern_data['confidence'],
                occurrences=pattern_data['occurrences'],
                created_at=datetime.now(timezone.utc)
            )
            db.add(pattern)
            stored_count += 1
        
        await db.commit()
        logger.info(f"✅ Stored {stored_count} patterns in database")
        return stored_count
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to store patterns: {e}", exc_info=True)
        raise


async def get_patterns(
    db: AsyncSession,
    pattern_type: Optional[str] = None,
    device_id: Optional[str] = None,
    min_confidence: Optional[float] = None,
    limit: int = 100
) -> List[Pattern]:
    """
    Retrieve patterns from database with optional filters.
    
    Args:
        db: Database session
        pattern_type: Filter by pattern type (time_of_day, co_occurrence, anomaly)
        device_id: Filter by device ID
        min_confidence: Minimum confidence threshold
        limit: Maximum number of patterns to return
    
    Returns:
        List of Pattern objects
    """
    try:
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
        logger.error(f"Failed to retrieve patterns: {e}", exc_info=True)
        raise


async def delete_old_patterns(db: AsyncSession, days_old: int = 30) -> int:
    """
    Delete patterns older than specified days.
    
    Args:
        db: Database session
        days_old: Delete patterns older than this many days
    
    Returns:
        Number of patterns deleted
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        stmt = delete(Pattern).where(Pattern.created_at < cutoff_date)
        result = await db.execute(stmt)
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} patterns older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete old patterns: {e}", exc_info=True)
        raise


async def get_pattern_stats(db: AsyncSession) -> Dict:
    """
    Get pattern statistics from database.
    
    Returns:
        Dictionary with pattern counts and statistics
    """
    try:
        # Total patterns
        total_result = await db.execute(select(func.count()).select_from(Pattern))
        total_patterns = total_result.scalar() or 0
        
        # Patterns by type
        type_result = await db.execute(
            select(Pattern.pattern_type, func.count())
            .group_by(Pattern.pattern_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}
        
        # Unique devices
        devices_result = await db.execute(
            select(func.count(func.distinct(Pattern.device_id))).select_from(Pattern)
        )
        unique_devices = devices_result.scalar() or 0
        
        # Average confidence
        avg_conf_result = await db.execute(
            select(func.avg(Pattern.confidence)).select_from(Pattern)
        )
        avg_confidence = avg_conf_result.scalar() or 0.0
        
        return {
            'total_patterns': total_patterns,
            'by_type': by_type,
            'unique_devices': unique_devices,
            'avg_confidence': float(avg_confidence)
        }
        
    except Exception as e:
        logger.error(f"Failed to get pattern stats: {e}", exc_info=True)
        raise


# ============================================================================
# Suggestion CRUD Operations
# ============================================================================

async def store_suggestion(db: AsyncSession, suggestion_data: Dict, commit: bool = True) -> Suggestion:
    """
    Store automation suggestion in database.
    
    Args:
        db: Database session
        suggestion_data: Suggestion dictionary
        commit: Whether to commit immediately (default: True)
    
    Returns:
        Stored Suggestion object
    """
    try:
        # Story AI1.24: automation_yaml can be NULL for draft suggestions
        suggestion = Suggestion(
            pattern_id=suggestion_data.get('pattern_id'),
            title=suggestion_data['title'],
            description_only=suggestion_data.get('description', suggestion_data.get('description_only', '')),
            automation_yaml=suggestion_data.get('automation_yaml'),  # Can be None for drafts
            status='draft',  # Conversational flow status
            confidence=suggestion_data['confidence'],
            category=suggestion_data.get('category'),
            priority=suggestion_data.get('priority'),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(suggestion)
        
        if commit:
            await db.commit()
            await db.refresh(suggestion)
        
        logger.info(f"✅ Stored suggestion: {suggestion.title}")
        return suggestion
        
    except Exception as e:
        if commit:
            await db.rollback()
        logger.error(f"Failed to store suggestion: {e}", exc_info=True)
        raise


async def get_suggestions(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Suggestion]:
    """
    Retrieve automation suggestions from database.
    
    Args:
        db: Database session
        status: Filter by status (pending, approved, deployed, rejected)
        limit: Maximum number of suggestions to return
    
    Returns:
        List of Suggestion objects
    """
    try:
        query = select(Suggestion)
        
        if status:
            query = query.where(Suggestion.status == status)
        
        query = query.order_by(Suggestion.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        suggestions = result.scalars().all()
        
        logger.info(f"Retrieved {len(suggestions)} suggestions from database")
        return list(suggestions)
        
    except Exception as e:
        logger.error(f"Failed to retrieve suggestions: {e}", exc_info=True)
        raise


# ============================================================================
# User Feedback CRUD Operations
# ============================================================================

async def store_feedback(db: AsyncSession, feedback_data: Dict) -> UserFeedback:
    """
    Store user feedback on a suggestion.
    
    Args:
        db: Database session
        feedback_data: Feedback dictionary
    
    Returns:
        Stored UserFeedback object
    """
    try:
        feedback = UserFeedback(
            suggestion_id=feedback_data['suggestion_id'],
            action=feedback_data['action'],
            feedback_text=feedback_data.get('feedback_text'),
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        
        logger.info(f"✅ Stored feedback for suggestion {feedback.suggestion_id}: {feedback.action}")
        return feedback
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to store feedback: {e}", exc_info=True)
        raise


# ============================================================================
# Epic AI-2: Device Intelligence CRUD Operations (Story AI2.2)
# ============================================================================

async def upsert_device_capability(
    db: AsyncSession,
    device_model: str,
    manufacturer: str,
    description: str,
    capabilities: dict,
    mqtt_exposes: list,
    integration_type: str = 'zigbee2mqtt'
) -> DeviceCapability:
    """
    Insert or update device capability.
    
    Uses merge() for upsert semantics (insert if new, update if exists).
    
    Story AI2.2: Capability Database Schema & Storage
    Epic AI-2: Device Intelligence System
    
    Args:
        db: Database session
        device_model: Device model identifier (primary key)
        manufacturer: Manufacturer name
        description: Device description
        capabilities: Parsed capabilities dict
        mqtt_exposes: Raw MQTT exposes array
        integration_type: Integration type (default: zigbee2mqtt)
        
    Returns:
        DeviceCapability record (new or updated)
        
    Example:
        capability = await upsert_device_capability(
            db=session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Red Series Dimmer Switch",
            capabilities={"light_control": {}, "smart_bulb_mode": {}},
            mqtt_exposes=[...]
        )
    """
    try:
        # Check if capability exists (proper async upsert pattern)
        existing = await get_device_capability(db, device_model)
        
        if existing:
            # Update existing
            existing.manufacturer = manufacturer
            existing.integration_type = integration_type
            existing.description = description
            existing.capabilities = capabilities
            existing.mqtt_exposes = mqtt_exposes
            existing.last_updated = datetime.now(timezone.utc)
            capability = existing
        else:
            # Insert new
            capability = DeviceCapability(
                device_model=device_model,
                manufacturer=manufacturer,
                integration_type=integration_type,
                description=description,
                capabilities=capabilities,
                mqtt_exposes=mqtt_exposes,
                last_updated=datetime.now(timezone.utc)
            )
            db.add(capability)
        
        await db.commit()
        await db.refresh(capability)
        
        logger.debug(f"✅ Upserted capability for {manufacturer} {device_model}")
        return capability
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to upsert capability for {device_model}: {e}", exc_info=True)
        raise


async def get_device_capability(db: AsyncSession, device_model: str) -> Optional[DeviceCapability]:
    """
    Get device capability by model.
    
    Args:
        db: Database session
        device_model: Device model identifier
        
    Returns:
        DeviceCapability or None if not found
        
    Example:
        capability = await get_device_capability(db, "VZM31-SN")
        if capability:
            print(f"Found {len(capability.capabilities)} features")
    """
    try:
        result = await db.execute(
            select(DeviceCapability).where(DeviceCapability.device_model == device_model)
        )
        capability = result.scalars().first()
        
        if capability:
            logger.debug(f"Retrieved capability for {device_model}")
        else:
            logger.debug(f"No capability found for {device_model}")
        
        return capability
        
    except Exception as e:
        logger.error(f"Failed to get capability for {device_model}: {e}", exc_info=True)
        raise


async def get_all_capabilities(
    db: AsyncSession,
    manufacturer: Optional[str] = None,
    integration_type: Optional[str] = None
) -> List[DeviceCapability]:
    """
    Get all device capabilities with optional filters.
    
    Args:
        db: Database session
        manufacturer: Filter by manufacturer (e.g., "Inovelli")
        integration_type: Filter by integration (e.g., "zigbee2mqtt")
        
    Returns:
        List of all DeviceCapability records matching filters
        
    Example:
        # Get all Inovelli devices
        inovelli_devices = await get_all_capabilities(db, manufacturer="Inovelli")
    """
    try:
        query = select(DeviceCapability)
        
        if manufacturer:
            query = query.where(DeviceCapability.manufacturer == manufacturer)
        
        if integration_type:
            query = query.where(DeviceCapability.integration_type == integration_type)
        
        query = query.order_by(DeviceCapability.manufacturer, DeviceCapability.device_model)
        
        result = await db.execute(query)
        capabilities = result.scalars().all()
        
        logger.info(f"Retrieved {len(capabilities)} device capabilities")
        return list(capabilities)
        
    except Exception as e:
        logger.error(f"Failed to get capabilities: {e}", exc_info=True)
        raise


async def initialize_feature_usage(
    db: AsyncSession,
    device_id: str,
    features: list[str]
) -> list[DeviceFeatureUsage]:
    """
    Initialize feature usage tracking for a device.
    
    Creates DeviceFeatureUsage records for all device features,
    initially marked as unconfigured (Story 2.3 will detect configured).
    
    Story AI2.2: Capability Database Schema & Storage
    Epic AI-2: Device Intelligence System
    
    Args:
        db: Database session
        device_id: Device instance ID (e.g., "light.kitchen_switch")
        features: List of feature names from capabilities
        
    Returns:
        List of created DeviceFeatureUsage records
        
    Example:
        await initialize_feature_usage(
            db=session,
            device_id="light.kitchen_switch",
            features=["led_notifications", "smart_bulb_mode", "auto_off_timer"]
        )
    """
    try:
        usage_records = []
        
        for feature_name in features:
            # Check if usage record exists
            result = await db.execute(
                select(DeviceFeatureUsage).where(
                    DeviceFeatureUsage.device_id == device_id,
                    DeviceFeatureUsage.feature_name == feature_name
                )
            )
            existing = result.scalars().first()
            
            if existing:
                # Update existing
                existing.last_checked = datetime.now(timezone.utc)
                usage = existing
            else:
                # Create new
                usage = DeviceFeatureUsage(
                    device_id=device_id,
                    feature_name=feature_name,
                    configured=False,  # Story 2.3 will detect configured features
                    discovered_date=datetime.now(timezone.utc),
                    last_checked=datetime.now(timezone.utc)
                )
                db.add(usage)
            
            usage_records.append(usage)
        
        await db.commit()
        logger.debug(f"✅ Initialized {len(features)} feature usage records for {device_id}")
        
        return usage_records
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to initialize feature usage for {device_id}: {e}", exc_info=True)
        raise


async def get_device_feature_usage(db: AsyncSession, device_id: str) -> List[DeviceFeatureUsage]:
    """
    Get all feature usage records for a device.
    
    Args:
        db: Database session
        device_id: Device instance ID
        
    Returns:
        List of DeviceFeatureUsage records for the device
    """
    try:
        result = await db.execute(
            select(DeviceFeatureUsage).where(DeviceFeatureUsage.device_id == device_id)
        )
        usage = result.scalars().all()
        
        logger.debug(f"Retrieved {len(usage)} feature usage records for {device_id}")
        return list(usage)
        
    except Exception as e:
        logger.error(f"Failed to get feature usage for {device_id}: {e}", exc_info=True)
        raise


async def get_capability_stats(db: AsyncSession) -> Dict:
    """
    Get capability database statistics.
    
    Returns:
        Dictionary with capability and usage statistics
        
    Example:
        stats = await get_capability_stats(db)
        print(f"Total models: {stats['total_models']}")
        print(f"By manufacturer: {stats['by_manufacturer']}")
    """
    try:
        # Total device models
        total_result = await db.execute(select(func.count()).select_from(DeviceCapability))
        total_models = total_result.scalar() or 0
        
        # Models by manufacturer
        manuf_result = await db.execute(
            select(DeviceCapability.manufacturer, func.count())
            .group_by(DeviceCapability.manufacturer)
        )
        by_manufacturer = {row[0]: row[1] for row in manuf_result.all()}
        
        # Total feature usage records
        usage_result = await db.execute(select(func.count()).select_from(DeviceFeatureUsage))
        total_usage_records = usage_result.scalar() or 0
        
        # Configured vs unconfigured features
        configured_result = await db.execute(
            select(DeviceFeatureUsage.configured, func.count())
            .group_by(DeviceFeatureUsage.configured)
        )
        by_configured = {bool(row[0]): row[1] for row in configured_result.all()}
        
        return {
            'total_models': total_models,
            'by_manufacturer': by_manufacturer,
            'total_usage_records': total_usage_records,
            'configured_features': by_configured.get(True, 0),
            'unconfigured_features': by_configured.get(False, 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to get capability stats: {e}", exc_info=True)
        raise


# ============================================================================
# Synergy Opportunity CRUD Operations (Epic AI-3, Story AI3.1)
# ============================================================================

async def store_synergy_opportunity(db: AsyncSession, synergy_data: Dict) -> SynergyOpportunity:
    """
    Store a synergy opportunity in database.
    
    Args:
        db: Database session
        synergy_data: Synergy opportunity dictionary from detector
    
    Returns:
        Created SynergyOpportunity instance
        
    Story AI3.1: Device Synergy Detector Foundation
    """
    import json
    
    try:
        synergy = SynergyOpportunity(
            synergy_id=synergy_data['synergy_id'],
            synergy_type=synergy_data['synergy_type'],
            device_ids=json.dumps(synergy_data['devices']),
            opportunity_metadata=synergy_data.get('opportunity_metadata', {}),
            impact_score=synergy_data['impact_score'],
            complexity=synergy_data['complexity'],
            confidence=synergy_data['confidence'],
            area=synergy_data.get('area'),
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(synergy)
        await db.commit()
        await db.refresh(synergy)
        
        logger.debug(f"Stored synergy opportunity: {synergy.synergy_id}")
        return synergy
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to store synergy opportunity: {e}", exc_info=True)
        raise


async def store_synergy_opportunities(db: AsyncSession, synergies: List[Dict]) -> int:
    """
    Store multiple synergy opportunities in database.
    
    Args:
        db: Database session
        synergies: List of synergy dictionaries from detector
    
    Returns:
        Number of synergies stored
        
    Story AI3.1: Device Synergy Detector Foundation
    """
    import json
    
    if not synergies:
        logger.warning("No synergies to store")
        return 0
    
    try:
        stored_count = 0
        
        for synergy_data in synergies:
            # Create metadata dict from synergy data
            metadata = {
                'trigger_entity': synergy_data.get('trigger_entity'),
                'trigger_name': synergy_data.get('trigger_name'),
                'action_entity': synergy_data.get('action_entity'),
                'action_name': synergy_data.get('action_name'),
                'relationship': synergy_data.get('relationship'),
                'rationale': synergy_data.get('rationale')
            }
            
            synergy = SynergyOpportunity(
                synergy_id=synergy_data['synergy_id'],
                synergy_type=synergy_data['synergy_type'],
                device_ids=json.dumps(synergy_data['devices']),
                opportunity_metadata=metadata,
                impact_score=synergy_data['impact_score'],
                complexity=synergy_data['complexity'],
                confidence=synergy_data['confidence'],
                area=synergy_data.get('area'),
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(synergy)
            stored_count += 1
        
        await db.commit()
        logger.info(f"Stored {stored_count} synergy opportunities")
        return stored_count
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to store synergies: {e}", exc_info=True)
        raise


async def get_synergy_opportunities(
    db: AsyncSession,
    synergy_type: Optional[str] = None,
    min_confidence: float = 0.0,
    limit: int = 100
) -> List[SynergyOpportunity]:
    """
    Retrieve synergy opportunities from database.
    
    Args:
        db: Database session
        synergy_type: Optional filter by synergy type
        min_confidence: Minimum confidence threshold
        limit: Maximum number of results
    
    Returns:
        List of SynergyOpportunity instances
        
    Story AI3.1: Device Synergy Detector Foundation
    """
    try:
        query = select(SynergyOpportunity).where(
            SynergyOpportunity.confidence >= min_confidence
        )
        
        if synergy_type:
            query = query.where(SynergyOpportunity.synergy_type == synergy_type)
        
        query = query.order_by(SynergyOpportunity.impact_score.desc()).limit(limit)
        
        result = await db.execute(query)
        synergies = result.scalars().all()
        
        logger.debug(f"Retrieved {len(synergies)} synergy opportunities")
        return list(synergies)
        
    except Exception as e:
        logger.error(f"Failed to get synergies: {e}", exc_info=True)
        raise


async def get_synergy_stats(db: AsyncSession) -> Dict:
    """
    Get synergy opportunity statistics.
    
    Returns:
        Dictionary with synergy statistics
        
    Story AI3.1: Device Synergy Detector Foundation
    """
    try:
        # Total synergies
        total_result = await db.execute(select(func.count()).select_from(SynergyOpportunity))
        total = total_result.scalar() or 0
        
        # By type
        type_result = await db.execute(
            select(SynergyOpportunity.synergy_type, func.count())
            .group_by(SynergyOpportunity.synergy_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}
        
        # By complexity
        complexity_result = await db.execute(
            select(SynergyOpportunity.complexity, func.count())
            .group_by(SynergyOpportunity.complexity)
        )
        by_complexity = {row[0]: row[1] for row in complexity_result.all()}
        
        # Average impact score
        avg_impact_result = await db.execute(
            select(func.avg(SynergyOpportunity.impact_score))
        )
        avg_impact = avg_impact_result.scalar() or 0.0
        
        return {
            'total_synergies': total,
            'by_type': by_type,
            'by_complexity': by_complexity,
            'avg_impact_score': round(float(avg_impact), 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to get synergy stats: {e}", exc_info=True)
        raise

