# Event Flow Architecture

## Overview

This document describes the complete event flow from Home Assistant through the HA-Ingestor system. **Updated November 2025**: State machine pattern implemented for robust connection and processing state management.

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

### Stage 3: Validated Event

**Source:** Enrichment Pipeline's `DataValidationEngine.validate_event()`  
**Format:** Same as Stage 2, with validation metadata

**Validation Checks:**
1. **Entity ID Validation**
   - Must be present at top level
   - Must match pattern: `^[a-z_]+\.[a-z0-9_]+$`
   - Domain should be in known domains list (warning if not)

2. **Event Structure Validation**
   - Must have `event_type` field
   - Must have `entity_id` field at top level
   - State objects must NOT have `entity_id` field

3. **State Object Validation**
   - Must have `state` field (can be empty string, not null)
   - Must have `last_changed` timestamp
   - Must have `last_updated` timestamp
   - May have `attributes` object

4. **Timestamp Validation**
   - Should be valid ISO 8601 format
   - Should be reasonable (not far future/past)

**Validation Result:**
```python
ValidationResult(
    is_valid=True,
    errors=[],  # List of error messages
    warnings=['Unknown domain: custom_sensor'],  # List of warnings
    domain='sensor',
    event_type='state_changed',
    severity='info'
)
```

### Stage 4: Normalized Event

**Source:** Enrichment Pipeline's `DataNormalizer.normalize_event()`  
**Format:** Enhanced with normalization metadata

```json
{
  "event_type": "state_changed",
  "entity_id": "sensor.living_room_temperature",
  "domain": "sensor",
  "normalized_state": 22.5,
  "normalized_unit": "celsius",
  ...
  "_normalized": {
    "timestamp": "2025-10-13T02:30:00.500000+00:00",
    "version": "1.0.0",
    "source": "websocket-ingestion"
  }
}
```

**Normalization Operations:**
- Timestamp normalization (ensure ISO 8601 format)
- State value type conversion
- Unit standardization
- Entity metadata extraction
- Data quality validation

### Stage 3: InfluxDB Point

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

**Decision:** WebSocket Service flattens Home Assistant events before sending to Enrichment Pipeline

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

**Validation Points:**
1. **WebSocket Service**: Basic event type and structure checks
2. **Enrichment Pipeline HTTP Handler**: Request format validation
3. **DataValidationEngine**: Comprehensive event validation
4. **DataNormalizer**: Post-normalization validation

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

```python
# Test event validation
from services.enrichment_pipeline.src.data_validator import DataValidationEngine

validator = DataValidationEngine()
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

result = validator.validate_event(test_event)
print(f"Valid: {result.is_valid}")
print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")
```

## Performance Characteristics

### Throughput
- **WebSocket → Enrichment**: 1000+ events/second
- **Validation**: < 1ms per event
- **Normalization**: < 2ms per event
- **InfluxDB Write**: < 5ms per event
- **Total Latency**: < 10ms end-to-end

### Resource Usage
- **CPU**: < 10% per service under normal load
- **Memory**: < 256MB per service
- **Network**: < 1MB/s between services

### Scaling Considerations
- **Horizontal Scaling**: Multiple enrichment pipeline instances supported
- **Load Balancing**: Round-robin across instances
- **Circuit Breaker**: Prevents cascade failures
- **Batch Processing**: Supports batch writes to InfluxDB

## Monitoring and Observability

### Key Metrics to Monitor
1. **Event Processing Rate**: Events processed per second
2. **Validation Success Rate**: Percentage of events passing validation
3. **Normalization Success Rate**: Percentage of events normalized successfully
4. **InfluxDB Write Success Rate**: Percentage of successful database writes
5. **Circuit Breaker Status**: Open/closed state and failure count
6. **Processing Latency**: P50, P95, P99 latencies

### Health Checks
- **Enrichment Pipeline**: `/health` endpoint shows validation and normalization stats
- **WebSocket Service**: Circuit breaker status indicates enrichment pipeline health
- **InfluxDB**: Connection status in enrichment pipeline health check

### Troubleshooting

#### Events Not Flowing
1. Check WebSocket service circuit breaker status
2. Check enrichment pipeline health endpoint
3. Review enrichment pipeline logs for validation errors
4. Verify InfluxDB connection

#### Validation Failures
1. Check event structure matches flattened format
2. Verify `entity_id` is at top level, not in state objects
3. Check state objects have required fields: `state`, `last_changed`, `last_updated`
4. Review validation error messages in logs

#### Performance Issues
1. Check InfluxDB write latency
2. Monitor validation and normalization duration
3. Check for memory leaks
4. Verify circuit breaker isn't thrashing

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

## References

- [Blueprint Architecture](./BLUEPRINT_ARCHITECTURE.md) - Blueprint-First Architecture details
- [API Documentation](../API_DOCUMENTATION.md) - Complete API reference
- [Data Models](./data-models.md) - Detailed data model specifications
- [Event Validation Fix](../fixes/event-validation-fix-summary.md) - October 2025 validation fix details
- [Event Structure Alignment](../fixes/event-structure-alignment.md) - Event structure design document
- [Home Assistant WebSocket API](https://developers.home-assistant.io/docs/api/websocket) - Official HA API docs

