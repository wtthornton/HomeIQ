# Device Discovery Architecture - Visual Diagram

**Related**: [home-assistant-device-discovery-research.md](./home-assistant-device-discovery-research.md)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          HOME ASSISTANT                                  │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Device Registry  │  │ Entity Registry  │  │ Config Entries   │     │
│  │                  │  │                  │  │                  │     │
│  │ - Devices        │  │ - Entities       │  │ - Integrations   │     │
│  │ - Metadata       │  │ - Unique IDs     │  │ - Setup State    │     │
│  │ - Connections    │  │ - Platforms      │  │ - Versions       │     │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘     │
│           │                     │                     │                │
│           └─────────────────────┴─────────────────────┘                │
│                                 │                                       │
│                     ┌───────────▼───────────┐                          │
│                     │   WebSocket API       │                          │
│                     │   /api/websocket      │                          │
│                     └───────────┬───────────┘                          │
└─────────────────────────────────┼────────────────────────────────────┘
                                  │
                                  │ WebSocket Connection
                                  │ (already established)
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│                         HA-INGESTOR                                   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │           DEVICE DISCOVERY SERVICE (NEW)                        │ │
│  │                                                                 │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │ │
│  │  │   Initial    │  │   Event      │  │   Periodic Sync      │ │ │
│  │  │   Discovery  │  │   Subscriber │  │   Scheduler          │ │ │
│  │  │              │  │              │  │                      │ │ │
│  │  │ - Get all    │  │ - Device     │  │ - Every 1-6 hours   │ │ │
│  │  │   devices    │  │   updates    │  │ - Full refresh      │ │ │
│  │  │ - Get all    │  │ - Entity     │  │ - Consistency check │ │ │
│  │  │   entities   │  │   updates    │  │                      │ │ │
│  │  │ - Get config │  │ - Config     │  │                      │ │ │
│  │  │   entries    │  │   changes    │  │                      │ │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │ │
│  │         │                 │                     │             │ │
│  │         └─────────────────┴─────────────────────┘             │ │
│  │                           │                                   │ │
│  │                  ┌────────▼─────────┐                         │ │
│  │                  │ Change Detector  │                         │ │
│  │                  │ - New devices    │                         │ │
│  │                  │ - Removed items  │                         │ │
│  │                  │ - Updates        │                         │ │
│  │                  └────────┬─────────┘                         │ │
│  └─────────────────────────────┼────────────────────────────────┘ │
│                                │                                    │
│  ┌─────────────────────────────▼────────────────────────────────┐ │
│  │      WEBSOCKET INGESTION SERVICE (ENHANCED)                   │ │
│  │                                                               │ │
│  │  Existing:                         New:                      │ │
│  │  ✅ State change events            ✨ Device registry events │ │
│  │  ✅ HA connection                  ✨ Entity registry events │ │
│  │  ✅ Event processing               ✨ Config entry events    │ │
│  └────────────────────────────────────────┬──────────────────────┘ │
│                                           │                         │
│  ┌────────────────────────────────────────▼──────────────────────┐ │
│  │                   INFLUXDB STORAGE                             │ │
│  │                                                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐ │ │
│  │  │   devices/   │  │  entities/   │  │ home_assistant/     │ │ │
│  │  │   (NEW)      │  │  (NEW)       │  │ (EXISTING)          │ │ │
│  │  │              │  │              │  │                     │ │ │
│  │  │ - Device     │  │ - Entity     │  │ - State history    │ │ │
│  │  │   inventory  │  │   registry   │  │ - Events           │ │ │
│  │  │ - Metadata   │  │ - Config     │  │ - Attributes       │ │ │
│  │  │ - History    │  │ - Caps       │  │                     │ │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘ │ │
│  └─────────┼──────────────────┼─────────────────────┼────────────┘ │
│            │                  │                     │              │
│  ┌─────────▼──────────────────▼─────────────────────▼────────────┐ │
│  │                   ADMIN API (ENHANCED)                         │ │
│  │                                                                │ │
│  │  Existing:                        New:                        │ │
│  │  ✅ GET /api/health               ✨ GET /api/devices         │ │
│  │  ✅ GET /api/statistics           ✨ GET /api/entities        │ │
│  │  ✅ GET /api/events               ✨ GET /api/integrations    │ │
│  │                                   ✨ GET /api/devices/{id}    │ │
│  │                                   ✨ GET /api/topology        │ │
│  └────────────────────────────────────────┬───────────────────────┘ │
│                                           │                          │
│  ┌────────────────────────────────────────▼───────────────────────┐ │
│  │              HEALTH DASHBOARD (ENHANCED)                       │ │
│  │                                                                │ │
│  │  Existing Tabs:                   New Tabs:                   │ │
│  │  ✅ Overview                       ✨ Devices                 │ │
│  │  ✅ Services                       ✨ Entity Browser          │ │
│  │  ✅ Dependencies                   ✨ Integrations            │ │
│  │  ✅ Monitoring                     ✨ Topology View           │ │
│  │  ✅ Settings                                                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Initial Discovery (On Startup)

