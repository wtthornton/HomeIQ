"""
Entity Model for Database Storage
Story 22.2 - Simple entity registry with FK to devices
Epic 2025: Enhanced with Entity Registry name fields and capabilities
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

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
    name_by_user = Column(String)  # User-customized name (if set) - PRIORITY: Used first for display
    original_name = Column(String)  # Original name before user customization
    friendly_name = Column(String, index=True)  # Stored computed value: name_by_user or name or original_name
    # NOTE: friendly_name is computed at write time with priority: name_by_user > name > original_name
    # This ensures users see their custom names from Home Assistant when available

    # Entity Capabilities (2025 HA API)
    supported_features = Column(Integer)  # Bitmask of supported features (from attributes.supported_features)
    capabilities = Column(JSONB)  # Parsed capabilities list (brightness, color, effect, etc.)
    available_services = Column(JSONB)  # List of available service calls for this entity (e.g., ["light.turn_on", "light.turn_off", "light.toggle"])

    # Entity Attributes
    icon = Column(String)  # Current icon (from Entity Registry, may be user-customized)
    original_icon = Column(String)  # Original icon from integration/platform
    device_class = Column(String, index=True)  # Device class (e.g., "motion", "door", "temperature")
    unit_of_measurement = Column(String)  # Unit of measurement for sensors

    # Entity Registry 2025 Attributes (Phase 1-2 Implementation)
    aliases = Column(JSONB)  # Array of alternative names for entity resolution
    labels = Column(JSONB)  # Array of label IDs for organizational filtering
    options = Column(JSONB)  # Entity-specific options/config (e.g., default brightness, preferred colors)

    # Source tracking
    config_entry_id = Column(String, index=True)  # Config entry ID (source tracking)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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
Index('idx_entity_config_entry', Entity.config_entry_id)
# Phase 1-2: Indexes for new 2025 HA API attributes
Index('idx_entity_name_by_user', Entity.name_by_user)  # For user-customized name lookups
# Story 62.2-62.3: GIN indexes for JSONB label/alias queries
Index('idx_entity_labels_gin', Entity.labels, postgresql_using='gin')
Index('idx_entity_aliases_gin', Entity.aliases, postgresql_using='gin')

