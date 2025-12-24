# Home Assistant Device & Entity Discovery Research

**Date:** October 12, 2025  
**Purpose:** Research methods to discover, capture, and maintain up-to-date information about all devices, entities, and integrations connected to Home Assistant  
**Status:** Research & Planning Phase  
**Project:** HA-Ingestor

---

## Executive Summary

This document outlines research findings and recommendations for comprehensively discovering and maintaining information about all devices, entities, services, and integrations connected to the Home Assistant instance that HA-Ingestor monitors.

### Key Findings

1. **Multiple Data Layers**: Home Assistant stores device/entity information across multiple registries
2. **WebSocket API Best**: Real-time discovery and updates via WebSocket commands
3. **REST API Available**: Fallback option using templating for device queries
4. **Event-Driven Updates**: Subscribe to registry updates for real-time sync
5. **Current State**: Our implementation captures events but not device inventory

---

## Home Assistant Data Architecture

### Three Core Registries

Home Assistant maintains three primary registries that contain all connected device/entity information:

#### 1. **Entity Registry**
- **Purpose**: Tracks all entities in the system
- **Contains**: Entity configuration, unique IDs, associated devices, areas
- **Scope**: All entities regardless of state

#### 2. **Device Registry**
- **Purpose**: Tracks physical/logical devices
- **Contains**: Device info, manufacturer, model, firmware version, connections
- **Scope**: Devices that entities belong to

#### 3. **Config Entries Registry**
- **Purpose**: Tracks integration configurations
- **Contains**: Integration setups, domains, entry IDs
- **Scope**: All active integrations

### Data Relationships

```
Config Entry (Integration)
    ↓
Device (Physical Device)
    ↓
Entity (Individual Sensor/Switch/etc)
    ↓
State (Current Value/Status)
```

**Example:**
```
Config Entry: "Philips Hue Bridge"
    Device: "Hue Bridge Living Room" (manufacturer: Signify, model: BSB002)
        Entity: "light.living_room_lamp" (current state: "on", brightness: 80%)
        Entity: "light.living_room_ceiling" (current state: "off")
```

---

## Discovery Methods - Ranked by Recommendation

### ⭐ Method 1: WebSocket API Registry Commands (RECOMMENDED)

**Rating**: ⭐⭐⭐⭐⭐ (5/5)  
**Best For**: Comprehensive discovery + real-time updates  
**Complexity**: Medium  
**Performance**: Excellent

#### Why This is Best
- ✅ Direct access to all three registries
- ✅ Real-time updates via subscription
- ✅ Single connection for discovery + monitoring
- ✅ No polling required
- ✅ Already have WebSocket infrastructure

#### Available WebSocket Commands

##### Get All Config Entries
```json
{
  "id": 1,
  "type": "config_entries/list"
}
```

**Response includes:**
- All integration configurations
- Entry IDs, domains, titles
- Setup state, version info

##### Get Device Registry
```json
{
  "id": 2,
  "type": "config/device_registry/list"
}
```

**Response includes:**
- All devices with full metadata
- Manufacturer, model, sw_version, hw_version
- Connections (MAC, IP, etc.)
- Associated config entries and areas
- Device identifiers

##### Get Entity Registry
```json
{
  "id": 3,
  "type": "config/entity_registry/list"
}
```

**Response includes:**
- All entities (even disabled ones)
- Entity IDs, unique IDs
- Associated device and config entry
- Entity platform, category
- Customizations and capabilities

##### Get Current States
```json
{
  "id": 4,
  "type": "get_states"
}
```

**Response includes:**
- Current state of ALL entities
- Attributes, timestamps
- Context information

#### Subscribe to Registry Updates

##### Entity Registry Changes
```json
{
  "id": 5,
  "type": "subscribe_events",
  "event_type": "entity_registry_updated"
}
```

##### Device Registry Changes
```json
{
  "id": 6,
  "type": "subscribe_events",
  "event_type": "device_registry_updated"
}
```

##### Config Entry Changes
```json
{
  "id": 7,
  "type": "subscribe_events",
  "event_type": "config_entry_discovered"
}
```

#### Implementation Pattern

