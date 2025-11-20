"""
Device Model for SQLite Storage
Story 22.2 - Simple device registry
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from ..database import Base


class Device(Base):
    """Device registry model - stores HA device metadata"""

    __tablename__ = "devices"

    # Primary key
    device_id = Column(String, primary_key=True)

    # Device metadata
    name = Column(String, nullable=False)
    name_by_user = Column(String)  # User-customized device name
    manufacturer = Column(String, default="Unknown")
    model = Column(String, default="Unknown")
    sw_version = Column(String, default="Unknown")
    area_id = Column(String, index=True)  # Room/area location
    integration = Column(String, index=True)  # HA integration source
    entry_type = Column(String)  # Entry type (service, config_entry, etc.)
    configuration_url = Column(String)  # Device configuration URL
    suggested_area = Column(String)  # Suggested area for device

    # Source tracking
    config_entry_id = Column(String, index=True)  # Config entry ID (source tracking)
    via_device = Column(String, ForeignKey("devices.device_id"), index=True)  # Parent device (self-referential FK)

    # Timestamps
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to entities
    entities = relationship("Entity", back_populates="device", cascade="all, delete-orphan")

    # Self-referential relationship for via_device
    parent_device = relationship("Device", remote_side="Device.device_id", foreign_keys=[via_device], backref="child_devices")

    def __repr__(self):
        return f"<Device(device_id='{self.device_id}', name='{self.name}')>"


# Indexes for common queries
Index('idx_device_area', Device.area_id)
Index('idx_device_integration', Device.integration)
Index('idx_device_manufacturer', Device.manufacturer)
Index('idx_device_config_entry', Device.config_entry_id)
Index('idx_device_via_device', Device.via_device)

