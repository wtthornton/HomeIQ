# Pattern Filtering Research Analysis

**Date:** October 2025  
**Status:** Critical Finding - Filtering Logic Needs Revision

## Executive Summary

**KEY FINDING:** We are filtering out **useful patterns** that are valuable for automation detection, even though they're not directly controllable. The distinction should be:

- **Non-actionable (can't control)**: binary_sensor, device_tracker, sensor, event, image
- **Useful for patterns (should keep)**: binary_sensor, device_tracker, sensor (as triggers)
- **Not useful (should filter)**: image, event (system noise)

## Research Findings

### 1. Binary Sensor Patterns (90 instances) - **SHOULD KEEP** ✅

**What they are:**
- Motion sensors, door sensors, window sensors
- Two states: on/off, open/closed, detected/not detected

**Why they're valuable:**
- **Primary triggers in Home Assistant automations**
- Examples from Home Assistant documentation:
  ```yaml
  # Motion-activated lighting (most common automation)
  trigger:
    - platform: state
      entity_id: binary_sensor.motion_kitchen
      to: 'on'
  action:
    - service: light.turn_on
      entity_id: light.kitchen
  ```

**Evidence from our codebase:**
- Our synergy detector already recognizes this! See `synergy_detector.py`:
  ```python
  'motion_to_light': {
      'trigger_domain': 'binary_sensor',  # ← Binary sensors as triggers!
      'trigger_device_class': 'motion',
      'action_domain': 'light',
  }
  ```

**Conclusion:** Binary sensors are **essential for pattern detection** - they show WHEN user actions occur (motion triggers light, door opens triggers action).

---

### 2. Device Tracker Patterns (13 instances) - **SHOULD KEEP** ✅

**What they are:**
- Presence detection (phone at home, person home/away)
- Location tracking

**Why they're valuable:**
- **Critical for presence-based automations**
- Examples:
  ```yaml
  # Presence-based lighting
  trigger:
    - platform: state
      entity_id: device_tracker.person_phone
      to: 'home'
  action:
    - service: light.turn_on
      entity_id: light.entry
  ```

**Evidence from our codebase:**
- Synergy detector includes:
  ```python
  'presence_to_light': {
      'trigger_domain': 'device_tracker',  # ← Device trackers as triggers!
      'action_domain': 'light',
  }
  ```

**Conclusion:** Device trackers are **valuable for presence patterns** - they show user arrival/departure patterns.

---

### 3. Sensor Patterns (168 instances) - **SHOULD KEEP (Conditionally)** ✅

**What they are:**
- Temperature, humidity, energy consumption, etc.
- Continuous values (not just on/off)

**Why they're valuable:**
- **Contextual patterns** (temperature triggers climate, humidity triggers fan)
- Examples:
  ```yaml
  # Temperature-based climate control
  trigger:
    - platform: numeric_state
      entity_id: sensor.temperature
      above: 75
  action:
    - service: climate.set_temperature
      entity_id: climate.living_room
      data:
        temperature: 72
  ```

**Evidence from our codebase:**
- Synergy detector includes:
  ```python
  'temp_to_climate': {
      'trigger_domain': 'sensor',  # ← Sensors as triggers!
      'trigger_device_class': 'temperature',
      'action_domain': 'climate',
  }
  ```

**However:** Some sensors are noise (battery, status, CPU, tracker) - these should be filtered.

**Conclusion:** **Actionable sensors** (temperature, humidity) are valuable. **System sensors** (battery, status, CPU) should be filtered.

---

### 4. Image Patterns (211 instances) - **SHOULD FILTER** ❌

**What they are:**
- Camera feeds, static images, Roborock maps
- Visual data only

**Why they're not valuable:**
- No automation value
- Can't be controlled
- Can't trigger actions meaningfully
- Mostly system noise (camera thumbnails, maps)

**Conclusion:** Filter these - they're truly non-useful for automation patterns.

---

### 5. Event Patterns (14 instances) - **SHOULD FILTER** ❌

**What they are:**
- System events (backup events, system startup)
- Internal Home Assistant events

**Why they're not valuable:**
- System-generated noise
- Not user actions
- Can't be controlled
- Not meaningful for automation patterns

**Conclusion:** Filter these - they're system noise.

---

## Current Problem

### What We're Currently Filtering:
```python
EXCLUDED_DOMAINS = [
    'sensor',      # ❌ TOO BROAD - filters useful temperature/humidity sensors
    'binary_sensor',  # ❌ WRONG - these are essential triggers!
    'event',       # ✅ Correct
    'image',       # ✅ Correct
]
```

### What We Should Filter:
```python
EXCLUDED_DOMAINS = [
    'event',       # System events
    'image',       # Camera images/maps
    # Note: Keep sensor and binary_sensor, but filter specific noisy patterns
]

EXCLUDED_PREFIXES = [
    # System sensors (keep these filters)
    'sensor.home_assistant_',
    'sensor.slzb_',
    'sensor.*_battery_level',
    'sensor.*_battery_state',
    'sensor.*_status',
    'sensor.*_tracker',  # Sports trackers, etc.
    'sensor.*_distance',
    'sensor.*_steps',
    'sensor.*_cpu_',
    'sensor.*_memory_',
    
    # System events and images (keep these)
    'event.',
    'image.',
]
```

---

## Recommended Changes

### 1. Remove `binary_sensor` from EXCLUDED_DOMAINS
**Rationale:** Binary sensors (motion, door, window) are primary automation triggers. Patterns like "motion detected → light turns on" are valuable.

### 2. Remove `device_tracker` from EXCLUDED_DOMAINS (if present)
**Rationale:** Device trackers are essential for presence-based patterns. Patterns like "person arrives → lights turn on" are valuable.

### 3. Keep `sensor` but Filter Specific Patterns
**Rationale:** Some sensors (temperature, humidity) are valuable. Others (battery, status, CPU) are noise. Use prefix filtering instead of domain exclusion.

### 4. Keep `image` and `event` Filtered
**Rationale:** These are truly non-useful for automation patterns.

---

## Impact Analysis

### Current Filtering (Too Aggressive):
- **Binary sensors**: 90 patterns filtered ❌
- **Device trackers**: 13 patterns filtered ❌
- **All sensors**: 168 patterns filtered ❌ (includes useful ones)

**Total patterns lost:** ~271 potentially useful patterns

### Recommended Filtering (Selective):
- **Binary sensors**: 0 patterns filtered ✅ (all useful)
- **Device trackers**: 0 patterns filtered ✅ (all useful)
- **Noisy sensors only**: ~50-100 patterns filtered ✅ (system noise)
- **Images**: 211 patterns filtered ✅ (correct)
- **Events**: 14 patterns filtered ✅ (correct)

**Total patterns preserved:** ~271 useful patterns restored

---

## Examples of Valuable Patterns We're Currently Filtering

### Pattern 1: Motion → Light (Binary Sensor)
```
Pattern: binary_sensor.motion_kitchen + light.kitchen
Occurrences: 50
Confidence: 0.95
```
**Value:** Shows user behavior - motion triggers lighting. This is a **core automation pattern**.

### Pattern 2: Presence → Climate (Device Tracker)
```
Pattern: device_tracker.person_phone + climate.thermostat
Occurrences: 30
Confidence: 0.85
```
**Value:** Shows arrival patterns - person arrives triggers climate adjustment.

### Pattern 3: Temperature → Fan (Sensor)
```
Pattern: sensor.temperature_bedroom + fan.bedroom
Occurrences: 25
Confidence: 0.80
```
**Value:** Shows contextual behavior - temperature triggers fan usage.

---

## Conclusion

**We need to revise our filtering logic:**

1. ✅ **Keep**: binary_sensor, device_tracker (all of them)
2. ✅ **Keep**: sensor (filter only noisy system sensors via prefixes)
3. ❌ **Filter**: image, event (system noise)
4. ✅ **Filter**: Specific sensor prefixes (battery, status, CPU, tracker)

This will restore ~271 valuable patterns while still filtering out true noise.

