"""
Device Descriptor Builder

Epic AI-4, Story AI4.1: Device Embedding Generation
Generates natural language descriptions for smart home devices.

Example outputs:
- "motion sensor that detects presence in kitchen area"
- "dimmable light with RGB color control in living room area"
- "smart thermostat controlling HVAC temperature in whole house"
"""

import logging

logger = logging.getLogger(__name__)


class DeviceDescriptorBuilder:
    """
    Generates natural language descriptions for devices.
    
    Story AI4.1: Device Embedding Generation
    Context7 Best Practice: Clear, semantic descriptors for embedding quality
    """

    def __init__(self, capability_service=None):
        """
        Initialize descriptor builder.
        
        Args:
            capability_service: Service for fetching device capabilities
        """
        self.capability_service = capability_service
        self._action_mappings = self._load_action_mappings()
        self._friendly_device_names = self._load_friendly_names()

    def create_descriptor(
        self,
        device: dict,
        entity: dict,
        capabilities: dict | None = None
    ) -> str:
        """
        Create semantic device descriptor.
        
        Format:
        "{device_class} that {primary_action} in {area} area with {capabilities}"
        
        Args:
            device: Device metadata from data-api
            entity: Entity metadata from data-api
            capabilities: Device capabilities from device intelligence
        
        Returns:
            Natural language device description
        
        Examples:
            >>> builder.create_descriptor(device, entity)
            "motion sensor that detects presence in kitchen area"
            
            >>> builder.create_descriptor(device, entity, capabilities)
            "dimmable light with RGB color control in living room area"
        """
        # Extract components
        device_class = self._get_device_class(entity)
        primary_action = self._get_primary_action(entity, capabilities)
        area = entity.get('area_id', 'unknown')
        capability_features = self._get_top_capabilities(capabilities, limit=3)

        # Build descriptor
        descriptor = f"{device_class} that {primary_action}"
        descriptor += f" in {area} area"

        if capability_features:
            descriptor += f" with {', '.join(capability_features)}"

        logger.debug(f"Generated descriptor for {entity.get('entity_id')}: {descriptor}")

        return descriptor

    def _get_device_class(self, entity: dict) -> str:
        """
        Get friendly device class name.
        
        Args:
            entity: Entity metadata
        
        Returns:
            Friendly device class (e.g., "motion sensor", "dimmable light")
        """
        domain = entity['entity_id'].split('.')[0]
        device_class = entity.get('device_class', entity.get('original_device_class'))

        # Check friendly name mapping
        if domain in self._friendly_device_names:
            domain_mapping = self._friendly_device_names[domain]

            if isinstance(domain_mapping, dict) and device_class:
                return domain_mapping.get(device_class, f"{domain} device")
            elif isinstance(domain_mapping, str):
                return domain_mapping

        # Fallback to domain
        return f"{domain} device"

    def _get_primary_action(
        self,
        entity: dict,
        capabilities: dict | None = None
    ) -> str:
        """
        Determine primary action/purpose of device.
        
        Args:
            entity: Entity metadata
            capabilities: Device capabilities
        
        Returns:
            Primary action description (e.g., "detects presence", "controls brightness")
        """
        domain = entity['entity_id'].split('.')[0]
        device_class = entity.get('device_class', entity.get('original_device_class'))

        # Check action mapping
        if domain in self._action_mappings:
            domain_actions = self._action_mappings[domain]

            if isinstance(domain_actions, dict) and device_class:
                return domain_actions.get(device_class, 'controls state')
            elif isinstance(domain_actions, str):
                return domain_actions

        # Fallback
        return 'controls state'

    def _get_top_capabilities(
        self,
        capabilities: dict | None,
        limit: int = 3
    ) -> list[str]:
        """
        Extract top N capabilities for descriptor.
        
        Args:
            capabilities: Device capabilities dict
            limit: Maximum number of capabilities to include
        
        Returns:
            List of friendly capability names
        """
        if not capabilities or not isinstance(capabilities, dict):
            return []

        cap_list = capabilities.get('capabilities', {})
        if not cap_list:
            return []

        # Prioritize user-facing capabilities
        priority_caps = ['brightness', 'color_xy', 'color_temp', 'speed', 'position']

        friendly_caps = []

        # Add priority caps first
        for cap_name in priority_caps:
            if cap_name in cap_list:
                friendly_caps.append(self._friendly_cap_name(cap_name))

        # Add remaining caps
        for cap_name in cap_list.keys():
            if cap_name not in priority_caps:
                friendly_caps.append(self._friendly_cap_name(cap_name))

            if len(friendly_caps) >= limit:
                break

        return friendly_caps[:limit]

    def _friendly_cap_name(self, cap_name: str) -> str:
        """
        Convert capability name to friendly format.
        
        Args:
            cap_name: Internal capability name
        
        Returns:
            Friendly capability name
        """
        mappings = {
            'color_xy': 'RGB color control',
            'color_temp': 'color temperature',
            'brightness': 'brightness control',
            'speed': 'speed control',
            'position': 'position control',
            'auto_off_timer': 'auto-off timer',
            'smart_bulb_mode': 'smart bulb mode',
            'led_notifications': 'LED notifications'
        }

        return mappings.get(cap_name, cap_name.replace('_', ' '))

    def _load_friendly_names(self) -> dict:
        """
        Load friendly device name mappings.
        
        Returns:
            Dict mapping domain/device_class to friendly names
        """
        return {
            'binary_sensor': {
                'motion': 'motion sensor',
                'door': 'door sensor',
                'occupancy': 'occupancy sensor',
                'window': 'window sensor',
                'opening': 'opening sensor',
                'vibration': 'vibration sensor'
            },
            'sensor': {
                'temperature': 'temperature sensor',
                'humidity': 'humidity sensor',
                'battery': 'battery sensor',
                'illuminance': 'light sensor',
                'power': 'power meter'
            },
            'light': 'dimmable light',
            'switch': 'smart switch',
            'climate': 'smart thermostat',
            'lock': 'smart lock',
            'fan': 'ceiling fan',
            'cover': 'motorized cover',
            'media_player': 'media player',
            'camera': 'security camera'
        }

    def _load_action_mappings(self) -> dict:
        """
        Load primary action mappings.
        
        Returns:
            Dict mapping domain/device_class to actions
        """
        return {
            'binary_sensor': {
                'motion': 'detects presence',
                'door': 'detects door state',
                'occupancy': 'detects occupancy',
                'window': 'detects window state',
                'opening': 'detects opening',
                'vibration': 'detects vibration'
            },
            'sensor': {
                'temperature': 'measures temperature',
                'humidity': 'measures humidity',
                'battery': 'monitors battery level',
                'illuminance': 'measures light level',
                'power': 'measures power usage'
            },
            'light': 'controls lighting brightness',
            'switch': 'controls power state',
            'climate': 'controls HVAC temperature',
            'lock': 'controls lock state',
            'fan': 'controls fan speed',
            'cover': 'controls position',
            'media_player': 'controls media playback',
            'camera': 'provides video surveillance'
        }

