"""
Data models for Home Assistant device and entity discovery

Simple dataclasses for storing device, entity, and config entry information.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Device:
    """Device model representing a Home Assistant device"""

    device_id: str
    name: str
    manufacturer: str
    model: str
    sw_version: str | None = None
    area_id: str | None = None
    entity_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> bool:
        """Validate required fields"""
        if not self.device_id:
            raise ValueError("device_id is required")
        if not self.name:
            raise ValueError("name is required")
        return True

    def to_influx_point(self) -> dict[str, Any]:
        """
        Convert device to InfluxDB point format
        
        Returns:
            Dictionary with measurement, tags, fields, and time
        """
        return {
            "measurement": "devices",
            "tags": {
                "device_id": self.device_id,
                "manufacturer": self.manufacturer or "Unknown",
                "model": self.model or "Unknown",
                "area_id": self.area_id or "unassigned"
            },
            "fields": {
                "name": self.name,
                "sw_version": self.sw_version or "Unknown",
                "entity_count": self.entity_count
            },
            "time": self.timestamp
        }

    @classmethod
    def from_ha_device(cls, ha_device: dict[str, Any]) -> 'Device':
        """
        Create Device from Home Assistant device registry entry
        
        Args:
            ha_device: Device dictionary from HA registry
            
        Returns:
            Device instance
        """
        return cls(
            device_id=ha_device.get("id", ""),
            name=ha_device.get("name") or ha_device.get("name_by_user") or "Unknown Device",
            manufacturer=ha_device.get("manufacturer", "Unknown"),
            model=ha_device.get("model", "Unknown"),
            sw_version=ha_device.get("sw_version"),
            area_id=ha_device.get("area_id"),
            entity_count=0  # Will be calculated later
        )


@dataclass
class Entity:
    """Entity model representing a Home Assistant entity"""

    entity_id: str
    device_id: str | None = None
    domain: str = "unknown"
    platform: str = "unknown"
    unique_id: str | None = None
    area_id: str | None = None
    disabled: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> bool:
        """Validate required fields"""
        if not self.entity_id:
            raise ValueError("entity_id is required")
        return True

    def to_influx_point(self) -> dict[str, Any]:
        """
        Convert entity to InfluxDB point format
        
        Returns:
            Dictionary with measurement, tags, fields, and time
        """
        return {
            "measurement": "entities",
            "tags": {
                "entity_id": self.entity_id,
                "device_id": self.device_id or "unknown",
                "domain": self.domain,
                "platform": self.platform,
                "area_id": self.area_id or "unassigned"
            },
            "fields": {
                "unique_id": self.unique_id or "",
                "disabled": self.disabled
            },
            "time": self.timestamp
        }

    @classmethod
    def from_ha_entity(cls, ha_entity: dict[str, Any]) -> 'Entity':
        """
        Create Entity from Home Assistant entity registry entry
        
        Args:
            ha_entity: Entity dictionary from HA registry
            
        Returns:
            Entity instance
        """
        entity_id = ha_entity.get("entity_id", "")
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"

        return cls(
            entity_id=entity_id,
            device_id=ha_entity.get("device_id"),
            domain=domain,
            platform=ha_entity.get("platform", "unknown"),
            unique_id=ha_entity.get("unique_id"),
            area_id=ha_entity.get("area_id"),
            disabled=ha_entity.get("disabled_by") is not None
        )


@dataclass
class ConfigEntry:
    """Config entry model representing a Home Assistant integration"""

    entry_id: str
    domain: str
    title: str
    state: str = "unknown"
    version: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> bool:
        """Validate required fields"""
        if not self.entry_id:
            raise ValueError("entry_id is required")
        if not self.domain:
            raise ValueError("domain is required")
        return True

    def to_influx_point(self) -> dict[str, Any]:
        """
        Convert config entry to InfluxDB point format
        
        Returns:
            Dictionary with measurement, tags, fields, and time
        """
        return {
            "measurement": "config_entries",
            "tags": {
                "entry_id": self.entry_id,
                "domain": self.domain,
                "state": self.state
            },
            "fields": {
                "title": self.title,
                "version": self.version
            },
            "time": self.timestamp
        }

    @classmethod
    def from_ha_config_entry(cls, ha_entry: dict[str, Any]) -> 'ConfigEntry':
        """
        Create ConfigEntry from Home Assistant config entry
        
        Args:
            ha_entry: Config entry dictionary from HA
            
        Returns:
            ConfigEntry instance
        """
        return cls(
            entry_id=ha_entry.get("entry_id", ""),
            domain=ha_entry.get("domain", "unknown"),
            title=ha_entry.get("title", "Unknown Integration"),
            state=ha_entry.get("state", "unknown"),
            version=ha_entry.get("version", 1)
        )

