# Epic 23: Enhanced Event Data Capture - User Guide

**Last Updated:** January 15, 2025  
**Status:** ✅ Production Ready  

---

## Overview

Epic 23 adds powerful analytical capabilities to your Home Assistant data by capturing additional context about events, devices, and timing. This enables automation debugging, room-based analytics, behavioral pattern detection, and device reliability monitoring.

---

## New Features

### 1. 🔍 Automation Chain Tracing

**What It Does:** Shows you which automation triggered a state change and traces the entire chain of events.

**API Endpoint:**
```bash
GET http://localhost:8003/api/v1/events/automation-trace/{context_id}
```

**Use Cases:**
- Debug why your lights turned on unexpectedly
- Trace complex multi-step automations
- Identify automation loops
- Understand automation interactions

**Example:**
```bash
# Find what triggered event abc123
curl "http://localhost:8003/api/v1/events/automation-trace/abc123"

# Response shows the chain:
# Motion sensor detected → Automation triggered → Light turned on → Fan started
```

---

### 2. 📍 Room and Device Analytics

**What It Does:** Links every event to its physical device and room location.

**API Filters:**
```bash
GET http://localhost:8003/api/v1/events
  ?area_id=living_room
  ?device_id=device_abc123
```

**Use Cases:**
- Energy usage per room
- Temperature monitoring by zone
- All sensors on a specific device
- Location-based automation insights

**Examples:**
```bash
# Get all events from the bedroom
curl "http://localhost:8003/api/v1/events?area_id=bedroom&limit=100"

# Get all events from a specific device
curl "http://localhost:8003/api/v1/events?device_id=aeotec_multisensor_6"

# Combine filters: bedroom power usage
curl "http://localhost:8003/api/v1/events?area_id=bedroom&device_class=power"
```

---

### 3. ⏱️ Time-Based Behavioral Analysis

**What It Does:** Calculates how long each sensor/device stayed in its previous state.

**New Field:** `duration_in_state_seconds`

**Use Cases:**
- Motion sensor dwell time (how long was room occupied?)
- Door/window open duration (security monitoring)
- Light on-time tracking (energy efficiency)
- Identify flapping sensors (unstable readings)

**Examples:**

**InfluxDB Query - Find doors left open >30 minutes:**
```flux
from(bucket: "home_assistant_events")
  |> range(start: -7d)
  |> filter(fn: (r) => r["device_class"] == "door")
  |> filter(fn: (r) => r["_field"] == "duration_in_state_seconds")
  |> filter(fn: (r) => r["_value"] > 1800)
```

**InfluxDB Query - Average motion detection time:**
```flux
from(bucket: "home_assistant_events")
  |> range(start: -24h)
  |> filter(fn: (r) => r["entity_id"] == "binary_sensor.motion_living_room")
  |> filter(fn: (r) => r["_field"] == "duration_in_state_seconds")
  |> mean()
```

---

### 4. 🧹 Clean Analytics with Entity Filtering

**What It Does:** Hides diagnostic and config entities to show only real user-facing data.

**API Filters:**
```bash
GET http://localhost:8003/api/v1/events
  ?exclude_category=diagnostic
  ?entity_category=config
```

**Use Cases:**
- Clean event counts (exclude system entities)
- Focus on user-facing sensors
- Debug mode (show only diagnostic entities)
- Configuration review (show only config entities)

**Examples:**
```bash
# Get clean analytics (no diagnostic noise)
curl "http://localhost:8003/api/v1/events?exclude_category=diagnostic&limit=100"

# Show only diagnostic entities (system monitoring)
curl "http://localhost:8003/api/v1/events?entity_category=diagnostic"
```

**Entity Categories:**
- `null` - Regular user-facing entities (sensors, lights, switches)
- `diagnostic` - System diagnostic (CPU, memory, network stats)
- `config` - Configuration entities (settings, options)

---

### 5. 🔧 Device Reliability Tracking

**What It Does:** Analyzes which device manufacturers and models are most/least reliable.

**API Endpoint:**
```bash
GET http://localhost:8003/api/devices/reliability
  ?period=7d
  &group_by=manufacturer
```

**Use Cases:**
- Identify unreliable device brands
- Track firmware version issues
- Plan device upgrades
- Predictive maintenance

