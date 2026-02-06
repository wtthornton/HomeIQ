# Event Flow Architecture

## Overview

This document describes the complete event flow from Home Assistant through the HA-Ingestor system. **Updated February 2026**: State machine pattern implemented for robust connection and processing state management. Automation execution architecture includes asynchronous task queue with Huey SQLite backend.

## Service Tiers

The services involved in event flow are classified by criticality:

| Tier | Services | Role |
|------|----------|------|
| **Tier 1** (Critical) | websocket-ingestion, data-api, InfluxDB | Core data pipeline |
| **Tier 2** (Essential) | weather-api, energy-correlator | Data enrichment |
| **Tier 3** (AI/ML) | ai-core-service, pattern-service | Intelligence layer |

For complete service ranking, see **[Services Ranked by Importance](../../services/SERVICES_RANKED_BY_IMPORTANCE.md)**.

## Event Flow Diagram

```
┌─────────────────┐
│  Home Assistant │
│   WebSocket     │
└────────┬────────┘
         │ Raw HA Event
         │ (Nested Structure)
         ↓
┌─────────────────────────┐
│  WebSocket Client       │
│  (HA Connection)        │
└────────┬────────────────┘
         │ Raw HA Event
         ↓
┌─────────────────────────┐
│  EventProcessor         │
│  extract_event_data()   │
└────────┬────────────────┘
         │ Flattened Event
         │ (entity_id at top level)
         ↓
┌─────────────────────────┐
│  InfluxDB Writer        │
│  write_event()          │
└────────┬────────────────┘
         │ InfluxDB Point
         ↓
┌─────────────────────────┐
│  InfluxDB               │
│  (Time Series Storage)  │
└────────┬────────────────┘
         │ Data Available
         ↓
┌─────────────────────────┐
│  External Services       │
│  (Weather, Energy, etc.) │
│  Consume from InfluxDB   │
└─────────────────────────┘
```

## Architecture Change (October 2025)

**Previous Architecture (Deprecated):**
- Events → WebSocket Ingestion → Enrichment Pipeline → InfluxDB
- Monolithic processing with internal weather enrichment

**Current Architecture (Active):**
- Events → WebSocket Ingestion → InfluxDB → External Services
- Clean microservices with external weather integration
- External services consume data from InfluxDB as needed

## Data Transformation Stages

### Stage 1: Home Assistant Raw Event

**Source:** Home Assistant WebSocket API  
**Format:** Nested JSON structure per HA WebSocket API specification

```json
{
  "id": 18,
  "type": "event",
  "event": {
    "event_type": "state_changed",
    "data": {
      "entity_id": "sensor.living_room_temperature",
      "new_state": {
        "entity_id": "sensor.living_room_temperature",
        "state": "22.5",
        "attributes": {
          "unit_of_measurement": "°C",
          "friendly_name": "Living Room Temperature"
        },
        "last_changed": "2025-10-13T02:30:00+00:00",
        "last_updated": "2025-10-13T02:30:00+00:00",
        "context": {
          "id": "abc123",
          "parent_id": null,
          "user_id": null
        }
      },
      "old_state": {
        "entity_id": "sensor.living_room_temperature",
        "state": "22.3",
        "attributes": {
          "unit_of_measurement": "°C",
          "friendly_name": "Living Room Temperature"
        },
        "last_changed": "2025-10-13T02:25:00+00:00",
        "last_updated": "2025-10-13T02:29:55+00:00",
        "context": {
          "id": "xyz789",
          "parent_id": null,
          "user_id": null
        }
      }
    },
    "time_fired": "2025-10-13T02:30:00.123456+00:00",
    "origin": "LOCAL",
    "context": {
      "id": "abc123",
      "parent_id": null,
      "user_id": null
    }
  }
}
```

**Characteristics:**
- Deeply nested structure with `event.data.entity_id`
- `entity_id` is repeated in both the `data` object and within each state object
- Full Home Assistant state objects with all fields

### Stage 2: Flattened Event (After EventProcessor)

**Source:** WebSocket Ingestion Service's `EventProcessor.extract_event_data()`  
**Format:** Flattened JSON structure with top-level fields  
**Note:** Events are processed inline and written directly to InfluxDB (Epic 31)

