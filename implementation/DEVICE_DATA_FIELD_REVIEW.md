# Device Data Field-Level Review

**Purpose:** Complete reference for all device, entity, and event data fields captured from Home Assistant  
**Last Updated:** January 20, 2025  
**Status:** ✅ FULLY OPERATIONAL - All data collection active  
**Enhancements:** Device Database fields added (Phase 1.1 - January 2025)

---

## Overview

The system captures three types of data from Home Assistant:

1. **Device Metadata** (SQLite) - Physical device information
2. **Entity Metadata** (SQLite) - Entity/sensor information linked to devices
3. **Event Data** (InfluxDB) - Time-series state changes and events

**Storage Architecture:**
- **SQLite:** Fast relational queries for device/entity browsing (<10ms)
- **InfluxDB:** Time-series events and metrics (optimized for time-range queries)

---

## 1. Device Data (SQLite)

**Database:** `data/metadata.db`  
**Table:** `devices`  
**Model:** `services/data-api/src/models/device.py`

### Device Fields

| Field | Type | Required | Indexed | Description | Example |
|-------|------|----------|---------|-------------|---------|
| `device_id` | String | ✅ Yes | Primary Key | Unique device identifier from Home Assistant | `"a1b2c3d4e5f6"` |
| `name` | String | ✅ Yes | No | Device name (default or user-customized) | `"Living Room Motion Sensor"` |
| `name_by_user` | String | No | No | User-customized device name (preferred over `name` when available) | `"Main Motion Sensor"` |
| `manufacturer` | String | No | ✅ Yes | Device manufacturer/brand | `"Philips"`, `"IKEA"`, `"Xiaomi"` |
| `model` | String | No | ✅ Yes | Device model number/name | `"Hue Motion Sensor"`, `"TRADFRI"` |
| `sw_version` | String | No | No | Software/firmware version | `"1.2.3"`, `"20250101"` |
| `area_id` | String | No | ✅ Yes | Room/area assignment | `"living_room"`, `"bedroom_1"` |
| `suggested_area` | String | No | No | Suggested area ID for device (from HA) | `"living_room"` |
| `integration` | String | No | ✅ Yes | Home Assistant integration source | `"hue"`, `"mqtt"`, `"zwave"` |
| `entry_type` | String | No | No | Entry type (service, config_entry, etc.) | `"config_entry"`, `"service"` |
| `configuration_url` | String | No | No | URL for device configuration page | `"https://example.com/config"` |
| `device_type` | String | No | ✅ Yes | Device classification (Phase 1.1) | `"fridge"`, `"light"`, `"sensor"`, `"thermostat"` |
| `device_category` | String | No | ✅ Yes | Device category (Phase 1.1) | `"appliance"`, `"lighting"`, `"security"`, `"climate"` |
| `power_consumption_idle_w` | Float | No | No | Standby power consumption (Phase 1.1) | `2.5` |
| `power_consumption_active_w` | Float | No | No | Active power consumption (Phase 1.1) | `10.0` |
| `power_consumption_max_w` | Float | No | No | Peak power consumption (Phase 1.1) | `15.0` |
| `infrared_codes_json` | Text | No | No | IR codes if applicable (Phase 1.1) | JSON string |
| `setup_instructions_url` | String | No | No | Link to setup guide (Phase 1.1) | `"https://..."` |
| `troubleshooting_notes` | Text | No | No | Common issues and solutions (Phase 1.1) | Text |
| `device_features_json` | Text | No | No | Structured capabilities (Phase 1.1) | JSON string |
| `community_rating` | Float | No | No | Rating from Device Database (Phase 1.1) | `4.5` |
| `last_capability_sync` | DateTime | No | No | When capabilities were last updated (Phase 1.1) | `"2025-01-20T12:00:00Z"` |
| `last_seen` | DateTime | No | No | Last time device was active | `"2025-10-18T14:30:00Z"` |
| `created_at` | DateTime | No | No | When device was first discovered | `"2025-01-15T08:00:00Z"` |
| `entities` | Relationship | - | - | List of entities belonging to this device | (see Entity Data) |

### How Device Data is Populated

**Source:** Home Assistant Device Registry API  
**Endpoint:** Called by `websocket-ingestion` service during initial discovery  
**Update Frequency:** 
- Full refresh: On service startup
- Updates: When device metadata changes in Home Assistant

