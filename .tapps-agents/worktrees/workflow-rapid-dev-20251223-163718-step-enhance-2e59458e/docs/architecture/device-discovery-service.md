# Device Discovery Service Architecture

**Epic**: 19 - Device & Entity Discovery  
**Status**: Design  
**Complexity**: Low-Medium  
**Philosophy**: Simple, practical, reuse existing infrastructure

---

## Overview

Add device/entity discovery capability to existing WebSocket ingestion service. Query Home Assistant registries on startup and subscribe to registry change events for real-time updates.

**Key Principle**: Reuse everything, add minimal new code.

---

## Architecture Diagram (Updated October 2025)

### Current Implementation ✅

```
┌─────────────────────────────────────────────────┐
│        HOME ASSISTANT                            │
│  - Device Registry (99 devices)                 │
│  - Entity Registry (100+ entities)              │
│  - Config Entries                                │
└────────────────┬────────────────────────────────┘
                 │ WebSocket (on connect)
┌────────────────▼────────────────────────────────┐
│   WEBSOCKET INGESTION SERVICE                   │
│                                                  │
│   ✅ discovery_service.py                       │
│   - discover_devices()                          │
│   - discover_entities()                         │
│   - store_discovery_results()                   │
│                                                  │
│   ✅ main.py (_on_connect)                      │
│   - Triggers discovery on connect               │
│                                                  │
└────────────────┬────────────────────────────────┘
                 │ HTTP POST (aiohttp)
┌────────────────▼────────────────────────────────┐
│          DATA API SERVICE                        │
│                                                  │
│   ✅ POST /internal/devices/bulk_upsert         │
│   ✅ POST /internal/entities/bulk_upsert        │
│                                                  │
│   Uses: SQLAlchemy merge() for upsert           │
└────────────────┬────────────────────────────────┘
                 │ Store
┌────────────────▼────────────────────────────────┐
│            SQLITE (Primary) ✅                   │
│   - devices table (99 devices)                  │
│   - entities table (100+ entities)              │
│   - Fast queries (<10ms)                        │
│   - WAL mode enabled                            │
└────────────────┬────────────────────────────────┘
                 │ Query
┌────────────────▼────────────────────────────────┐
│          DATA API ENDPOINTS                      │
│   ✅ GET /api/devices                           │
│   ✅ GET /api/entities                          │
│   ✅ GET /api/integrations                      │
└────────────────┬────────────────────────────────┘
                 │ Served to
┌────────────────▼────────────────────────────────┐
│          HEALTH DASHBOARD                        │
│   - Overview Tab (HA Integration section)       │
│   - Devices Tab (full device browser)           │
└─────────────────────────────────────────────────┘
```

### Key Changes (October 2025)

**Before**: ❌ HA → InfluxDB → (manual sync) → SQLite  
**After**: ✅ HA → SQLite (direct via HTTP POST)

**Benefits**:
- Real-time updates (no sync lag)
- Simpler architecture (no sync scripts)
- Automated on connection
- Single source of truth

---

## Components

### 1. Discovery Service (NEW)

**File**: `services/websocket-ingestion/src/discovery_service.py`

**Purpose**: Send registry commands and handle responses

**Methods**:
```python
async def discover_devices(websocket) -> List[Device]:
    """Send device_registry/list command"""
    
async def discover_entities(websocket) -> List[Entity]:
    """Send entity_registry/list command"""
    
async def discover_config_entries(websocket) -> List[ConfigEntry]:
    """Send config_entries/list command"""
```

**Keep It Simple**:
- 3 functions, one per registry type
- Parse JSON response
- Return data models
- No complex logic

---

### 2. Registry Processor (NEW)

**File**: `services/websocket-ingestion/src/registry_processor.py`

**Purpose**: Convert HA registry data to our models and store

**Methods**:
```python
def process_device(device_data: dict) -> Device:
    """Convert HA device to our Device model"""
    
def process_entity(entity_data: dict) -> Entity:
    """Convert HA entity to our Entity model"""
    
async def store_devices(devices: List[Device], influxdb):
    """Batch write devices to InfluxDB"""
```

**Keep It Simple**:
- Extract only needed fields
- Minimal transformation
- Batch writes for performance

---

