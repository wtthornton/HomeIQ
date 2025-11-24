# Database Schema

**Related Documents:**
- [Database Optimization Guide](database-optimization.md) - Performance tuning and best practices

---

## Hybrid Database Architecture (Epic 22)

This system uses a **hybrid database architecture** optimizing for different data types:

- **InfluxDB 2.7**: Time-series data (events, metrics, sports scores)
- **SQLite 3.45+**: Metadata and relational data (devices, entities, webhooks)

---

## InfluxDB Schema Design

**Database:** `home_assistant`
**Organization:** `home_assistant`
**Primary Bucket:** `home_assistant_events` (365 days retention)
**Additional Buckets:** 
- `sports_data` (90 days retention)
- `weather_data` (180 days retention) 
- `system_metrics` (30 days retention)

**Status:** ✅ Schema validated and deployed (January 2025)

### Primary Measurement: `home_assistant_events`

**Purpose:** Store all Home Assistant events with enrichment data for time-series analysis

#### Tags (for filtering and grouping):

**Core Event Tags:**
- `entity_id` - Home Assistant entity identifier (e.g., "sensor.living_room_temperature")
- `domain` - Entity domain (sensor, switch, light, binary_sensor, etc.)
- `device_class` - Device classification (temperature, motion, humidity, etc.)
- `event_type` - Event type (state_changed, call_service, etc.)

**Spatial & Device Tags** [Epic 23.2]:
- `device_id` - Physical device identifier for device-level aggregation ✅
- `area_id` - Room/area ID for spatial analytics ✅

**Integration & Classification Tags:**
- `integration` - HA integration source (zwave, mqtt, zigbee, etc.) ✅ **NEW: Oct 2025**
- `entity_category` - Entity classification (null, diagnostic, config) [Epic 23.4] ✅

**Temporal Tags:**
- `time_of_day` - Time period (morning: 5am-12pm, afternoon: 12pm-5pm, evening: 5pm-9pm, night: 9pm-5am) ✅ **NEW: Oct 2025**

**Weather Tags** (DEPRECATED - Epic 31):
- `weather_condition` - **DEPRECATED** (Oct 2025) - Historical events only. Use weather-api service (Port 8009) for new weather data.

**Planned Tags** (designed but not currently implemented):
- `area` - Room/area name (human-readable) - ⚠️ Have `area_id`, need name resolution
- `device_name` - Friendly device name - ⚠️ NOT IMPLEMENTED
- `location` - Geographic location - ⚠️ PARTIAL (only from weather entities)

#### Fields (measurements and values):

**IMPORTANT**: The enrichment pipeline uses a **flattened attribute schema** where each Home Assistant attribute becomes a separate field. This provides better query performance but results in 150+ dynamic fields per measurement.

**Core Event Fields:**
- `state` - Current state value (string) - *Note: documented as `state_value` in design, implemented as `state`*
- `old_state` - Previous state value (string) - *Note: documented as `previous_state` in design*
- `context_id` - Context identifier for event correlation (string) [Epic 23.1]
- `duration_in_state_seconds` - Time entity has been in current state (float) [Epic 23.3]

**Device Metadata Fields** [Epic 23.5]:
- `manufacturer` - Device manufacturer (string)
- `model` - Device model (string)
- `sw_version` - Software/firmware version (string)

**Entity Metadata Fields:**
- `friendly_name` - Human-readable entity name (string)
- `icon` - Entity icon identifier (string)
- `unit_of_measurement` - Measurement unit (string)

**Flattened Attribute Fields** (dynamic, 120+ fields):
Each Home Assistant attribute is stored as `attr_{attribute_name}`:
- `attr_temperature` - Temperature from attributes (float)
- `attr_humidity` - Humidity from attributes (float)
- `attr_pressure` - Pressure from attributes (float)
- `attr_battery_level` - Battery level (float)
- `attr_brightness` - Light brightness (integer)
- `attr_color_temp` - Color temperature (integer)
- `attr_latitude` - Location latitude (float)
- `attr_longitude` - Location longitude (float)
- ... and 100+ more dynamic fields based on entity attributes

**Weather Enrichment Fields** ✅ **ACTIVE (Oct 18, 2025)**:
- `weather_temp` - Ambient temperature context in Celsius (float) ✅
- `weather_humidity` - Ambient humidity percentage (integer) ✅
- `weather_pressure` - Ambient pressure in hPa (float) ✅
- `wind_speed` - Wind speed in m/s (float) ✅
- `weather_description` - Weather description text (string) ✅

**Weather Tags**:
- `weather_condition` - Weather condition (Clear, Clouds, Rain, etc.) ✅ **NEW: Oct 2025**