```json
{
  "event_type": "state_changed",
  "timestamp": "2025-10-13T02:30:00.123456",
  "entity_id": "sensor.living_room_temperature",
  "domain": "sensor",
  "time_fired": "2025-10-13T02:30:00.123456+00:00",
  "origin": "LOCAL",
  "context": {
    "id": "abc123",
    "parent_id": null,
    "user_id": null
  },
  "old_state": {
    "state": "22.3",
    "attributes": {
      "unit_of_measurement": "°C",
      "friendly_name": "Living Room Temperature"
    },
    "last_changed": "2025-10-13T02:25:00+00:00",
    "last_updated": "2025-10-13T02:29:55+00:00"
  },
  "new_state": {
    "state": "22.5",
    "attributes": {
      "unit_of_measurement": "°C",
      "friendly_name": "Living Room Temperature"
    },
    "last_changed": "2025-10-13T02:30:00+00:00",
    "last_updated": "2025-10-13T02:30:00+00:00"
  },
  "state_change": {
    "from": "22.3",
    "to": "22.5",
    "changed": true
  },
  "weather": {
    "temperature": 15.2,
    "humidity": 65,
    "condition": "clear"
  },
  "weather_enriched": true,
  "weather_location": "Las Vegas, NV, US",
  "raw_data": {
    "event_type": "state_changed",
    "data": {
      "entity_id": "sensor.living_room_temperature",
      "old_state": {...},
      "new_state": {...}
    }
  }
}
```

**Characteristics:**
- **entity_id is at the top level** (not in `data` or state objects)
- State objects are **simplified** (no `entity_id` field in them)
- Includes `state_change` summary for quick access
- May include weather enrichment data
- Preserves `raw_data` for audit trail

**Key Transformation:**
```python
# EventProcessor.extract_event_data() transformation:
# BEFORE: event['event']['data']['entity_id']
# AFTER:  event['entity_id']

# BEFORE: event['event']['data']['new_state']['entity_id']
# AFTER:  event['new_state']['state'] (no entity_id in state object)
```

### Stage 3: InfluxDB Point (Epic 31 - Direct Write)

**Source:** WebSocket Ingestion Service's InfluxDB Writer (inline normalization - Epic 31)  
**Format:** InfluxDB Line Protocol

```
home_assistant_events,entity_id=sensor.living_room_temperature,domain=sensor state=22.5,unit="celsius" 1697155800000000000
```

**InfluxDB Schema:**
- **Measurement**: `home_assistant_events`
- **Tags**: `entity_id`, `domain`, `device_class`
- **Fields**: `state`, `unit`, `attributes`, `weather_*`
- **Timestamp**: Nanosecond precision

## Service Communication Patterns

### WebSocket Ingestion → InfluxDB (Direct Write - Epic 31)

**Protocol:** Direct InfluxDB Write (Inline Processing)  
**Method:** Batch writes via InfluxDB Client  
**Timeout:** Configurable via `BATCH_TIMEOUT` (default: 5.0 seconds)  
**Batch Size:** Configurable via `BATCH_SIZE` (default: 100 events)  
**Retry Policy:** Automatic retries with exponential backoff via InfluxDB client

**Current Architecture (Epic 31):**
- All normalization happens inline in websocket-ingestion
- No intermediate HTTP service calls
- Direct writes to InfluxDB for improved latency and reliability

### Error Handling Flow

```
Event Received
     ↓
Validation Failed? → Log error, Continue processing (for now)
     ↓
Normalization Failed? → Return False, Log error
     ↓
InfluxDB Write Failed? → Return False, Log error, Retry
     ↓
Success → Return True
```

## State Machine Pattern (November 2025)

The WebSocket Ingestion service uses formal state machines for connection and processing state management, inspired by Home Assistant's state management patterns.

### Connection State Machine

**Location:** `services/websocket-ingestion/src/state_machine.py`

**States:**
- `DISCONNECTED` - Initial state, not connected
- `CONNECTING` - Establishing WebSocket connection
- `AUTHENTICATING` - Authenticating with Home Assistant
- `CONNECTED` - Active connection
- `RECONNECTING` - Attempting to reconnect after failure
- `FAILED` - Connection failed