### 3. Data Models (NEW)

**File**: `services/websocket-ingestion/src/models.py`

**Purpose**: Simple data classes

```python
from dataclasses import dataclass

@dataclass
class Device:
    device_id: str
    name: str
    manufacturer: str
    model: str
    sw_version: str
    area_id: str
    entity_count: int
    timestamp: str

@dataclass
class Entity:
    entity_id: str
    device_id: str
    domain: str  # light, sensor, switch, etc
    platform: str
    unique_id: str
    area_id: str
    timestamp: str
```

**Keep It Simple**:
- Python dataclasses (built-in, simple)
- Only essential fields
- No complex relationships
- Easy to serialize

---

### 4. Connection Manager (ENHANCED)

**File**: `services/websocket-ingestion/src/connection_manager.py`

**Changes**:
```python
async def _on_connect(self):
    """Enhanced to include discovery"""
    # Existing: Subscribe to state_changed
    await self._subscribe_to_events()
    
    # NEW: Discover devices/entities on connect
    await self.discovery_service.discover_all()
    
    # NEW: Subscribe to registry events
    await self._subscribe_to_registry_events()

async def _subscribe_to_registry_events(self):
    """Subscribe to device/entity registry updates"""
    await self.client.send_json({
        "id": self._get_next_id(),
        "type": "subscribe_events",
        "event_type": "device_registry_updated"
    })
    await self.client.send_json({
        "id": self._get_next_id(),
        "type": "subscribe_events",
        "event_type": "entity_registry_updated"
    })
```

**Keep It Simple**:
- Add 2 method calls to existing flow
- Reuse existing subscription pattern
- No major refactoring

---

### 5. InfluxDB Storage (ENHANCED)

**File**: `services/websocket-ingestion/src/influxdb_wrapper.py`

**New Methods**:
```python
async def write_device(self, device: Device):
    """Write device to devices/ bucket"""
    point = {
        "measurement": "devices",
        "tags": {
            "device_id": device.device_id,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "area_id": device.area_id or "unknown"
        },
        "fields": {
            "name": device.name,
            "sw_version": device.sw_version,
            "entity_count": device.entity_count
        },
        "time": device.timestamp
    }
    await self._write("devices", point)

async def query_devices(self, filters: dict = None) -> List[Device]:
    """Query devices from InfluxDB"""
    # Simple Flux query
```

**Keep It Simple**:
- Copy existing write pattern
- Flat schema (no complex joins)
- Basic queries only

---

### 6. Admin API Endpoints (NEW)

**File**: `services/admin-api/src/devices_endpoints.py`

**Endpoints**:
```python
@router.get("/api/devices")
async def list_devices(
    limit: int = 100,
    manufacturer: str = None
):
    """List all devices"""
    devices = await influxdb.query_devices({
        "limit": limit,
        "manufacturer": manufacturer
    })
    return {"devices": devices}

@router.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    """Get single device"""
    device = await influxdb.get_device(device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    return device

@router.get("/api/entities")
async def list_entities(
    limit: int = 100,
    domain: str = None
):
    """List all entities"""
    # Similar to devices
```

**Keep It Simple**:
- Copy existing endpoint pattern
- Basic pagination (limit only)
- Simple filters
- Standard REST responses

---

## Data Flow

### Initial Discovery (On Startup)

```
1. WebSocket connects
2. Authenticate (existing)
3. Subscribe to state_changed (existing)
4. NEW: Send device_registry/list command
5. NEW: Parse devices, store in InfluxDB
6. NEW: Send entity_registry/list command
7. NEW: Parse entities, store in InfluxDB
8. NEW: Subscribe to registry update events
9. Start listening for events
```

### Real-Time Updates

```
1. HA device added/removed/changed
2. HA sends device_registry_updated event
3. Parse event data
4. Update InfluxDB
5. Log change
```

---

## InfluxDB Schema

### Devices Bucket

**Measurement**: `devices`

**Tags** (indexed):
- `device_id` (unique)
- `manufacturer`
- `model`
- `area_id`

**Fields**:
- `name` (string)
- `sw_version` (string)
- `entity_count` (int)

**Retention**: 90 days

### Entities Bucket

**Measurement**: `entities`