**Note (UPDATED Oct 2025 - Epic 31)**: Weather enrichment has been **migrated to standalone weather-api service** (Port 8009). Historical events retain embedded weather fields for backward compatibility. New events do NOT include weather fields - use time-window JOINs with weather_data measurement for weather correlation queries.

---

### Schema Architecture Decision: Flattened Attributes

**Design Choice**: The enrichment pipeline flattens all Home Assistant entity attributes into separate InfluxDB fields with an `attr_` prefix.

**Rationale** (based on InfluxDB best practices from Context7):
- ✅ **Better Query Performance**: Direct field access vs JSON parsing
- ✅ **Type Preservation**: Numbers stay numeric, booleans stay boolean
- ✅ **Easier Analytics**: Each attribute can be queried/aggregated independently
- ✅ **InfluxDB Optimized**: Fields are optimized for time-series queries

**Trade-offs Accepted**:
- ⚠️ **Wide Schema**: ~150 fields vs designed 17 fields
- ⚠️ **Storage Overhead**: Field names repeated per event
- ✅ **Query Performance**: Significantly faster than JSON field queries

**Implementation Location**: `services/enrichment-pipeline/src/influxdb_wrapper.py` (Line 214)

```python
# Flattens all attributes with attr_ prefix
for key, value in attributes.items():
    if self._is_valid_field_value(value):
        point.field(f"attr_{key}", value)
```

**Alternative Design** (not used): Store all attributes in single JSON field (`attributes`)
- Used in websocket-ingestion fallback schema
- Requires JSON parsing for attribute queries
- ~4x slower for attribute-based filtering

---

### Recent Schema Enhancements (October 2025)

**New Tags Added**:
1. **`integration` tag** - Identifies the source integration (zwave, mqtt, zigbee, homekit, etc.)
   - Enables filtering by integration type
   - Useful for debugging integration-specific issues
   - Example query: "Show all zigbee device states"
   - Implementation: `services/enrichment-pipeline/src/influxdb_wrapper.py` (Line 167-170)

2. **`time_of_day` tag** - Temporal categorization of events
   - Values: morning (5am-12pm), afternoon (12pm-5pm), evening (5pm-9pm), night (9pm-5am)
   - Enables temporal pattern analysis
   - Example query: "Show all lights turned on in the evening"
   - Supports circadian rhythm analysis
   - Implementation: `services/enrichment-pipeline/src/influxdb_wrapper.py` (Line 172-193)

3. **`weather_condition` tag** - Current weather condition for context-aware queries
   - Values: Clear, Clouds, Rain, Snow, Thunderstorm, etc.
   - Enables weather-based filtering
   - Example query: "Show all motion events when it was raining"
   - Implementation: `services/enrichment-pipeline/src/influxdb_wrapper.py` (Line 306-307)

**New Fields Added**:
1. **Weather enrichment fields** - Current weather context for all events
   - `weather_temp` (°C), `weather_humidity` (%), `weather_pressure` (hPa), `wind_speed` (m/s)
   - Source: OpenWeatherMap API (Las Vegas, NV)
   - Cache: 5-minute TTL with 97%+ hit rate
   - Implementation: `services/enrichment-pipeline/src/influxdb_wrapper.py` (Line 281-310)

**Impact**: All tags and fields are applied to new events. Weather enrichment activated after cache clear (Oct 18, 2025, 11:11 AM).

---
- **[Epic 23.3]** `duration_in_state_seconds` - Time entity was in previous state (float) ✅
- **[Epic 23.5]** `manufacturer` - Device manufacturer for reliability analysis (string) ✅
- **[Epic 23.5]** `model` - Device model for reliability analysis (string) ✅
- **[Epic 23.5]** `sw_version` - Device firmware version for version correlation (string) ✅

### Schema Examples

#### Temperature Sensor Event:
```
Measurement: home_assistant_events
Tags:
  entity_id: sensor.living_room_temperature
  domain: sensor
  device_class: temperature
  area: living_room
  device_id: aeotec_multisensor_6        ← Epic 23.2
  area_id: living_room                   ← Epic 23.2
  weather_condition: clear
  time_of_day: evening
Fields:
  state_value: "22.5"
  normalized_value: 22.5
  weather_temp: 18.2
  weather_humidity: 65.0
  weather_pressure: 1013.25
  unit_of_measurement: "°C"
  context_id: "abc123"                   ← Epic 23.1
  context_parent_id: "automation_xyz"    ← Epic 23.1
  duration_in_state_seconds: 123.45      ← Epic 23.3
  manufacturer: "Aeotec"                 ← Epic 23.5
  model: "ZW100 MultiSensor 6"           ← Epic 23.5
  sw_version: "1.10"                     ← Epic 23.5
Timestamp: 2024-12-19T15:30:00Z
```

