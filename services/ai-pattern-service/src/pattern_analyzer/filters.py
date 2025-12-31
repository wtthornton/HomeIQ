"""
Shared Filtering Module for Pattern Detection

Centralizes filtering logic for external data sources, system noise, and non-actionable entities.
Used by all pattern detectors to ensure consistent filtering.

Epic 39: Pattern and Synergy Validation Improvements
Based on recommendations from FINAL_RECOMMENDATIONS_PATTERN_SYNERGY_VALIDATION.md
"""

import logging
from typing import Set

import pandas as pd

logger = logging.getLogger(__name__)

# System noise filtering constants
EXCLUDED_DOMAINS: Set[str] = {
    'image',      # Maps, camera images
    'event',      # System events
    'update',     # Software updates
    'camera',     # Camera entities
    'button',     # Buttons (not automation targets)
    'weather',    # Weather entities (external data)
    'calendar',   # Calendar entities (external events)
}

EXCLUDED_ENTITY_PREFIXES: list[str] = [
    'sensor.home_assistant_',  # System sensors
    'sensor.slzb_',            # Coordinator sensors
    'image.',                  # Images/maps (Roborock, cameras)
    'event.',                  # System events
    'binary_sensor.system_',   # System binary sensors
    'camera.',                 # Camera entities
    'button.',                 # Button entities
    'update.',                 # Update entities
]

# External data patterns (sports, weather, calendar, energy APIs)
EXTERNAL_DATA_PATTERNS: list[str] = [
    '_tracker',                # External API trackers (sports, etc.)
    'team_tracker',            # Sports team tracker entities
    'nfl_', 'nhl_', 'mlb_', 'nba_', 'ncaa_',  # Sports league entities
    'weather_',                # Weather API entities
    'openweathermap_',         # OpenWeatherMap integration
    'carbon_intensity_',       # Carbon intensity API
    'electricity_pricing_',    # Electricity pricing API
    'national_grid_',          # National Grid API
    'calendar_',               # Calendar entities (external events)
]

# System monitoring patterns
SYSTEM_NOISE_PATTERNS: list[str] = [
    '_cpu_',                   # CPU/monitoring sensors
    '_temp',                   # Temperature sensors (system)
    '_chip_',                  # Chip temperature sensors
    'coordinator_',            # Coordinator-related sensors
    '_battery',                # Battery level sensors
    '_memory_',                # Memory sensors
    '_signal_strength',        # Signal strength
    '_linkquality',            # Zigbee link quality
    '_update_',                # Update status
    '_uptime',                 # Uptime sensors
    '_last_seen',              # Last seen timestamps
]

# Domain categorization for pattern validation
ACTIONABLE_DOMAINS: Set[str] = {
    'light', 'switch', 'climate', 'media_player',
    'lock', 'cover', 'fan', 'vacuum', 'scene'
}

TRIGGER_DOMAINS: Set[str] = {
    'binary_sensor', 'sensor', 'device_tracker',
    'person', 'input_boolean', 'input_select'
}

PASSIVE_DOMAINS: Set[str] = {
    'image', 'camera', 'weather', 'sun', 'event', 'update', 'calendar'
}


