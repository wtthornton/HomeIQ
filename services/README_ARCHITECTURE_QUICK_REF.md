# Services Architecture Quick Reference

**Last Updated:** February 23, 2026 (Phase 5: Service Groups + Resilience)
**Purpose:** Quick reference for developers working on services

---

## Services Overview

**Total Services:** 50+ microservices organized into **6 deployment groups** and 7 criticality tiers

For detailed documentation, see:
- **[Service Groups Architecture](../docs/architecture/service-groups.md)** - Canonical reference for the 6-group structure
- **[Services Ranked by Importance](./SERVICES_RANKED_BY_IMPORTANCE.md)** - Comprehensive tier classification and operational guidelines

---

## Service Group Architecture

HomeIQ services are organized into 6 independently deployable groups:

```
                    +------------------------------+
                    |   Group 1: core-platform     |
                    |   influxdb, data-api,        |
                    |   websocket-ingestion,       |
                    |   admin-api, health-dashboard,|
                    |   data-retention             |
                    +---------------+--------------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
          v                         v                         v
  +----------------+     +-------------------+     +-------------------+
  | Group 2:       |     | Group 3:          |     | Group 5:          |
  | data-collectors|     | ml-engine         |     | device-management |
  | 8 services     |     | 9+1 services      |     | 8 services        |
  +----------------+     +---------+---------+     +-------------------+
                                   |
                                   v
                    +------------------------------+
                    |   Group 4: automation-       |
                    |   intelligence (16 services) |
                    +---------------+--------------+
                                    |
                                    v
                    +------------------------------+
                    |   Group 6: frontends         |
                    |   3 services + infra          |
                    +------------------------------+
```

### Group Deployment Commands

```bash
# Full stack (all groups via root compose)
docker compose up -d

# Core only (minimal data pipeline)
docker compose -f compose/core.yml up -d

# Core + collectors (data pipeline with enrichment)
docker compose -f compose/core.yml -f compose/collectors.yml up -d

# Core + ML + automation (AI features)
docker compose -f compose/core.yml -f compose/ml.yml -f compose/automation.yml up -d

# Single group rebuild
docker compose -f compose/ml.yml up -d --build
```

For complete deployment commands per group, see the [Service Groups Architecture](../docs/architecture/service-groups.md) and [Deployment Runbook](../docs/deployment/DEPLOYMENT_RUNBOOK.md).

---

## IMPORTANT: Epic 31 Architecture Changes

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

# Service → data-api (query) — use CrossGroupClient for cross-group calls
response = await self._cross_client.call("GET", "/api/v1/events")

# Service → data-api (store metadata)
response = await self._cross_client.call("POST", "/internal/devices/bulk_upsert", json=data)
```

### ❌ NOT ALLOWED

```python
# Service → enrichment-pipeline (DEPRECATED)
await httpx.post("http://enrichment-pipeline:8002/events")  # DON'T DO THIS

# Service → websocket-ingestion (wrong direction)
await httpx.post("http://websocket-ingestion:8001/events")  # DON'T DO THIS

# Service → Service (creates coupling)
await httpx.get("http://weather-api:8009/current")  # Use InfluxDB instead

# Raw httpx for cross-group calls (no resilience)
await httpx.get("http://data-api:8006/api/entities")  # Use CrossGroupClient instead
```

### Cross-Group Resilience Pattern

All cross-group HTTP calls **must** use the `shared/resilience` module. This provides circuit breakers, retry with backoff, Bearer auth, and OTel trace propagation.

```python
from shared.resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

# Module-level shared breaker (one per target group)
_core_platform_breaker = CircuitBreaker(name="core-platform")

class DataAPIClient:
    def __init__(self, base_url="http://data-api:8006", api_key=None):
        self._cross_client = CrossGroupClient(
            base_url=base_url, group_name="core-platform",
            timeout=30.0, max_retries=3, auth_token=api_key,
            circuit_breaker=_core_platform_breaker,
        )

    async def fetch_entities(self):
        try:
            response = await self._cross_client.call("GET", "/api/entities")
            response.raise_for_status()
            return response.json().get("entities", [])
        except CircuitOpenError:
            return []  # Graceful degradation