**API Endpoint for Access:**
```
GET http://localhost:8006/api/devices
GET http://localhost:8006/api/devices/{device_id}
```

**Filters Available:**
- `manufacturer` - Filter by manufacturer
- `model` - Filter by model
- `area_id` - Filter by room/area
- `platform` - Filter by integration platform
- `device_type` - Filter by device type (Phase 1.1)
- `device_category` - Filter by device category (Phase 1.1)

### Example Device Record

```json
{
  "device_id": "a1b2c3d4e5f6",
  "name": "Living Room Motion Sensor",
  "name_by_user": "Main Motion Sensor",
  "manufacturer": "Philips",
  "model": "Hue Motion Sensor",
  "sw_version": "1.50.2_r30933",
  "area_id": "living_room",
  "suggested_area": "living_room",
  "integration": "hue",
  "entry_type": "config_entry",
  "configuration_url": null,
  "last_seen": "2025-10-18T14:30:00Z",
  "created_at": "2025-01-15T08:00:00Z",
  "entity_count": 4
}
```

---

## 2. Entity Data (SQLite)

**Database:** `data/metadata.db`  
**Table:** `entities`  
**Model:** `services/data-api/src/models/entity.py`

### Entity Fields

| Field | Type | Required | Indexed | Description | Example |
|-------|------|----------|---------|-------------|---------|
| `entity_id` | String | ✅ Yes | Primary Key | Unique entity identifier (domain.object_id) | `"sensor.living_room_temperature"` |
| `device_id` | String | No | ✅ Yes | Parent device ID (Foreign Key) | `"a1b2c3d4e5f6"` |
| `domain` | String | ✅ Yes | ✅ Yes | Entity domain/type | `"sensor"`, `"light"`, `"switch"`, `"binary_sensor"` |
| `platform` | String | No | No | Integration platform that created entity | `"hue"`, `"mqtt"`, `"template"` |
| `unique_id` | String | No | No | Unique ID within platform | `"00:17:88:01:02:ab:cd:ef-01-0402"` |
| `area_id` | String | No | ✅ Yes | Room/area assignment | `"living_room"`, `"kitchen"` |
| `disabled` | Boolean | No | No | Whether entity is disabled in HA | `true`, `false` |
| `created_at` | DateTime | No | No | When entity was first discovered | `"2025-01-15T08:00:00Z"` |
| `device` | Relationship | - | - | Parent device object | (see Device Data) |

### Entity Domains (Common Values)

| Domain | Purpose | Example Entity ID |
|--------|---------|-------------------|
| `sensor` | Measurement/status sensors | `sensor.living_room_temperature` |
| `binary_sensor` | On/off sensors (motion, door, etc.) | `binary_sensor.front_door` |
| `light` | Controllable lights | `light.living_room_lamp` |
| `switch` | On/off switches | `switch.bedroom_fan` |
| `climate` | HVAC/thermostat controls | `climate.main_thermostat` |
| `cover` | Blinds, garage doors | `cover.garage_door` |
| `lock` | Smart locks | `lock.front_door` |
| `camera` | Cameras | `camera.front_yard` |
| `media_player` | Media devices | `media_player.living_room_tv` |
| `fan` | Fan controls | `fan.bedroom_ceiling_fan` |
| `alarm_control_panel` | Security systems | `alarm_control_panel.home` |

### How Entity Data is Populated

**Source:** Home Assistant Entity Registry API  
**Endpoint:** Called by `websocket-ingestion` service during discovery  
**Update Frequency:**
- Full refresh: On service startup
- Updates: When entity metadata changes

**API Endpoint for Access:**
```
GET http://localhost:8006/api/entities
GET http://localhost:8006/api/entities/{entity_id}
```

**Filters Available:**
- `domain` - Filter by entity domain
- `platform` - Filter by platform
- `device_id` - Get all entities for a device

### Example Entity Record

```json
{
  "entity_id": "sensor.living_room_temperature",
  "device_id": "a1b2c3d4e5f6",
  "domain": "sensor",
  "platform": "hue",
  "unique_id": "00:17:88:01:02:ab:cd:ef-01-0402",
  "area_id": "living_room",
  "disabled": false,
  "created_at": "2025-01-15T08:00:00Z"
}
```