```python
async def discover_all_devices(websocket):
    """Comprehensive device discovery via WebSocket"""
    
    # Step 1: Get all config entries (integrations)
    await websocket.send_json({
        "id": 1,
        "type": "config_entries/list"
    })
    config_entries = await websocket.receive_json()
    
    # Step 2: Get all devices
    await websocket.send_json({
        "id": 2,
        "type": "config/device_registry/list"
    })
    devices = await websocket.receive_json()
    
    # Step 3: Get all entities
    await websocket.send_json({
        "id": 3,
        "type": "config/entity_registry/list"
    })
    entities = await websocket.receive_json()
    
    # Step 4: Get current states
    await websocket.send_json({
        "id": 4,
        "type": "get_states"
    })
    states = await websocket.receive_json()
    
    # Step 5: Subscribe to updates
    await websocket.send_json({
        "id": 5,
        "type": "subscribe_events",
        "event_type": "device_registry_updated"
    })
    
    return {
        "config_entries": config_entries,
        "devices": devices,
        "entities": entities,
        "states": states
    }
```

---

### ⭐ Method 2: REST API + Template Queries

**Rating**: ⭐⭐⭐⭐ (4/5)  
**Best For**: One-time discovery, simple queries  
**Complexity**: Low  
**Performance**: Good for periodic polling

#### Template Endpoint

**Endpoint**: `POST /api/template`

**Request Body**:
```json
{
  "template": "{{ states | map(attribute='entity_id') | list }}"
}
```

#### Get All Devices with Entities

```python
template = """
{% set devices = states | map(attribute='entity_id') | map('device_id') | unique | reject('eq', None) | list %}
{%- set ns = namespace(devices = []) %}
{%- for device in devices %}
  {%- set entities = device_entities(device) | list %}
  {%- if entities %}
    {%- set ns.devices = ns.devices + [{
        'device_id': device,
        'name': device_attr(device, 'name'),
        'manufacturer': device_attr(device, 'manufacturer'),
        'model': device_attr(device, 'model'),
        'sw_version': device_attr(device, 'sw_version'),
        'entities': entities
    }] %}
  {%- endif %}
{%- endfor %}
{{ ns.devices | tojson }}
"""

response = requests.post(
    "http://homeassistant:8123/api/template",
    headers={"Authorization": f"Bearer {token}"},
    json={"template": template}
)
devices = response.json()
```

#### Get All Areas with Devices

```python
template = """
{% set areas = states | map(attribute='entity_id') | map('area_id') | unique | reject('eq', None) | list %}
{%- set ns = namespace(areas = []) %}
{%- for area_id in areas %}
  {%- set ns.areas = ns.areas + [{
      'area_id': area_id,
      'name': area_name(area_id),
      'devices': area_devices(area_id) | list,
      'entities': area_entities(area_id) | list
  }] %}
{%- endfor %}
{{ ns.areas | tojson }}
"""
```

#### Pros & Cons

**Pros:**
- ✅ Simple HTTP requests
- ✅ Flexible Jinja2 templating
- ✅ No WebSocket required
- ✅ Easy to test with curl

**Cons:**
- ❌ No real-time updates
- ❌ Requires polling for changes
- ❌ More API calls needed
- ❌ Template syntax complexity

---

### ⭐ Method 3: Combined WebSocket Events + Periodic Sync

**Rating**: ⭐⭐⭐⭐⭐ (5/5)  
**Best For**: Production use, high reliability  
**Complexity**: Medium-High  
**Performance**: Excellent

#### Strategy

1. **Initial Discovery** (WebSocket registry commands)
   - Get full inventory on startup
   - Store in local database/cache

2. **Real-Time Updates** (Event subscriptions)
   - Subscribe to state_changed events (already doing this)
   - Subscribe to entity_registry_updated
   - Subscribe to device_registry_updated
   - Subscribe to config_entry_discovered

3. **Periodic Sync** (Scheduled refresh)
   - Full registry sync every 1-6 hours
   - Catch any missed events
   - Verify data consistency

4. **Change Detection**
   - Compare current vs stored inventory
   - Detect new devices/entities
   - Detect removed devices/entities
   - Detect configuration changes