```

**Key rules:**
- **Cross-group calls** (e.g., G4 → G1): Use `CrossGroupClient` with shared `CircuitBreaker`
- **Same-group calls** (e.g., G4 → G4): Use direct `httpx` — no circuit breaker needed
- **External APIs** (e.g., HA, OpenAI): Use direct `httpx` or `aiohttp` — not group-managed
- **One breaker per target group**: All clients calling the same group share one breaker instance

**Breaker mapping:**

| Target Group | Breaker Name | Used By |
|-------------|-------------|---------|
| core-platform (G1) | `core-platform` | 6 services across G4 and G5 |
| data-collectors (G2) | `data-collectors` | proactive-agent-service |
| ml-engine (G3) | `ml-engine` | ha-ai-agent-service, device-health-monitor |

For full documentation, see [`shared/resilience/README.md`](../shared/resilience/README.md).

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

### Tier 1: Mission-Critical

| Service | Port | Purpose | Dependencies |
|---------|------|---------|--------------|
| websocket-ingestion | 8001 | HA event ingestion | InfluxDB, data-api |
| admin-api | 8004 | System monitoring | All services |
| data-api | 8006 | Query hub | InfluxDB, SQLite |
| InfluxDB | 8086 | Time-series DB | None |
| health-dashboard | 3000 | React UI | data-api, admin-api |

### Tier 2: Essential Data Integration

| Service | Port | Purpose | Dependencies |
|---------|------|---------|--------------|
| data-retention | 8080 | Data lifecycle management | InfluxDB, SQLite |
| ha-setup-service | 8024 | HA health monitoring | HA, MQTT, Zigbee2MQTT |
| weather-api | 8009 | Weather data | InfluxDB |
| smart-meter-service | 8014 | Power monitoring | InfluxDB |
| energy-correlator | 8017 | Power causality | InfluxDB |

### Tier 3: AI/ML Core

| Service | Port | Purpose | Dependencies |
|---------|------|---------|--------------|
| ai-core-service | 8018 | AI orchestration | openvino, ml-service |
| device-intelligence-service | 8028 | Device capabilities | SQLite |
| openvino-service | 8026 | Embeddings/reranking | PyTorch |
| ml-service | 8025 | Clustering/anomaly | scikit-learn |
| energy-forecasting | 8037 | Energy predictions | InfluxDB |

### Tier 4+: Enhanced/Optional

| Service | Port | Purpose | Dependencies |
|---------|------|---------|--------------|
| air-quality-service | 8012 | AQI data | InfluxDB |
| sports-api | 8005 | Team Tracker | InfluxDB (standalone) |
| carbon-intensity-service | 8010 | Carbon data | InfluxDB |
| electricity-pricing-service | 8011 | Pricing data | InfluxDB |
| calendar-service | 8013 | HA calendar | InfluxDB |
| log-aggregator | 8015 | Centralized logs | Docker |
| automation-miner | 8029 | Community crawling | SQLite |
| automation-linter | 8016 | YAML linting | None (standalone) |
| ai-automation-ui | 3001 | AI automation UI | ai services |

### Deprecated Services

| Service | Port | Status | Replacement |
|---------|------|--------|-------------|
| ~~enrichment-pipeline~~ | ~~8002~~ | **DEPRECATED** | Inline in websocket-ingestion |

For complete service ranking and operational guidelines, see **[Services Ranked by Importance](./SERVICES_RANKED_BY_IMPORTANCE.md)**

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

- **[Service Groups Architecture](../docs/architecture/service-groups.md)** - Canonical reference for the 6-group deployment structure
- **[Services Ranked by Importance](./SERVICES_RANKED_BY_IMPORTANCE.md)** - Complete service tier classification
- **[Deployment Runbook](../docs/deployment/DEPLOYMENT_RUNBOOK.md)** - Per-group deployment procedures
- **[Master Call Tree Index](../implementation/analysis/MASTER_CALL_TREE_INDEX.md)** - All call trees
- **[HA Event Call Tree](../implementation/analysis/HA_EVENT_CALL_TREE.md)** - Detailed event flow
- **[Tech Stack](../docs/architecture/tech-stack.md)** - Technology choices
- **[Source Tree](../docs/architecture/source-tree.md)** - File organization
- **[Event Flow Architecture](../docs/architecture/event-flow-architecture.md)** - Data flow documentation

---

**Quick Tip:** When in doubt about the architecture, check the actual code in `services/websocket-ingestion/src/main.py` - it has clear Epic 31 deprecation comments showing what was removed.

---

**Last Updated:** February 23, 2026
**Epic Context:** Post-Epic 31 (enrichment-pipeline deprecated), Phase 5 (Service Groups + Resilience)
**Service Count:** 50+ microservices across 6 deployment groups and 7 criticality tiers