```
┌──────────────────────┐
│  HA-Ingestor Starts  │
└──────────┬───────────┘
           │
           │ 1. WebSocket connects
           ▼
┌──────────────────────┐
│  WebSocket Connected │
│  & Authenticated     │
└──────────┬───────────┘
           │
           │ 2. Send registry commands
           ▼
┌───────────────────────────────────────────────────────────┐
│  Send 4 WebSocket Commands:                               │
│  - {"type": "config/device_registry/list"}      (id: 1)  │
│  - {"type": "config/entity_registry/list"}      (id: 2)  │
│  - {"type": "config_entries/list"}              (id: 3)  │
│  - {"type": "get_states"}                       (id: 4)  │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 3. Receive responses
                        ▼
┌───────────────────────────────────────────────────────────┐
│  Parse Responses:                                         │
│  - 150 devices                                            │
│  - 450 entities                                           │
│  - 25 config entries                                      │
│  - 450 current states                                     │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 4. Store in InfluxDB
                        ▼
┌───────────────────────────────────────────────────────────┐
│  Write to InfluxDB:                                       │
│  - devices/ bucket: 150 points                           │
│  - entities/ bucket: 450 points                          │
│  - home_assistant/ bucket: 450 state points              │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 5. Subscribe to updates
                        ▼
┌───────────────────────────────────────────────────────────┐
│  Subscribe to Events:                                     │
│  - device_registry_updated                                │
│  - entity_registry_updated                                │
│  - state_changed (already subscribed)                     │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 6. Ready
                        ▼
┌──────────────────────────────┐
│  Discovery Complete ✅        │
│  Monitoring for updates...   │
└──────────────────────────────┘
```

---

### Real-Time Update Flow

```
┌──────────────────────┐
│  Device Added in HA  │
│  (e.g., new light)   │
└──────────┬───────────┘
           │
           │ 1. HA sends event
           ▼
┌─────────────────────────────────────────────────────────┐
│  WebSocket Event:                                       │
│  {                                                      │
│    "type": "event",                                     │
│    "event": {                                           │
│      "event_type": "device_registry_updated",           │
│      "data": {                                          │
│        "action": "create",                              │
│        "device_id": "new_light_123",                    │
│        "device": { ... }                                │
│      }                                                  │
│    }                                                    │
│  }                                                      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ 2. Process event
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Event Processor:                                       │
│  - Detect: New device                                   │
│  - Parse: Device metadata                               │
│  - Enrich: Add timestamps                               │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ 3. Store update
                      ▼
┌─────────────────────────────────────────────────────────┐
│  InfluxDB Write:                                        │
│  - devices/ bucket: New device point                    │
│  - Tag: action=create                                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ 4. Notify
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Update Dashboard:                                      │
│  - Refresh device list                                  │
│  - Show notification: "New device added"                │
└─────────────────────────────────────────────────────────┘
```

---

### Periodic Sync Flow

```
┌──────────────────────┐
│  Sync Timer Fires    │
│  (every 1 hour)      │
└──────────┬───────────┘
           │
           │ 1. Trigger sync
           ▼
┌───────────────────────────────────────────────────────────┐
│  Sync Scheduler:                                          │
│  - Check: Last sync was 60 minutes ago                    │
│  - Decide: Full refresh needed                            │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 2. Fetch current data
                        ▼
┌───────────────────────────────────────────────────────────┐
│  Query HA Registries:                                     │
│  - Get all devices (current)                              │
│  - Get all entities (current)                             │
│  - Get config entries (current)                           │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 3. Load stored data
                        ▼
┌───────────────────────────────────────────────────────────┐
│  Query InfluxDB:                                          │
│  - Load latest devices snapshot                           │
│  - Load latest entities snapshot                          │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 4. Compare & detect changes
                        ▼
┌───────────────────────────────────────────────────────────┐
│  Change Detector:                                         │
│  ✅ Match: 148 devices (no change)                        │
│  ✨ New: 2 devices                                        │
│  ❌ Removed: 0 devices                                    │
│  🔄 Modified: 1 device (firmware update)                  │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 5. Update storage
                        ▼
┌───────────────────────────────────────────────────────────┐
│  Write Changes:                                           │
│  - Store 2 new devices                                    │
│  - Update 1 device metadata                               │
│  - Log sync results                                       │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ 6. Report
                        ▼
┌──────────────────────────────────┐
│  Sync Complete ✅                 │
│  - 2 new devices                 │
│  - 1 update                      │
│  - Next sync: 1 hour             │
└──────────────────────────────────┘
```

---

## Component Interaction Sequence

### Full Discovery + Monitoring Sequence