**Valid Transitions:**
```python
DISCONNECTED → CONNECTING
CONNECTING → AUTHENTICATING | FAILED
AUTHENTICATING → CONNECTED | FAILED
CONNECTED → RECONNECTING | DISCONNECTED
RECONNECTING → CONNECTING | FAILED | DISCONNECTED
FAILED → RECONNECTING | DISCONNECTED
```

**Integration:**
- `ConnectionManager` uses `ConnectionStateMachine` for all state transitions
- Invalid transitions raise `InvalidStateTransition` exception
- State history tracking for debugging
- Force transitions available for recovery scenarios

### Processing State Machine

**States:**
- `STOPPED` - Not processing events
- `STARTING` - Initializing processing
- `RUNNING` - Actively processing events
- `PAUSED` - Temporarily paused
- `STOPPING` - Shutting down gracefully
- `ERROR` - Error state

**Valid Transitions:**
```python
STOPPED → STARTING
STARTING → RUNNING | ERROR
RUNNING → PAUSED | STOPPING | ERROR
PAUSED → RUNNING | STOPPING | ERROR
STOPPING → STOPPED
ERROR → STARTING | STOPPED | RUNNING
```

**Integration:**
- `BatchProcessor` uses `ProcessingStateMachine` for batch processing state
- `AsyncEventProcessor` uses `ProcessingStateMachine` for async event processing state
- State transitions are validated and logged
- History tracking available via `get_history()`

**Benefits:**
- Prevents invalid state transitions
- Makes state management explicit and testable
- Easier debugging and monitoring
- Clear state transition rules

**Test Coverage:** 15/15 tests passing (100%), 95% code coverage

## Key Design Decisions

### Why Flatten Event Structure?

**Decision:** WebSocket Service flattens Home Assistant events inline before writing to InfluxDB (Epic 31)

**Rationale:**
1. **Reduced Payload Size**: Eliminates redundant `entity_id` fields
2. **Clearer API Contract**: Single source of truth for entity_id
3. **Easier Validation**: Top-level fields are simpler to validate
4. **Better Performance**: Less JSON parsing overhead
5. **Separation of Concerns**: WebSocket service handles HA-specific extraction

**Trade-offs:**
- Pro: Simpler downstream processing
- Pro: More efficient HTTP transport
- Con: Services must agree on flattened structure
- Con: Raw HA event data preserved in `raw_data` for audit

### Why Validate at Multiple Levels?

**Validation Points (Epic 31 - Inline Processing):**
1. **WebSocket Service**: Basic event type and structure checks (inline validation)
2. **EventProcessor**: Comprehensive event validation before normalization
3. **InfluxDB Writer**: Final validation before database write
4. **Post-write validation**: Data integrity checks (optional)

**Rationale:**
- Defense in depth
- Early failure detection
- Clear error messages at each layer
- Different validation concerns at each level

## Migration Notes

### Epic 31 (October 2025) - Enrichment Pipeline Deprecation

**Change:** Enrichment-pipeline service was deprecated and removed

**Reason:** Simplified architecture, reduced latency, fewer failure points

**Solution:** 
- All normalization now happens inline in websocket-ingestion service
- Direct writes to InfluxDB from websocket-ingestion
- External services (weather-api, etc.) write directly to InfluxDB

**Files Modified:**
- `services/websocket-ingestion/src/main.py` - Added inline normalization
- All normalization logic moved from enrichment-pipeline into websocket-ingestion

**Documentation:**
- Updated architecture documentation to reflect direct write pattern
- Updated API documentation with current event flow
- All external services follow standalone pattern (fetch → write → query)

## Testing the Event Flow

### End-to-End Test

```bash
# 1. Check WebSocket service health
curl http://localhost:8001/health

# 2. Verify events are flowing from Home Assistant
# Events are automatically ingested via WebSocket connection

# 3. Verify events in InfluxDB (via data-api)
curl http://localhost:8006/api/v1/events?entity_id=sensor.test&limit=10

# 4. Or query InfluxDB directly
docker exec homeiq-influxdb influx query \
  'from(bucket:"home_assistant_events") 
   |> range(start: -1h) 
   |> filter(fn: (r) => r.entity_id == "sensor.test")'
```