---

## 3. Home Assistant Event Data (InfluxDB)

**Database:** InfluxDB  
**Bucket:** `home_assistant_events`  
**Measurement:** `home_assistant_events`  
**Schema:** Defined in `services/enrichment-pipeline/src/influxdb_wrapper.py` (Line 180-280)

### Event Structure

Events are stored with **tags** (indexed for fast queries) and **fields** (actual data values).

### Tags (Indexed for Querying)

| Tag | Type | Description | Example |
|-----|------|-------------|---------|
| `entity_id` | String | Entity that changed | `"sensor.living_room_temperature"` |
| `domain` | String | Entity domain | `"sensor"`, `"light"`, `"switch"` |
| `device_class` | String | Device classification | `"temperature"`, `"motion"`, `"humidity"` |
| `event_type` | String | Type of event | `"state_changed"`, `"call_service"` |
| `origin` | String | Event origin | `"LOCAL"`, `"REMOTE"` |
| `time_of_day` | String | Time period when event occurred | `"morning"`, `"afternoon"`, `"evening"`, `"night"` |
| `area_id` | String | Room/area location (Epic 23.2) | `"living_room"`, `"bedroom"` |
| `device_id` | String | Physical device identifier (Epic 23.2) | `"a1b2c3d4e5f6"` |
| `platform` | String | Integration platform | `"hue"`, `"mqtt"`, `"zwave"` |

### Core Fields (State Data)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `state` | String | Current state value | `"22.5"`, `"on"`, `"off"`, `"idle"` |
| `old_state` | String | Previous state value | `"22.3"`, `"off"` |
| `friendly_name` | String | Human-readable name | `"Living Room Temperature"` |
| `unit_of_measurement` | String | Measurement unit | `"°C"`, `"%"`, `"W"` |
| `icon` | String | Material Design Icon | `"mdi:thermometer"`, `"mdi:lightbulb"` |

### Attribute Fields (Prefixed with `attr_`)

Attributes from Home Assistant entities are stored with `attr_` prefix. Common examples:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `attr_brightness` | Float | Light brightness (0-255) | `255`, `128` |
| `attr_temperature` | Float | Temperature value | `22.5`, `68.2` |
| `attr_humidity` | Float | Humidity percentage | `65.5` |
| `attr_battery` | Float | Battery level (0-100) | `87` |
| `attr_power` | Float | Power consumption (W) | `45.2` |
| `attr_energy` | Float | Energy usage (kWh) | `12.5` |
| `attr_voltage` | Float | Voltage (V) | `230` |
| `attr_current` | Float | Current (A) | `0.5` |
| `attr_color_temp` | Float | Color temperature (mireds) | `370` |
| `attr_rgb_color` | String | RGB color value | `"255,128,0"` |
| `attr_effect` | String | Light effect | `"rainbow"`, `"colorloop"` |
| `attr_device_class` | String | Device classification | `"temperature"`, `"motion"` |
| `attr_state_class` | String | State measurement type | `"measurement"`, `"total"` |

**Note:** Attributes are dynamic - different entity types have different attributes. The system automatically extracts and stores all valid attributes with proper type normalization.

### Context Fields (Automation Tracking - Epic 23.1)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `context_id` | String | Unique context identifier | `"abc123def456"` |
| `context_parent_id` | String | Parent context for automation chains | `"xyz789uvw012"` |
| `context_user_id` | String | User who triggered the event | `"system"`, `"user123"` |

**Purpose:** Track automation causality chains (e.g., motion sensor → light automation → light state change)

### Time-Based Analytics Fields (Epic 23.3)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `duration_in_state_seconds` | Float | Seconds entity was in previous state | `3600.0` (1 hour) |

**Purpose:** Calculate how long entities stay in each state (e.g., light was on for 2 hours)

### Device Metadata Fields (Epic 23.5)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `manufacturer` | String | Device manufacturer | `"Philips"`, `"Xiaomi"` |
| `model` | String | Device model | `"Hue Motion Sensor"` |
| `sw_version` | String | Software/firmware version | `"1.50.2_r30933"` |

**Purpose:** Device reliability analysis and tracking by manufacturer/model

