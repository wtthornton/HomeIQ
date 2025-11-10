"""
Trigger Device Discovery

Discovers trigger devices (sensors) based on analyzed trigger conditions.
Searches for sensors matching the required device class and location.

Part of Phase 1: Trigger Device Discovery for Presence Sensor Detection
"""

import logging
from typing import List, Dict, Any, Optional

from ..clients.device_intelligence_client import DeviceIntelligenceClient

logger = logging.getLogger(__name__)


class TriggerDeviceDiscovery:
    """
    Discovers trigger devices (sensors) based on trigger conditions.
    
    Example:
        conditions = [{
            'trigger_type': 'presence',
            'required_device_class': 'occupancy',
            'required_sensor_type': 'binary_sensor',
            'location': 'office'
        }]
        devices = await discovery.discover_trigger_devices(conditions)
        # Returns: [{
        #     'entity_id': 'binary_sensor.ps_fp2_office',
        #     'name': 'PS FP2 Office',
        #     'type': 'device',
        #     'domain': 'binary_sensor',
        #     'device_class': 'occupancy',
        #     'extraction_method': 'trigger_discovery'
        # }]
    """
    
    def __init__(self, device_intelligence_client: DeviceIntelligenceClient):
        """
        Initialize trigger device discovery.
        
        Args:
            device_intelligence_client: Client for querying device intelligence service
        """
        self.device_client = device_intelligence_client
        logger.debug("TriggerDeviceDiscovery initialized")
    
    async def discover_trigger_devices(
        self,
        trigger_conditions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Discover trigger devices based on trigger conditions.
        
        Args:
            trigger_conditions: List of trigger condition dictionaries from TriggerConditionAnalyzer
            
        Returns:
            List of entity dictionaries with trigger device information
        """
        if not trigger_conditions:
            return []
        
        discovered_devices = []
        seen_entity_ids = set()  # Avoid duplicates
        
        for condition in trigger_conditions:
            try:
                # Extract condition details
                trigger_type = condition.get('trigger_type')
                device_class = condition.get('required_device_class')
                sensor_type = condition.get('required_sensor_type', 'binary_sensor')
                location = condition.get('location')
                
                if not trigger_type or not device_class:
                    logger.warning(f"Invalid condition missing trigger_type or device_class: {condition}")
                    continue
                
                # Search for matching sensors
                matching_sensors = await self._search_matching_sensors(
                    trigger_type=trigger_type,
                    device_class=device_class,
                    sensor_type=sensor_type,
                    location=location
                )
                
                # Convert sensors to entity format
                for sensor in matching_sensors:
                    entity_id = self._extract_entity_id(sensor)
                    if not entity_id:
                        logger.warning(f"Sensor missing entity_id: {sensor}")
                        continue
                    
                    # Avoid duplicates
                    if entity_id in seen_entity_ids:
                        continue
                    seen_entity_ids.add(entity_id)
                    
                    # Build entity dictionary
                    entity = self._sensor_to_entity(sensor, condition)
                    discovered_devices.append(entity)
                    
                    logger.debug(
                        f"Discovered trigger device: {entity_id} "
                        f"(type: {trigger_type}, location: {location})"
                    )
                
            except Exception as e:
                logger.error(f"Error discovering devices for condition {condition}: {e}", exc_info=True)
                continue
        
        logger.info(f"Discovered {len(discovered_devices)} trigger devices from {len(trigger_conditions)} conditions")
        return discovered_devices
    
    async def _search_matching_sensors(
        self,
        trigger_type: str,
        device_class: str,
        sensor_type: str,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for sensors matching the trigger condition.
        
        Args:
            trigger_type: Type of trigger ('presence', 'motion', 'door', etc.)
            device_class: Required device class ('occupancy', 'motion', 'door', etc.)
            sensor_type: Required sensor type ('binary_sensor', 'sensor')
            location: Optional location context
            
        Returns:
            List of matching sensor device dictionaries
        """
        # Get all devices from device intelligence service
        all_devices = await self.device_client.get_all_devices(limit=200)
        
        matching_sensors = []
        
        for device in all_devices:
            if not isinstance(device, dict):
                logger.debug(f"Skipping non-dict device entry: {device!r}")
                continue
            # Check if device has entities
            entities = device.get('entities', [])
            if not isinstance(entities, list):
                logger.debug(f"Device {device.get('id') or device.get('name')} has non-list entities payload: {type(entities).__name__}")
                continue
            if not entities:
                continue
            
            # Filter entities by sensor type and device class
            for entity in entities:
                if not isinstance(entity, dict):
                    logger.debug(
                        "Skipping malformed entity entry for device %s: %r",
                        device.get('id') or device.get('name'),
                        entity
                    )
                    continue
                entity_domain = entity.get('domain', '')
                entity_device_class = entity.get('device_class', '')
                
                # Check if entity matches sensor type
                if entity_domain != sensor_type:
                    continue
                
                # Check if device class matches
                if entity_device_class and entity_device_class.lower() != device_class.lower():
                    continue
                
                # Check location if specified
                if location:
                    device_area = device.get('area_name', '').lower()
                    device_name = device.get('name', '').lower()
                    entity_name = entity.get('name', '').lower()
                    
                    location_lower = location.lower()
                    
                    # Check if location matches area, device name, or entity name
                    location_match = (
                        location_lower in device_area or
                        location_lower in device_name or
                        location_lower in entity_name or
                        device_area in location_lower or
                        device_name in location_lower or
                        entity_name in location_lower
                    )
                    
                    if not location_match:
                        continue
                
                # Add matching sensor (with full device context)
                sensor_with_context = {
                    **entity,
                    'device_id': device.get('id') or device.get('device_id'),
                    'device_name': device.get('name'),
                    'area_name': device.get('area_name'),
                    'area_id': device.get('area_id'),
                    'manufacturer': device.get('manufacturer'),
                    'model': device.get('model')
                }
                matching_sensors.append(sensor_with_context)
        
        logger.debug(
            f"Found {len(matching_sensors)} matching sensors for "
            f"trigger_type={trigger_type}, device_class={device_class}, location={location}"
        )
        
        return matching_sensors
    
    def _extract_entity_id(self, sensor: Dict[str, Any]) -> Optional[str]:
        """
        Extract entity_id from sensor dictionary.
        
        Args:
            sensor: Sensor dictionary from device intelligence
            
        Returns:
            Entity ID string or None
        """
        # Try direct entity_id first
        entity_id = sensor.get('entity_id')
        if entity_id:
            return entity_id
        
        # Try constructing from domain and unique_id
        domain = sensor.get('domain')
        unique_id = sensor.get('unique_id')
        if domain and unique_id:
            # Format: domain.unique_id (simplified - may need adjustment)
            return f"{domain}.{unique_id.lower().replace(' ', '_').replace('-', '_')}"
        
        return None
    
    def _sensor_to_entity(
        self,
        sensor: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert sensor dictionary to entity format.
        
        Args:
            sensor: Sensor dictionary from device intelligence
            condition: Original trigger condition
            
        Returns:
            Entity dictionary in format expected by entity extractor
        """
        entity_id = self._extract_entity_id(sensor)
        
        # Get name (prefer entity name, fallback to device name)
        name = sensor.get('name') or sensor.get('device_name') or entity_id
        
        return {
            'entity_id': entity_id,
            'name': name,
            'type': 'device',
            'domain': sensor.get('domain', 'binary_sensor'),
            'device_class': sensor.get('device_class'),
            'area_name': sensor.get('area_name'),
            'area_id': sensor.get('area_id'),
            'manufacturer': sensor.get('manufacturer'),
            'model': sensor.get('model'),
            'extraction_method': 'trigger_discovery',
            'trigger_type': condition.get('trigger_type'),
            'confidence': condition.get('confidence', 0.8)
        }


