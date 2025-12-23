"""
Production Home Type Profiler

Profile single home for production use.
Lightweight, NUC-optimized: Statistical features only, batch processing.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from ..clients.data_api_client import DataAPIClient
from .home_type_profiler import HomeTypeProfiler

logger = logging.getLogger(__name__)


class ProductionHomeTypeProfiler:
    """
    Profile single home for production use.
    
    Lightweight, NUC-optimized:
    - Statistical features only (no heavy embeddings)
    - Batch processing (daily at 3 AM)
    - Incremental updates
    """
    
    def __init__(self, data_api_client: DataAPIClient):
        """
        Initialize production profiler.
        
        Args:
            data_api_client: Data API client for fetching devices and events
        """
        self.data_api = data_api_client
        self.profiler = HomeTypeProfiler()
        logger.info("ProductionHomeTypeProfiler initialized")
    
    async def profile_current_home(
        self,
        home_id: str = 'default'
    ) -> dict[str, Any]:
        """
        Profile current home from production data.
        
        Sources:
        - Devices (from SQLite via data-api)
        - Events (from InfluxDB, last 30 days)
        - Patterns (from pattern detection, optional)
        
        Args:
            home_id: Home identifier (default: 'default')
        
        Returns:
            Home profile dictionary
        """
        logger.info(f"Profiling home: {home_id}")
        
        # Fetch devices
        try:
            devices = await self.data_api.fetch_devices(limit=1000)
            logger.info(f"Fetched {len(devices)} devices")
        except Exception as e:
            logger.error(f"Failed to fetch devices: {e}")
            devices = []
        
        # Fetch entities to get entity_id mappings
        try:
            entities = await self.data_api.fetch_entities(limit=1000)
            # Create mapping from device_id to entity_ids
            device_to_entities: dict[str, list[str]] = {}
            for entity in entities:
                device_id = entity.get('device_id', '')
                entity_id = entity.get('entity_id', '')
                if device_id and entity_id:
                    if device_id not in device_to_entities:
                        device_to_entities[device_id] = []
                    device_to_entities[device_id].append(entity_id)
            logger.info(f"Fetched {len(entities)} entities, mapped to {len(device_to_entities)} devices")
        except Exception as e:
            logger.warning(f"Failed to fetch entities: {e}")
            device_to_entities = {}
        
        # Fetch events (last 30 days)
        events = []
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=30)
            
            # Fetch all events for the time period
            events_df = await self.data_api.fetch_events(
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            
            # Convert DataFrame to list of dicts for profiler
            # fetch_events always returns a DataFrame (may be empty)
            if isinstance(events_df, pd.DataFrame) and not events_df.empty:
                events = events_df.to_dict('records')
                # Ensure events have expected format
                for event in events:
                    # Convert timestamp to ISO string if needed
                    if 'timestamp' in event and hasattr(event['timestamp'], 'isoformat'):
                        event['timestamp'] = event['timestamp'].isoformat()
                    # Ensure event_type field
                    if 'event_type' not in event:
                        event['event_type'] = 'state_changed'
                    # Ensure attributes dict
                    if 'attributes' not in event:
                        event['attributes'] = {}
                    # Add device_type to attributes if available
                    if 'domain' in event:
                        event['attributes']['device_type'] = event['domain']
            
            logger.info(f"Fetched {len(events)} events")
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            events = []
        
        # Convert devices to format expected by profiler
        # Profiler expects: entity_id, device_type, area, category, device_class
        profiler_devices = []
        for device in devices:
            device_id = device.get('device_id', '')
            # Get entity_ids for this device
            entity_ids = device_to_entities.get(device_id, [])
            
            # If no entities, skip or create a placeholder
            if not entity_ids:
                continue
            
            # Create device entry for each entity (or just first one)
            for entity_id in entity_ids[:1]:  # Use first entity per device
                # Extract device type from entity_id domain
                domain = entity_id.split('.')[0] if '.' in entity_id else 'sensor'
                
                profiler_devices.append({
                    'entity_id': entity_id,
                    'device_type': domain,
                    'area': device.get('area_id', 'Unknown'),
                    'category': self._infer_category(domain),
                    'device_class': None  # Could be enhanced
                })
        
        # Extract areas from devices
        areas = []
        area_names = set()
        for device in devices:
            area_name = device.get('area_id', 'Unknown')
            if area_name and area_name not in area_names:
                areas.append({
                    'name': area_name,
                    'type': 'indoor'  # Default, could be enhanced
                })
                area_names.add(area_name)
        
        # Profile home
        profile = await self.profiler.profile_home(
            home_id=home_id,
            devices=profiler_devices,
            events=events,
            areas=areas,
            patterns=None  # Could fetch from pattern detection if needed
        )
        
        logger.info(f"✅ Profiled home: {home_id}")
        return profile
    
    def _infer_category(self, device_type: str) -> str:
        """
        Infer device category from device type.
        
        Args:
            device_type: Device type/domain (e.g., 'light', 'sensor')
        
        Returns:
            Category string
        """
        category_map = {
            'binary_sensor': 'security',
            'alarm_control_panel': 'security',
            'lock': 'security',
            'camera': 'security',
            'climate': 'climate',
            'sensor': 'monitoring',
            'light': 'lighting',
            'switch': 'appliance',
            'vacuum': 'appliance',
            'media_player': 'appliance',
            'cover': 'appliance',
            'fan': 'climate',
        }
        return category_map.get(device_type, 'general')

