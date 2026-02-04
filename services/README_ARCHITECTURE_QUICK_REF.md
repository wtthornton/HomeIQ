# Services Architecture Quick Reference

**Last Updated:** January 8, 2026 (Epic 31+)  
**Purpose:** Quick reference for developers working on services

---

## 🚨 IMPORTANT: Epic 31 Architecture Changes

### What Changed

**BEFORE Epic 31:**
```
HA → websocket-ingestion → enrichment-pipeline → InfluxDB
```

**AFTER Epic 31 (CURRENT):**
```
HA → websocket-ingestion → InfluxDB (DIRECT)
```

### Deprecated Services

| Service | Port | Status | Replacement |
|---------|------|--------|-------------|
| enrichment-pipeline | 8002 | ❌ DEPRECATED | Inline normalization in websocket-ingestion |

**DO NOT:**
- Reference enrichment-pipeline in new code
- Create HTTP clients to enrichment-pipeline
- Suggest enrichment-pipeline for data processing

---

## Service Architecture Patterns

### Pattern A: Event Ingestion (Primary Data Path)

**Service:** websocket-ingestion (Port 8001)

**Flow:**
```
1. Connect to HA WebSocket
2. Subscribe to state_changed events
3. Process and normalize events inline
4. Write directly to InfluxDB
5. Discover devices/entities → data-api → SQLite
```

**Key Files:**
- `main.py` - Service entry point
- `connection_manager.py` - WebSocket management
- `event_processor.py` - Event validation and processing
- `influxdb_batch_writer.py` - Direct InfluxDB writes

---

### Pattern B: External API Integration

**Services:** weather-api, sports-api, carbon-intensity, air-quality, etc.

**Flow:**
```
1. Fetch data from external API (ESPN, OpenWeatherMap, etc.)
2. Write directly to InfluxDB
3. No service-to-service dependencies
4. Dashboard queries via data-api
```

**Example:** sports-api (Port 8005)
```python
# Fetch from Home Assistant Team Tracker sensors
sensors = await ha_client.get_team_tracker_sensors()

# Write directly to InfluxDB
await influxdb.write_sports_data(sensors)

# Dashboard queries via data-api
# GET http://localhost:8006/api/v1/sports/games
```

---

### Pattern C: Query API

**Service:** data-api (Port 8006)

**Purpose:** Central query endpoint for all data

**Queries:**
- Events → InfluxDB
- Devices/Entities → SQLite
- Sports → InfluxDB
- Analytics → InfluxDB

**DO NOT:**
- Query InfluxDB directly from services
- Create duplicate query logic
- ✅ Always query via data-api

---

## Service Communication Rules

### ✅ ALLOWED

```python
# Service → InfluxDB (direct write)
await self.influxdb_client.write_event(event)

# Service → data-api (query)
response = await httpx.get("http://data-api:8006/api/v1/events")

# Service → data-api (store metadata)
response = await httpx.post("http://data-api:8006/internal/devices/bulk_upsert")
```

### ❌ NOT ALLOWED

```python
# Service → enrichment-pipeline (DEPRECATED)
await httpx.post("http://enrichment-pipeline:8002/events")  # DON'T DO THIS

# Service → websocket-ingestion (wrong direction)
await httpx.post("http://websocket-ingestion:8001/events")  # DON'T DO THIS

# Service → Service (creates coupling)
await httpx.get("http://weather-api:8009/current")  # Use InfluxDB instead
```

---

## Database Patterns (Epic 22)

### Time-Series Data → InfluxDB

**Use InfluxDB for:**
- Events with timestamps
- Metrics that change over time
- Sports scores
- Weather data
- Analytics data

**Example:**
```python
from influxdb_client import Point

point = Point("home_assistant_events") \
    .tag("entity_id", "light.living_room") \
    .tag("domain", "light") \
    .field("state", "on") \
    .time(datetime.now())

await influxdb.write(point)
```

### Metadata → SQLite

**Use SQLite for:**
- Devices (manufacturer, model, etc.)
- Entities (friendly_name, device_class, etc.)
- Webhooks (team_id, event_type, etc.)
- Configuration

**Example:**
```python
from sqlalchemy import select
from models import Device

async with async_session() as session:
    result = await session.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
```

---

## Performance Guidelines

### Batching

