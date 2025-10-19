# Event Flow Architecture

## Overview

This document describes the complete event flow from Home Assistant through the HA-Ingestor system, including data transformations at each stage.

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
│  HTTP Client            │
│  POST /events           │
└────────┬────────────────┘
         │ Flattened Event
         ↓
┌─────────────────────────┐
│  Enrichment Pipeline    │
│  events_handler()       │
└────────┬────────────────┘
         │ Flattened Event
         ↓
┌─────────────────────────┐
│  DataValidationEngine   │
│  validate_event()       │
└────────┬────────────────┘
         │ Validated Event
         ↓
┌─────────────────────────┐
│  DataNormalizer         │
│  normalize_event()      │
└────────┬────────────────┘
         │ Normalized Event
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
└─────────────────────────┘
```

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
**Transport:** HTTP POST to `http://enrichment-pipeline:8002/events`

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
    "source": "enrichment-pipeline"
  }
}
```

**Normalization Operations:**
- Timestamp normalization (ensure ISO 8601 format)
- State value type conversion
- Unit standardization
- Entity metadata extraction
- Data quality validation

### Stage 5: InfluxDB Point

**Source:** Enrichment Pipeline's InfluxDB Writer  
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

### WebSocket → Enrichment Pipeline

**Protocol:** HTTP POST  
**Endpoint:** `http://enrichment-pipeline:8002/events`  
**Content-Type:** `application/json`  
**Timeout:** 5 seconds  
**Retry Policy:** 2 retries with exponential backoff  
**Circuit Breaker:** Opens after 5 consecutive failures, resets after 30 seconds

**Success Response:**
```json
{
  "status": "success",
  "event_id": "evt_abc123"
}
```

**Failure Response:**
```json
{
  "status": "failed",
  "reason": "processing_failed"
}
```

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

### October 2025 Fix

**Problem:** Enrichment Pipeline validator expected `entity_id` in state objects

**Solution:** Updated validator to:
1. Extract `entity_id` from top level, not `event['data']['entity_id']`
2. Remove `entity_id` from required state object fields
3. Validate `entity_id` only at event level

**Files Modified:**
- `services/enrichment-pipeline/src/data_validator.py`
- `services/enrichment-pipeline/src/data_normalizer.py`
- `services/enrichment-pipeline/src/main.py`

**Documentation:**
- Added this architecture document
- Updated API documentation with correct event structure
- Updated data models with ProcessedEvent specification

## Testing the Event Flow

### End-to-End Test

```bash
# 1. Check WebSocket service health
curl http://localhost:8001/health

# 2. Check Enrichment Pipeline health
curl http://localhost:8002/health

# 3. Send test event to Enrichment Pipeline
curl -X POST http://localhost:8002/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "state_changed",
    "entity_id": "sensor.test",
    "domain": "sensor",
    "new_state": {
      "state": "100",
      "attributes": {},
      "last_changed": "2025-10-13T00:00:00Z",
      "last_updated": "2025-10-13T00:00:00Z"
    }
  }'

# 4. Verify event in InfluxDB
docker exec homeiq-influxdb influx query \
  'from(bucket:"home_assistant_events") 
   |> range(start: -1h) 
   |> filter(fn: (r) => r.entity_id == "sensor.test")'
```

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

## References

- [API Documentation](../API_DOCUMENTATION.md) - Complete API reference
- [Data Models](./data-models.md) - Detailed data model specifications
- [Event Validation Fix](../fixes/event-validation-fix-summary.md) - October 2025 validation fix details
- [Event Structure Alignment](../fixes/event-structure-alignment.md) - Event structure design document
- [Home Assistant WebSocket API](https://developers.home-assistant.io/docs/api/websocket) - Official HA API docs

