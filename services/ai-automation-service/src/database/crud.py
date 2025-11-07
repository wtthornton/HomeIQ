"""
CRUD operations for AI Automation Service database
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, case, and_, or_
from typing import List, Dict, Optional, Union, Any, Tuple
from datetime import datetime, timedelta, timezone
import logging

from .models import (
    Pattern,
    PatternHistory,
    Suggestion,
    UserFeedback,
    DeviceCapability,
    DeviceFeatureUsage,
    SynergyOpportunity,
    ManualRefreshTrigger,
    AnalysisRunStatus,
    SystemSettings,
    TrainingRun,
    get_system_settings_defaults,
)
from ..pattern_detection.pattern_filters import validate_pattern

logger = logging.getLogger(__name__)


def _get_attr_safe(obj: Union[Dict, Any], attr: str, default: Any) -> Any:
    """
    Safely get attribute from dict or object.
    
    Context7 Best Practice: Type-safe attribute access that handles
    both dict and SQLAlchemy objects without raising exceptions.
    
    Args:
        obj: Dictionary or object instance (e.g., SQLAlchemy model)
        attr: Attribute name
        default: Default value if attribute not found
    
    Returns:
        Attribute value or default
    """
    if isinstance(obj, dict):
        return obj.get(attr, default)
    else:
        return getattr(obj, attr, default)


# ============================================================================
# System Settings CRUD Operations
# ============================================================================

_SYSTEM_SETTINGS_FIELDS = {
    'schedule_enabled',
    'schedule_time',
    'min_confidence',
    'max_suggestions',
    'enabled_categories',
    'budget_limit',
    'notifications_enabled',
    'notification_email',
    'soft_prompt_enabled',
    'soft_prompt_model_dir',
    'soft_prompt_confidence_threshold',
    'guardrail_enabled',
    'guardrail_model_name',
    'guardrail_threshold',
}


async def get_system_settings(db: AsyncSession) -> SystemSettings:
    """Fetch persisted system settings, seeding defaults if necessary."""

    result = await db.execute(select(SystemSettings).limit(1))
    system_settings = result.scalar_one_or_none()

    if not system_settings:
        defaults = get_system_settings_defaults()
        system_settings = SystemSettings(**defaults)
        system_settings.id = 1
        db.add(system_settings)
        await db.commit()
        await db.refresh(system_settings)
        logger.info("Created default system settings record")

    return system_settings


async def update_system_settings(db: AsyncSession, updates: Dict[str, Any]) -> SystemSettings:
    """Persist new system settings values."""

    settings_record = await get_system_settings(db)

    for field, value in updates.items():
        if field not in _SYSTEM_SETTINGS_FIELDS:
            logger.debug("Ignoring unknown system settings field: %s", field)
            continue

        if field == 'enabled_categories' and isinstance(value, dict):
            # Merge with defaults to avoid missing keys
            merged_categories = {**_get_attr_safe(settings_record, 'enabled_categories', {}), **value}
            setattr(settings_record, field, merged_categories)
        elif value is not None:
            setattr(settings_record, field, value)

    settings_record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(settings_record)

    return settings_record


# ============================================================================
# Training Run CRUD Operations
# ============================================================================

async def get_active_training_run(db: AsyncSession) -> Optional[TrainingRun]:
    """Fetch the currently running training run if one exists."""

    result = await db.execute(
        select(TrainingRun).where(TrainingRun.status == 'running').limit(1)
    )
    return result.scalar_one_or_none()


async def create_training_run(db: AsyncSession, values: Dict[str, Any]) -> TrainingRun:
    """Create and persist a new training run entry."""

    run = TrainingRun(**values)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def update_training_run(db: AsyncSession, run_id: int, updates: Dict[str, Any]) -> Optional[TrainingRun]:
    """Update an existing training run record."""

    result = await db.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return None

    for field, value in updates.items():
        if hasattr(run, field):
            setattr(run, field, value)

    await db.commit()
    await db.refresh(run)
    return run


async def list_training_runs(db: AsyncSession, limit: int = 20) -> List[TrainingRun]:
    """Return recent training runs ordered by newest first."""

    result = await db.execute(
        select(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ============================================================================
# Pattern CRUD Operations
# ============================================================================

async def store_patterns(db: AsyncSession, patterns: List[Dict]) -> int:
    """
    Store detected patterns in database with history tracking.
    
    Phase 1: Enhanced to track pattern history and update trend cache.
    
    Args:
        db: Database session
        patterns: List of pattern dictionaries from detector
    
    Returns:
        Number of patterns stored/updated
    """
    if not patterns:
        logger.warning("No patterns to store")
        return 0
    
    try:
        from ..integration.pattern_history_validator import PatternHistoryValidator
        
        history_validator = PatternHistoryValidator(db)
        stored_count = 0
        now = datetime.now(timezone.utc)
        
        # Filter out invalid patterns before storing
        valid_patterns = [p for p in patterns if validate_pattern(p)]
        filtered_count = len(patterns) - len(valid_patterns)
        
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} invalid patterns (non-actionable devices, low occurrences, or low confidence)")
        
        for pattern_data in valid_patterns:
            # Check if pattern already exists (same type and device)
            query = select(Pattern).where(
                Pattern.pattern_type == pattern_data['pattern_type'],
                Pattern.device_id == pattern_data['device_id']
            )
            result = await db.execute(query)
            existing_pattern = result.scalar_one_or_none()
            
            if existing_pattern:
                # Update existing pattern
                existing_pattern.confidence = pattern_data['confidence']
                existing_pattern.occurrences = pattern_data['occurrences']
                existing_pattern.pattern_metadata = pattern_data.get('metadata', {})
                existing_pattern.last_seen = now
                existing_pattern.updated_at = now
                pattern = existing_pattern
                logger.debug(f"Updated existing pattern {pattern.id} for {pattern.device_id}")
            else:
                # Create new pattern
                pattern = Pattern(
                    pattern_type=pattern_data['pattern_type'],
                    device_id=pattern_data['device_id'],
                    pattern_metadata=pattern_data.get('metadata', {}),
                    confidence=pattern_data['confidence'],
                    occurrences=pattern_data['occurrences'],
                    created_at=now,
                    updated_at=now,
                    first_seen=now,
                    last_seen=now,
                    confidence_history_count=1
                )
                db.add(pattern)
            
            stored_count += 1
        
        # Commit to get pattern IDs
        await db.flush()
        
        # Store history snapshots and update trends
        for i, pattern_data in enumerate(valid_patterns):
            # Find the pattern we just created/updated
            query = select(Pattern).where(
                Pattern.pattern_type == pattern_data['pattern_type'],
                Pattern.device_id == pattern_data['device_id']
            )
            result = await db.execute(query)
            pattern = result.scalar_one_or_none()
            
            if pattern:
                # Store history snapshot
                try:
                    await history_validator.store_snapshot(
                        pattern_id=pattern.id,
                        confidence=pattern.confidence,
                        occurrences=pattern.occurrences
                    )
                    
                    # Update trend cache (async, but we'll wait for it)
                    if pattern.confidence_history_count >= 2:
                        await history_validator.update_pattern_trend_cache(pattern.id)
                except Exception as e:
                    # Log but don't fail if history storage fails
                    logger.warning(f"Failed to store history for pattern {pattern.id}: {e}")
        
        await db.commit()
        logger.info(f"✅ Stored {stored_count} patterns in database with history tracking")
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
        
        # Unique devices - need to handle combined device_ids (e.g., "device1+device2" for co-occurrence patterns)
        # Fetch all device_ids and split by '+' to get individual devices
        device_ids_result = await db.execute(
            select(Pattern.device_id).select_from(Pattern)
        )
        device_ids = [row[0] for row in device_ids_result.all()]
        
        # Split combined device_ids (co-occurrence patterns) and collect unique devices
        unique_device_set = set()
        for device_id in device_ids:
            if device_id:
                # Split by '+' to handle co-occurrence patterns (e.g., "device1+device2")
                individual_devices = device_id.split('+')
                unique_device_set.update(individual_devices)
        
        unique_devices = len(unique_device_set)
        
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
    """Store automation suggestion in database with enriched metadata."""
    try:
        if 'title' not in suggestion_data:
            raise ValueError("suggestion_data must include a title field")
        if 'confidence' not in suggestion_data:
            raise ValueError("suggestion_data must include a confidence field")

        description_text = suggestion_data.get('description_only') or suggestion_data.get('description') or ''

        conversation_history = suggestion_data.get('conversation_history')
        if isinstance(conversation_history, str):
            try:
                import json
                conversation_history = json.loads(conversation_history)
            except Exception:
                conversation_history = []
        if conversation_history is None:
            conversation_history = []

        refinement_count = int(suggestion_data.get('refinement_count') or 0)

        status = suggestion_data.get('status', 'draft')

        device_capabilities = suggestion_data.get('device_capabilities') or {}

        device_info = suggestion_data.get('device_info') or []
        devices_involved = suggestion_data.get('devices_involved') or []

        def _collect_device_ids() -> List[str]:
            candidates: List[str] = []
            for key in ('device_id', 'device1', 'device2'):
                value = suggestion_data.get(key)
                if isinstance(value, str):
                    candidates.append(value)
                elif isinstance(value, list):
                    candidates.extend([v for v in value if isinstance(v, str)])

            metadata = suggestion_data.get('metadata') or {}
            if isinstance(metadata, dict):
                for key in ('device_id', 'device1', 'device2', 'devices'):
                    value = metadata.get(key)
                    if isinstance(value, str):
                        candidates.append(value)
                    elif isinstance(value, list):
                        candidates.extend([v for v in value if isinstance(v, str)])

            if isinstance(devices_involved, list):
                candidates.extend([v for v in devices_involved if isinstance(v, str)])

            return list(dict.fromkeys([c for c in candidates if c]))

        collected_ids = _collect_device_ids()

        if not device_info and collected_ids:
            def _friendly_name(entity_id: str) -> str:
                if '.' in entity_id:
                    name_part = entity_id.split('.', 1)[1]
                    return name_part.replace('_', ' ').title()
                return entity_id

            for entity_id in collected_ids:
                domain = entity_id.split('.', 1)[0] if '.' in entity_id else 'device'
                device_info.append({
                    'entity_id': entity_id,
                    'friendly_name': _friendly_name(entity_id),
                    'domain': domain,
                    'selected': True
                })

        if device_info:
            # Merge with existing device list stored in device_capabilities if present
            existing_devices = []
            if isinstance(device_capabilities, dict):
                existing_devices = device_capabilities.get('devices', []) or []
            else:
                device_capabilities = {}

            merged_devices: Dict[str, Dict[str, Any]] = {}
            for entry in existing_devices:
                entity_id = entry.get('entity_id') if isinstance(entry, dict) else None
                if entity_id:
                    merged_devices[entity_id] = entry
            for entry in device_info:
                entity_id = entry.get('entity_id') if isinstance(entry, dict) else None
                if entity_id:
                    merged_devices.setdefault(entity_id, entry)
            device_capabilities['devices'] = list(merged_devices.values())

        suggestion = Suggestion(
            pattern_id=suggestion_data.get('pattern_id'),
            title=suggestion_data['title'],
            description_only=description_text,
            automation_yaml=suggestion_data.get('automation_yaml'),
            status=status,
            confidence=suggestion_data['confidence'],
            category=suggestion_data.get('category'),
            priority=suggestion_data.get('priority'),
            conversation_history=conversation_history,
            refinement_count=refinement_count,
            device_capabilities=device_capabilities,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        if suggestion_data.get('ha_automation_id'):
            suggestion.ha_automation_id = suggestion_data.get('ha_automation_id')

        yaml_generated_at = suggestion_data.get('yaml_generated_at')
        if yaml_generated_at:
            if isinstance(yaml_generated_at, datetime):
                suggestion.yaml_generated_at = yaml_generated_at
            else:
                try:
                    suggestion.yaml_generated_at = datetime.fromisoformat(yaml_generated_at)
                except Exception:
                    pass

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
        feedback_summary = (
            select(
                UserFeedback.suggestion_id.label('suggestion_id'),
                func.sum(
                    case((UserFeedback.action == 'approved', 1), else_=0)
                ).label('approvals'),
                func.sum(
                    case((UserFeedback.action == 'rejected', 1), else_=0)
                ).label('rejections'),
                func.max(UserFeedback.created_at).label('last_feedback')
            )
            .group_by(UserFeedback.suggestion_id)
            .subquery()
        )

        approval_weight = func.coalesce(feedback_summary.c.approvals, 0)
        rejection_weight = func.coalesce(feedback_summary.c.rejections, 0)
        weighted_score = Suggestion.confidence + (approval_weight * 0.1) - (rejection_weight * 0.1)

        query = (
            select(
                Suggestion,
                weighted_score.label('weighted_score'),
                approval_weight.label('approvals'),
                rejection_weight.label('rejections'),
                feedback_summary.c.last_feedback.label('last_feedback')
            )
            .outerjoin(feedback_summary, feedback_summary.c.suggestion_id == Suggestion.id)
        )
        
        if status:
            query = query.where(Suggestion.status == status)
        
        query = query.order_by(weighted_score.desc(), Suggestion.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()

        suggestions: List[Suggestion] = []
        for suggestion, score, approvals, rejections, last_feedback in rows:
            suggestion.weighted_score = float(score) if score is not None else float(suggestion.confidence)
            suggestion.feedback_summary = {
                'approvals': int(approvals or 0),
                'rejections': int(rejections or 0),
                'last_feedback': last_feedback.isoformat() if last_feedback else None
            }
            suggestions.append(suggestion)
        
        logger.info(f"Retrieved {len(suggestions)} suggestions from database (feedback-weighted)")
        return suggestions
        
    except Exception as e:
        logger.error(f"Failed to retrieve suggestions: {e}", exc_info=True)
        raise


# ============================================================================
# Manual Refresh Audit Operations
# ============================================================================

async def can_trigger_manual_refresh(
    db: AsyncSession,
    cooldown_hours: int = 24
) -> Tuple[bool, Optional[datetime]]:
    """
    Determine whether a manual refresh can be triggered based on cooldown.
    """
    result = await db.execute(select(func.max(ManualRefreshTrigger.triggered_at)))
    last_trigger = result.scalar()

    if not last_trigger:
        return True, None

    now = datetime.now(timezone.utc)
    if now - last_trigger >= timedelta(hours=cooldown_hours):
        return True, last_trigger

    return False, last_trigger


async def record_manual_refresh(db: AsyncSession) -> ManualRefreshTrigger:
    """
    Record a manual refresh trigger event.
    """
    try:
        trigger = ManualRefreshTrigger(triggered_at=datetime.now(timezone.utc))
        db.add(trigger)
        await db.commit()
        await db.refresh(trigger)
        logger.info("Manual suggestion refresh recorded")
        return trigger
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to record manual refresh trigger: {e}", exc_info=True)
        raise


# ============================================================================
# Analysis Run Status Operations
# ============================================================================

def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        logger.debug(f"Failed to parse datetime from value: {value}")
        return None


async def record_analysis_run(db: AsyncSession, job_result: Dict) -> AnalysisRunStatus:
    """
    Persist the outcome of an analysis run for telemetry.
    """
    try:
        started_at = _parse_iso_datetime(job_result.get('start_time')) or datetime.now(timezone.utc)
        finished_at = _parse_iso_datetime(job_result.get('end_time'))

        run = AnalysisRunStatus(
            status=job_result.get('status', 'unknown'),
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=job_result.get('duration_seconds'),
            details=job_result
        )

        db.add(run)
        await db.commit()
        await db.refresh(run)
        logger.info("Analysis run status recorded")
        return run
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to record analysis run status: {e}", exc_info=True)
        raise


async def get_latest_analysis_run(db: AsyncSession) -> Optional[AnalysisRunStatus]:
    """
    Retrieve the most recent analysis run record.
    """
    result = await db.execute(
        select(AnalysisRunStatus).order_by(AnalysisRunStatus.started_at.desc()).limit(1)
    )
    return result.scalars().first()


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
        
        suggestion = await db.get(Suggestion, feedback_data['suggestion_id'])
        if suggestion:
            suggestion.updated_at = feedback.created_at
            if feedback_data['action'] == 'approved' and not suggestion.approved_at:
                suggestion.approved_at = feedback.created_at
        
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


async def get_capability_freshness(
    db: AsyncSession,
    max_age_hours: int = 24
) -> Dict[str, Any]:
    """
    Summarize freshness of capability data.

    Returns overall model counts plus a list of models whose capability
    snapshots are older than the provided threshold.
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=max_age_hours)

    total_result = await db.execute(select(func.count()).select_from(DeviceCapability))
    total_models = total_result.scalar() or 0

    if total_models == 0:
        return {
            "total_models": 0,
            "stale_count": 0,
            "stale_models": [],
            "threshold_iso": threshold.isoformat()
        }

    stale_query = await db.execute(
        select(DeviceCapability.device_model, DeviceCapability.last_updated)
        .where(
            or_(
                DeviceCapability.last_updated.is_(None),
                DeviceCapability.last_updated < threshold
            )
        )
    )
    stale_rows = stale_query.all()
    stale_models = [
        {
            "model": row[0],
            "last_updated": row[1].isoformat() if row[1] else None
        }
        for row in stale_rows
    ]

    newest_result = await db.execute(
        select(func.max(DeviceCapability.last_updated))
    )
    newest_timestamp = newest_result.scalar()

    return {
        "total_models": total_models,
        "stale_count": len(stale_models),
        "stale_models": stale_models,
        "threshold_iso": threshold.isoformat(),
        "newest_update": newest_timestamp.isoformat() if newest_timestamp else None
    }


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
    Phase 2: Supports pattern validation fields
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
            created_at=datetime.now(timezone.utc),
            # Phase 2: Pattern validation fields (defaults if not provided)
            pattern_support_score=synergy_data.get('pattern_support_score', 0.0),
            validated_by_patterns=synergy_data.get('validated_by_patterns', False),
            supporting_pattern_ids=json.dumps(synergy_data.get('supporting_pattern_ids', [])) if synergy_data.get('supporting_pattern_ids') else None
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