---

## 4. Enriched Data (Added by Our System)

### Weather Enrichment

**Source:** Weather API integration  
**Added by:** `enrichment-pipeline` service  
**Purpose:** Correlate device states with weather conditions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `weather_temperature` | Float | Outside temperature (°C) | `15.5` |
| `weather_humidity` | Float | Outside humidity (%) | `72.0` |
| `weather_pressure` | Float | Atmospheric pressure (hPa) | `1013.25` |
| `weather_condition` | String | Weather description | `"Clear"`, `"Cloudy"`, `"Rain"` |
| `weather_wind_speed` | Float | Wind speed (m/s) | `3.5` |
| `weather_cloudiness` | Float | Cloud coverage (%) | `40.0` |

### Data Quality Metrics (Epic 18)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `validation_status` | String | Data validation result | `"valid"`, `"warning"`, `"error"` |
| `quality_score` | Float | Data quality score (0-100) | `95.5` |
| `normalized` | Boolean | Whether data was normalized | `true` |

---

## 5. Query Patterns

### Common Query Scenarios

**1. Get all devices in a room:**
```http
GET http://localhost:8006/api/devices?area_id=living_room
```

**2. Get all temperature sensors:**
```http
GET http://localhost:8006/api/entities?domain=sensor
```

**3. Get devices by manufacturer:**
```http
GET http://localhost:8006/api/devices?manufacturer=Philips
```

**4. Get entities for a specific device:**
```http
GET http://localhost:8006/api/entities?device_id=a1b2c3d4e5f6
```

**5. Get recent events for an entity (InfluxDB):**
```flux
from(bucket: "home_assistant_events")
  |> range(start: -1h)
  |> filter(fn: (r) => r["entity_id"] == "sensor.living_room_temperature")
  |> filter(fn: (r) => r["_field"] == "state")
```

---

## 6. Data Flow

```
Home Assistant
     ↓
[WebSocket Connection]
     ↓
websocket-ingestion service
     ↓
[Device/Entity Discovery] → SQLite (devices, entities tables)
     ↓
[State Change Events]
     ↓
enrichment-pipeline service
     ↓
[Add weather, normalize data, extract attributes]
     ↓
InfluxDB (home_assistant_events measurement)
     ↓
[Query via data-api]
     ↓
Health Dashboard / API Consumers
```

---

## 7. Type Normalization

The `enrichment-pipeline` performs automatic type normalization to prevent InfluxDB type conflicts:

### Boolean Normalization

Converts various string representations to actual booleans:

| Input | Output |
|-------|--------|
| `"on"`, `"true"`, `"1"`, `"yes"`, `"enabled"`, `"active"` | `true` |
| `"off"`, `"false"`, `"0"`, `"no"`, `"disabled"`, `"inactive"` | `false` |

### Numeric Normalization

Converts numeric strings to floats:

| Input | Output |
|-------|--------|
| `"22.5"` | `22.5` (float) |
| `"100"` | `100.0` (float) |
| `"on"` | `"on"` (string, not numeric) |

### Unit Normalization

Standardizes units for consistency:

| Original | Normalized |
|----------|------------|
| `"°C"`, `"celsius"` | `"celsius"` |
| `"°F"`, `"fahrenheit"` | `"fahrenheit"` |
| `"hPa"`, `"mbar"` | `"hectopascal"` |

**Purpose:** Prevent InfluxDB type conflicts where a field receives different data types over time.

---

## 8. Data Freshness

### Update Frequencies

| Data Type | Update Frequency | Source |
|-----------|------------------|--------|
| Device Metadata | On startup + on-demand | Home Assistant Device Registry |
| Entity Metadata | On startup + on-demand | Home Assistant Entity Registry |
| State Events | Real-time (0-100ms) | Home Assistant WebSocket stream |
| Weather Data | Every 15 minutes (cached) | Weather API |
| Device Discovery | Every 5 minutes | Home Assistant discovery events |

### Data Retention

| Data Type | Retention Period | Storage |
|-----------|------------------|---------|
| Device/Entity Metadata | Indefinite | SQLite |
| Recent Events | 90 days (default) | InfluxDB |
| Aggregated Metrics | 1 year | InfluxDB (downsampled) |
| System Logs | 30 days | Docker logs |