#### Implementation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     HA-INGESTOR                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Device Discovery Service (New)                       │  │
│  │  - Initial inventory sync                             │  │
│  │  - Registry subscriptions                             │  │
│  │  - Periodic refresh scheduler                         │  │
│  │  - Change detection                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  WebSocket Ingestion (Existing)                       │  │
│  │  - State change events                                │  │
│  │  - Entity registry events (new subscription)          │  │
│  │  - Device registry events (new subscription)          │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  InfluxDB Storage                                     │  │
│  │  - devices bucket (new)                               │  │
│  │  - entities bucket (new)                              │  │
│  │  - home_assistant bucket (existing - states)          │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Admin API (Enhanced)                                 │  │
│  │  - GET /api/devices                                   │  │
│  │  - GET /api/entities                                  │  │
│  │  - GET /api/integrations                              │  │
│  │  - GET /api/devices/{id}/entities                     │  │
│  │  - GET /api/devices/{id}/history                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Health Dashboard (Enhanced)                          │  │
│  │  - Devices tab (new)                                  │  │
│  │  - Device topology view (new)                         │  │
│  │  - Entity browser (new)                               │  │
│  │  - Integration status (new)                           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Storage Strategy

### Recommended InfluxDB Schema

#### Devices Bucket

**Measurement**: `devices`

**Tags**:
- `device_id` (unique identifier)
- `domain` (integration domain: hue, zwave, mqtt, etc.)
- `manufacturer`
- `model`
- `area_id`
- `config_entry_id`

**Fields**:
- `name` (string)
- `name_by_user` (string)
- `sw_version` (string)
- `hw_version` (string)
- `serial_number` (string)
- `model_id` (string)
- `configuration_url` (string)
- `disabled` (boolean)
- `entity_count` (integer)
- `last_seen` (timestamp)

**Example Point**:
```python
{
    "measurement": "devices",
    "tags": {
        "device_id": "abc123",
        "domain": "hue",
        "manufacturer": "Signify",
        "model": "BSB002",
        "area_id": "living_room"
    },
    "fields": {
        "name": "Hue Bridge Living Room",
        "sw_version": "1.58.0",
        "entity_count": 12,
        "last_seen": "2025-10-12T10:30:00Z"
    },
    "time": "2025-10-12T10:30:00Z"
}
```

#### Entities Bucket

**Measurement**: `entities`

**Tags**:
- `entity_id` (unique identifier)
- `device_id` (associated device)
- `domain` (entity domain: light, sensor, switch, etc.)
- `platform` (integration platform)
- `area_id`
- `entity_category` (config, diagnostic)

**Fields**:
- `name` (string)
- `original_name` (string)
- `unique_id` (string)
- `disabled` (boolean)
- `hidden` (boolean)
- `icon` (string)
- `unit_of_measurement` (string)
- `device_class` (string)
- `capabilities` (json)
- `last_seen` (timestamp)

#### Config Entries Bucket

**Measurement**: `config_entries`

**Tags**:
- `entry_id` (unique identifier)
- `domain` (integration domain)

**Fields**:
- `title` (string)
- `state` (loaded, setup_error, etc.)
- `version` (integer)
- `device_count` (integer)
- `entity_count` (integer)
- `last_updated` (timestamp)

---

## Update Strategies

### Strategy A: Event-Driven Only (Reactive)

**Approach**: React to HA events only

**Pros**:
- ✅ Real-time updates
- ✅ Low overhead
- ✅ No polling

**Cons**:
- ❌ May miss events during disconnection
- ❌ No recovery mechanism
- ❌ Depends on event reliability

**Use Case**: Low-critical systems, testing

---

### Strategy B: Periodic Sync Only (Proactive)

**Approach**: Poll registries on schedule

**Pros**:
- ✅ Simple implementation
- ✅ Guaranteed consistency
- ✅ Easy to verify

**Cons**:
- ❌ Stale data between syncs
- ❌ Higher API load
- ❌ Polling overhead

**Use Case**: Low-frequency updates acceptable

---

### Strategy C: Hybrid Event + Sync (RECOMMENDED)

**Approach**: Event-driven with periodic verification

**Configuration**:
```yaml
discovery:
  initial_sync: true
  events:
    subscribe_on_connect: true
    event_types:
      - entity_registry_updated
      - device_registry_updated
      - config_entry_discovered
  periodic_sync:
    enabled: true
    interval: 3600  # 1 hour
    full_refresh: true
  change_detection:
    enabled: true
    notify_on_change: true
    store_history: true
```

**Benefits**:
- ✅ Real-time updates from events
- ✅ Guaranteed consistency from periodic sync
- ✅ Missed event recovery
- ✅ Change detection and auditing