**Example:**
```bash
# Device reliability by manufacturer (last 7 days)
curl "http://localhost:8003/api/devices/reliability?period=7d&group_by=manufacturer"

# Response:
{
  "total_events_analyzed": 150000,
  "metadata_coverage_percentage": 75.0,
  "reliability_data": [
    {"manufacturer": "Aeotec", "event_count": 45000, "percentage": 30.0},
    {"manufacturer": "Philips", "event_count": 38000, "percentage": 25.3},
    {"manufacturer": "Sonoff", "event_count": 32000, "percentage": 21.3}
  ]
}

# By model:
curl "http://localhost:8003/api/devices/reliability?period=30d&group_by=model"
```

---

## Common Use Cases

### Automation Debugging

**Scenario:** Your lights turn on randomly and you want to know why.

**Solution:**
1. Check recent events to find the light state change
2. Get the `context_id` from the event
3. Use automation trace API to see the chain
4. Identify which automation or manual action triggered it

```bash
# Step 1: Get recent light events
curl "http://localhost:8003/api/v1/events?entity_id=light.living_room&limit=10"

# Step 2: Copy context_id from suspicious event
# Step 3: Trace the automation chain
curl "http://localhost:8003/api/v1/events/automation-trace/{context_id}"

# Result: Motion sensor → Automation "Lights On Motion" → Light
```

---

### Energy Analysis by Room

**Scenario:** Find out which room uses the most energy.

**Solution:** Query events by area_id and power device_class.

```bash
# Living room energy events
curl "http://localhost:8003/api/v1/events?area_id=living_room&device_class=power&limit=1000"

# Bedroom energy events
curl "http://localhost:8003/api/v1/events?area_id=bedroom&device_class=power&limit=1000"

# Use InfluxDB for aggregation:
from(bucket: "home_assistant_events")
  |> range(start: -30d)
  |> filter(fn: (r) => r["area_id"] == "living_room")
  |> filter(fn: (r) => r["device_class"] == "power")
  |> aggregateWindow(every: 1d, fn: sum)
```

---

### Security Monitoring - Door Open Duration

**Scenario:** Get alerts when doors/windows are left open too long.

**Solution:** Query duration_in_state_seconds for door sensors.

```flux
// Find doors open longer than 10 minutes in last 24h
from(bucket: "home_assistant_events")
  |> range(start: -24h)
  |> filter(fn: (r) => r["device_class"] == "door")
  |> filter(fn: (r) => r["_field"] == "duration_in_state_seconds")
  |> filter(fn: (r) => r["_value"] > 600)
  |> filter(fn: (r) => r["state"] == "off")  // Door closed (duration in open state)
```

---

### Device Reliability Review

**Scenario:** Decide which brand to buy for next sensor.

**Solution:** Check reliability metrics by manufacturer.

```bash
# Get manufacturer reliability (last 30 days)
curl "http://localhost:8003/api/devices/reliability?period=30d&group_by=manufacturer"

# Interpretation:
# - More events = more active/reliable (or more devices)
# - Compare with device count from /api/devices
# - Look for outliers (very few or very many events per device)
```

---

## Data Field Reference

### Quick Field Lookup

| Field | Type | When Populated | Example Value |
|-------|------|----------------|---------------|
| `context_id` | string | Always | "abc123def456" |
| `context_parent_id` | string | Automation-triggered | "automation_xyz" |
| `context_user_id` | string | User-triggered | "user_home_owner" |
| `device_id` | string | Entity has device | "aeotec_multisensor_6" |
| `area_id` | string | Entity/device in area | "living_room" |
| `duration_in_state` | number | Has old_state | 123.45 (seconds) |
| `entity_category` | string | Some entities | "diagnostic" or "config" |
| `manufacturer` | string | Has device | "Aeotec" |
| `model` | string | Has device | "ZW100 MultiSensor 6" |
| `sw_version` | string | Has device | "1.10" |

### Coverage Expectations

- **context_id:** 100% of events
- **context_parent_id:** ~50% (automation-triggered only)
- **device_id:** ~95% (entities with devices)
- **area_id:** ~80% (devices/entities with area assignment)
- **duration_in_state:** ~99% (events with old_state)
- **entity_category:** ~15% (HA limitation)
- **manufacturer/model/sw_version:** ~95% (when device_id present)

---

## InfluxDB Query Examples

### Automation Analysis

```flux
// Events triggered by automations (have parent_id)
from(bucket: "home_assistant_events")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_field"] == "context_parent_id")
  |> count()

// Events triggered by specific automation
from(bucket: "home_assistant_events")
  |> range(start: -7d)
  |> filter(fn: (r) => r["context_parent_id"] == "automation_lights_motion")
```