```
HA               WebSocket          Discovery        InfluxDB        Dashboard
│                Service            Service          │               │
│                │                  │                │               │
├─ Connect ─────>│                  │                │               │
│<── Auth OK ────┤                  │                │               │
│                │                  │                │               │
│                ├── Trigger ──────>│                │               │
│<── List Devices ─────────────────┤                │               │
├── 150 Devices ─────────────────>│                │               │
│                │                  ├── Store ──────>│               │
│                │                  │<── OK ─────────┤               │
│                │                  │                │               │
│<── List Entities ────────────────┤                │               │
├── 450 Entities ─────────────────>│                │               │
│                │                  ├── Store ──────>│               │
│                │                  │<── OK ─────────┤               │
│                │                  │                │               │
│<── Subscribe Events ─────────────┤                │               │
├── Subscribed ───────────────────>│                │               │
│                │                  ├── Ready ──────────────────────>│
│                │                  │                │<── Display ───┤
│                │                  │                │               │
│── New Device ─>│                  │                │               │
│                ├── Event ────────>│                │               │
│                │                  ├── Process ─────>│               │
│                │                  │<── Stored ──────┤               │
│                │                  ├── Notify ──────────────────────>│
│                │                  │                │<── Update ────┤
│                │                  │                │               │
```

---

## Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND                                 │
│  React 18.2 + TypeScript 5.2 + TailwindCSS 3.4             │
│  - DevicesTab.tsx (new)                                     │
│  - EntityBrowser.tsx (new)                                  │
│  - TopologyView.tsx (new)                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────────┐
│                   BACKEND - ADMIN API                       │
│  FastAPI 0.104.1 + Python 3.11                             │
│  - devices_endpoints.py (new)                               │
│  - entities_endpoints.py (new)                              │
│  - topology_endpoints.py (new)                              │
└────────────────────────┬────────────────────────────────────┘
                         │ InfluxDB Query
┌────────────────────────▼────────────────────────────────────┐
│                STORAGE - INFLUXDB 2.7                       │
│  - devices/ bucket (new)                                    │
│  - entities/ bucket (new)                                   │
│  - home_assistant/ bucket (existing)                        │
└────────────────────────▲────────────────────────────────────┘
                         │ Write
┌────────────────────────┴────────────────────────────────────┐
│            INGESTION - WEBSOCKET SERVICE                    │
│  aiohttp 3.9.1 + Python 3.11                               │
│  - discovery_service.py (new)                               │
│  - registry_processor.py (new)                              │
│  - sync_scheduler.py (new)                                  │
│  - websocket_client.py (enhanced)                           │
└────────────────────────▲────────────────────────────────────┘
                         │ WebSocket
┌────────────────────────┴────────────────────────────────────┐
│                  HOME ASSISTANT                             │
│  WebSocket API + Device/Entity/Config Registries           │
└─────────────────────────────────────────────────────────────┘
```

---

## Performance Estimates

### Initial Discovery (Cold Start)

```
Time Breakdown:
├─ WebSocket connection: ~500ms
├─ Authentication: ~200ms
├─ Device registry query: ~300ms
├─ Entity registry query: ~500ms
├─ Config entries query: ~200ms
├─ States query: ~400ms
├─ Data processing: ~500ms
├─ InfluxDB writes: ~1000ms
└─ TOTAL: ~3.6 seconds

Data Transfer:
├─ Device registry: ~50KB
├─ Entity registry: ~150KB
├─ Config entries: ~20KB
├─ States: ~500KB
└─ TOTAL: ~720KB
```

### Real-Time Updates

```
Per Event:
├─ Receive: ~10ms
├─ Parse: ~5ms
├─ Process: ~20ms
├─ Store: ~50ms
└─ TOTAL: ~85ms latency

Frequency:
├─ Device changes: ~5 per day
├─ Entity changes: ~20 per day
├─ State changes: ~1000 per day (existing)
└─ TOTAL: ~1025 events/day
```

### Periodic Sync

```
Full Sync (every hour):
├─ Query registries: ~1 second
├─ Load stored data: ~500ms
├─ Compare & diff: ~300ms
├─ Update storage: ~500ms
└─ TOTAL: ~2.3 seconds

Impact:
├─ 24 syncs per day
├─ ~55 seconds total per day
├─ ~0.06% of time
└─ Negligible overhead
```

---

## Storage Requirements

### Estimated Storage (typical home)

```
Devices (100 devices):
├─ Per device: 500 bytes
├─ Per hour: 50KB
├─ Per day: 1.2MB
├─ 90 days: 108MB
└─ With compression: ~50MB

Entities (500 entities):
├─ Per entity: 300 bytes
├─ Per hour: 150KB
├─ Per day: 3.6MB
├─ 90 days: 324MB
└─ With compression: ~150MB

Total New Storage:
└─ ~200MB (90 days retention)

Existing States:
└─ ~10GB (already tracking)

Total System:
└─ ~10.2GB (minimal increase)
```

---

**Architecture**: Hybrid Event-Driven + Periodic Sync  
**Estimated Complexity**: Medium  
**Estimated Effort**: 6-8 weeks  
**Performance Impact**: < 5% overhead  
**Storage Impact**: < 2% increase  
**Reliability**: ⭐⭐⭐⭐⭐

