"""
Device Intelligence Service - Database Models

SQLAlchemy models for device storage and intelligence data.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

Base = declarative_base()


class Device(Base):
    """Device metadata table."""
    __tablename__ = 'devices'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String)
    model: Mapped[Optional[str]] = mapped_column(String)
    area_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    area_name: Mapped[Optional[str]] = mapped_column(String)
    integration: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sw_version: Mapped[Optional[str]] = mapped_column(String)
    hw_version: Mapped[Optional[str]] = mapped_column(String)
    power_source: Mapped[Optional[str]] = mapped_column(String)
    via_device_id: Mapped[Optional[str]] = mapped_column(String)
    ha_device_id: Mapped[Optional[str]] = mapped_column(String)
    zigbee_device_id: Mapped[Optional[str]] = mapped_column(String)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    health_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    disabled_by: Mapped[Optional[str]] = mapped_column(String)
    
    # Device classification
    device_class: Mapped[Optional[str]] = mapped_column(String, index=True)
    config_entry_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    connections_json: Mapped[Optional[str]] = mapped_column(Text)  # Store as JSON string
    identifiers_json: Mapped[Optional[str]] = mapped_column(Text)  # Store as JSON string
    zigbee_ieee: Mapped[Optional[str]] = mapped_column(String, index=True)
    is_battery_powered: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Additional HA device attributes
    name_by_user: Mapped[Optional[str]] = mapped_column(String)  # User-customized device name
    suggested_area: Mapped[Optional[str]] = mapped_column(String)  # Suggested area for device
    entry_type: Mapped[Optional[str]] = mapped_column(String)  # Entry type (service, config_entry, etc.)
    configuration_url: Mapped[Optional[str]] = mapped_column(String)  # Device configuration URL
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    capabilities: Mapped[List["DeviceCapability"]] = relationship(
        "DeviceCapability", 
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    health_metrics: Mapped[List["DeviceHealthMetric"]] = relationship(
        "DeviceHealthMetric", 
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    relationships: Mapped[List["DeviceRelationship"]] = relationship(
        "DeviceRelationship",
        foreign_keys="DeviceRelationship.source_device_id",
        back_populates="source_device",
        cascade="all, delete-orphan"
    )
    target_relationships: Mapped[List["DeviceRelationship"]] = relationship(
        "DeviceRelationship",
        foreign_keys="DeviceRelationship.target_device_id",
        back_populates="target_device",
        cascade="all, delete-orphan"
    )


class DeviceCapability(Base):
    """Device capabilities table."""
    __tablename__ = 'device_capabilities'
    
    device_id: Mapped[str] = mapped_column(String, ForeignKey('devices.id', ondelete='CASCADE'), primary_key=True)
    capability_name: Mapped[str] = mapped_column(String, primary_key=True)
    capability_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    properties: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    exposed: Mapped[bool] = mapped_column(Boolean, default=False)
    configured: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String, default="unknown")  # zigbee2mqtt, homeassistant, etc.
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="capabilities")


class DeviceRelationship(Base):
    """Device relationships table."""
    __tablename__ = 'device_relationships'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_device_id: Mapped[str] = mapped_column(String, ForeignKey('devices.id', ondelete='CASCADE'), index=True)
    target_device_id: Mapped[str] = mapped_column(String, ForeignKey('devices.id', ondelete='CASCADE'), index=True)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)  # parent, child, sibling, etc.
    strength: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    source_device: Mapped["Device"] = relationship("Device", foreign_keys=[source_device_id], back_populates="relationships")
    target_device: Mapped["Device"] = relationship("Device", foreign_keys=[target_device_id], back_populates="target_relationships")


class DeviceHealthMetric(Base):
    """Device health metrics table."""
    __tablename__ = 'device_health_metrics'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, ForeignKey('devices.id', ondelete='CASCADE'), index=True)
    metric_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_unit: Mapped[Optional[str]] = mapped_column(String)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    
    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="health_metrics")


class DeviceEntity(Base):
    """Device entities table (from Home Assistant)."""
    __tablename__ = 'device_entities'
    
    entity_id: Mapped[str] = mapped_column(String, primary_key=True)
    device_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey('devices.id', ondelete='CASCADE'), index=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    original_name: Mapped[Optional[str]] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False, index=True)
    disabled_by: Mapped[Optional[str]] = mapped_column(String)
    entity_category: Mapped[Optional[str]] = mapped_column(String)
    hidden_by: Mapped[Optional[str]] = mapped_column(String)
    has_entity_name: Mapped[bool] = mapped_column(Boolean, default=False)
    original_icon: Mapped[Optional[str]] = mapped_column(String)
    unique_id: Mapped[str] = mapped_column(String, nullable=False)
    translation_key: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    device: Mapped[Optional["Device"]] = relationship("Device")


class DeviceHygieneIssue(Base):
    """Captured device/entity hygiene issues for remediation."""

    __tablename__ = 'device_hygiene_issues'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    issue_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, default="medium", index=True)
    status: Mapped[str] = mapped_column(String, default="open", index=True)

    device_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey('devices.id', ondelete='SET NULL'), index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey('device_entities.entity_id', ondelete='SET NULL'), index=True)

    name: Mapped[Optional[str]] = mapped_column(String)
    suggested_action: Mapped[Optional[str]] = mapped_column(String)
    suggested_value: Mapped[Optional[str]] = mapped_column(String)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class DiscoverySession(Base):
    """Discovery session tracking table."""
    __tablename__ = 'discovery_sessions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, nullable=False)  # running, completed, failed
    devices_discovered: Mapped[int] = mapped_column(Integer, default=0)
    capabilities_discovered: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[Optional[List[str]]] = mapped_column(JSON)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


class CacheStats(Base):
    """Cache statistics table."""
    __tablename__ = 'cache_stats'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_type: Mapped[str] = mapped_column(String, nullable=False)  # redis, memory, etc.
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    miss_count: Mapped[int] = mapped_column(Integer, default=0)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    hit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    memory_usage: Mapped[Optional[str]] = mapped_column(String)
    key_count: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)


class TeamTrackerIntegration(Base):
    """Team Tracker integration status and configuration."""
    __tablename__ = 'team_tracker_integration'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    is_installed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    installation_status: Mapped[str] = mapped_column(String, default="not_installed")  # not_installed, detected, configured
    version: Mapped[Optional[str]] = mapped_column(String)
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class TeamTrackerTeam(Base):
    """Configured Team Tracker teams for automation context."""
    __tablename__ = 'team_tracker_teams'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[str] = mapped_column(String, nullable=False)  # Team abbreviation (e.g., "DAL", "NO")
    league_id: Mapped[str] = mapped_column(String, nullable=False, index=True)  # NFL, NBA, MLB, etc.
    team_name: Mapped[str] = mapped_column(String, nullable=False)  # Dallas Cowboys, New Orleans Saints
    team_long_name: Mapped[Optional[str]] = mapped_column(String)  # Full team name with city
    entity_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)  # sensor.team_tracker_cowboys
    sensor_name: Mapped[Optional[str]] = mapped_column(String)  # Custom sensor name from config
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Team metadata for AI context
    sport: Mapped[Optional[str]] = mapped_column(String)  # football, basketball, baseball, etc.
    team_abbreviation: Mapped[Optional[str]] = mapped_column(String)  # Short code
    team_logo: Mapped[Optional[str]] = mapped_column(String)  # Logo URL
    league_logo: Mapped[Optional[str]] = mapped_column(String)  # League logo URL

    # Configuration tracking
    configured_in_ha: Mapped[bool] = mapped_column(Boolean, default=False)  # Is this team configured in HA?
    last_detected: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # Last time entity was seen

    # User preferences
    user_notes: Mapped[Optional[str]] = mapped_column(Text)  # User notes about the team
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Priority for automation suggestions

    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
