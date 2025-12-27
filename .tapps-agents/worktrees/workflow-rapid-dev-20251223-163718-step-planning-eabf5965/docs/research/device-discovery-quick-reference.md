# Device Discovery - Quick Reference

**Main Document**: [home-assistant-device-discovery-research.md](./home-assistant-device-discovery-research.md)

---

## Top 3 Ideas (Ranked)

### 🥇 #1: Hybrid Event + Periodic Sync (RECOMMENDED)

**What**: Combine real-time WebSocket events with scheduled full syncs

**How**:
```python
# Initial: Get full inventory
websocket.send({"id": 1, "type": "config/device_registry/list"})
websocket.send({"id": 2, "type": "config/entity_registry/list"})

# Real-time: Subscribe to updates
websocket.send({"id": 3, "type": "subscribe_events", "event_type": "device_registry_updated"})

# Periodic: Full refresh every hour
schedule.every(1).hour.do(full_registry_sync)
```

**Why Best**:
- ✅ Real-time updates (< 1 second latency)
- ✅ Never miss changes (periodic backup)
- ✅ Reuses existing WebSocket
- ✅ Minimal overhead

**Effort**: 6-8 weeks  
**Complexity**: Medium  
**Reliability**: ⭐⭐⭐⭐⭐

---

### 🥈 #2: WebSocket Registry Commands Only

**What**: Use WebSocket commands to query registries on-demand

**How**:
```python
# Get all devices
await ws.send_json({"id": 1, "type": "config/device_registry/list"})
devices = await ws.receive_json()

# Get all entities  
await ws.send_json({"id": 2, "type": "config/entity_registry/list"})
entities = await ws.receive_json()
```

**Why Good**:
- ✅ Simple, direct access
- ✅ Single connection
- ✅ Official API

**Why Not Best**:
- ❌ No automatic updates
- ❌ Requires polling for changes

**Effort**: 2-3 weeks  
**Complexity**: Low  
**Reliability**: ⭐⭐⭐⭐

---

### 🥉 #3: REST API + Jinja2 Templates

**What**: Query devices using templated REST calls

**How**:
```python
template = """
{% set devices = states | map(attribute='entity_id') | map('device_id') | unique | list %}
{{ devices | tojson }}
"""

response = requests.post(
    "http://ha:8123/api/template",
    headers={"Authorization": f"Bearer {token}"},
    json={"template": template}
)
```

**Why Good**:
- ✅ No WebSocket needed
- ✅ Flexible queries
- ✅ Easy to test

**Why Not Best**:
- ❌ Requires polling
- ❌ Complex templates
- ❌ More HTTP overhead

**Effort**: 1-2 weeks  
**Complexity**: Low  
**Reliability**: ⭐⭐⭐

---

## Key WebSocket Commands

### Discovery Commands
```json
// Get all devices
{"id": 1, "type": "config/device_registry/list"}

// Get all entities  
{"id": 2, "type": "config/entity_registry/list"}

// Get all integrations
{"id": 3, "type": "config_entries/list"}

// Get current states
{"id": 4, "type": "get_states"}
```

### Subscription Commands
```json
// Subscribe to device changes
{"id": 5, "type": "subscribe_events", "event_type": "device_registry_updated"}

// Subscribe to entity changes
{"id": 6, "type": "subscribe_events", "event_type": "entity_registry_updated"}

// Subscribe to integration changes
{"id": 7, "type": "subscribe_events", "event_type": "config_entry_discovered"}
```

---

## Data You'll Get

### Device Info
- Device ID, name, manufacturer, model
- Firmware version (sw_version)
- Hardware version (hw_version)
- Serial number
- Connections (MAC, IP, etc.)
- Area/room location
- Associated entities

### Entity Info
- Entity ID, unique ID
- Associated device
- Domain (light, sensor, switch, etc.)
- Platform (integration)
- Capabilities and features
- Configuration
- Current state

### Integration Info
- Entry ID, domain
- Title and description
- Setup state
- Version
- Device count
- Entity count

---

## Recommended Storage (InfluxDB)

### Buckets
```
devices/        - Device inventory and metadata
entities/       - Entity registry and configuration
integrations/   - Integration/config entry info
```

### Retention
```
Devices:      90 days (rarely change)
Entities:     90 days (occasionally change)
Integrations: 90 days (rarely change)
```

---

## Implementation Phases

### Phase 1: Foundation (2 weeks)
- Add WebSocket registry commands
- Create data models
- Basic InfluxDB storage

### Phase 2: Real-Time (2 weeks)
- Subscribe to registry events
- Change detection
- Event processing

### Phase 3: Sync (2 weeks)
- Periodic full sync
- Consistency checks
- Error recovery

### Phase 4: API/Dashboard (2 weeks)
- Admin API endpoints
- Dashboard devices tab
- Documentation

**Total**: 8 weeks for complete implementation

---

## Quick Start Code

### Minimal Discovery

```python
async def discover_ha_inventory(websocket):
    """Get complete HA inventory"""
    
    # Get devices
    await websocket.send_json({
        "id": 1,
        "type": "config/device_registry/list"
    })
    devices_response = await websocket.receive_json()
    
    # Get entities
    await websocket.send_json({
        "id": 2,
        "type": "config/entity_registry/list"
    })
    entities_response = await websocket.receive_json()
    
    # Get current states
    await websocket.send_json({
        "id": 3,
        "type": "get_states"
    })
    states_response = await websocket.receive_json()
    
    return {
        "devices": devices_response["result"],
        "entities": entities_response["result"],
        "states": states_response["result"]
    }
```

### Minimal Event Subscription

```python
async def subscribe_to_registry_changes(websocket):
    """Subscribe to device/entity changes"""
    
    # Subscribe to device updates
    await websocket.send_json({
        "id": 10,
        "type": "subscribe_events",
        "event_type": "device_registry_updated"
    })
    
    # Subscribe to entity updates
    await websocket.send_json({
        "id": 11,
        "type": "subscribe_events",
        "event_type": "entity_registry_updated"
    })
    
    # Handle events
    async for msg in websocket:
        data = msg.json()
        if data.get("type") == "event":
            event = data["event"]
            if event["event_type"] == "device_registry_updated":
                await handle_device_change(event["data"])
            elif event["event_type"] == "entity_registry_updated":
                await handle_entity_change(event["data"])
```

---

## Decision Matrix

| Factor | Hybrid | WebSocket | REST | Current (State Only) |
|--------|--------|-----------|------|----------------------|
| Real-time updates | ✅ | ❌ | ❌ | ✅ |
| Complete inventory | ✅ | ✅ | ✅ | ❌ |
| Reliability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Complexity | Medium | Low | Low | Very Low |
| Overhead | Low | Medium | Medium | Very Low |
| Implementation | 8 weeks | 3 weeks | 2 weeks | Done |

---

## Next Steps

1. ✅ **Review research** (this document)
2. ⏸️ **Decide on approach** (recommend Hybrid)
3. ⏸️ **Create architecture document**
4. ⏸️ **Write implementation stories**
5. ⏸️ **Begin Phase 1 development**

---

**Status**: Research Complete  
**Recommendation**: Hybrid Event + Periodic Sync  
**Confidence**: High  
**Ready for**: Architecture & Story Creation

