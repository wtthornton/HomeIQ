"""
Incremental Home Type Updater

Update home type profile incrementally (not full reprocessing).
Leverages existing incremental learning infrastructure.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from .home_type_profiler import HomeTypeProfiler

logger = logging.getLogger(__name__)


class IncrementalHomeTypeUpdater:
    """
    Update home type profile incrementally.
    
    Leverages existing incremental learning infrastructure.
    """
    
    def __init__(self, profiler: HomeTypeProfiler):
        """
        Initialize incremental updater.
        
        Args:
            profiler: HomeTypeProfiler instance
        """
        self.profiler = profiler
        logger.info("IncrementalHomeTypeUpdater initialized")
    
    async def incremental_update(
        self,
        home_id: str,
        new_devices: list[dict[str, Any]],
        new_events: list[dict[str, Any]],
        new_patterns: list[dict[str, Any]] | None = None,
        last_update_time: datetime | None = None,
        existing_profile: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Update home profile incrementally (not full reprocessing).
        
        Uses existing incremental learning patterns.
        
        Args:
            home_id: Home identifier
            new_devices: New devices added since last update
            new_events: New events since last update
            new_patterns: New patterns detected since last update
            last_update_time: Timestamp of last update
            existing_profile: Existing profile to update
        
        Returns:
            Updated profile dictionary
        """
        logger.info(f"Incremental update for home: {home_id}")
        
        if existing_profile is None:
            # Full reprocessing if no existing profile
            logger.warning("No existing profile, performing full reprocessing")
            return await self.profiler.profile_home(
                home_id=home_id,
                devices=new_devices,
                events=new_events,
                patterns=new_patterns
            )
        
        # Incremental update: merge new data with existing profile
        updated_profile = existing_profile.copy()
        
        # Update device composition
        if new_devices:
            device_comp = updated_profile.get('device_composition', {})
            device_comp['total_devices'] = device_comp.get('total_devices', 0) + len(new_devices)
            # Note: Full ratio recalculation would require all devices, so we skip for incremental
        
        # Update event patterns
        if new_events:
            event_patterns = updated_profile.get('event_patterns', {})
            event_patterns['total_events'] = event_patterns.get('total_events', 0) + len(new_events)
            # Note: events_per_day would need full event set to recalculate
        
        # Update behavior patterns
        if new_patterns:
            behavior = updated_profile.get('behavior_patterns', {})
            behavior['pattern_count'] = behavior.get('pattern_count', 0) + len(new_patterns)
        
        updated_profile['updated_at'] = datetime.now(timezone.utc).isoformat()
        updated_profile['last_update_time'] = last_update_time.isoformat() if last_update_time else None
        
        logger.info(f"✅ Incremental update complete for home: {home_id}")
        return updated_profile