**Recommended Sync Intervals**:
- **Devices**: Every 1-6 hours (rarely change)
- **Entities**: Every 30-60 minutes (occasionally change)
- **States**: Real-time via events (already doing this)
- **Config Entries**: Every 6-24 hours (rarely change)

---

## Implementation Recommendations

### Phase 1: Foundation (Week 1-2)

#### Tasks:
1. **Add WebSocket Commands**
   - Implement registry list commands
   - Add subscription for registry events
   - Test command/response handling

2. **Create Data Models**
   - Define Device, Entity, ConfigEntry classes
   - Add validation and serialization
   - Create storage adapters

3. **Storage Layer**
   - Create new InfluxDB buckets
   - Define retention policies
   - Implement write/query functions

#### Deliverables:
- ✅ Device/entity discovery working
- ✅ Data stored in InfluxDB
- ✅ Basic query capabilities

---

### Phase 2: Real-Time Updates (Week 3-4)

#### Tasks:
1. **Event Subscriptions**
   - Subscribe to registry update events
   - Handle event processing
   - Update local storage

2. **Change Detection**
   - Implement diff algorithm
   - Detect additions/removals
   - Track modifications

3. **Event Handlers**
   - Process device registry events
   - Process entity registry events
   - Process config entry events

#### Deliverables:
- ✅ Real-time registry updates
- ✅ Change detection working
- ✅ Event-driven sync

---

### Phase 3: Periodic Sync (Week 5-6)

#### Tasks:
1. **Scheduler**
   - Implement sync scheduler
   - Configurable intervals
   - Error handling

2. **Full Refresh**
   - Periodic full registry sync
   - Compare with stored data
   - Reconcile differences

3. **Health Monitoring**
   - Track sync status
   - Monitor for inconsistencies
   - Alert on failures

#### Deliverables:
- ✅ Periodic sync working
- ✅ Data consistency guaranteed
- ✅ Monitoring dashboard

---

### Phase 4: API & Dashboard (Week 7-8)

#### Tasks:
1. **Admin API Endpoints**
   - GET /api/devices
   - GET /api/entities
   - GET /api/integrations
   - GET /api/devices/{id}/entities

2. **Health Dashboard**
   - Devices tab
   - Entity browser
   - Integration status
   - Device topology view

3. **Documentation**
   - API documentation
   - User guide
   - Architecture diagrams

#### Deliverables:
- ✅ Complete API
- ✅ Enhanced dashboard
- ✅ Full documentation

---

## Example Data Structures

### Device Registry Entry

```json
{
  "id": "abc123",
  "config_entries": ["entry_1"],
  "connections": [["mac", "00:11:22:33:44:55"]],
  "identifiers": [["hue", "001788fffe1234"]],
  "manufacturer": "Signify",
  "model": "BSB002",
  "model_id": null,
  "name": "Hue Bridge",
  "name_by_user": "Living Room Hue Bridge",
  "sw_version": "1.58.0",
  "hw_version": "2.0",
  "serial_number": "001788fffe1234",
  "via_device_id": null,
  "area_id": "living_room",
  "configuration_url": "http://192.168.1.100",
  "disabled_by": null,
  "entry_type": "service"
}
```

### Entity Registry Entry

```json
{
  "entity_id": "light.living_room_lamp",
  "unique_id": "hue_light_001788fffe5678",
  "platform": "hue",
  "device_id": "abc123",
  "config_entry_id": "entry_1",
  "area_id": "living_room",
  "name": null,
  "original_name": "Living Room Lamp",
  "icon": null,
  "entity_category": null,
  "unit_of_measurement": null,
  "device_class": null,
  "disabled_by": null,
  "hidden_by": null,
  "has_entity_name": true,
  "capabilities": {
    "supported_color_modes": ["color_temp", "rgb"],
    "min_color_temp_kelvin": 2000,
    "max_color_temp_kelvin": 6535
  },
  "supported_features": 63
}
```

### Config Entry

```json
{
  "entry_id": "entry_1",
  "domain": "hue",
  "title": "Philips Hue",
  "data": {},
  "options": {},
  "pref_disable_new_entities": false,
  "pref_disable_polling": false,
  "source": "user",
  "state": "loaded",
  "disabled_by": null,
  "version": 2
}
```

---

## Performance Considerations

### Network Load

