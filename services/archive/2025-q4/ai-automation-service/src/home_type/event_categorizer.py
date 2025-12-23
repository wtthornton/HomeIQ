"""
Event Category Mapper

Map events to categories based on home type context.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventCategoryMapper:
    """
    Map events to categories based on home type.
    
    Categories:
    - security
    - climate
    - lighting
    - appliance
    - monitoring
    - general
    """
    
    # Category mappings by device type
    DEVICE_TYPE_CATEGORIES = {
        'binary_sensor': 'security',
        'alarm_control_panel': 'security',
        'lock': 'security',
        'camera': 'security',
        'climate': 'climate',
        'sensor': 'monitoring',  # Default, can be overridden
        'light': 'lighting',
        'switch': 'appliance',
        'vacuum': 'appliance',
        'media_player': 'appliance',
        'cover': 'appliance',
        'fan': 'climate',
    }
    
    # Device class overrides
    DEVICE_CLASS_CATEGORIES = {
        'motion': 'security',
        'door': 'security',
        'window': 'security',
        'temperature': 'climate',
        'humidity': 'climate',
        'battery': 'monitoring',
        'power': 'monitoring',
        'energy': 'monitoring',
    }
    
    def __init__(self):
        """Initialize event categorizer."""
        logger.info("EventCategoryMapper initialized")
    
    def categorize_events(
        self,
        events: list[dict[str, Any]],
        home_type: str | None = None,
        device_categories: dict[str, str] | None = None
    ) -> dict[str, str]:
        """
        Categorize events using home type context.
        
        Args:
            events: List of event dictionaries
            home_type: Optional home type for context
            device_categories: Optional mapping of entity_id to category
        
        Returns:
            Dict mapping event_id or entity_id to category
        """
        categories = {}
        
        for event in events:
            entity_id = event.get('entity_id', '')
            device_type = event.get('attributes', {}).get('device_type', '')
            device_class = event.get('attributes', {}).get('device_class', '')
            
            # Use provided device categories if available
            if device_categories and entity_id in device_categories:
                category = device_categories[entity_id]
            else:
                # Determine category from device type/class
                category = self._determine_category(device_type, device_class, home_type)
            
            categories[entity_id] = category
        
        logger.debug(f"Categorized {len(categories)} events")
        return categories
    
    def _determine_category(
        self,
        device_type: str,
        device_class: str | None = None,
        home_type: str | None = None
    ) -> str:
        """
        Determine event category from device type/class.
        
        Args:
            device_type: Device type
            device_class: Optional device class
            home_type: Optional home type for context
        
        Returns:
            Category string
        """
        # Check device class first (more specific)
        if device_class and device_class in self.DEVICE_CLASS_CATEGORIES:
            return self.DEVICE_CLASS_CATEGORIES[device_class]
        
        # Check device type
        if device_type in self.DEVICE_TYPE_CATEGORIES:
            return self.DEVICE_TYPE_CATEGORIES[device_type]
        
        # Default
        return 'general'