async def store_synergy_opportunities(
    db: AsyncSession,
    synergies: List[Dict],
    validate_with_patterns: bool = True,
    min_pattern_confidence: float = 0.7
) -> int:
    """
    Store multiple synergy opportunities in database with optional pattern validation.
    
    Phase 2: Enhanced to validate synergies against patterns.
    
    Args:
        db: Database session
        synergies: List of synergy dictionaries from detector
        validate_with_patterns: Whether to validate against patterns (default: True)
        min_pattern_confidence: Minimum pattern confidence for validation (default: 0.7)
    
    Returns:
        Number of synergies stored
        
    Story AI3.1: Device Synergy Detector Foundation
    Phase 2: Pattern-Synergy Cross-Validation
    """
    import json
    from sqlalchemy.exc import IntegrityError, PendingRollbackError
    
    if not synergies:
        logger.warning("No synergies to store")
        return 0
    
    # Ensure session is in a good state before starting
    try:
        # Check if session needs rollback
        if hasattr(db, 'in_transaction') and db.in_transaction():
            try:
                # Try a simple query to check session health
                await db.execute(select(1))
            except (PendingRollbackError, Exception):
                logger.warning("Session in bad state, rolling back before starting")
                await db.rollback()
    except Exception as e:
        logger.warning(f"Error checking session state: {e}, attempting rollback")
        try:
            await db.rollback()
        except Exception:
            pass  # Ignore rollback errors if session is already closed
    
    try:
        # Import validator if pattern validation is enabled
        pattern_validator = None
        if validate_with_patterns:
            try:
                from ..integration.pattern_synergy_validator import PatternSynergyValidator
                pattern_validator = PatternSynergyValidator(db)
            except ImportError:
                logger.warning("PatternSynergyValidator not available, skipping pattern validation")
                validate_with_patterns = False
        
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
                
                # Phase 2: Validate with patterns if enabled
                pattern_support_score = 0.0
                validated_by_patterns = False
                supporting_pattern_ids = []
                
                if validate_with_patterns and pattern_validator:
                    try:
                        validation_result = await pattern_validator.validate_synergy_with_patterns(
                            synergy_data, min_pattern_confidence
                        )
                        pattern_support_score = validation_result.get('pattern_support_score', 0.0)
                        validated_by_patterns = validation_result.get('validated_by_patterns', False)
                        supporting_patterns = validation_result.get('supporting_patterns', [])
                        supporting_pattern_ids = [p['pattern_id'] for p in supporting_patterns]
                        
                        # Optionally adjust confidence based on pattern support
                        confidence_adjustment = validation_result.get('recommended_confidence_adjustment', 0.0)
                        synergy_data['confidence'] = min(1.0, max(0.0, synergy_data['confidence'] + confidence_adjustment))
                        
                    except Exception as e:
                        logger.warning(f"Failed to validate synergy {synergy_data.get('synergy_id')} with patterns: {e}")
                
                # Epic AI-4: Extract n-level synergy fields
                synergy_depth = synergy_data.get('synergy_depth', 2)  # Default to 2 for pairs
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
                    existing_synergy.pattern_support_score = pattern_support_score
                    existing_synergy.validated_by_patterns = validated_by_patterns
                    existing_synergy.supporting_pattern_ids = json.dumps(supporting_pattern_ids) if supporting_pattern_ids else None
                    # Epic AI-4: Update n-level fields
                    existing_synergy.synergy_depth = synergy_depth
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
                        # Phase 2: Pattern validation fields
                        pattern_support_score=pattern_support_score,
                        validated_by_patterns=validated_by_patterns,
                        supporting_pattern_ids=json.dumps(supporting_pattern_ids) if supporting_pattern_ids else None,
                        # Epic AI-4: N-level synergy fields
                        synergy_depth=synergy_depth,
                        chain_devices=json.dumps(chain_devices) if chain_devices else None
                    )
                    db.add(synergy)
                    stored_count += 1
                    logger.debug(f"Added new synergy: {synergy_id}")
                    
            except IntegrityError as e:
                # Handle duplicate key errors gracefully
                await db.rollback()
                skipped_count += 1
                logger.warning(f"Skipped duplicate synergy {synergy_data.get('synergy_id')}: {e}")
                # Continue with next synergy
                continue
            except Exception as e:
                # Handle other errors for this specific synergy
                logger.warning(f"Error processing synergy {synergy_data.get('synergy_id')}: {e}")
                skipped_count += 1
                # Rollback this transaction and continue
                try:
                    await db.rollback()
                except Exception:
                    pass
                continue
        
        # Commit all changes
        try:
            await db.commit()
            validated_count = sum(1 for s in synergies if s.get('_validated', False)) if validate_with_patterns else 0
            logger.info(
                f"✅ Stored {stored_count} new, updated {updated_count} existing synergy opportunities"
                + (f" ({validated_count} validated by patterns)" if validate_with_patterns else "")
                + (f", skipped {skipped_count} duplicates/errors" if skipped_count > 0 else "")
            )
            return stored_count + updated_count
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error during commit: {e}", exc_info=True)
            # Return partial success
            return stored_count + updated_count
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit synergy opportunities: {e}", exc_info=True)
            raise
        
    except PendingRollbackError as e:
        logger.error(f"Session in bad state (PendingRollbackError): {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        raise Exception("Database session error - please retry the request")
    except Exception as e:
        logger.error(f"Failed to store synergy opportunities: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        raise


async def get_synergy_opportunities(
    db: AsyncSession,
    synergy_type: Optional[str] = None,
    min_confidence: float = 0.0,
    synergy_depth: Optional[int] = None,
    limit: int = 100,
    order_by_priority: bool = False,
    min_priority: Optional[float] = None
) -> List[SynergyOpportunity]:
    """
    Retrieve synergy opportunities from database.
    
    Args:
        db: Database session
        synergy_type: Optional filter by synergy type
        min_confidence: Minimum confidence threshold
        limit: Maximum number of results
        order_by_priority: If True, order by calculated priority score instead of impact_score
        min_priority: Optional minimum priority score threshold (only used if order_by_priority=True)
    
    Returns:
        List of SynergyOpportunity instances
        
    Story AI3.1: Device Synergy Detector Foundation
    Enhanced: Priority-based selection support
    """
    try:
        logger.info(f"get_synergy_opportunities called: synergy_type={synergy_type}, min_confidence={min_confidence}, synergy_depth={synergy_depth}, limit={limit}")
        
        # Build all conditions in a list, then apply with and_()
        conditions = [SynergyOpportunity.confidence >= min_confidence]
        
        if synergy_depth is not None:
            conditions.append(SynergyOpportunity.synergy_depth == synergy_depth)
            logger.info(f"Added synergy_depth filter: {synergy_depth}")
        
        if synergy_type:
            conditions.append(SynergyOpportunity.synergy_type == synergy_type)
            logger.info(f"Added synergy_type filter: {synergy_type}")
        
        # Apply all conditions with and_() to ensure proper SQL generation
        query = select(SynergyOpportunity).where(and_(*conditions))
        
        # Priority-based ordering
        if order_by_priority:
            # Calculate priority score in SQL (mirrors Python function logic)
            # Formula: (impact_score * 0.40) + (confidence * 0.25) + (pattern_support_score * 0.25) 
            #          + (validated_bonus * 0.10) + complexity_adjustment
            priority_score = (
                SynergyOpportunity.impact_score * 0.40 +
                SynergyOpportunity.confidence * 0.25 +
                func.coalesce(SynergyOpportunity.pattern_support_score, 0.0) * 0.25 +
                case(
                    (SynergyOpportunity.validated_by_patterns == True, 0.10),
                    else_=0.0
                ) +
                case(
                    (SynergyOpportunity.complexity == 'low', 0.10),
                    (SynergyOpportunity.complexity == 'high', -0.10),
                    else_=0.0
                )
            )
            
            # Order by priority score (descending)
            query = query.order_by(priority_score.desc()).limit(limit * 2 if min_priority else limit)
        else:
            # Default: order by impact_score (backward compatible)
            query = query.order_by(SynergyOpportunity.impact_score.desc()).limit(limit)
        
        # Log the query for debugging - compile to see actual SQL
        from sqlalchemy.dialects import sqlite
        compiled_query = query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
        logger.info(f"Executing query with filters: synergy_type={synergy_type!r}, min_confidence={min_confidence}")
        logger.info(f"Query SQL: {str(compiled_query)}")
        
        result = await db.execute(query)
        synergies = result.scalars().all()
        
        # Log results
        if synergies:
            logger.info(f"Query returned {len(synergies)} results. First result type: {synergies[0].synergy_type if synergies else 'N/A'}")
            # Log first few types to verify filtering
            types = [s.synergy_type for s in synergies[:5]]
            logger.info(f"First 5 result types: {types}")
        else:
            logger.info(f"Query returned 0 results")
        
        # Filter by min_priority in Python (SQLite compatibility - single home install, acceptable overhead)
        if order_by_priority and min_priority is not None:
            filtered_synergies = []
            for synergy in synergies:
                priority = calculate_synergy_priority_score(synergy)
                if priority >= min_priority:
                    filtered_synergies.append(synergy)
                if len(filtered_synergies) >= limit:
                    break
            synergies = filtered_synergies
        
        logger.debug(f"Retrieved {len(synergies)} synergy opportunities (order_by_priority={order_by_priority})")
        return list(synergies)
        
    except Exception as e:
        # Check if error is due to missing Phase 2 columns (pattern_support_score, etc.)
        error_str = str(e)
        if 'pattern_support_score' in error_str or 'validated_by_patterns' in error_str or 'supporting_pattern_ids' in error_str:
            logger.warning(
                "Phase 2 columns (pattern_support_score, validated_by_patterns, supporting_pattern_ids) "
                "not found in database. Migration may not have been run. "
                "Using explicit column selection to work around missing columns."
            )
            # Fallback: Use explicit column selection to avoid Phase 2 columns
            # Note: This will return objects without Phase 2 fields, but they can be accessed safely with getattr
            # Note: select is already imported at module level, so no need to re-import
            base_columns = [
                SynergyOpportunity.id,
                SynergyOpportunity.synergy_id,
                SynergyOpportunity.synergy_type,
                SynergyOpportunity.device_ids,
                SynergyOpportunity.opportunity_metadata,
                SynergyOpportunity.impact_score,
                SynergyOpportunity.complexity,
                SynergyOpportunity.confidence,
                SynergyOpportunity.area,
                SynergyOpportunity.created_at
            ]
            
            fallback_query = select(*base_columns).where(
                SynergyOpportunity.confidence >= min_confidence
            )
            
            if synergy_type:
                fallback_query = fallback_query.where(SynergyOpportunity.synergy_type == synergy_type)
            
            fallback_query = fallback_query.order_by(SynergyOpportunity.impact_score.desc()).limit(limit)
            
            result = await db.execute(fallback_query)
            rows = result.all()
            
            # Convert rows to SynergyOpportunity-like objects (they'll be missing Phase 2 fields)
            synergies = []
            for row in rows:
                # Create a minimal object with just the base fields
                # Phase 2 fields will be None/False when accessed via getattr
                synergy = SynergyOpportunity(
                    id=row.id,
                    synergy_id=row.synergy_id,
                    synergy_type=row.synergy_type,
                    device_ids=row.device_ids,
                    opportunity_metadata=row.opportunity_metadata,
                    impact_score=row.impact_score,
                    complexity=row.complexity,
                    confidence=row.confidence,
                    area=row.area,
                    created_at=row.created_at,
                    # Phase 2 fields with defaults
                    pattern_support_score=0.0,
                    validated_by_patterns=False,
                    supporting_pattern_ids=None
                )
                synergies.append(synergy)
            
            logger.debug(f"Retrieved {len(synergies)} synergy opportunities (using fallback query)")
            return synergies
        
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
        
        # Phase 2: Pattern validation statistics
        validated_count = 0
        avg_pattern_support = 0.0
        try:
            validated_result = await db.execute(
                select(func.count()).select_from(SynergyOpportunity).where(
                    SynergyOpportunity.validated_by_patterns == True
                )
            )
            validated_count = validated_result.scalar() or 0
            
            pattern_support_result = await db.execute(
                select(func.avg(SynergyOpportunity.pattern_support_score))
            )
            avg_pattern_support = pattern_support_result.scalar() or 0.0
        except Exception as e:
            # Phase 2 columns might not exist - use defaults
            logger.debug(f"Phase 2 columns not available in stats: {e}")
        
        result = {
            'total_synergies': total,
            'by_type': by_type,
            'by_complexity': by_complexity,
            'avg_impact_score': round(float(avg_impact), 2)
        }
        
        # Add Phase 2 stats if available
        if validated_count > 0 or avg_pattern_support > 0:
            result['validated_by_patterns'] = validated_count
            result['avg_pattern_support_score'] = round(float(avg_pattern_support), 2)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get synergy stats: {e}", exc_info=True)
        raise


def calculate_synergy_priority_score(synergy: Dict) -> float:
    """
    Calculate priority score for a synergy opportunity.
    
    Priority score formula:
    - 40% impact_score
    - 25% confidence
    - 25% pattern_support_score
    - 10% validation bonus (if validated_by_patterns)
    - Complexity adjustment: low=+0.10, medium=0, high=-0.10
    
    Args:
        synergy: Synergy opportunity dictionary or SynergyOpportunity instance
                 Must have: impact_score, confidence, complexity
                 Optional: pattern_support_score, validated_by_patterns
    
    Returns:
        Priority score (0.0-1.0)
        
    Example:
        synergy = {
            'impact_score': 0.7,
            'confidence': 0.8,
            'pattern_support_score': 0.75,
            'validated_by_patterns': True,
            'complexity': 'low'
        }
        score = calculate_synergy_priority_score(synergy)  # ~0.88
    """
    # Extract values safely (works with both dict and object)
    # Context7 Best Practice: Use helper function for type-safe attribute access
    impact_score = float(_get_attr_safe(synergy, 'impact_score', 0.5))
    confidence = float(_get_attr_safe(synergy, 'confidence', 0.7))
    pattern_support_score = float(_get_attr_safe(synergy, 'pattern_support_score', 0.0))
    validated_by_patterns = bool(_get_attr_safe(synergy, 'validated_by_patterns', False))
    complexity = str(_get_attr_safe(synergy, 'complexity', 'medium')).lower()
    
    # Base score calculation
    base_score = (
        impact_score * 0.40 +
        confidence * 0.25 +
        pattern_support_score * 0.25 +
        (0.10 if validated_by_patterns else 0.0)
    )
    
    # Complexity adjustment
    if complexity == 'low':
        base_score += 0.10
    elif complexity == 'high':
        base_score -= 0.10
    # medium complexity: no adjustment
    
    # Clamp to 0.0-1.0 range
    return max(0.0, min(1.0, base_score))
