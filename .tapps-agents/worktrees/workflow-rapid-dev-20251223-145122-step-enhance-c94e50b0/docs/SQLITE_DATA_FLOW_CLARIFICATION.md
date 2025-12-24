# SQLite Data Flow Clarification - Epic 22

**Common Misconception**: Data flows InfluxDB → SQLite  
**Reality**: InfluxDB and SQLite store **different data types** independently

---

## ❌ **INCORRECT Understanding**

```
Home Assistant Event
       ↓
   InfluxDB (stores everything)
       ↓
   SQLite (migrates metadata from InfluxDB)
```

**This is NOT how it works!**

---

## ✅ **CORRECT Understanding**

```
Home Assistant Event
       ↓
   ┌───────────────────┐
   │  Event Data       │
   │  (state changes,  │
   │   sensor values)  │
   └────────┬──────────┘
            │
            ├──────────────────┐
            ▼                  ▼
     InfluxDB              SQLite
     (Time-Series)         (Metadata)
     - State values        - Device info
     - Sensor readings     - Entity list
     - Timestamps          - Webhooks
     - Metrics
```

**They store DIFFERENT data from the SAME source!**

---

## 📊 Data Separation by Type

### InfluxDB Stores: **TIME-SERIES Data**

**What**: Values that change over time
```json
{
  "measurement": "home_assistant_events",
  "timestamp": "2025-01-14T12:00:00Z",
  "tags": {
    "entity_id": "sensor.living_room_temp",
    "domain": "sensor"
  },
  "fields": {
    "state_value": "22.5",
    "normalized_value": 22.5
  }
}
```

**Examples**:
- Temperature reading at 12:00 → 22.5°C
- Temperature reading at 12:05 → 22.7°C
- Temperature reading at 12:10 → 22.6°C
- Light state at 18:00 → "on"
- Light state at 22:00 → "off"

**Why InfluxDB**: Optimized for time-range queries ("show me temperature from 8am-5pm")

---

### SQLite Stores: **METADATA** (Registry Data)

**What**: Information ABOUT the devices/entities (not their values)
```json
{
  "table": "devices",
  "device_id": "abc123",
  "name": "Living Room Sensor",
  "manufacturer": "Aqara",
  "model": "WSDCGQ11LM",
  "area_id": "living_room",
  "integration": "zigbee"
}
```

**Examples**:
- Device "abc123" is made by Aqara
- Entity "sensor.living_room_temp" belongs to device "abc123"
- Entity "sensor.living_room_temp" is in domain "sensor"
- Webhook "xyz789" subscribes to "game_started" events

**Why SQLite**: Optimized for lookups and relationships ("show me all devices in living room")

---

## 🔄 Actual Data Flow

### For Home Assistant Events

```
┌─────────────────────────────────────────────┐
│ Home Assistant Fires Event:                 │
│ "sensor.living_room_temp changed to 22.5°C" │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ WebSocket Ingestion  │
        │ Receives event       │
        └──────────┬───────────┘
                   │
                   ├─────────────────────────────┐
                   │                             │
                   ▼                             ▼
        ┌──────────────────────┐    ┌──────────────────────┐
        │   InfluxDB           │    │   SQLite             │
        │   STORES:            │    │   DOES NOT STORE:    │
        │   - Timestamp        │    │   - NOT sensor values│
        │   - Value: 22.5      │    │   - NOT state changes│
        │   - State: "22.5"    │    │                      │
        └──────────────────────┘    └──────────────────────┘
```

**The event data goes ONLY to InfluxDB.**

---

### For Device Discovery (Story 19)

```
┌─────────────────────────────────────────────┐
│ WebSocket Ingestion discovers device:       │
│ "Found device abc123 - Living Room Sensor"  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Discovery Service    │
        │ Parses device info   │
        └──────────┬───────────┘
                   │
                   ├─────────────────────────────┐
                   │                             │
                   ▼                             ▼
        ┌──────────────────────┐    ┌──────────────────────┐
        │   InfluxDB           │    │   SQLite             │
        │   STORES:            │    │   STORES:            │
        │   - Device events    │    │   - Device ID        │
        │   - State changes    │    │   - Name             │
        │   (time-series)      │    │   - Manufacturer     │
        │                      │    │   - Model            │
        │                      │    │   - Area             │
        │                      │    │   (metadata)         │
        └──────────────────────┘    └──────────────────────┘
```

**Device metadata goes to SQLite, device events go to InfluxDB.**

---

