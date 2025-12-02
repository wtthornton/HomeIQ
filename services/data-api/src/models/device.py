"""
Device Model for SQLite Storage
Story 22.2 - Simple device registry
Phase 1.1: Enhanced with device intelligence fields
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, JSON, String, Text
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

    # Device Registry 2025 Attributes (Phase 2-3 Implementation)
    labels = Column(JSON)  # Array of label IDs for organizational filtering
    serial_number = Column(String, nullable=True)  # Optional serial number (if available from integration)
    model_id = Column(String, nullable=True)  # Optional model ID (manufacturer identifier, may differ from model)

    # Source tracking
    config_entry_id = Column(String, index=True)  # Config entry ID (source tracking)
    via_device = Column(String, ForeignKey("devices.device_id"), index=True)  # Parent device (self-referential FK)

    # Phase 1.1: Device intelligence fields
    device_type = Column(String, index=True)  # Device classification: "fridge", "light", "sensor", "thermostat", etc.
    device_category = Column(String, index=True)  # Category: "appliance", "lighting", "security", "climate"
    power_consumption_idle_w = Column(Float)  # Standby power consumption
    power_consumption_active_w = Column(Float)  # Active power consumption
    power_consumption_max_w = Column(Float)  # Peak power consumption
    infrared_codes_json = Column(Text)  # IR codes if applicable (stored as JSON string)
    setup_instructions_url = Column(String)  # Link to setup guide
    troubleshooting_notes = Column(Text)  # Common issues and solutions
    device_features_json = Column(Text)  # Structured capabilities (stored as JSON string)
    community_rating = Column(Float)  # Rating from Device Database (if available)
    last_capability_sync = Column(DateTime)  # When capabilities were last updated

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
# Phase 1.1: Device intelligence indexes
Index('idx_device_type', Device.device_type)
Index('idx_device_category', Device.device_category)