class EventFilter:
    """
    Centralized event filtering for pattern detection.
    
    Filters out:
    - External data sources (sports, weather, calendar, energy APIs)
    - System noise (monitoring sensors, coordinators)
    - Non-actionable entities (images, cameras, buttons)
    """
    
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
    
    @staticmethod
    def is_external_data_entity(entity_id: str) -> bool:
        """
        Check if entity ID represents external data source.
        
        External data sources include:
        - Sports/team trackers
        - Weather APIs
        - Calendar entities
        - Energy/carbon APIs
        
        Args:
            entity_id: Entity ID to check
            
        Returns:
            True if external data source, False otherwise
        """
        entity_lower = entity_id.lower()
        domain = EventFilter.get_domain(entity_id)
        
        # Check domain-level exclusions
        if domain in {'weather', 'calendar'}:
            return True
        
        # Check external data patterns
        for pattern in EXTERNAL_DATA_PATTERNS:
            if pattern in entity_lower:
                return True
        
        return False
    
    @staticmethod
    def is_system_noise(entity_id: str) -> bool:
        """
        Check if entity ID represents system noise.
        
        System noise includes:
        - System sensors
        - Coordinator sensors
        - Monitoring sensors (CPU, memory, temperature)
        - Update entities
        
        Args:
            entity_id: Entity ID to check
            
        Returns:
            True if system noise, False otherwise
        """
        domain = EventFilter.get_domain(entity_id)
        
        # Check domain-level exclusions
        if domain in EXCLUDED_DOMAINS:
            return True
        
        # Check prefixes
        for prefix in EXCLUDED_ENTITY_PREFIXES:
            if entity_id.startswith(prefix):
                return True
        
        # Check system noise patterns
        entity_lower = entity_id.lower()
        for pattern in SYSTEM_NOISE_PATTERNS:
            if pattern in entity_lower:
                return True
        
        return False
    
    @staticmethod
    def is_actionable_entity(entity_id: str) -> bool:
        """
        Check if entity ID represents an actionable (user-controllable) device.
        
        Actionable entities are those that can be controlled or used in automations:
        - Lights, switches, climate, media players
        - Locks, covers, fans, vacuums
        - Sensors that trigger automations
        
        Args:
            entity_id: Entity ID to check
            
        Returns:
            True if actionable, False otherwise
        """
        # Exclude external data and system noise
        if EventFilter.is_external_data_entity(entity_id):
            return False
        
        if EventFilter.is_system_noise(entity_id):
            return False
        
        return True
    
    @staticmethod
    def filter_events(events_df: pd.DataFrame, entity_column: str = 'entity_id') -> pd.DataFrame:
        """
        Filter events DataFrame to exclude external data and system noise.
        
        This is the main pre-filtering method to use before pattern detection.
        
        Args:
            events_df: DataFrame containing events with entity_id column
            entity_column: Name of column containing entity IDs (default: 'entity_id')
            
        Returns:
            Filtered DataFrame with only actionable events
        """
        if events_df.empty:
            return events_df
        
        if entity_column not in events_df.columns:
            logger.warning(f"Column '{entity_column}' not found in events DataFrame. Available columns: {events_df.columns.tolist()}")
            return events_df
        
        original_count = len(events_df)
        
        # Create mask for actionable events
        mask = events_df[entity_column].apply(EventFilter.is_actionable_entity)
        filtered_df = events_df[mask].copy()
        
        filtered_count = len(filtered_df)
        excluded_count = original_count - filtered_count
        
        if excluded_count > 0:
            logger.info(
                f"Filtered events: {original_count} → {filtered_count} "
                f"({excluded_count} excluded: external data/system noise)"
            )
        
        return filtered_df
    
    @staticmethod
    def filter_external_data_sources(events_df: pd.DataFrame, entity_column: str = 'entity_id') -> pd.DataFrame:
        """
        Filter out only external data sources (sports, weather, calendar, energy APIs).
        
        This is a more targeted filter that only removes external data,
        keeping system sensors that might be useful for patterns.
        
        Args:
            events_df: DataFrame containing events with entity_id column
            entity_column: Name of column containing entity IDs (default: 'entity_id')
            
        Returns:
            Filtered DataFrame with external data sources removed
        """
        if events_df.empty:
            return events_df
        
        if entity_column not in events_df.columns:
            logger.warning(f"Column '{entity_column}' not found in events DataFrame")
            return events_df
        
        original_count = len(events_df)
        
        # Create mask excluding external data
        mask = ~events_df[entity_column].apply(EventFilter.is_external_data_entity)
        filtered_df = events_df[mask].copy()
        
        filtered_count = len(filtered_df)
        excluded_count = original_count - filtered_count
        
        if excluded_count > 0:
            logger.info(
                f"Filtered external data: {original_count} → {filtered_count} "
                f"({excluded_count} external data entities excluded)"
            )
        
        return filtered_df
