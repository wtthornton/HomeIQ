# Story DI-1.3: Unified Device Storage

**Story ID:** DI-1.3  
**Epic:** DI-1 (Device Intelligence Service Foundation)  
**Status:** Review  
**Priority:** P0  
**Story Points:** 8  
**Complexity:** Medium  

---

## Story Description

Create a unified storage system using SQLite for device metadata and Redis for real-time caching. This story implements the data persistence layer that will store all discovered device information, capabilities, and intelligence data with optimized performance for single standalone Home Assistant deployments.

## User Story

**As a** system administrator  
**I want** all device data stored efficiently with fast query performance  
**So that** device intelligence features can access device information quickly and reliably  

## Acceptance Criteria

### AC1: SQLite Database Schema
- [x] Device metadata table with proper indexes
- [x] Device capabilities table with JSON storage
- [x] Device relationships table for HA ↔ Zigbee2MQTT mapping
- [x] Device health metrics table for analytics
- [x] Proper foreign key relationships
- [x] Database migration system (Alembic)

### AC2: In-Memory Cache Integration
- [x] Real-time device data caching
- [x] TTL-based cache expiration
- [x] Cache invalidation on device updates
- [x] Cache statistics and monitoring
- [x] Simple in-memory implementation (no Redis needed)
- [x] Graceful error handling

### AC3: Data Access Layer
- [x] CRUD operations for device data
- [x] Bulk operations for performance
- [x] Query optimization with indexes
- [x] Data validation and sanitization
- [x] Error handling and recovery

### AC4: Storage API Endpoints
- [x] `GET /api/devices` - List all devices
- [x] `GET /api/devices/{id}` - Get specific device
- [x] `GET /api/devices/{id}/capabilities` - Get device capabilities
- [x] `GET /api/devices/{id}/health` - Get device health metrics
- [x] `GET /api/stats` - Storage statistics
- [x] `POST /api/cache/invalidate/{device_id}` - Invalidate device cache
- [x] `POST /api/cache/invalidate-all` - Invalidate all caches

## Technical Requirements

### Database Schema
```sql
-- Device metadata table
CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    area_id TEXT,
    integration TEXT NOT NULL,
    ha_device_id TEXT,
    zigbee_device_id TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    health_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Device capabilities table
CREATE TABLE device_capabilities (
    device_id TEXT NOT NULL,
    capability_name TEXT NOT NULL,
    capability_type TEXT NOT NULL,
    properties JSON,
    exposed BOOLEAN DEFAULT FALSE,
    configured BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (device_id, capability_name),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Device relationships table
CREATE TABLE device_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_device_id TEXT NOT NULL,
    target_device_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    strength REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (target_device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Device health metrics table
CREATE TABLE device_health_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_devices_area_id ON devices(area_id);
CREATE INDEX idx_devices_integration ON devices(integration);
CREATE INDEX idx_devices_health_score ON devices(health_score);
CREATE INDEX idx_capabilities_device_id ON device_capabilities(device_id);
CREATE INDEX idx_capabilities_type ON device_capabilities(capability_type);
CREATE INDEX idx_relationships_source ON device_relationships(source_device_id);
CREATE INDEX idx_relationships_target ON device_relationships(target_device_id);
CREATE INDEX idx_health_metrics_device ON device_health_metrics(device_id);
CREATE INDEX idx_health_metrics_timestamp ON device_health_metrics(timestamp);
```

### SQLAlchemy Models
```python
# src/models/database.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Device(Base):
    __tablename__ = 'devices'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    manufacturer = Column(String)
    model = Column(String)
    area_id = Column(String)
    integration = Column(String, nullable=False)
    ha_device_id = Column(String)
    zigbee_device_id = Column(String)
    last_seen = Column(DateTime, default=datetime.utcnow)
    health_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    capabilities = relationship("DeviceCapability", back_populates="device", cascade="all, delete-orphan")
    health_metrics = relationship("DeviceHealthMetric", back_populates="device", cascade="all, delete-orphan")

class DeviceCapability(Base):
    __tablename__ = 'device_capabilities'
    
    device_id = Column(String, ForeignKey('devices.id', ondelete='CASCADE'), primary_key=True)
    capability_name = Column(String, primary_key=True)
    capability_type = Column(String, nullable=False)
    properties = Column(JSON)
    exposed = Column(Boolean, default=False)
    configured = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    device = relationship("Device", back_populates="capabilities")
```