#### Switch Event:
```
Measurement: home_assistant_events
Tags:
  entity_id: switch.living_room_lamp
  domain: switch
  device_class: switch
  area: living_room
  weather_condition: cloudy
  time_of_day: evening
Fields:
  state_value: "on"
  previous_state: "off"
  normalized_value: 1.0
Timestamp: 2024-12-19T15:30:00Z
```

### Continuous Queries (Downsampling)

#### Hourly Summaries:
```sql
CREATE CONTINUOUS QUERY "hourly_summaries" ON "home_assistant"
BEGIN
  SELECT 
    mean("normalized_value") as avg_value,
    min("normalized_value") as min_value,
    max("normalized_value") as max_value,
    count("state_value") as event_count
  INTO "home_assistant"."autogen"."hourly_events"
  FROM "home_assistant"."autogen"."home_assistant_events"
  GROUP BY time(1h), "entity_id", "domain", "device_class"
END
```

#### Daily Summaries:
```sql
CREATE CONTINUOUS QUERY "daily_summaries" ON "home_assistant"
BEGIN
  SELECT 
    mean("normalized_value") as avg_value,
    min("normalized_value") as min_value,
    max("normalized_value") as max_value,
    count("state_value") as event_count,
    sum("energy_consumption") as total_energy
  INTO "home_assistant"."autogen"."daily_events"
  FROM "home_assistant"."autogen"."home_assistant_events"
  GROUP BY time(1d), "entity_id", "domain", "device_class"
END
```

### Retention Policies (Current Configuration)

#### Primary Bucket: `home_assistant_events`
- **Retention:** 365 days (1 year) ✅
- **Purpose:** Home Assistant event data with Epic 23 enhancements

#### Sports Data Bucket: `sports_data`
- **Retention:** 90 days ✅
- **Purpose:** Sports scores and game data

#### Weather Data Bucket: `weather_data`
- **Retention:** 180 days ✅
- **Purpose:** Weather data from weather-api service (Port 8009) ✅ **Epic 31**
- **Measurement:** `weather` (location, condition, temperature, humidity, pressure, wind_speed)
- **Source:** OpenWeatherMap API via standalone weather-api microservice

#### System Metrics Bucket: `system_metrics`
- **Retention:** 30 days ✅
- **Purpose:** System performance and health metrics

**Note:** All buckets are configured and validated as of January 2025

---

## SQLite Schema Design (Epic 22 + October 2025 Enhancement)

**Database Files:**
- `data/metadata.db` (data-api service) - Devices and entities
- `data/webhooks.db` (sports-data service) - Webhook subscriptions

**Data Population** (Updated October 2025):
- **Devices & Entities**: Direct from Home Assistant WebSocket discovery
- **Method**: POST to `/internal/devices/bulk_upsert` (automated on connection)
- **Frequency**: On WebSocket connect/reconnect
- **Current Data**: 99 real devices, 100+ real entities ✅

**Configuration:**
- **WAL Mode**: Enabled for concurrent reads/writes
- **Synchronous**: NORMAL (fast, safe)
- **Cache Size**: 64MB
- **Foreign Keys**: Enabled

### Devices Table (data-api)

**Purpose:** Store Home Assistant device metadata for fast lookups and relational queries

**Schema:**
```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    sw_version TEXT,
    area_id TEXT,
    integration TEXT,
    config_entry_id TEXT,
    via_device TEXT REFERENCES devices(device_id),
    last_seen TIMESTAMP,
    created_at TIMESTAMP
);

CREATE INDEX idx_device_area ON devices(area_id);
CREATE INDEX idx_device_integration ON devices(integration);
CREATE INDEX idx_device_manufacturer ON devices(manufacturer);
CREATE INDEX idx_device_config_entry ON devices(config_entry_id);
CREATE INDEX idx_device_via_device ON devices(via_device);
```

**Fields:**
- `device_id`: Unique device identifier (primary key)
- `name`: Friendly device name
- `manufacturer`: Device manufacturer (e.g., "Philips", "Sonoff")
- `model`: Device model number
- `sw_version`: Software/firmware version
- `area_id`: Room/area location (e.g., "living_room", "bedroom")
- `integration`: HA integration source (e.g., "zwave", "mqtt", "zigbee")
- `config_entry_id`: Config entry ID (source tracking) - **NEW**
- `via_device`: Parent device ID (self-referential FK for device hierarchy) - **NEW**
- `last_seen`: Last time device was active
- `created_at`: First discovery timestamp

**Example Row:**
```json
{
  "device_id": "abc123def456",
  "name": "Living Room Light",
  "manufacturer": "Philips",
  "model": "Hue White A19",
  "sw_version": "1.88.1",
  "area_id": "living_room",
  "integration": "hue",
  "last_seen": "2025-01-14T12:30:00Z",
  "created_at": "2024-06-15T10:00:00Z"
}
```

### Entities Table (data-api)

**Purpose:** Store Home Assistant entity metadata with foreign key relationship to devices

