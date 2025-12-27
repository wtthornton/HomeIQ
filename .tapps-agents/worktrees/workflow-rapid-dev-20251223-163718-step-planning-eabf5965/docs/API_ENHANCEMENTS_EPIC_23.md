# API Enhancements - Epic 23

**Last Updated:** January 15, 2025  
**Epic:** Enhanced Event Data Capture  
**Status:** ✅ Complete  

---

## New API Endpoints

### 1. Automation Chain Tracing

**Endpoint:** `GET /api/v1/events/automation-trace/{context_id}`

**Parameters:**
- `context_id` (path, required): Context ID to trace
- `max_depth` (query, optional): Maximum chain depth (default: 10)
- `include_details` (query, optional): Include full event details (default: true)

**Response:**
```json
[
  {
    "depth": 0,
    "context_id": "abc123",
    "context_parent_id": "automation_xyz",
    "timestamp": "2025-01-15T12:00:00Z",
    "entity_id": "light.living_room",
    "event_type": "state_changed",
    "state": "on",
    "old_state": "off"
  },
  {
    "depth": 1,
    "context_id": "def456",
    "context_parent_id": "abc123",
    "timestamp": "2025-01-15T12:00:01Z",
    "entity_id": "fan.living_room",
    "event_type": "state_changed",
    "state": "on"
  }
]
```

**Use Cases:**
- Debug automation chains
- Identify automation loops
- Trace event causality
- Understand automation interactions

---

### 2. Device Reliability Metrics

**Endpoint:** `GET /api/devices/reliability`

**Parameters:**
- `period` (query, optional): Time period (default: "7d", values: "1d", "7d", "30d")
- `group_by` (query, optional): Group by "manufacturer" or "model" (default: "manufacturer")

**Response:**
```json
{
  "period": "7d",
  "group_by": "manufacturer",
  "total_events_analyzed": 150000,
  "total_events_in_period": 200000,
  "metadata_coverage_percentage": 75.0,
  "reliability_data": [
    {
      "manufacturer": "Aeotec",
      "event_count": 45000,
      "percentage": 30.0
    },
    {
      "manufacturer": "Philips",
      "event_count": 38000,
      "percentage": 25.3
    },
    {
      "manufacturer": "Sonoff",
      "event_count": 32000,
      "percentage": 21.3
    }
  ],
  "timestamp": "2025-01-15T12:00:00Z"
}
```

**Use Cases:**
- Identify unreliable manufacturers
- Compare device models
- Plan device upgrades
- Predictive maintenance

---

## Enhanced Query Parameters

### Events Endpoint Enhancements

**Endpoint:** `GET /api/v1/events`

**New Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `device_id` | string | Filter by device ID | ?device_id=aeotec_sensor |
| `area_id` | string | Filter by room/area | ?area_id=living_room |
| `entity_category` | string | Include only category | ?entity_category=diagnostic |
| `exclude_category` | string | Exclude category | ?exclude_category=diagnostic |

**Combined Examples:**

```bash
# Living room power events (spatial analytics)
GET /api/v1/events?area_id=living_room&device_class=power&limit=100

# All sensors on device XYZ (device-level analysis)
GET /api/v1/events?device_id=aeotec_multisensor_6&limit=100

# Clean analytics (exclude diagnostic noise)
GET /api/v1/events?exclude_category=diagnostic&limit=100

# Bedroom temperature, no diagnostic entities
GET /api/v1/events?area_id=bedroom&device_class=temperature&exclude_category=diagnostic
```

---

## New Data Fields in Event Responses

### Context Fields (Epic 23.1)

```json
{
  "context_id": "abc123def456",
  "context_parent_id": "automation_lights_motion",
  "context_user_id": "user_home_owner"
}
```

**When Populated:**
- context_id: Always (100%)
- context_parent_id: Automation-triggered events (~50%)
- context_user_id: User-triggered events (~30%)

---

### Device/Area Fields (Epic 23.2)

```json
{
  "device_id": "aeotec_multisensor_6",
  "area_id": "living_room"
}
```

**When Populated:**
- device_id: Entities with physical devices (~95%)
- area_id: Entities/devices assigned to areas (~80%)

---

### Time Analytics Field (Epic 23.3)

```json
{
  "duration_in_state": 123.45
}
```

**Description:** Seconds the entity was in its previous state

**When Populated:** Events with old_state (~99%)

**Special Cases:**
- First state: null (no previous state)
- Negative values: Clamped to 0 (with warning log)
- >7 days: Stored with warning log

---

### Device Metadata Fields (Epic 23.5)

```json
{
  "device_metadata": {
    "manufacturer": "Aeotec",
    "model": "ZW100 MultiSensor 6",
    "sw_version": "1.10"
  }
}
```

**When Populated:** Events with device_id (~95%)

---

## Backward Compatibility

### All Changes Are Backward Compatible ✅

- ✅ New fields are optional (null if not available)
- ✅ Existing queries work unchanged
- ✅ No breaking changes to API responses
- ✅ No schema migration required
- ✅ Graceful degradation when fields missing

### Migration Notes

**No action required** - The system will:
1. Automatically populate new fields for incoming events
2. Return null for fields on historical events
3. Handle queries with missing fields gracefully

**Historical Data:**
- Events before Epic 23 deployment won't have new fields
- New fields only captured going forward
- No backfill planned (not needed for analytics)

---

## Performance Considerations

### Query Optimization

**Fast Queries (use tags):**
```bash
# ✅ Indexed - Fast
?device_id=xxx
?area_id=xxx
?entity_category=xxx
```

**Slower Queries (use fields):**
```bash
# ⚠️ Not indexed - Slower
duration_in_state > 1800
manufacturer == "Aeotec"
```

**Tip:** For frequent queries on manufacturer/model, consider creating continuous queries or materialized views in InfluxDB.

---

## Rate Limits

No new rate limits introduced. Standard limits apply:
- API requests: No hard limit (reasonable use)
- InfluxDB queries: Limited by InfluxDB performance
- WebSocket connections: 1 per service

---

## Error Codes

### New Error Scenarios

**404 Not Found:**
- `/automation-trace/{context_id}` - Context ID not found in database

**400 Bad Request:**
- Invalid period format (must be: 1d, 7d, 30d)
- Invalid group_by parameter (must be: manufacturer, model)

**500 Internal Server Error:**
- InfluxDB connection failure
- Query execution error

---

## Version History

### Epic 23 (January 2025)
- ✅ Added `/automation-trace` endpoint
- ✅ Added `/devices/reliability` endpoint
- ✅ Added 4 query parameters to `/events` endpoint
- ✅ Added 10 new data fields to event responses

---

**Complete API Documentation:** See OpenAPI/Swagger docs at `http://localhost:8003/docs` (when deployed)

