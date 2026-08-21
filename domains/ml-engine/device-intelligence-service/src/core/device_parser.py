"""
Device Intelligence Service - Device Parser

Device data parsing and normalization for multi-source device discovery.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..clients.ha_client import HAArea, HADevice, HAEntity

logger = logging.getLogger(__name__)


@dataclass
class UnifiedDevice:
    """Unified device representation built from Home Assistant registry data."""

    # Core identification
    id: str
    name: str
    manufacturer: str
    model: str

    # Location and organization
    area_id: str | None = None
    area_name: str | None = None
    integration: str = "unknown"
    device_class: str | None = None  # Device type (light, sensor, etc.)

    # Device metadata
    sw_version: str | None = None
    hw_version: str | None = None
    power_source: str | None = None
    via_device_id: str | None = None

    # Capabilities and features
    capabilities: list[dict[str, Any]] = None
    entities: list[dict[str, Any]] = None

    # Source data references
    ha_device: HADevice | None = None

    # Status and health
    disabled_by: str | None = None
    last_seen: datetime | None = None
    health_score: int | None = None

    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        """Initialize mutable defaults after dataclass init."""
        if self.capabilities is None:
            object.__setattr__(self, "capabilities", [])
        if self.entities is None:
            object.__setattr__(self, "entities", [])
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(UTC))
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", datetime.now(UTC))


class DeviceParser:
    """Parser for normalizing device data from multiple sources."""

    def __init__(self):
        self.devices: dict[str, UnifiedDevice] = {}
        self.areas: dict[str, HAArea] = {}
        self.config_entries: dict[str, str] = {}  # Maps config_entry_id -> domain/integration

    def update_areas(self, areas: list[HAArea]):
        """Update area registry for device normalization."""
        self.areas = {area.area_id: area for area in areas}
        logger.info(f"Updated area registry with {len(self.areas)} areas")

    def update_config_entries(self, config_entries: dict[str, str]):
        """Update config entries mapping for integration resolution."""
        self.config_entries = config_entries
        logger.info(f"Updated config entries mapping with {len(self.config_entries)} entries")

    def parse_devices(
        self,
        ha_devices: list[HADevice],
        ha_entities: list[HAEntity],
    ) -> list[UnifiedDevice]:
        """Parse and normalize devices from the Home Assistant registries."""
        logger.info(f"Parsing {len(ha_devices)} HA devices, {len(ha_entities)} entities")

        unified_devices = []

        # Process Home Assistant devices
        for ha_device in ha_devices:
            try:
                unified_device = self._parse_ha_device(ha_device, ha_entities)
                if unified_device:
                    unified_devices.append(unified_device)
                    self.devices[unified_device.id] = unified_device
            except Exception as e:
                logger.error(f"Error parsing HA device {ha_device.id}: {e}")

        logger.info(f"Parsed {len(unified_devices)} unified devices")
        return unified_devices

    def _parse_ha_device(
        self,
        ha_device: HADevice,
        ha_entities: list[HAEntity],
    ) -> UnifiedDevice | None:
        """Parse a Home Assistant device into unified format."""

        # Get device entities
        device_entities = [e for e in ha_entities if e.device_id == ha_device.id]

        # Infer capabilities from the device's entities and device class
        capabilities = self._infer_capabilities_from_entities(device_entities, ha_device)

        # Get area name
        area_name = None
        if ha_device.area_id and ha_device.area_id in self.areas:
            area_name = self.areas[ha_device.area_id].name

        # Resolve integration from config entries
        integration = self._resolve_integration(ha_device)

        # Extract device class
        device_class = self._extract_device_class(device_entities)

        # Create unified device
        unified_device = UnifiedDevice(
            id=ha_device.id,
            name=ha_device.name_by_user or ha_device.name,  # Prefer user-customized name
            manufacturer=ha_device.manufacturer or "Unknown",
            model=ha_device.model or "Unknown",
            area_id=ha_device.area_id,
            area_name=area_name,
            integration=integration,
            device_class=device_class,
            sw_version=ha_device.sw_version,
            hw_version=ha_device.hw_version,
            power_source=None,
            via_device_id=ha_device.via_device_id,
            capabilities=capabilities,
            entities=[self._entity_to_dict(e) for e in device_entities],
            ha_device=ha_device,
            disabled_by=ha_device.disabled_by,
            last_seen=None,
            health_score=self._calculate_health_score(ha_device, device_entities),
            created_at=ha_device.created_at,
            updated_at=ha_device.updated_at,
        )

        return unified_device

    def _resolve_integration(self, ha_device: HADevice) -> str:
        """
        Resolve integration name from device's config entries.

        Args:
            ha_device: Home Assistant device

        Returns:
            Integration domain name, or "unknown" if not found
        """
        # If device has config_entries, look up the integration from the first one
        if ha_device.config_entries and len(ha_device.config_entries) > 0:
            config_entry_id = ha_device.config_entries[0]
            integration = self.config_entries.get(config_entry_id)
            if integration:
                return integration

        # Fallback: try to extract from identifiers
        for identifier in ha_device.identifiers:
            if len(identifier) >= 2:
                # First element is often the integration domain
                potential_integration = identifier[0]
                # Filter out non-integration identifiers
                if potential_integration not in ["ieee_address", "mac", "serial"]:
                    return potential_integration

        # Last fallback
        return "unknown"

    def _infer_capabilities_from_entities(
        self, entities: list[HAEntity], _device: HADevice
    ) -> list[dict[str, Any]]:
        """Infer capabilities from a device's entities and device class."""
        capabilities = []

        # Extract unique domains from entities
        domains = {e.domain for e in entities}

        # Map domains to common capabilities
        domain_capabilities = {
            "light": {
                "name": "brightness",
                "type": "numeric",
                "properties": {"value_min": 0, "value_max": 255},
                "exposed": True,
                "configured": True,
                "source": "inferred",
            },
            "fan": {
                "name": "speed",
                "type": "enum",
                "properties": {"values": ["off", "low", "medium", "high"]},
                "exposed": True,
                "configured": True,
                "source": "inferred",
            },
            "climate": {
                "name": "temperature",
                "type": "numeric",
                "properties": {"value_min": 16, "value_max": 30, "unit": "celsius"},
                "exposed": True,
                "configured": True,
                "source": "inferred",
            },
            "cover": {
                "name": "position",
                "type": "numeric",
                "properties": {"value_min": 0, "value_max": 100},
                "exposed": True,
                "configured": True,
                "source": "inferred",
            },
        }

        # Add capabilities based on domains present
        for domain in domains:
            if domain in domain_capabilities:
                capabilities.append(domain_capabilities[domain].copy())

        return capabilities

    def _entity_to_dict(self, entity: HAEntity) -> dict[str, Any]:
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
            "updated_at": entity.updated_at.isoformat(),
        }

    def _extract_device_class(self, entities: list[HAEntity]) -> str | None:
        """Extract device class from entity domains."""
        domain_priority = [
            "light",
            "switch",
            "sensor",
            "binary_sensor",
            "climate",
            "cover",
            "lock",
            "fan",
        ]

        # Try to find a device class from entity domains
        for domain in domain_priority:
            if any(e.domain == domain for e in entities):
                return domain

        # Return first entity domain if available
        return entities[0].domain if entities else None

    def _calculate_health_score(
        self,
        ha_device: HADevice | None,
        entities: list[HAEntity],
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

        # Deduct for missing critical information
        if not ha_device or not ha_device.manufacturer:
            score -= 10
        if not ha_device or not ha_device.model:
            score -= 10

        return max(0, score)

    def get_device(self, device_id: str) -> UnifiedDevice | None:
        """Get unified device by ID."""
        return self.devices.get(device_id)

    def get_all_devices(self) -> list[UnifiedDevice]:
        """Get all unified devices."""
        return list(self.devices.values())

    def get_devices_by_area(self, area_id: str) -> list[UnifiedDevice]:
        """Get devices by area ID."""
        return [d for d in self.devices.values() if d.area_id == area_id]

    def get_devices_by_integration(self, integration: str) -> list[UnifiedDevice]:
        """Get devices by integration type."""
        return [d for d in self.devices.values() if d.integration == integration]