---

## 9. Example Complete Event

Here's what a complete enriched event looks like in InfluxDB:

```json
{
  "_measurement": "home_assistant_events",
  "_time": "2025-10-18T14:30:00Z",
  
  "tags": {
    "entity_id": "sensor.living_room_temperature",
    "domain": "sensor",
    "device_class": "temperature",
    "event_type": "state_changed",
    "origin": "LOCAL",
    "time_of_day": "afternoon",
    "area_id": "living_room",
    "device_id": "a1b2c3d4e5f6",
    "platform": "hue"
  },
  
  "fields": {
    "state": "22.5",
    "old_state": "22.3",
    "friendly_name": "Living Room Temperature",
    "unit_of_measurement": "°C",
    "icon": "mdi:thermometer",
    
    "attr_temperature": 22.5,
    "attr_humidity": 65.5,
    "attr_battery": 87.0,
    "attr_device_class": "temperature",
    "attr_state_class": "measurement",
    
    "context_id": "abc123def456",
    "context_parent_id": null,
    "context_user_id": null,
    
    "duration_in_state_seconds": 300.0,
    
    "manufacturer": "Philips",
    "model": "Hue Motion Sensor",
    "sw_version": "1.50.2_r30933",
    
    "weather_temperature": 15.5,
    "weather_humidity": 72.0,
    "weather_pressure": 1013.25,
    "weather_condition": "Clear",
    "weather_wind_speed": 3.5,
    
    "validation_status": "valid",
    "quality_score": 98.5,
    "normalized": true
  }
}
```

---

## 10. API Reference

### Device Endpoints

```
GET  /api/devices                    # List all devices
GET  /api/devices/{device_id}        # Get specific device
GET  /api/devices/reliability        # Device reliability metrics
POST /internal/devices/bulk_upsert   # Bulk update devices (internal)
```

### Entity Endpoints

```
GET  /api/entities                   # List all entities
GET  /api/entities/{entity_id}       # Get specific entity
POST /internal/entities/bulk_upsert  # Bulk update entities (internal)
```

### Integration Endpoints

```
GET /api/integrations                           # List all integrations
GET /api/integrations/{platform}/performance    # Platform performance metrics
GET /api/integrations/{platform}/analytics      # Platform analytics
```

### Event Endpoints

```
GET /api/events                 # Recent events
GET /api/events/{id}            # Specific event
GET /api/events/search          # Search events
GET /api/events/stats           # Event statistics
```

---

## 11. Dashboard Access

### Health Dashboard

**URL:** http://localhost:3000

**Tabs with Device Data:**
- **Devices Tab:** Browse devices and entities by manufacturer, room, or domain
- **Events Tab:** Real-time state change events
- **Data Sources Tab:** Integration performance and device discovery status
- **Dependencies Tab:** Service relationships and data flow

### Direct API Access

**Base URL:** http://localhost:8006

All endpoints return JSON and support CORS for frontend access.

---

## 12. Technical Notes

### Performance Characteristics

**SQLite Queries:**
- Device lookups: <5ms
- Entity queries: <10ms
- Filtered queries: <15ms

**InfluxDB Queries:**
- Recent events (1 hour): ~50ms
- Daily aggregations: ~200ms
- Complex analytics: ~500ms

### Data Volume Estimates

**Typical Home (20 devices, 80 entities):**
- Device metadata: ~5 KB
- Entity metadata: ~20 KB
- Events per day: ~10,000-50,000 (depending on activity)
- Storage per day: ~5-25 MB (InfluxDB)

### Schema Evolution

The schema is versioned and uses migrations:
- **SQLite:** Alembic migrations in `services/data-api/alembic/versions/`
- **InfluxDB:** Schema defined in code, backward compatible

---

## Summary

This system captures **three layers of data**:

1. **Device Layer (SQLite)** - What physical devices exist
2. **Entity Layer (SQLite)** - What sensors/controls each device provides
3. **Event Layer (InfluxDB)** - What those sensors/controls are doing over time

The data is **enriched** with weather context, normalized for consistency, and **indexed** for fast queries across both relational (device/entity browsing) and time-series (event history) patterns.

All data is accessible via REST APIs and displayed in the Health Dashboard for easy exploration.