**Note:** Events flow automatically from Home Assistant through websocket-ingestion to InfluxDB. No manual event submission needed for normal operation.

### Validation Test

**Note:** Event validation is now done inline in websocket-ingestion (Epic 31).
Events are validated before being written to InfluxDB.

```python
# Test event structure
test_event = {
    "event_type": "state_changed",
    "entity_id": "sensor.test",
    "domain": "sensor",
    "new_state": {
        "state": "on",
        "attributes": {},
        "last_changed": "2025-10-13T00:00:00Z",
        "last_updated": "2025-10-13T00:00:00Z"
    }
}

# Validation happens inline in websocket-ingestion service
# See: services/websocket-ingestion/src/event_processor.py
```

## Performance Characteristics

### Throughput (Epic 31 - Direct Writes)
- **WebSocket → InfluxDB**: 10,000+ events/second
- **Validation**: < 1ms per event (inline)
- **InfluxDB Batch Write**: 10-30ms per batch
- **Total Latency**: < 50ms end-to-end

### Resource Usage
- **CPU**: < 10% per service under normal load
- **Memory**: < 512MB for websocket-ingestion
- **Network**: Minimal (direct writes to InfluxDB)

### Scaling Considerations
- **Batch Processing**: Configurable batch size (BATCH_SIZE, default: 100)
- **Batch Timeout**: Configurable timeout (BATCH_TIMEOUT, default: 5.0s)
- **Circuit Breaker**: Prevents cascade failures
- **Horizontal Scaling**: Multiple websocket-ingestion instances supported

## Monitoring and Observability

### Key Metrics to Monitor
1. **Event Processing Rate**: Events processed per second
2. **Validation Success Rate**: Percentage of events passing validation
3. **Normalization Success Rate**: Percentage of events normalized successfully
4. **InfluxDB Write Success Rate**: Percentage of successful database writes
5. **Circuit Breaker Status**: Open/closed state and failure count
6. **Processing Latency**: P50, P95, P99 latencies

### Health Checks (Epic 31)
- **WebSocket Ingestion**: `/health` endpoint shows connection status, batch stats, InfluxDB status
- **InfluxDB**: Connection status in websocket-ingestion health check
- **External Services**: Each service has its own `/health` endpoint

### Troubleshooting

#### Events Not Flowing
1. Check websocket-ingestion health: `curl http://localhost:8001/health`
2. Verify HA WebSocket connection is established
3. Check InfluxDB connection status
4. Review websocket-ingestion logs for errors

#### Validation Failures
1. Check event structure matches flattened format
2. Verify `entity_id` is at top level, not in state objects
3. Check state objects have required fields: `state`, `last_changed`, `last_updated`
4. Review validation error messages in websocket-ingestion logs

#### Performance Issues
1. Check InfluxDB write latency (batch processor stats)
2. Monitor batch queue size
3. Check for memory pressure (MAX_MEMORY_MB setting)
4. Verify batch timeout settings (BATCH_TIMEOUT)

## Automation Generation Flow (January 2026)

The event data flowing through this architecture is also analyzed by the AI Pattern Service to detect automation opportunities. See [Blueprint Architecture](./BLUEPRINT_ARCHITECTURE.md) for the complete automation generation flow.

### High-Level Flow

```
Events from InfluxDB
        ↓
AI Pattern Service (Pattern Analysis)
        ↓
Synergy Detection (Cross-device correlations)
        ↓
Blueprint Opportunity Engine (Blueprint matching)
        ↓
Blueprint Deployer (Home Assistant automation creation)
```

### Integration Points

1. **Data API → AI Pattern Service**: Query historical event data for pattern analysis
2. **Blueprint Index Service → AI Pattern Service**: Search indexed community blueprints
3. **AI Pattern Service → Home Assistant**: Deploy automations via REST API

### Key Benefits

- Events are automatically analyzed for automation opportunities
- Community blueprints are matched to user device inventory
- Automations are deployed with auto-filled entity IDs
- Higher success rate than manual automation creation

## Automation Execution Architecture (January 2026)

The `api-automation-edge` service (Port 8025) handles automation execution with an asynchronous task queue pattern using Huey with SQLite backend.