**Tags** (indexed):
- `entity_id` (unique)
- `device_id`
- `domain` (light, sensor, switch, etc.)
- `platform`
- `area_id`

**Fields**:
- `unique_id` (string)
- `disabled` (boolean)

**Retention**: 90 days

---

## Integration Points

### Existing Code to Reuse
1. ✅ **WebSocket Connection**: `websocket_client.py` - Already working
2. ✅ **Event Processing**: `event_processor.py` - Same pattern
3. ✅ **InfluxDB Writes**: `influxdb_wrapper.py` - Same methods
4. ✅ **API Endpoints**: `admin-api/src/main.py` - Same router pattern
5. ✅ **Error Handling**: `error_handler.py` - Same approach

### New Code to Add
1. 🆕 `discovery_service.py` - ~100 lines
2. 🆕 `registry_processor.py` - ~150 lines
3. 🆕 `models.py` - ~50 lines
4. 🆕 `devices_endpoints.py` - ~200 lines
5. 🔧 Enhance `connection_manager.py` - +30 lines

**Total New Code**: ~530 lines (minimal!)

---

## WebSocket Commands

### Device Registry
```json
{
  "id": 100,
  "type": "config/device_registry/list"
}
```

**Response**:
```json
{
  "id": 100,
  "type": "result",
  "success": true,
  "result": [
    {
      "id": "abc123",
      "name": "Living Room Light",
      "manufacturer": "Philips",
      "model": "Hue Bulb",
      "sw_version": "1.58.0",
      "area_id": "living_room",
      ...
    }
  ]
}
```

### Entity Registry
```json
{
  "id": 101,
  "type": "config/entity_registry/list"
}
```

### Subscribe to Updates
```json
{
  "id": 102,
  "type": "subscribe_events",
  "event_type": "device_registry_updated"
}
```

**Event Received**:
```json
{
  "id": 102,
  "type": "event",
  "event": {
    "event_type": "device_registry_updated",
    "data": {
      "action": "create",  // or "update", "remove"
      "device_id": "abc123",
      "device": { ... }
    }
  }
}
```

---

## Performance Considerations

### Initial Discovery
- **Time**: ~4 seconds (100 devices, 500 entities)
- **When**: Only on startup
- **Impact**: One-time cost

### Real-Time Updates
- **Frequency**: ~25 events/day (rare)
- **Latency**: < 100ms
- **Impact**: Negligible

### Storage
- **Size**: ~200MB (90 days, typical home)
- **Impact**: < 2% of total storage

### API Queries
- **Response Time**: < 100ms
- **Concurrent Users**: Low (1-5)
- **Caching**: Not needed initially

---

## Testing Strategy

### Unit Tests
- `test_discovery_service.py` - Test registry commands
- `test_registry_processor.py` - Test data conversion
- `test_models.py` - Test data models

### Integration Tests
- Test full discovery flow with mock HA
- Test registry event handling
- Test InfluxDB writes
- Test API endpoints

### Manual Testing
- Connect to real HA instance
- Verify device discovery
- Add/remove device in HA
- Verify real-time update
- Query API endpoints

---

## Error Handling

### Discovery Failures
- Log error, continue with what succeeded
- Retry on next reconnect
- Don't block state event processing

### Registry Event Errors
- Log error, skip malformed event
- Don't crash service

### Storage Errors
- Retry with backoff
- Log for monitoring

**Philosophy**: Fail gracefully, don't take down the service

---

## Security

- ✅ Reuse existing HA token auth
- ✅ Admin API already has auth
- ✅ No new auth needed
- ✅ Device data not sensitive (already visible in HA)

---

## Rollback Plan

1. Remove registry event subscriptions
2. Stop writing to devices/entities buckets
3. Remove API endpoints
4. Service continues working (state events unaffected)

**Risk**: LOW - Discovery is additive, doesn't change existing functionality

---

## Next Steps

1. ✅ Epic created
2. ✅ Architecture designed
3. ⏭️ Create Story 19.1
4. ⏭️ Implement discovery service
5. ⏭️ Test with real HA instance

---

**Architecture**: Simple, Pragmatic, Reuses Existing  
**Risk**: Low  
**Effort**: ~530 lines of new code  
**Timeline**: 4-6 weeks

