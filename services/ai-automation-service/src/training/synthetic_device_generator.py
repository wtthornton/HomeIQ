"""
Synthetic Device Generator

Generate devices for synthetic homes based on home type, areas, and device categories.
"""

import logging
import random
from typing import Any

from ..llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class SyntheticDeviceGenerator:
    """
    Generate devices for synthetic homes.
    
    Pipeline:
    1. Generate devices for each area
    2. Assign device types based on area context
    3. Distribute devices across categories (security, climate, lighting, etc.)
    """
    
    # Device type templates by category
    DEVICE_TEMPLATES = {
        'security': [
            {'device_type': 'binary_sensor', 'device_class': 'motion', 'name': 'Motion Sensor'},
            {'device_type': 'binary_sensor', 'device_class': 'door', 'name': 'Door Sensor'},
            {'device_type': 'binary_sensor', 'device_class': 'window', 'name': 'Window Sensor'},
            {'device_type': 'alarm_control_panel', 'name': 'Security Alarm'},
            {'device_type': 'lock', 'name': 'Smart Lock'},
            {'device_type': 'camera', 'name': 'Security Camera'}
        ],
        'climate': [
            {'device_type': 'climate', 'name': 'Thermostat'},
            {'device_type': 'sensor', 'device_class': 'temperature', 'name': 'Temperature Sensor'},
            {'device_type': 'sensor', 'device_class': 'humidity', 'name': 'Humidity Sensor'},
            {'device_type': 'fan', 'name': 'Smart Fan'},
            {'device_type': 'switch', 'name': 'HVAC Switch'}
        ],
        'lighting': [
            {'device_type': 'light', 'name': 'Smart Light'},
            {'device_type': 'light', 'name': 'LED Strip'},
            {'device_type': 'switch', 'name': 'Light Switch'},
            {'device_type': 'scene', 'name': 'Lighting Scene'}
        ],
        'appliances': [
            {'device_type': 'switch', 'name': 'Smart Switch'},
            {'device_type': 'vacuum', 'name': 'Robot Vacuum'},
            {'device_type': 'media_player', 'name': 'Smart Speaker'},
            {'device_type': 'cover', 'name': 'Smart Blinds'}
        ],
        'monitoring': [
            {'device_type': 'sensor', 'device_class': 'battery', 'name': 'Battery Sensor'},
            {'device_type': 'sensor', 'device_class': 'power', 'name': 'Power Monitor'},
            {'device_type': 'sensor', 'device_class': 'energy', 'name': 'Energy Monitor'},
            {'device_type': 'binary_sensor', 'device_class': 'smoke', 'name': 'Smoke Detector'}
        ]
    }
    
    def __init__(self, openai_client: OpenAIClient):
        """
        Initialize device generator.
        
        Args:
            openai_client: OpenAI client for LLM generation
        """
        self.llm = openai_client
        logger.info("SyntheticDeviceGenerator initialized")
    
    async def generate_devices(
        self,
        home_data: dict[str, Any],
        areas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Generate devices for a synthetic home.
        
        Args:
            home_data: Home data from synthetic home generator
            areas: List of areas for the home
        
        Returns:
            List of device dictionaries
        """
        home_type = home_data.get('home_type', 'single_family_house')
        home_metadata = home_data.get('metadata', {})
        device_categories = home_metadata.get('device_categories', {})
        
        # Try to extract devices from LLM response if available
        if device_categories:
            devices = await self._generate_from_categories(
                device_categories,
                areas,
                home_type
            )
        else:
            # Generate devices based on home type and areas
            devices = await self._generate_from_template(
                home_type,
                areas,
                home_data.get('size_category', 'medium')
            )
        
        logger.info(f"✅ Generated {len(devices)} devices")
        return devices
    
    async def _generate_from_categories(
        self,
        device_categories: dict[str, Any],
        areas: list[dict[str, Any]],
        home_type: str
    ) -> list[dict[str, Any]]:
        """
        Generate devices from category specifications.
        
        Args:
            device_categories: Device category specifications from LLM
            areas: List of areas
            home_type: Type of home
        
        Returns:
            List of device dictionaries
        """
        devices = []
        area_names = [area['name'] for area in areas]
        
        for category, category_data in device_categories.items():
            count = category_data.get('count', 0)
            device_types = category_data.get('devices', [])
            
            if count == 0:
                continue
            
            # Distribute devices across areas
            devices_per_area = max(1, count // len(area_names)) if area_names else count
            
            for i in range(count):
                area = random.choice(area_names) if area_names else 'Unknown'
                
                # Select device type
                if device_types:
                    device_type_str = random.choice(device_types)
                else:
                    # Use template
                    template = self.DEVICE_TEMPLATES.get(category, [])
                    if template:
                        device_template = random.choice(template)
                        device_type_str = device_template['device_type']
                    else:
                        device_type_str = 'sensor'
                
                # Create device
                device = self._create_device(
                    device_type_str=device_type_str,
                    category=category,
                    area=area,
                    index=i + 1
                )
                devices.append(device)
        
        return devices
    
    async def _generate_from_template(
        self,
        home_type: str,
        areas: list[dict[str, Any]],
        size_category: str
    ) -> list[dict[str, Any]]:
        """
        Generate devices from template based on home type and size.
        
        Args:
            home_type: Type of home
            areas: List of areas
            size_category: Size category (small, medium, large, extra_large)
        
        Returns:
            List of device dictionaries
        """
        # Determine device counts by category based on size
        size_multipliers = {
            'small': 0.6,
            'medium': 1.0,
            'large': 1.5,
            'extra_large': 2.0
        }
        multiplier = size_multipliers.get(size_category, 1.0)
        
        # Base device counts per category
        base_counts = {
            'security': 5,
            'climate': 3,
            'lighting': 8,
            'appliances': 4,
            'monitoring': 3
        }
        
        devices = []
        area_names = [area['name'] for area in areas]
        
        for category, base_count in base_counts.items():
            count = int(base_count * multiplier)
            template = self.DEVICE_TEMPLATES.get(category, [])
            
            if not template:
                continue
            
            for i in range(count):
                area = random.choice(area_names) if area_names else 'Unknown'
                device_template = random.choice(template)
                
                device = self._create_device(
                    device_type_str=device_template['device_type'],
                    device_class=device_template.get('device_class'),
                    name_template=device_template.get('name', 'Device'),
                    category=category,
                    area=area,
                    index=i + 1
                )
                devices.append(device)
        
        return devices
    
    def _create_device(
        self,
        device_type_str: str,
        category: str,
        area: str,
        index: int,
        device_class: str | None = None,
        name_template: str = 'Device'
    ) -> dict[str, Any]:
        """
        Create a device dictionary.
        
        Args:
            device_type_str: Device type (e.g., 'light', 'sensor')
            category: Device category (security, climate, etc.)
            area: Area name
            index: Device index
            device_class: Optional device class
            name_template: Name template
        
        Returns:
            Device dictionary
        """
        # Generate entity_id
        area_slug = area.lower().replace(' ', '_')
        device_name = f"{name_template.lower().replace(' ', '_')}_{index}"
        entity_id = f"{device_type_str}.{area_slug}_{device_name}"
        
        device = {
            'entity_id': entity_id,
            'device_type': device_type_str,
            'name': f"{name_template} {index}",
            'area': area,
            'category': category,
            'device_class': device_class
        }
        
        return device

