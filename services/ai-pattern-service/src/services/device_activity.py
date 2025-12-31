"""
Device Activity Service

Tracks and filters devices based on activity within time windows.
Used to filter patterns and synergies by device activity.

Based on recommendations from DEVICE_ACTIVITY_FILTERING_RECOMMENDATIONS.md
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Set

from ..clients.data_api_client import DataAPIClient
from ..config import settings

logger = logging.getLogger(__name__)

# Domain-specific activity windows (days)
# Based on device usage patterns from research
DOMAIN_ACTIVITY_WINDOWS = {
    # Daily/Weekly devices (7 days)
    'light': 7,
    'switch': 7,
    'lock': 7,
    'media_player': 7,
    'binary_sensor': 7,
    'vacuum': 7,
    
    # Monthly devices (30 days)
    'climate': 30,
    'cover': 30,
    'fan': 30,
    'sensor': 30,  # Most sensors
    
    # Seasonal devices (90 days)
    'irrigation': 90,
    
    # Default: 30 days
    'default': 30
}


class DeviceActivityService:
    """
    Service for tracking device activity and filtering by activity windows.
    
    Provides methods to:
    - Identify active devices from events
    - Get domain-specific activity windows
    - Filter patterns/synergies by device activity
    """
    
    def __init__(self, data_api_client: DataAPIClient | None = None):
        """
        Initialize device activity service.
        
        Args:
            data_api_client: Optional Data API client (will create if not provided)
        """
        self.data_api_client = data_api_client
        self._active_devices_cache: dict[tuple[int, datetime], Set[str]] = {}
        logger.info("DeviceActivityService initialized")
    
    @staticmethod
    def get_domain_activity_window(domain: str) -> int:
        """
        Get activity window for a domain.
        
        Args:
            domain: Device domain (e.g., 'light', 'switch', 'climate')
            
        Returns:
            Activity window in days
        """
        return DOMAIN_ACTIVITY_WINDOWS.get(domain, DOMAIN_ACTIVITY_WINDOWS['default'])
    
    @staticmethod
    def get_domain(entity_id: str) -> str:
        """
        Extract domain from entity ID.
        
        Args:
            entity_id: Entity ID (e.g., "light.bedroom", "sensor.temperature")
            
        Returns:
            Domain name (e.g., "light", "sensor")
        """
        if '.' in entity_id:
            return entity_id.split('.')[0]
        return ''
    
    async def get_active_devices(
        self,
        window_days: int = 30,
        data_api_client: DataAPIClient | None = None
    ) -> Set[str]:
        """
        Get set of active device/entity IDs from events.
        
        A device is considered active if it has events within the time window.
        
        Args:
            window_days: Time window in days (default: 30)
            data_api_client: Optional Data API client (uses self.data_api_client if not provided)
            
        Returns:
            Set of active entity IDs
        """
        # Use provided client or instance client
        client = data_api_client or self.data_api_client
        if not client:
            logger.warning("No Data API client available, returning empty set")
            return set()
        
        # Check cache
        cache_key = (window_days, datetime.now(timezone.utc).date())
        if cache_key in self._active_devices_cache:
            logger.debug(f"Using cached active devices for {window_days}-day window")
            return self._active_devices_cache[cache_key]
        
        logger.info(f"Identifying active devices (last {window_days} days)...")
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=window_days)
            
            # Fetch events from Data API
            events_df = await client.fetch_events(
                start_time=start_time,
                end_time=end_time,
                limit=50000  # Reasonable limit
            )
            
            if events_df.empty:
                logger.info("No events found in time window")
                return set()
            
            # Extract unique entity IDs from events
            # Handle both 'entity_id' and 'device_id' columns
            entity_column = 'entity_id' if 'entity_id' in events_df.columns else 'device_id'
            if entity_column not in events_df.columns:
                logger.warning(f"Neither 'entity_id' nor 'device_id' found in events DataFrame")
                return set()
            
            active_entities = set(events_df[entity_column].dropna().unique())
            
            logger.info(f"Found {len(active_entities)} active entities in last {window_days} days")
            
            # Cache result (for today only)
            self._active_devices_cache[cache_key] = active_entities
            
            return active_entities
            
        except Exception as e:
            logger.error(f"Failed to get active devices: {e}", exc_info=True)
            return set()
    
    def is_device_active(
        self,
        entity_id: str,
        active_devices: Set[str]
    ) -> bool:
        """
        Check if a device/entity is active.
        
        Args:
            entity_id: Entity ID to check
            active_devices: Set of active entity IDs
            
        Returns:
            True if device is active, False otherwise
        """
        return entity_id in active_devices
    
    def filter_patterns_by_activity(
        self,
        patterns: list[dict],
        active_devices: Set[str]
    ) -> list[dict]:
        """
        Filter patterns to only include those with active devices.
        
        Args:
            patterns: List of pattern dictionaries
            active_devices: Set of active entity IDs
            
        Returns:
            Filtered list of patterns
        """
        if not active_devices:
            logger.warning("No active devices provided, returning all patterns")
            return patterns
        
        filtered_patterns = []
        for pattern in patterns:
            # Extract device/entity IDs from pattern
            pattern_entities = self._extract_pattern_entities(pattern)
            
            # Check if any entity in pattern is active
            if any(entity_id in active_devices for entity_id in pattern_entities):
                filtered_patterns.append(pattern)
        
        logger.info(
            f"Filtered patterns: {len(patterns)} → {len(filtered_patterns)} "
            f"({len(patterns) - len(filtered_patterns)} inactive patterns removed)"
        )
        
        return filtered_patterns
    
    def filter_synergies_by_activity(
        self,
        synergies: list[dict],
        active_devices: Set[str]
    ) -> list[dict]:
        """
        Filter synergies to only include those with active devices.
        
        Args:
            synergies: List of synergy dictionaries
            active_devices: Set of active entity IDs
            
        Returns:
            Filtered list of synergies
        """
        if not active_devices:
            logger.warning("No active devices provided, returning all synergies")
            return synergies
        
        filtered_synergies = []
        for synergy in synergies:
            # Extract device/entity IDs from synergy
            synergy_entities = self._extract_synergy_entities(synergy)
            
            # Check if any entity in synergy is active
            if any(entity_id in active_devices for entity_id in synergy_entities):
                filtered_synergies.append(synergy)
        
        logger.info(
            f"Filtered synergies: {len(synergies)} → {len(filtered_synergies)} "
            f"({len(synergies) - len(filtered_synergies)} inactive synergies removed)"
        )
        
        return filtered_synergies
    
    def _extract_pattern_entities(self, pattern: dict) -> Set[str]:
        """
        Extract entity IDs from a pattern dictionary.
        
        Args:
            pattern: Pattern dictionary
            
        Returns:
            Set of entity IDs in the pattern
        """
        entities = set()
        
        # Check for device_id field
        if 'device_id' in pattern:
            device_id = pattern['device_id']
            if device_id:
                # Handle co-occurrence patterns with '+' separator
                entities.update(device_id.split('+'))
        
        # Check for entities field
        if 'entities' in pattern:
            entities_list = pattern['entities']
            if isinstance(entities_list, list):
                entities.update(entities_list)
            elif isinstance(entities_list, str):
                # Try to parse as JSON
                try:
                    import json
                    parsed = json.loads(entities_list)
                    if isinstance(parsed, list):
                        entities.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Check for device1/device2 fields (co-occurrence patterns)
        if 'device1' in pattern:
            entities.add(pattern['device1'])
        if 'device2' in pattern:
            entities.add(pattern['device2'])
        
        return entities
    
    def _extract_synergy_entities(self, synergy: dict) -> Set[str]:
        """
        Extract entity IDs from a synergy dictionary.
        
        Args:
            synergy: Synergy dictionary
            
        Returns:
            Set of entity IDs in the synergy
        """
        entities = set()
        
        # Check for device_ids field
        if 'device_ids' in synergy:
            device_ids = synergy['device_ids']
            if isinstance(device_ids, list):
                entities.update(device_ids)
            elif isinstance(device_ids, str):
                # Try to parse as JSON
                try:
                    import json
                    parsed = json.loads(device_ids)
                    if isinstance(parsed, list):
                        entities.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Check for entities field
        if 'entities' in synergy:
            entities_list = synergy['entities']
            if isinstance(entities_list, list):
                entities.update(entities_list)
        
        # Check for trigger/action fields
        if 'trigger' in synergy:
            entities.add(synergy['trigger'])
        if 'action' in synergy:
            entities.add(synergy['action'])
        
        # Check for chain_devices field
        if 'chain_devices' in synergy:
            chain_devices = synergy['chain_devices']
            if isinstance(chain_devices, list):
                entities.update(chain_devices)
        
        return entities
