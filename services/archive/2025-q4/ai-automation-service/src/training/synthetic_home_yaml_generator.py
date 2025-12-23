"""
Synthetic Home YAML Generator

Convert home structure to synthetic-home YAML format for integration with
home-assistant-synthetic-home library.

Optional integration module for future use with synthetic-home library.
"""

import logging
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class SyntheticHomeYAMLGenerator:
    """
    Convert home structure to synthetic-home YAML format.
    
    This allows integration with the home-assistant-synthetic-home library
    for validation and enhanced device definitions.
    """
    
    def __init__(self):
        """Initialize YAML generator."""
        logger.info("SyntheticHomeYAMLGenerator initialized")
    
    def convert_to_yaml(
        self,
        home_data: dict[str, Any]
    ) -> str:
        """
        Convert home data to synthetic-home YAML format.
        
        Args:
            home_data: Home data dictionary with areas, devices, etc.
        
        Returns:
            YAML string in synthetic-home format
        """
        yaml_structure = {
            'home': {
                'name': home_data.get('metadata', {}).get('home', {}).get('name', 'Synthetic Home'),
                'type': home_data.get('home_type', 'single_family_house'),
                'country_code': 'US',
                'location': 'Synthetic Location'
            },
            'areas': self._convert_areas(home_data.get('areas', [])),
            'devices': self._convert_devices(home_data.get('devices', [])),
            'entities': self._convert_entities(home_data.get('devices', []))
        }
        
        return yaml.dump(yaml_structure, default_flow_style=False, sort_keys=False)
    
    def _convert_areas(
        self,
        areas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convert areas to synthetic-home format.
        
        Args:
            areas: List of area dictionaries
        
        Returns:
            List of area dictionaries in synthetic-home format
        """
        yaml_areas = []
        for area in areas:
            area_slug = area['name'].lower().replace(' ', '_')
            yaml_areas.append({
                'name': area['name'],
                'id': area_slug,
                'type': area.get('type', 'indoor')
            })
        return yaml_areas
    
    def _convert_devices(
        self,
        devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convert devices to synthetic-home format.
        
        Args:
            devices: List of device dictionaries
        
        Returns:
            List of device dictionaries in synthetic-home format
        """
        yaml_devices = []
        device_groups = {}
        
        # Group devices by area and category
        for device in devices:
            area = device.get('area', 'Unknown')
            category = device.get('category', 'unknown')
            key = f"{area}_{category}"
            
            if key not in device_groups:
                device_groups[key] = {
                    'name': f"{category.title()} {area}",
                    'id': key.lower().replace(' ', '_'),
                    'area': area.lower().replace(' ', '_'),
                    'device_type': device.get('device_type', 'sensor'),
                    'model': 'Synthetic Model',
                    'mfg': 'Synthetic Manufacturer',
                    'sw_version': '1.0.0'
                }
        
        return list(device_groups.values())
    
    def _convert_entities(
        self,
        devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convert devices to entities in synthetic-home format.
        
        Args:
            devices: List of device dictionaries
        
        Returns:
            List of entity dictionaries in synthetic-home format
        """
        entities = []
        for device in devices:
            entity_id = device.get('entity_id', 'unknown.entity')
            # Extract device name from entity_id (format: device_type.area_name)
            device_name = entity_id.split('.')[0] if '.' in entity_id else entity_id
            
            entity = {
                'name': device.get('name', 'Unknown Device'),
                'id': entity_id,
                'area': device.get('area', 'Unknown').lower().replace(' ', '_'),
                'device': device_name,
                'state': self._get_default_state(device.get('device_type', 'sensor'))
            }
            
            # Add attributes based on device type
            if device.get('device_class'):
                entity['attributes'] = {
                    'device_class': device['device_class']
                }
            
            entities.append(entity)
        
        return entities
    
    def _get_default_state(self, device_type: str) -> str:
        """
        Get default state for device type.
        
        Args:
            device_type: Device type string
        
        Returns:
            Default state value
        """
        default_states = {
            'light': 'off',
            'switch': 'off',
            'binary_sensor': 'off',
            'sensor': '0',
            'climate': 'off',
            'cover': 'closed',
            'lock': 'locked',
            'fan': 'off'
        }
        return default_states.get(device_type, 'unknown')

