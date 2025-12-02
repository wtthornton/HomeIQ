"""
Synthetic Device Generator

Generate devices for synthetic homes based on home type, areas, and device categories using templates.

Enhanced with HA 2024 naming conventions:
- Entity ID format: {area}_{device}_{detail}
- Friendly names for display
- Voice-friendly aliases
"""

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class SyntheticDeviceGenerator:
    """
    Generate devices for synthetic homes with HA 2024 naming conventions.
    
    Pipeline:
    1. Generate devices for each area
    2. Assign device types based on area context
    3. Distribute devices across categories (security, climate, lighting, etc.)
    4. Apply HA 2024 naming conventions (entity ID + friendly name)
    
    HA 2024 Naming Format:
    - Entity ID: {domain}.{area}_{device}_{detail} (lowercase, underscores)
    - Friendly Name: {Area} {Device} {Detail} (title case, spaces)
    """
    
    # Voice-friendly name mappings for common devices
    VOICE_FRIENDLY_NAMES = {
        'media_player': 'TV',
        'climate': 'Thermostat',
        'binary_sensor.motion': 'Motion Sensor',
        'binary_sensor.door': 'Door Sensor',
        'binary_sensor.window': 'Window Sensor',
        'binary_sensor.smoke': 'Smoke Detector',
        'lock': 'Lock',
        'light': 'Light',
        'sensor.temperature': 'Temperature Sensor',
        'sensor.humidity': 'Humidity Sensor',
        'sensor.battery': 'Battery',
        'sensor.power': 'Power Monitor',
        'sensor.energy': 'Energy Monitor',
        'switch': 'Switch',
        'fan': 'Fan',
        'cover': 'Blinds',
        'vacuum': 'Vacuum',
        'camera': 'Camera',
        'alarm_control_panel': 'Alarm'
    }
    
    # Device location details by device type
    DEVICE_LOCATION_DETAILS = {
        'light': ['ceiling', 'wall', 'desk', 'floor', 'strip'],
        'binary_sensor.motion': ['motion', 'presence'],
        'binary_sensor.door': ['door', 'entry'],
        'binary_sensor.window': ['window'],
        'camera': ['indoor', 'outdoor', 'doorbell'],
        'lock': ['front', 'back', 'side'],
        'switch': ['outlet', 'wall'],
        'cover': ['blinds', 'shades', 'curtains']
    }
    
    # Failure scenario definitions (5 new scenarios for Epic AI-11)
    FAILURE_SCENARIOS = {
        'integration_failure': {
            'description': 'Zigbee/Z-Wave integration disconnection',
            'symptoms': {
                'unavailable_states': True,  # Device becomes unavailable
                'connection_drops': True,  # Frequent connection drops
                'delayed_responses': True,  # Slow or no response
                'error_messages': ['unavailable', 'connection_lost', 'timeout']
            },
            'affected_device_types': ['binary_sensor', 'sensor', 'light', 'switch', 'lock', 'climate'],
            'probability': 0.10,  # 10% of affected devices
            'duration_days': (1, 7)  # Lasts 1-7 days
        },
        'config_error': {
            'description': 'Configuration error (invalid YAML, missing entities)',
            'symptoms': {
                'invalid_states': True,  # Invalid or null states
                'missing_attributes': True,  # Missing required attributes
                'error_messages': ['invalid_config', 'entity_not_found', 'yaml_error']
            },
            'affected_device_types': ['sensor', 'binary_sensor', 'automation', 'script'],
            'probability': 0.08,  # 8% of affected devices
            'duration_days': (0, 1)  # Usually fixed quickly or persists
        },
        'automation_loop': {
            'description': 'Automation loop causing recursive triggering',
            'symptoms': {
                'rapid_state_changes': True,  # Very frequent state changes
                'circular_dependencies': True,  # Triggers itself
                'error_messages': ['automation_loop', 'recursive_trigger', 'max_iterations']
            },
            'affected_device_types': ['automation', 'script', 'light', 'switch'],
            'probability': 0.05,  # 5% of affected devices
            'duration_days': (0.1, 0.5)  # Short duration (hours to half day)
        },
        'resource_exhaustion': {
            'description': 'Resource exhaustion (memory/CPU spikes)',
            'symptoms': {
                'slow_responses': True,  # Very slow response times
                'timeout_errors': True,  # Frequent timeouts
                'degraded_performance': True,  # Overall system slowdown
                'error_messages': ['timeout', 'memory_error', 'cpu_overload']
            },
            'affected_device_types': ['sensor', 'binary_sensor', 'camera', 'media_player'],
            'probability': 0.06,  # 6% of affected devices
            'duration_days': (0.5, 3)  # Lasts hours to days
        },
        'api_rate_limit': {
            'description': 'API rate limiting from external services',
            'symptoms': {
                'rate_limit_errors': True,  # 429 errors
                'delayed_updates': True,  # Updates delayed or skipped
                'intermittent_failures': True,  # Works sometimes, fails others
                'error_messages': ['rate_limit', 'too_many_requests', 'quota_exceeded']
            },
            'affected_device_types': ['weather', 'sensor', 'media_player', 'camera'],
            'probability': 0.05,  # 5% of affected devices
            'duration_days': (0.1, 1)  # Usually resolved within hours
        }
    }
    
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
    
    def __init__(self):
        """
        Initialize device generator.
        """
        logger.info("SyntheticDeviceGenerator initialized")
    
    def generate_devices(
        self,
        home_data: dict[str, Any],
        areas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Generate devices for a synthetic home using templates.
        
        Args:
            home_data: Home data from synthetic home generator
            areas: List of areas for the home
        
        Returns:
            List of device dictionaries
        """
        home_type = home_data.get('home_type', 'single_family_house')
        home_metadata = home_data.get('metadata', {})
        device_categories = home_metadata.get('device_categories', {})
        size_category = home_data.get('size_category', 'medium')
        
        # If device_categories exist in metadata, use them but map to templates
        if device_categories:
            devices = self._generate_from_categories(
                device_categories,
                areas,
                home_type,
                size_category
            )
        else:
            # Generate devices based on home type, areas, and size
            devices = self._generate_from_template(
                home_type,
                areas,
                size_category
            )
        
        # Assign failure scenarios to devices
        devices = self._assign_failure_scenarios(devices)
        
        logger.info(f"✅ Generated {len(devices)} devices")
        return devices
    
    def _generate_from_categories(
        self,
        device_categories: dict[str, Any],
        areas: list[dict[str, Any]],
        home_type: str,
        size_category: str
    ) -> list[dict[str, Any]]:
        """
        Generate devices from category specifications using templates.
        
        Args:
            device_categories: Device category specifications
            areas: List of areas
            home_type: Type of home (unused, kept for API compatibility)
            size_category: Size category (unused, kept for API compatibility)
        
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
            for i in range(count):
                area = random.choice(area_names) if area_names else 'Unknown'
                
                # Select device type - map to template if needed
                if device_types:
                    # Try to find matching template device
                    device_type_str = None
                    template = self.DEVICE_TEMPLATES.get(category, [])
                    for template_device in template:
                        if template_device['device_type'] in device_types:
                            device_type_str = template_device['device_type']
                            device_class = template_device.get('device_class')
                            name_template = template_device.get('name', 'Device')
                            break
                    
                    # If no match, use first device type from list or fallback
                    if device_type_str is None:
                        device_type_str = device_types[0] if device_types else 'sensor'
                        device_class = None
                        name_template = 'Device'
                else:
                    # Use template
                    template = self.DEVICE_TEMPLATES.get(category, [])
                    if template:
                        device_template = random.choice(template)
                        device_type_str = device_template['device_type']
                        device_class = device_template.get('device_class')
                        name_template = device_template.get('name', 'Device')
                    else:
                        device_type_str = 'sensor'
                        device_class = None
                        name_template = 'Device'
                
                # Create device
                device = self._create_device(
                    device_type_str=device_type_str,
                    category=category,
                    area=area,
                    index=i + 1,
                    device_class=device_class,
                    name_template=name_template
                )
                devices.append(device)
        
        return devices
    
    def _generate_from_template(
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
    
    def _generate_entity_id(
        self,
        device_type: str,
        area: str,
        device_class: str | None = None,
        detail: str = ""
    ) -> str:
        """
        Generate HA 2024 compliant entity ID.
        
        Format: {domain}.{area}_{device}_{detail}
        
        Args:
            device_type: Device domain (light, sensor, etc.)
            area: Area name
            device_class: Optional device class (motion, door, etc.)
            detail: Optional detail (ceiling, wall, etc.)
        
        Returns:
            Entity ID string (e.g., 'light.kitchen_light_ceiling')
        """
        area_normalized = self._normalize_area_name(area)
        device_normalized = self._normalize_device_name(device_type, device_class)
        
        # Build entity name parts
        parts = [area_normalized]
        
        # Add device type (except for generic sensors/binary_sensors where class is more specific)
        if device_type in ['sensor', 'binary_sensor'] and device_class:
            parts.append(device_class)
        else:
            parts.append(device_normalized)
        
        # Add detail if provided
        if detail:
            detail_normalized = self._normalize_detail(detail)
            parts.append(detail_normalized)
        
        # Add 'sensor' suffix for binary_sensor and sensor types
        if device_type in ['sensor', 'binary_sensor'] and not parts[-1].endswith('sensor'):
            parts.append('sensor')
        
        entity_name = '_'.join(parts)
        return f"{device_type}.{entity_name}"
    
    def _generate_friendly_name(
        self,
        device_type: str,
        area: str,
        device_class: str | None = None,
        detail: str = "",
        voice_friendly: bool = True
    ) -> str:
        """
        Generate human-readable friendly name.
        
        Format: {Area} {Device} {Detail}
        
        Args:
            device_type: Device domain
            area: Area name
            device_class: Optional device class
            detail: Optional detail
            voice_friendly: Use voice-friendly aliases
        
        Returns:
            Friendly name string (e.g., 'Kitchen Light Ceiling')
        """
        # Get device name
        if voice_friendly:
            # Try full key with device class
            lookup_key = f"{device_type}.{device_class}" if device_class else device_type
            device_name = self.VOICE_FRIENDLY_NAMES.get(
                lookup_key,
                self.VOICE_FRIENDLY_NAMES.get(device_type, self._humanize(device_type))
            )
        else:
            device_name = self._humanize(device_type)
        
        # Build friendly name parts
        area_name = self._humanize(area)
        
        # For sensors, include device class in name
        if device_type in ['sensor', 'binary_sensor'] and device_class:
            # If device class not already in device_name, add it
            if device_class.lower() not in device_name.lower():
                device_name = f"{self._humanize(device_class)} {device_name}"
        
        if detail:
            detail_name = self._humanize(detail)
            return f"{area_name} {device_name} {detail_name}"
        else:
            return f"{area_name} {device_name}"
    
    def _normalize_area_name(self, area: str) -> str:
        """
        Normalize area name for entity ID.
        
        Args:
            area: Area name
        
        Returns:
            Normalized area name (lowercase, underscores, no spaces/special chars)
        """
        import re
        # Convert to lowercase
        normalized = area.lower()
        # Replace spaces, hyphens, and slashes with underscores
        normalized = normalized.replace(' ', '_').replace('-', '_').replace('/', '_')
        # Remove any remaining special characters (keep only letters, numbers, underscores)
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        # Remove duplicate underscores
        normalized = re.sub(r'_+', '_', normalized)
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        return normalized
    
    def _normalize_device_name(self, device_type: str, device_class: str | None = None) -> str:
        """
        Normalize device type for entity ID.
        
        Args:
            device_type: Device type
            device_class: Optional device class
        
        Returns:
            Normalized device name
        """
        # Remove domain prefix if present
        if '.' in device_type:
            device_type = device_type.split('.')[1]
        
        # For sensors, use device class if available
        if device_type in ['sensor', 'binary_sensor'] and device_class:
            return device_class.lower().replace(' ', '_')
        
        return device_type.lower().replace(' ', '_')
    
    def _normalize_detail(self, detail: str) -> str:
        """
        Normalize detail for entity ID.
        
        Args:
            detail: Detail string
        
        Returns:
            Normalized detail (lowercase, underscores)
        """
        return detail.lower().replace(' ', '_').replace('-', '_')
    
    def _humanize(self, text: str) -> str:
        """
        Convert snake_case or kebab-case to Title Case for display.
        
        Args:
            text: Text to humanize
        
        Returns:
            Humanized text (e.g., 'motion_sensor' -> 'Motion Sensor')
        """
        return text.replace('_', ' ').replace('-', ' ').title()
    
    def _get_device_detail(
        self,
        device_type: str,
        device_class: str | None,
        index: int
    ) -> str:
        """
        Get detail string for device based on type and index.
        
        Args:
            device_type: Device type
            device_class: Device class
            index: Device index for variation
        
        Returns:
            Detail string (e.g., 'ceiling', 'wall', 'motion')
        """
        # Build lookup key
        lookup_key = f"{device_type}.{device_class}" if device_class else device_type
        
        # Get available details for this device type
        details = self.DEVICE_LOCATION_DETAILS.get(lookup_key, [])
        
        if details:
            # Cycle through details based on index
            return details[index % len(details)]
        
        return ""
    
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
        Create a device dictionary with HA 2024 naming conventions.
        
        Args:
            device_type_str: Device type (e.g., 'light', 'sensor')
            category: Device category (security, climate, etc.)
            area: Area name
            index: Device index
            device_class: Optional device class (motion, door, temperature, etc.)
            name_template: Name template (unused, kept for compatibility)
        
        Returns:
            Device dictionary with entity_id, friendly_name, and metadata
        """
        # Get detail for this device (location/type specific)
        detail = self._get_device_detail(device_type_str, device_class, index)
        
        # Generate HA 2024 compliant entity ID
        entity_id = self._generate_entity_id(
            device_type=device_type_str,
            area=area,
            device_class=device_class,
            detail=detail
        )
        
        # Generate human-readable friendly name
        friendly_name = self._generate_friendly_name(
            device_type=device_type_str,
            area=area,
            device_class=device_class,
            detail=detail,
            voice_friendly=True
        )
        
        device = {
            'entity_id': entity_id,
            'friendly_name': friendly_name,
            'device_type': device_type_str,
            'name': friendly_name,  # Alias for backward compatibility
            'area': area,
            'category': category,
            'device_class': device_class,
            'attributes': {
                'friendly_name': friendly_name,
                'device_class': device_class,
                'area': area,
                'category': category
            }
        }
        
        return device
    
    def _assign_failure_scenarios(
        self,
        devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Assign failure scenarios to devices based on probability and device type compatibility.
        
        Args:
            devices: List of device dictionaries
        
        Returns:
            List of devices with failure scenarios assigned (if applicable)
        """
        for device in devices:
            device_type = device.get('device_type', '')
            
            # Check each failure scenario to see if it applies to this device type
            for scenario_name, scenario_config in self.FAILURE_SCENARIOS.items():
                # Check if device type is affected by this scenario
                if device_type in scenario_config.get('affected_device_types', []):
                    # Randomly assign based on probability
                    if random.random() < scenario_config['probability']:
                        # Assign failure scenario
                        device['failure_scenario'] = scenario_name
                        device['failure_symptoms'] = scenario_config['symptoms']
                        
                        # Calculate failure duration
                        duration_range = scenario_config.get('duration_days', (1, 7))
                        device['failure_duration_days'] = random.uniform(*duration_range)
                        
                        # Add failure metadata to attributes
                        if 'attributes' not in device:
                            device['attributes'] = {}
                        device['attributes']['failure_scenario'] = scenario_name
                        device['attributes']['failure_description'] = scenario_config['description']
                        
                        logger.debug(
                            f"Assigned failure scenario '{scenario_name}' to device "
                            f"{device.get('entity_id', 'unknown')}"
                        )
                        break  # Only assign one failure scenario per device
        
        # Log failure assignment summary
        failed_devices = [d for d in devices if 'failure_scenario' in d]
        if failed_devices:
            logger.info(
                f"Assigned failure scenarios to {len(failed_devices)}/{len(devices)} devices "
                f"({len(failed_devices)/len(devices)*100:.1f}%)"
            )
        
        return devices

