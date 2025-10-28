"""
Device Intelligence Service - Device Parser

Device data parsing and normalization for multi-source device discovery.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..clients.ha_client import HADevice, HAEntity, HAArea
from ..clients.mqtt_client import ZigbeeDevice, ZigbeeGroup

logger = logging.getLogger(__name__)


@dataclass
class UnifiedDevice:
    """Unified device representation combining HA and Zigbee2MQTT data."""
    # Core identification
    id: str
    name: str
    manufacturer: str
    model: str
    
    # Location and organization
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    integration: str = "unknown"
    device_class: Optional[str] = None  # Device type (light, sensor, etc.)
    
    # Device metadata
    sw_version: Optional[str] = None
    hw_version: Optional[str] = None
    power_source: Optional[str] = None
    via_device_id: Optional[str] = None
    
    # Capabilities and features
    capabilities: List[Dict[str, Any]] = None
    entities: List[Dict[str, Any]] = None
    
    # Source data references
    ha_device: Optional[HADevice] = None
    zigbee_device: Optional[ZigbeeDevice] = None
    
    # Status and health
    disabled_by: Optional[str] = None
    last_seen: Optional[datetime] = None
    health_score: Optional[int] = None
    
    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        """Initialize mutable defaults after dataclass init."""
        if self.capabilities is None:
            object.__setattr__(self, 'capabilities', [])
        if self.entities is None:
            object.__setattr__(self, 'entities', [])
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now(timezone.utc))
        if self.updated_at is None:
            object.__setattr__(self, 'updated_at', datetime.now(timezone.utc))


class DeviceParser:
    """Parser for normalizing device data from multiple sources."""
    
    def __init__(self):
        self.devices: Dict[str, UnifiedDevice] = {}
        self.areas: Dict[str, HAArea] = {}
    
    def update_areas(self, areas: List[HAArea]):
        """Update area registry for device normalization."""
        self.areas = {area.area_id: area for area in areas}
        logger.info(f"📋 Updated area registry with {len(self.areas)} areas")
    
    def parse_devices(
        self,
        ha_devices: List[HADevice],
        ha_entities: List[HAEntity],
        zigbee_devices: Dict[str, ZigbeeDevice]
    ) -> List[UnifiedDevice]:
        """Parse and normalize devices from multiple sources."""
        logger.info(f"🔄 Parsing {len(ha_devices)} HA devices, {len(ha_entities)} entities, {len(zigbee_devices)} Zigbee devices")
        
        unified_devices = []
        
        # Process Home Assistant devices
        for ha_device in ha_devices:
            try:
                unified_device = self._parse_ha_device(ha_device, ha_entities, zigbee_devices)
                if unified_device:
                    unified_devices.append(unified_device)
                    self.devices[unified_device.id] = unified_device
            except Exception as e:
                logger.error(f"❌ Error parsing HA device {ha_device.id}: {e}")
        
        # Process standalone Zigbee devices (not in HA)
        for zigbee_device in zigbee_devices.values():
            if not self._is_zigbee_device_in_ha(zigbee_device, ha_devices):
                try:
                    unified_device = self._parse_zigbee_device(zigbee_device)
                    if unified_device:
                        unified_devices.append(unified_device)
                        self.devices[unified_device.id] = unified_device
                except Exception as e:
                    logger.error(f"❌ Error parsing standalone Zigbee device {zigbee_device.ieee_address}: {e}")
        
        logger.info(f"✅ Parsed {len(unified_devices)} unified devices")
        return unified_devices
    
    def _parse_ha_device(
        self,
        ha_device: HADevice,
        ha_entities: List[HAEntity],
        zigbee_devices: Dict[str, ZigbeeDevice]
    ) -> Optional[UnifiedDevice]:
        """Parse a Home Assistant device into unified format."""
        
        # Find matching Zigbee device
        zigbee_device = self._find_matching_zigbee_device(ha_device, zigbee_devices)
        
        # Get device entities
        device_entities = [e for e in ha_entities if e.device_id == ha_device.id]
        
        # Parse capabilities from Zigbee device if available
        capabilities = []
        if zigbee_device and zigbee_device.exposes:
            capabilities = self._parse_zigbee_capabilities(zigbee_device.exposes)
        else:
            # Infer capabilities for non-MQTT devices based on device class and entities
            capabilities = self._infer_non_mqtt_capabilities(device_entities, ha_device)
        
        # Get area name
        area_name = None
        if ha_device.area_id and ha_device.area_id in self.areas:
            area_name = self.areas[ha_device.area_id].name
        
        # Extract device class
        device_class = self._extract_device_class(device_entities)
        
        # Create unified device
        unified_device = UnifiedDevice(
            id=ha_device.id,
            name=ha_device.name,
            manufacturer=ha_device.manufacturer or zigbee_device.manufacturer if zigbee_device else "Unknown",
            model=ha_device.model or zigbee_device.model if zigbee_device else "Unknown",
            area_id=ha_device.area_id,
            area_name=area_name,
            integration=ha_device.integration,
            device_class=device_class,
            sw_version=ha_device.sw_version or zigbee_device.software_build_id if zigbee_device else None,
            hw_version=ha_device.hw_version or zigbee_device.hardware_version if zigbee_device else None,
            power_source=zigbee_device.power_source if zigbee_device else None,
            via_device_id=ha_device.via_device_id,
            capabilities=capabilities,
            entities=[self._entity_to_dict(e) for e in device_entities],
            ha_device=ha_device,
            zigbee_device=zigbee_device,
            disabled_by=ha_device.disabled_by,
            last_seen=zigbee_device.last_seen if zigbee_device else None,
            health_score=self._calculate_health_score(ha_device, zigbee_device, device_entities),
            created_at=ha_device.created_at,
            updated_at=max(ha_device.updated_at, zigbee_device.last_seen if zigbee_device and zigbee_device.last_seen else datetime.min.replace(tzinfo=timezone.utc))
        )
        
        return unified_device
    
    def _parse_zigbee_device(self, zigbee_device: ZigbeeDevice) -> Optional[UnifiedDevice]:
        """Parse a standalone Zigbee device into unified format."""
        
        # Parse capabilities
        capabilities = self._parse_zigbee_capabilities(zigbee_device.exposes)
        
        # Extract device class from capabilities/exposes
        device_class = self._extract_device_class_from_zigbee(zigbee_device)
        
        # Create unified device
        unified_device = UnifiedDevice(
            id=f"zigbee_{zigbee_device.ieee_address}",
            name=zigbee_device.friendly_name,
            manufacturer=zigbee_device.manufacturer,
            model=zigbee_device.model,
            area_id=None,
            area_name=None,
            integration="zigbee2mqtt",
            device_class=device_class,
            sw_version=zigbee_device.software_build_id,
            hw_version=zigbee_device.hardware_version,
            power_source=zigbee_device.power_source,
            via_device_id=None,
            capabilities=capabilities,
            entities=[],
            ha_device=None,
            zigbee_device=zigbee_device,
            disabled_by=None,
            last_seen=zigbee_device.last_seen,
            health_score=self._calculate_health_score(None, zigbee_device, []),
            created_at=zigbee_device.last_seen or datetime.now(timezone.utc),
            updated_at=zigbee_device.last_seen or datetime.now(timezone.utc)
        )
        
        return unified_device
    
    def _find_matching_zigbee_device(
        self,
        ha_device: HADevice,
        zigbee_devices: Dict[str, ZigbeeDevice]
    ) -> Optional[ZigbeeDevice]:
        """Find matching Zigbee device for HA device."""
        
        # Try to match by identifiers
        for identifier in ha_device.identifiers:
            if len(identifier) >= 2:
                identifier_type, identifier_value = identifier[0], identifier[1]
                
                # Match by IEEE address
                if identifier_type == "ieee_address" and identifier_value in zigbee_devices:
                    return zigbee_devices[identifier_value]
                
                # Match by model/manufacturer
                if identifier_type in ["model", "manufacturer"]:
                    for zigbee_device in zigbee_devices.values():
                        if (identifier_type == "model" and zigbee_device.model == identifier_value) or \
                           (identifier_type == "manufacturer" and zigbee_device.manufacturer == identifier_value):
                            return zigbee_device
        
        return None
    
    def _is_zigbee_device_in_ha(
        self,
        zigbee_device: ZigbeeDevice,
        ha_devices: List[HADevice]
    ) -> bool:
        """Check if Zigbee device is already represented in HA."""
        
        for ha_device in ha_devices:
            for identifier in ha_device.identifiers:
                if len(identifier) >= 2 and identifier[0] == "ieee_address" and identifier[1] == zigbee_device.ieee_address:
                    return True
        
        return False
    
    def _parse_zigbee_capabilities(self, exposes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse Zigbee2MQTT exposes into capability format."""
        capabilities = []
        
        for expose in exposes:
            capability = {
                "name": expose.get("name", ""),
                "type": expose.get("type", ""),
                "properties": expose.get("properties", {}),
                "exposed": True,
                "configured": True,
                "source": "zigbee2mqtt"
            }
            capabilities.append(capability)
        
        return capabilities
    
    def _infer_non_mqtt_capabilities(self, entities: List[HAEntity], device: HADevice) -> List[Dict[str, Any]]:
        """Infer capabilities for non-MQTT devices based on entities and device class."""
        capabilities = []
        
        # Extract unique domains from entities
        domains = set(e.domain for e in entities)
        
        # Map domains to common capabilities
        domain_capabilities = {
            "light": {
                "name": "brightness",
                "type": "numeric",
                "properties": {"value_min": 0, "value_max": 255},
                "exposed": True,
                "configured": True,
                "source": "inferred"
            },
            "fan": {
                "name": "speed",
                "type": "enum",
                "properties": {"values": ["off", "low", "medium", "high"]},
                "exposed": True,
                "configured": True,
                "source": "inferred"
            },
            "climate": {
                "name": "temperature",
                "type": "numeric",
                "properties": {"value_min": 16, "value_max": 30, "unit": "celsius"},
                "exposed": True,
                "configured": True,
                "source": "inferred"
            },
            "cover": {
                "name": "position",
                "type": "numeric",
                "properties": {"value_min": 0, "value_max": 100},
                "exposed": True,
                "configured": True,
                "source": "inferred"
            }
        }
        
        # Add capabilities based on domains present
        for domain in domains:
            if domain in domain_capabilities:
                capabilities.append(domain_capabilities[domain].copy())
        
        return capabilities
    
    def _entity_to_dict(self, entity: HAEntity) -> Dict[str, Any]:
        """Convert HA entity to dictionary."""
        return {
            "entity_id": entity.entity_id,
            "name": entity.name,
            "platform": entity.platform,
            "domain": entity.domain,
            "disabled_by": entity.disabled_by,
            "entity_category": entity.entity_category,
            "unique_id": entity.unique_id,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat()
        }
    
    def _extract_device_class(self, entities: List[HAEntity]) -> Optional[str]:
        """Extract device class from entity domains."""
        domain_priority = ['light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover', 'lock', 'fan']
        
        # Try to find a device class from entity domains
        for domain in domain_priority:
            if any(e.domain == domain for e in entities):
                return domain
        
        # Return first entity domain if available
        return entities[0].domain if entities else None
    
    def _extract_device_class_from_zigbee(self, zigbee_device: ZigbeeDevice) -> Optional[str]:
        """Extract device class from Zigbee device capabilities."""
        if not zigbee_device.exposes:
            return None
        
        # Map common Zigbee capability types to device classes
        capability_to_class = {
            'light': 'light',
            'switch': 'switch',
            'occupancy': 'sensor',
            'temperature': 'sensor',
            'humidity': 'sensor',
            'battery': 'sensor',
            'cover': 'cover',
            'lock': 'lock',
            'fan': 'fan',
            'climate': 'climate'
        }
        
        for expose in zigbee_device.exposes:
            if isinstance(expose, dict):
                expose_type = expose.get('type', '').lower()
                if expose_type in capability_to_class:
                    return capability_to_class[expose_type]
                expose_name = expose.get('name', '').lower()
                if expose_name in capability_to_class:
                    return capability_to_class[expose_name]
        
        return None
    
    def _calculate_health_score(
        self,
        ha_device: Optional[HADevice],
        zigbee_device: Optional[ZigbeeDevice],
        entities: List[HAEntity]
    ) -> int:
        """Calculate device health score (0-100)."""
        score = 100
        
        # Deduct for disabled device
        if ha_device and ha_device.disabled_by:
            score -= 20
        
        # Deduct for disabled entities
        disabled_entities = len([e for e in entities if e.disabled_by])
        if entities:
            disabled_ratio = disabled_entities / len(entities)
            score -= int(disabled_ratio * 30)
        
        # Deduct for old last seen (Zigbee devices)
        if zigbee_device and zigbee_device.last_seen:
            hours_since_seen = (datetime.now(timezone.utc) - zigbee_device.last_seen).total_seconds() / 3600
            if hours_since_seen > 24:
                score -= min(30, int(hours_since_seen / 24) * 5)
        
        # Deduct for missing critical information
        if not ha_device or not ha_device.manufacturer:
            score -= 10
        if not ha_device or not ha_device.model:
            score -= 10
        
        return max(0, score)
    
    def get_device(self, device_id: str) -> Optional[UnifiedDevice]:
        """Get unified device by ID."""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[UnifiedDevice]:
        """Get all unified devices."""
        return list(self.devices.values())
    
    def get_devices_by_area(self, area_id: str) -> List[UnifiedDevice]:
        """Get devices by area ID."""
        return [d for d in self.devices.values() if d.area_id == area_id]
    
    def get_devices_by_integration(self, integration: str) -> List[UnifiedDevice]:
        """Get devices by integration type."""
        return [d for d in self.devices.values() if d.integration == integration]