**websocket-ingestion:**
- Batch size: 100 events (BATCH_SIZE)
- Batch timeout: 5.0 seconds (BATCH_TIMEOUT)
- Throughput: 10,000+ events/second

**DO:**
- ✅ Use batching for high-volume writes
- ✅ Configure batch size via environment variables
- ✅ Monitor batch processor performance

### InfluxDB Writes

**Best Practices:**
- Write in batches (100-1000 points)
- Use async writes
- Set appropriate timeouts (5-10 seconds)
- Handle field type conflicts gracefully

**Example:**
```python
# Batch write
points = [create_point(event) for event in batch]
await influxdb_manager.write_points(points)
```

---

## Service Ports Reference

| Service | Port | Purpose | Dependencies |
|---------|------|---------|--------------|
| websocket-ingestion | 8001 | HA event ingestion | InfluxDB, data-api |
| ~~enrichment-pipeline~~ | ~~8002~~ | **DEPRECATED** | ~~None~~ |
| admin-api | 8003 | System monitoring | All services |
| sports-api | 8005 | Team Tracker integration | InfluxDB (standalone) |
| data-api | 8006 | Query hub | InfluxDB, SQLite |
| weather-api | 8009 | Weather data | InfluxDB |
| carbon-intensity | 8010 | Carbon data | InfluxDB |
| air-quality | 8012 | AQI data | InfluxDB |
| calendar | 8013 | HA calendar | InfluxDB |
| **automation-linter** | **8020** | **HA automation linter/fixer** | **None (standalone)** |
| InfluxDB | 8086 | Time-series DB | None |
| health-dashboard | 3000 | React UI | data-api, admin-api |

---

## Epic 23 Enhancements (Still Active)

**Context Tracking:**
- `context_id`: Event ID
- `context_parent_id`: Parent event (for automation chains)
- `context_user_id`: User who triggered

**Spatial Analytics:**
- `device_id`: Physical device ID
- `area_id`: Room/area ID

**Duration Tracking:**
- `duration_in_state`: Seconds in previous state

**Device Metadata:**
- `manufacturer`: Device manufacturer
- `model`: Device model
- `sw_version`: Software version

**All fields stored in InfluxDB** for analytics.

---

## Common Mistakes to Avoid

### ❌ Don't Do This

```python
# Sending events to enrichment-pipeline (DEPRECATED)
await http_client.post("http://enrichment-pipeline:8002/events", json=event)

# Querying InfluxDB directly from dashboard
influx = InfluxDBClient(...)
events = influx.query("...")

# Creating service-to-service HTTP calls
weather = await httpx.get("http://weather-api:8009/current")
```

### ✅ Do This Instead

```python
# Write directly to InfluxDB
await self.influxdb_client.write_event(event)

# Query via data-api
events = await httpx.get("http://data-api:8006/api/v1/events")

# Query InfluxDB for shared data
weather = await data_api.get("http://data-api:8006/api/v1/events?domain=weather")
```

---

## Documentation Standards

### When Writing READMEs

```markdown
# ✅ CORRECT
Events are written directly to InfluxDB by websocket-ingestion (Epic 31).

# ❌ INCORRECT  
Events are sent to enrichment-pipeline for normalization before InfluxDB.
```

### When Writing Call Trees

- ✅ Mark deprecated services clearly
- ✅ Include Epic numbers for context
- ✅ Validate against actual code
- ✅ Update version numbers
- ✅ Add change logs

### When Creating Architecture Diagrams

```
# ✅ CORRECT (Epic 31)
HA → websocket-ingestion → InfluxDB

# ❌ INCORRECT (Pre-Epic 31)
HA → websocket-ingestion → enrichment-pipeline → InfluxDB
```

---

## Related Documentation

- **[Master Call Tree Index](../implementation/analysis/MASTER_CALL_TREE_INDEX.md)** - All call trees
- **[HA Event Call Tree](../implementation/analysis/HA_EVENT_CALL_TREE.md)** - Detailed event flow
- **[Tech Stack](../docs/architecture/tech-stack.md)** - Technology choices
- **[Source Tree](../docs/architecture/source-tree.md)** - File organization

---

**Quick Tip:** When in doubt about the architecture, check the actual code in `services/websocket-ingestion/src/main.py` - it has clear Epic 31 deprecation comments showing what was removed.

---

**Last Updated:** January 8, 2026  
**Epic Context:** Post-Epic 31 (enrichment-pipeline deprecated)