**Schema:**
```sql
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    device_id TEXT REFERENCES devices(device_id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    platform TEXT,
    unique_id TEXT,
    area_id TEXT,
    disabled BOOLEAN DEFAULT 0,
    config_entry_id TEXT,
    created_at TIMESTAMP
);

CREATE INDEX idx_entity_device ON entities(device_id);
CREATE INDEX idx_entity_domain ON entities(domain);
CREATE INDEX idx_entity_area ON entities(area_id);
CREATE INDEX idx_entity_config_entry ON entities(config_entry_id);
```

**Fields:**
- `entity_id`: Unique entity identifier (e.g., "light.living_room_lamp")
- `device_id`: Foreign key to devices table (CASCADE delete)
- `domain`: Entity domain (e.g., "light", "sensor", "switch")
- `platform`: Integration platform
- `unique_id`: Unique ID within platform
- `area_id`: Room/area location
- `disabled`: Whether entity is disabled
- `config_entry_id`: Config entry ID (source tracking) - **NEW**
- `created_at`: First discovery timestamp

**Example Row:**
```json
{
  "entity_id": "light.living_room_lamp",
  "device_id": "abc123def456",
  "domain": "light",
  "platform": "hue",
  "unique_id": "00:17:88:01:02:34:56:78-0b",
  "area_id": "living_room",
  "disabled": false,
  "created_at": "2024-06-15T10:00:00Z"
}
```

**Foreign Key Relationships:**
```
devices (1) ----< entities (N)
  └─ device_id ──> device_id

devices (1) ----< devices (N) [self-referential]
  └─ via_device ──> device_id [device hierarchy]
```

**Relationship Queries:**
The EntityRegistry service provides relationship query methods:
- `get_entities_by_device(device_id)` - Get all entities for a device
- `get_sibling_entities(entity_id)` - Get entities from same device
- `get_entities_in_area(area_id)` - Get all entities in an area
- `get_entities_by_config_entry(config_entry_id)` - Get entities by config entry
- `get_device_hierarchy(device_id)` - Get device hierarchy (via_device relationships)

### Webhooks Table (sports-data)

**Purpose:** Store webhook subscriptions for game event notifications

**Schema:**
```sql
CREATE TABLE webhooks (
    webhook_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    events TEXT NOT NULL,
    secret TEXT NOT NULL,
    team TEXT,
    created_at TIMESTAMP,
    total_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    last_success TEXT,
    last_failure TEXT,
    enabled BOOLEAN DEFAULT 1
);

CREATE INDEX idx_webhooks_team ON webhooks(team);
```

**Fields:**
- `webhook_id`: Unique webhook identifier (UUID)
- `url`: Webhook delivery URL
- `events`: JSON array of subscribed events (e.g., '["game_started", "score_changed"]')
- `secret`: HMAC secret for signature verification
- `team`: Optional team filter (e.g., "sf", "dal")
- `created_at`: Registration timestamp
- `total_calls`: Successful delivery count
- `failed_calls`: Failed delivery count
- `last_success`: Last successful delivery timestamp (ISO string)
- `last_failure`: Last failed delivery timestamp (ISO string)
- `enabled`: Whether webhook is active

**Example Row:**
```json
{
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/webhook/sports",
  "events": "[\"game_started\", \"score_changed\", \"game_ended\"]",
  "secret": "secret_key_at_least_16_chars",
  "team": "sf",
  "created_at": "2025-01-14T10:00:00Z",
  "total_calls": 45,
  "failed_calls": 2,
  "last_success": "2025-01-14T12:30:00Z",
  "last_failure": "2025-01-13T15:20:00Z",
  "enabled": true
}
```

---

## Query Performance Comparison

| Operation | InfluxDB (Before) | SQLite (After) | Improvement |
|-----------|-------------------|----------------|-------------|
| Get device by ID | ~50ms | <10ms | **5x faster** |
| List devices with filter | ~100ms | <15ms | **6-7x faster** |
| List entities by domain | ~40ms | <5ms | **8x faster** |
| Device with entity count (JOIN) | ~120ms (2 queries) | <10ms (1 query) | **12x faster** |

---

## Backup Strategy

### InfluxDB Backups
- Automated backups via InfluxDB CLI
- Backup retention: 30 days
- Location: `./backups/influxdb/`

### SQLite Backups
- Simple file copy (database files are self-contained)
- Backup command: `cp data/*.db backups/sqlite/`
- Can backup while database is running (WAL mode safe)
- Location: `./backups/sqlite/`

**Backup Script:**
```bash
# Backup both databases
mkdir -p backups/influxdb backups/sqlite
influx backup backups/influxdb/
cp services/data-api/data/metadata.db backups/sqlite/
cp services/sports-data/data/webhooks.db backups/sqlite/
```