## 🎯 Who Writes to SQLite?

### Current Implementation (Epic 22):

**SQLite is EMPTY initially!** No automatic migration implemented.

#### Option 1: Manual Entry (Current)
```bash
# You would manually add devices via API (not implemented yet)
POST /api/devices
{
  "device_id": "abc123",
  "name": "Living Room Sensor",
  "manufacturer": "Aqara"
}
```

#### Option 2: Device Discovery (Future - Not Implemented)
```python
# Would be in websocket-ingestion discovery service:
def on_device_discovered(device_info):
    # Write to SQLite
    db.add(Device(
        device_id=device_info['id'],
        name=device_info['name'],
        manufacturer=device_info['manufacturer']
    ))
    
    # ALSO write events to InfluxDB
    influxdb.write_event(device_info)
```

**We SKIPPED this in Story 22.2 to keep it simple!**

#### Option 3: Migration Script (Not Implemented)
```python
# Could query InfluxDB tags and populate SQLite:
def migrate_devices_from_influxdb():
    # Query unique devices from InfluxDB tags
    devices = influxdb.query("SHOW TAG VALUES FROM home_assistant_events WITH KEY = device_id")
    
    # Insert into SQLite
    for device in devices:
        db.add(Device(device_id=device['value']))
```

**We SKIPPED this to avoid complexity!**

---

## 🤔 So How Does SQLite Get Populated?

### Current State (As Implemented):

**SQLite tables are EMPTY** after Epic 22 deployment.

**Population will happen via:**

1. **Webhook Registration** (Works Now!)
   ```bash
   POST /api/v1/webhooks/register
   # Writes directly to SQLite webhooks.db
   ```

2. **Future Device Discovery** (To Be Implemented)
   - When implemented, device discovery will write to BOTH:
     - InfluxDB: Device events (time-series)
     - SQLite: Device metadata (registry)

3. **Manual API Calls** (Can Implement Later)
   ```bash
   POST /api/devices
   # Would write directly to SQLite
   ```

---

## 📈 Data Flow Summary

| Data Type | Source | Destination | Who Writes | When |
|-----------|--------|-------------|------------|------|
| **Sensor Values** | HA Events | InfluxDB | websocket-ingestion | Real-time |
| **State Changes** | HA Events | InfluxDB | websocket-ingestion | Real-time |
| **Sports Scores** | ESPN API | InfluxDB | sports-data | On fetch |
| **Device Metadata** | HA Discovery | SQLite | **NOT IMPLEMENTED YET** | On discovery |
| **Entity Metadata** | HA Discovery | SQLite | **NOT IMPLEMENTED YET** | On discovery |
| **Webhooks** | User Registration | SQLite | sports-data | On POST |

---

## 🔧 What We Skipped (Simplicity!)

In Story 22.2, we **intentionally skipped**:

1. ❌ Migration script from InfluxDB to SQLite
2. ❌ Dual-write in device discovery
3. ❌ Automatic population of device/entity tables

**Why?**
- Keep implementation simple
- SQLite infrastructure ready when needed
- Can populate manually or via future discovery service
- Empty tables don't hurt anything

---

## 💡 The Big Picture

**InfluxDB and SQLite are PARALLEL, not SEQUENTIAL:**

```
                    ┌─────────────┐
                    │ Data Source │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌─────────────────┐      ┌─────────────────┐
    │   InfluxDB      │      │    SQLite       │
    │   (What & When) │      │  (Who & Where)  │
    ├─────────────────┤      ├─────────────────┤
    │ Temperature:    │      │ Device:         │
    │  22.5°C at 12pm │      │  "Aqara Sensor" │
    │  22.7°C at 1pm  │      │  "Living Room"  │
    │  22.6°C at 2pm  │      │  "Zigbee"       │
    └─────────────────┘      └─────────────────┘
         TIME-SERIES              REGISTRY
```

**They answer different questions:**
- InfluxDB: "What was the temperature at 2pm?" → Time-series query
- SQLite: "What manufacturer made this sensor?" → Metadata lookup

---

## Summary

**No, data does NOT flow InfluxDB → SQLite.**

**Instead:**
- ✅ Different data types go to appropriate databases
- ✅ InfluxDB: Time-series values (events, metrics)
- ✅ SQLite: Metadata (device info, webhooks)
- ✅ Currently: SQLite populated manually or via webhooks API
- ✅ Future: Device discovery can write to BOTH databases

**The hybrid architecture uses the right tool for the right job!**