#### Initial Discovery
- **One-time**: 4 WebSocket commands
- **Data Size**: ~100KB - 10MB (depending on setup size)
- **Time**: 1-5 seconds

#### Real-Time Updates
- **Frequency**: Only when changes occur
- **Data Size**: 1-10KB per event
- **Overhead**: Minimal (< 1% of state events)

#### Periodic Sync
- **Frequency**: Configurable (1-24 hours)
- **Data Size**: Same as initial discovery
- **Impact**: Burst load, predictable

### Storage Impact

#### Estimated Storage (per device/entity)

**Devices**:
- Average: 500 bytes per device
- 100 devices: 50KB
- Retention: 90 days
- Total: ~4.5MB

**Entities**:
- Average: 300 bytes per entity
- 500 entities: 150KB
- Retention: 90 days
- Total: ~13.5MB

**Total Impact**: < 20MB for typical home setup

---

## Security & Privacy

### Considerations

1. **Sensitive Data**
   - Device serial numbers
   - MAC addresses
   - Configuration URLs
   - Network topology

2. **Access Control**
   - Admin API requires authentication
   - Dashboard restricted to authorized users
   - No external exposure

3. **Data Retention**
   - Configure retention policies
   - Auto-cleanup old data
   - GDPR compliance considerations

---

## Comparison Matrix

| Method | Real-Time | Comprehensive | Complexity | Performance | Reliability |
|--------|-----------|---------------|------------|-------------|-------------|
| WebSocket Only | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| REST Only | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Hybrid | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| State Events Only | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## Recommended Approach

### ✅ Final Recommendation: Hybrid Event + Sync Strategy

**Reasons:**
1. ✅ **Comprehensive**: Captures all devices, entities, and integrations
2. ✅ **Real-Time**: Event subscriptions for immediate updates
3. ✅ **Reliable**: Periodic sync ensures consistency
4. ✅ **Efficient**: Minimal overhead, reuses existing WebSocket
5. ✅ **Scalable**: Works for small and large HA installations
6. ✅ **Maintainable**: Clear separation of concerns

### Implementation Priority

**High Priority** (Immediate Value):
1. WebSocket registry commands
2. Initial discovery on startup
3. Basic storage in InfluxDB
4. Admin API endpoints

**Medium Priority** (Enhanced Reliability):
1. Event subscriptions for registry updates
2. Periodic sync scheduler
3. Change detection

**Low Priority** (Nice to Have):
1. Dashboard device browser
2. Device topology visualization
3. Historical device tracking

---

## Next Steps

### Research Phase Complete ✅

**Decisions Needed:**
1. Approve hybrid strategy approach
2. Determine sync intervals
3. Choose storage retention policies
4. Prioritize implementation phases

**Ready for:**
- Architecture design document
- Story creation for implementation
- Technical specification writing

---

## References

- **Home Assistant WebSocket API**: docs/kb/context7-cache/libraries/homeassistant/docs.md
- **Context7 Device Registry Docs**: /home-assistant/developers.home-assistant
- **Current Implementation**: services/websocket-ingestion/
- **InfluxDB Schema**: docs/architecture/database-schema.md

---

## Appendix: WebSocket Command Reference

### All Available Registry Commands

```json
// Config Entries
{"id": 1, "type": "config_entries/list"}
{"id": 2, "type": "config_entries/get", "entry_id": "..."}

// Device Registry
{"id": 3, "type": "config/device_registry/list"}
{"id": 4, "type": "config/device_registry/get", "device_id": "..."}

// Entity Registry
{"id": 5, "type": "config/entity_registry/list"}
{"id": 6, "type": "config/entity_registry/get", "entity_id": "..."}

// States
{"id": 7, "type": "get_states"}
{"id": 8, "type": "subscribe_events", "event_type": "state_changed"}

// Registry Events
{"id": 9, "type": "subscribe_events", "event_type": "device_registry_updated"}
{"id": 10, "type": "subscribe_events", "event_type": "entity_registry_updated"}
{"id": 11, "type": "subscribe_events", "event_type": "config_entry_discovered"}

// Area Registry
{"id": 12, "type": "config/area_registry/list"}

// Integration Registry
{"id": 13, "type": "integration/list"}
```

---

**Status**: Ready for Implementation Planning  
**Confidence Level**: High (Based on official HA documentation)  
**Risk Level**: Low (Well-documented APIs)

