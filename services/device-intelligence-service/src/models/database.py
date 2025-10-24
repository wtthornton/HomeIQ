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