### Execution Flow

**Synchronous Mode (`USE_TASK_QUEUE=false`):**
```
HTTP Request → Validate → Execute → Return Result (blocks)
```

**Asynchronous Mode (`USE_TASK_QUEUE=true`, default):**
```
HTTP Request → Validate → Queue Task → Return Task ID (fast)
                     ↓
              Huey Queue (SQLite)
                     ↓
              Worker Process → Execute → Store Result
                     ↓
              Result Queryable via API
```

### Task Queue Components

1. **Huey SQLite Backend**: Persistent task queue (survives restarts)
   - Database: `./data/automation_queue.db` (persisted in Docker volume)
   - Workers: 4 threads (configurable via `HUEY_WORKERS`)
   - Result Storage: 7 days TTL (configurable via `HUEY_RESULT_TTL`)

2. **Task Prioritization**: Based on automation risk level
   - High risk (security/safety): Priority 10, 10 retries, 60s delay
   - Medium risk (normal): Priority 5, 5 retries, 30s delay
   - Low risk (background): Priority 1, 3 retries, 15s delay

3. **Execution Features**:
   - **Delayed Execution**: `?delay=300` (seconds)
   - **Scheduled Execution**: `?eta=2026-01-20T14:30:00Z` (ISO datetime)
   - **Cron Scheduling**: Periodic tasks for automations with `trigger.type: "schedule"`
   - **Persistent Retry**: Retries survive service restarts

### API Endpoints

**Execution:**
- `POST /api/execute/{spec_id}` - Queue automation (or execute synchronously)
- `GET /api/tasks/{task_id}` - Get task status and result
- `GET /api/tasks` - List tasks (with filters)
- `POST /api/tasks/{task_id}/cancel` - Cancel pending task

**Scheduling:**
- `GET /api/schedules` - List all scheduled automations
- `POST /api/schedules/{spec_id}/enable` - Enable cron schedule
- `POST /api/schedules/{spec_id}/disable` - Disable cron schedule
- `GET /api/schedules/{spec_id}/next-run` - Get next run time

**Health:**
- `GET /health` - Health check with queue status (pending, scheduled, consumer status)

### Integration Points

- **Kill Switch**: Revokes queued tasks when kill switch activated (global/home/spec level)
- **Metrics**: Queue metrics (depth, execution time, success rate) sent to InfluxDB
- **Observability**: Task execution history, retry counts, failure analysis

### Configuration

Environment variables:
- `USE_TASK_QUEUE`: Enable task queue (default: "true")
- `HUEY_DATABASE_PATH`: SQLite database path (default: "./data/automation_queue.db")
- `HUEY_WORKERS`: Number of worker threads (default: 4)
- `HUEY_RESULT_TTL`: Result storage TTL in seconds (default: 604800 = 7 days)
- `HUEY_SCHEDULER_INTERVAL`: Periodic task check interval in seconds (default: 1.0)

### Benefits

- **Non-blocking HTTP**: Fast API responses (tasks execute in background)
- **Persistent Retry**: Tasks retry automatically across service restarts
- **Priority-based Execution**: High-risk automations execute first
- **Scheduled Execution**: Cron-based periodic tasks for time-based automations
- **Task Control**: Cancel pending tasks, query execution history
- **Backward Compatible**: Falls back to synchronous execution if task queue disabled

## References

- [Services Ranked by Importance](../../services/SERVICES_RANKED_BY_IMPORTANCE.md) - Complete service tier classification
- [Services Architecture Quick Reference](../../services/README_ARCHITECTURE_QUICK_REF.md) - Service patterns
- [Blueprint Architecture](./BLUEPRINT_ARCHITECTURE.md) - Blueprint-First Architecture details
- [API Documentation](../API_DOCUMENTATION.md) - Complete API reference
- [Data Models](./data-models.md) - Detailed data model specifications
- [Event Validation Fix](../fixes/event-validation-fix-summary.md) - October 2025 validation fix details
- [Event Structure Alignment](../fixes/event-structure-alignment.md) - Event structure design document
- [Home Assistant WebSocket API](https://developers.home-assistant.io/docs/api/websocket) - Official HA API docs