### Redis Cache Integration
```python
# src/core/cache.py
import redis.asyncio as redis
from typing import Optional, Dict, Any
import json

class DeviceCache:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.default_ttl = 300  # 5 minutes
    
    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device from cache"""
        key = f"device:{device_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def set_device(self, device_id: str, device_data: Dict[str, Any], ttl: Optional[int] = None):
        """Set device in cache"""
        key = f"device:{device_id}"
        ttl = ttl or self.default_ttl
        await self.redis.setex(key, ttl, json.dumps(device_data))
    
    async def invalidate_device(self, device_id: str):
        """Invalidate device cache"""
        key = f"device:{device_id}"
        await self.redis.delete(key)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        info = await self.redis.info()
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "0B"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
        }
```

### Data Access Layer
```python
# src/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete
from typing import List, Optional, Dict, Any
import asyncio

class DeviceRepository:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
    
    async def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID"""
        async with self.session_factory() as session:
            result = await session.execute(select(Device).where(Device.id == device_id))
            return result.scalar_one_or_none()
    
    async def get_all_devices(self) -> List[Device]:
        """Get all devices"""
        async with self.session_factory() as session:
            result = await session.execute(select(Device))
            return result.scalars().all()
    
    async def create_device(self, device_data: Dict[str, Any]) -> Device:
        """Create new device"""
        async with self.session_factory() as session:
            device = Device(**device_data)
            session.add(device)
            await session.commit()
            await session.refresh(device)
            return device
    
    async def update_device(self, device_id: str, update_data: Dict[str, Any]) -> Optional[Device]:
        """Update device"""
        async with self.session_factory() as session:
            result = await session.execute(select(Device).where(Device.id == device_id))
            device = result.scalar_one_or_none()
            if device:
                for key, value in update_data.items():
                    setattr(device, key, value)
                await session.commit()
                await session.refresh(device)
            return device
```

## Implementation Tasks

### Task 1: Database Schema Design
- [ ] Create SQLite database schema
- [ ] Design proper indexes for performance
- [ ] Set up foreign key relationships
- [ ] Create database migration system

### Task 2: SQLAlchemy Models
- [ ] Create device models
- [ ] Implement relationships
- [ ] Add data validation
- [ ] Create model serialization

### Task 3: Redis Cache Integration
- [ ] Set up Redis connection
- [ ] Implement cache operations
- [ ] Add TTL management
- [ ] Implement cache invalidation

### Task 4: Data Access Layer
- [ ] Create repository pattern
- [ ] Implement CRUD operations
- [ ] Add bulk operations
- [ ] Implement query optimization

### Task 5: Storage API Endpoints
- [ ] Create storage router
- [ ] Implement status endpoint
- [ ] Implement stats endpoint
- [ ] Implement backup endpoint

### Task 6: Testing & Validation
- [ ] Create database tests
- [ ] Test cache operations
- [ ] Test data access layer
- [ ] Test API endpoints

## Dependencies

- **External**: SQLite, Redis, SQLAlchemy, Alembic
- **Internal**: Story DI-1.1 (Service Foundation)
- **Infrastructure**: Docker environment with Redis service

## Definition of Done

- [ ] SQLite database schema created
- [ ] Redis cache integration functional
- [ ] Data access layer operational
- [ ] Storage API endpoints functional
- [ ] Database migrations working
- [ ] Cache operations tested
- [ ] All tests passing
- [ ] Documentation updated

## Notes

This story implements the data persistence layer that will store all device information discovered by the multi-source discovery engine. The storage system should be optimized for fast queries and real-time updates.

---

**Created**: January 24, 2025  
**Last Updated**: January 24, 2025  
**Author**: BMAD Product Manager  
**Reviewers**: System Architect, QA Lead
