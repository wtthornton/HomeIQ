"""
Entity Model for SQLite Storage
Story 22.2 - Simple entity registry with FK to devices
Epic 2025: Enhanced with Entity Registry name fields and capabilities
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Entity(Base):
    """Entity registry model - stores HA entity metadata with device relationship"""
    
    __tablename__ = "entities"
    
    # Primary key
    entity_id = Column(String, primary_key=True)
    
    # Foreign key to device
    device_id = Column(String, ForeignKey("devices.device_id", ondelete="CASCADE"), index=True)
    
    # Entity metadata
    domain = Column(String, nullable=False, index=True)  # light, sensor, switch, etc.
    platform = Column(String)  # Integration platform
    unique_id = Column(String)  # Unique ID within platform
    area_id = Column(String, index=True)  # Room/area location
    disabled = Column(Boolean, default=False)
    
    # Entity Registry Name Fields (2025 HA API)
    name = Column(String)  # Primary friendly name from Entity Registry (what shows in HA UI)
    name_by_user = Column(String)  # User-customized name (if set)
    original_name = Column(String)  # Original name before user customization
    friendly_name = Column(String, index=True)  # Computed: name_by_user or name or original_name
    
    # Entity Capabilities (2025 HA API)
    supported_features = Column(Integer)  # Bitmask of supported features (from attributes.supported_features)
    capabilities = Column(JSON)  # Parsed capabilities list (brightness, color, effect, etc.)
    available_services = Column(JSON)  # List of available service calls for this entity (e.g., ["light.turn_on", "light.turn_off", "light.toggle"])
    
    # Entity Attributes
    icon = Column(String)  # Entity icon from attributes
    device_class = Column(String, index=True)  # Device class (e.g., "motion", "door", "temperature")
    unit_of_measurement = Column(String)  # Unit of measurement for sensors
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to device
    device = relationship("Device", back_populates="entities")
    
    def __repr__(self):
        return f"<Entity(entity_id='{self.entity_id}', friendly_name='{self.friendly_name}', domain='{self.domain}')>"


# Indexes for common queries
Index('idx_entity_device', Entity.device_id)
Index('idx_entity_domain', Entity.domain)
Index('idx_entity_area', Entity.area_id)
Index('idx_entity_friendly_name', Entity.friendly_name)
Index('idx_entity_supported_features', Entity.supported_features)
Index('idx_entity_device_class', Entity.device_class)

