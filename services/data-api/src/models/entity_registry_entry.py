"""
EntityRegistryEntry Dataclass

Comprehensive entity registry entry with full relationship graph.
Matches pattern from home-assistant-pattern-improvements.md
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .entity import Entity
    from .device import Device


@dataclass
class EntityRegistryEntry:
    """Comprehensive entity registry entry with relationship tracking"""
    
    entity_id: str
    unique_id: str
    name: Optional[str] = None
    device_id: Optional[str] = None  # Links to device
    area_id: Optional[str] = None    # Links to area
    config_entry_id: Optional[str] = None  # Source tracking
    
    # Metadata
    platform: str = "unknown"
    domain: str = "unknown"
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    sw_version: Optional[str] = None
    via_device: Optional[str] = None  # Parent device (from device relationship)
    
    # Relationships
    related_entities: List[str] = field(default_factory=list)  # Siblings from same device
    capabilities: Dict[str, Any] = field(default_factory=dict)
    
    # Additional entity metadata
    friendly_name: Optional[str] = None
    name_by_user: Optional[str] = None
    original_name: Optional[str] = None
    disabled: bool = False
    supported_features: Optional[int] = None
    available_services: Optional[List[str]] = None
    icon: Optional[str] = None
    device_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    
    @classmethod
    def from_entity_and_device(
        cls,
        entity: "Entity",
        device: Optional["Device"] = None,
        related_entities: Optional[List[str]] = None
    ) -> "EntityRegistryEntry":
        """
        Create EntityRegistryEntry from Entity and Device models
        
        Args:
            entity: Entity model instance
            device: Optional Device model instance
            related_entities: Optional list of sibling entity IDs
            
        Returns:
            EntityRegistryEntry instance
        """
        return cls(
            entity_id=entity.entity_id,
            unique_id=entity.unique_id or "",
            name=entity.name,
            device_id=entity.device_id,
            area_id=entity.area_id,
            config_entry_id=entity.config_entry_id,
            platform=entity.platform or "unknown",
            domain=entity.domain or "unknown",
            manufacturer=device.manufacturer if device else None,
            model=device.model if device else None,
            sw_version=device.sw_version if device else None,
            via_device=device.via_device if device else None,
            related_entities=related_entities or [],
            capabilities=entity.capabilities or {},
            friendly_name=entity.friendly_name,
            name_by_user=entity.name_by_user,
            original_name=entity.original_name,
            disabled=entity.disabled,
            supported_features=entity.supported_features,
            available_services=entity.available_services,
            icon=entity.icon,
            device_class=entity.device_class,
            unit_of_measurement=entity.unit_of_measurement
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'entity_id': self.entity_id,
            'unique_id': self.unique_id,
            'name': self.name,
            'device_id': self.device_id,
            'area_id': self.area_id,
            'config_entry_id': self.config_entry_id,
            'platform': self.platform,
            'domain': self.domain,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'sw_version': self.sw_version,
            'via_device': self.via_device,
            'related_entities': self.related_entities,
            'capabilities': self.capabilities,
            'friendly_name': self.friendly_name,
            'name_by_user': self.name_by_user,
            'original_name': self.original_name,
            'disabled': self.disabled,
            'supported_features': self.supported_features,
            'available_services': self.available_services,
            'icon': self.icon,
            'device_class': self.device_class,
            'unit_of_measurement': self.unit_of_measurement
        }