### Room-Based Queries

```flux
// All events in living room
from(bucket: "home_assistant_events")
  |> range(start: -24h)
  |> filter(fn: (r) => r["area_id"] == "living_room")

// Temperature in bedroom
from(bucket: "home_assistant_events")
  |> range(start: -24h)
  |> filter(fn: (r) => r["area_id"] == "bedroom")
  |> filter(fn: (r) => r["device_class"] == "temperature")
```

### Time-Based Queries

```flux
// Average motion detection duration
from(bucket: "home_assistant_events")
  |> range(start: -7d)
  |> filter(fn: (r) => r["device_class"] == "motion")
  |> filter(fn: (r) => r["_field"] == "duration_in_state_seconds")
  |> mean()

// Lights on for >4 hours
from(bucket: "home_assistant_events")
  |> range(start: -30d)
  |> filter(fn: (r) => r["domain"] == "light")
  |> filter(fn: (r) => r["_field"] == "duration_in_state_seconds")
  |> filter(fn: (r) => r["_value"] > 14400)
```

---

## Troubleshooting

### Q: Why is context_parent_id null for my event?
**A:** context_parent_id is only present for automation-triggered events. Manual state changes (user interaction) don't have a parent context.

### Q: Why doesn't my entity have a device_id?
**A:** Some entities are "virtual" and not tied to physical devices (e.g., template sensors, input_boolean, scenes). This is expected.

### Q: Why is area_id missing?
**A:** Some entities/devices aren't assigned to an area in Home Assistant. You can assign areas in HA Settings → Devices & Services → Click device → Set area.

### Q: Duration values seem very high
**A:** Long durations (days/weeks) can occur for:
- Binary sensors that rarely change (e.g., smoke detector)
- Disabled entities
- Entities with infrequent updates

The system logs warnings for durations >7 days but stores the actual value.

### Q: What's the difference between entity_id filter and device_id filter?
**A:** 
- `entity_id`: One specific entity (e.g., sensor.living_room_temp)
- `device_id`: All entities on a device (e.g., all 4 sensors on a multi-sensor)

---

## Performance Notes

### Lookup Performance
- Device/area lookups: <1ms (in-memory cache)
- Duration calculation: <0.1ms (simple math)
- Total overhead: <5ms per event
- InfluxDB tag queries: Fast (indexed)

### Storage Impact
- Additional storage: +192 bytes per event (~38% increase)
- Annual cost: ~3.7 GB additional (for 50k events/day)
- Cloud storage: <$1/year estimated cost

---

## Best Practices

### Automation Debugging
1. Enable correlation in your automations (context_id is automatic)
2. Use automation trace API to understand event chains
3. Look for circular references (automation loops)

### Spatial Analytics
1. Assign areas to all devices in Home Assistant
2. Use consistent area names (living_room not "Living Room")
3. Query by area_id for room-based insights

### Time Analytics
1. duration_in_state is in seconds (divide by 3600 for hours)
2. First state changes have null duration (expected)
3. Check logs for duration warnings (outliers >7 days)

### Clean Data
1. Use `?exclude_category=diagnostic` by default
2. Only show diagnostic when debugging system issues
3. Config entities are rarely needed in analytics

### Device Reliability
1. Check reliability metrics monthly
2. Compare manufacturers before buying new devices
3. Track firmware versions if issues arise
4. Use with device count for accurate interpretation

---

## Integration with Home Assistant

### Create Automation Based on Duration

```yaml
# Example: Alert if door open >10 minutes
automation:
  - alias: "Door Open Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: 'on'
        for:
          minutes: 10
    action:
      - service: notify.mobile_app
        data:
          message: "Front door has been open for 10 minutes!"
```

Then use duration_in_state field to analyze:
- How often does this happen?
- What's the average duration?
- Which doors are left open most?

---

## Further Reading

- **Epic Specification:** `docs/prd/epic-23-enhanced-event-data-capture.md`
- **API Reference:** `implementation/EPIC_23_QUICK_REFERENCE.md`
- **Implementation Details:** `implementation/EPIC_23_COMPLETE.md`
- **Database Schema:** `docs/architecture/database-schema.md`

---

**Questions?** Check the troubleshooting section or review the comprehensive documentation in the `implementation/` directory.

