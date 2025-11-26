# Device Type Event Frequency Research

**Date:** November 25, 2025  
**Source:** Production HA analysis + [home-assistant-datasets](https://github.com/allenporter/home-assistant-datasets) review

---

## Executive Summary

**Key Finding:** Event frequencies vary dramatically by device type, from 0.19/day (switches) to 278.90/day (images/cameras).

**home-assistant-datasets Repository:** Does NOT specify event frequency rules. It focuses on:
- Synthetic home generation
- Device and area definitions
- Action generation
- **NOT** event state change frequencies over time

**Recommendation:** Use device-type-specific event frequencies based on production data analysis.

---

## Production Data Analysis (7 Days)

### Event Frequencies by Device Type (Domain)

| Device Type | Entities | Events/Day | Events/Entity/Day | Category | Recommended (50%) |
|-------------|----------|-----------|-------------------|----------|-------------------|
| **image** | 3 | 836.7 | **278.90** | VERY HIGH | 139.45 |
| **binary_sensor** | 12 | 875.6 | **72.96** | HIGH | 36.48 |
| **sensor** | 64 | 3,302.4 | **51.60** | HIGH | 25.80 |
| **media_player** | 7 | 385.3 | **55.04** | MEDIUM-HIGH | 27.52 |
| **light** | 42 | 885.6 | **21.09** | MEDIUM | 10.54 |
| **sun** | 1 | 212.0 | **212.00** | VARIABLE | 106.00 |
| **weather** | 1 | 18.6 | **18.57** | VARIABLE | 9.29 |
| **vacuum** | 1 | 15.9 | **15.86** | LOW | 7.93 |
| **scene** | 16 | 122.1 | **7.63** | LOW | 3.82 |
| **select** | 15 | 97.4 | **6.50** | LOW | 3.25 |
| **device_tracker** | 1 | 10.6 | **10.57** | VARIABLE | 5.29 |
| **person** | 1 | 10.4 | **10.43** | VARIABLE | 5.21 |
| **event** | 4 | 12.6 | **3.14** | VARIABLE | 2.00 |
| **remote** | 2 | 6.3 | **3.14** | VARIABLE | 2.00 |
| **automation** | 302 | 752.1 | **2.49** | LOW | 10.00* |
| **update** | 7 | 15.6 | **2.22** | VARIABLE | 2.00 |
| **zone** | 2 | 3.1 | **1.57** | VARIABLE | 2.00 |
| **number** | 6 | 1.7 | **0.29** | VARIABLE | 2.00 |
| **switch** | 12 | 2.3 | **0.19** | VERY LOW | 3.00* |
| **button** | 3 | 0.6 | **0.19** | VARIABLE | 2.00 |

\* Minimum thresholds applied

---

## Device Type Categories

### VERY HIGH Frequency (>100 events/entity/day)
- **image** (cameras): 278.90/day - Continuous image updates
- **sun**: 212.00/day - Position updates throughout day

**Recommendation:** 100-150 events/entity/day for testing

### HIGH Frequency (20-100 events/entity/day)
- **binary_sensor** (motion, door): 72.96/day - Frequent state changes
- **sensor** (temperature, light level): 51.60/day - Periodic updates
- **media_player**: 55.04/day - Playback state changes

**Recommendation:** 20-50 events/entity/day for testing

### MEDIUM Frequency (5-20 events/entity/day)
- **light**: 21.09/day - On/off cycles
- **weather**: 18.57/day - Periodic updates
- **vacuum**: 15.86/day - Status updates

**Recommendation:** 5-15 events/entity/day for testing

### LOW Frequency (<5 events/entity/day)
- **scene**: 7.63/day - Manual activations
- **select**: 6.50/day - Configuration changes
- **device_tracker**: 10.57/day - Location updates
- **person**: 10.43/day - Presence changes
- **automation**: 2.49/day - Trigger events
- **switch**: 0.19/day - Manual toggles
- **button**: 0.19/day - Manual presses

**Recommendation:** 1-5 events/entity/day for testing (minimum 2/day)

---

## home-assistant-datasets Repository Review

### What It Provides
✅ **Synthetic Home Definitions**
- Home descriptions (name, location, type, amenities)
- Area definitions (rooms, spaces)
- Device definitions (device_type, model, manufacturer)
- Device-entity mappings

✅ **Action Generation**
- Device actions that can be performed
- Evaluation tasks for AI models
- Ground truth for automation creation

✅ **Generation Framework**
- LLM-based synthetic data generation
- Notebooks for iterative generation
- Seed data for few-shot examples

### What It Does NOT Provide
❌ **Event Frequency Rules**
- No specifications for events per device type per day
- No state change frequency guidelines
- No time-series event generation rules

❌ **Event Generation Logic**
- Focuses on device definitions, not event patterns
- No guidance on realistic event sequences
- No patterns for co-occurrence (e.g., motion → light)

**Conclusion:** The repository is designed for **device and action evaluation**, not **event pattern testing**. We need to derive event frequencies from production data.

---

## Recommended Event Frequencies for Testing

### Device-Type-Specific Recommendations

Based on production data (50% of production for testing):

```python
DEVICE_TYPE_EVENT_FREQUENCIES = {
    # VERY HIGH (>100/day in production)
    'image': 140,           # Cameras - continuous updates
    'sun': 106,             # Sun position - continuous
    
    # HIGH (20-100/day in production)
    'binary_sensor': 36,    # Motion, door sensors - frequent
    'sensor': 26,           # Temperature, light sensors - periodic
    'media_player': 28,     # Playback state changes
    
    # MEDIUM (5-20/day in production)
    'light': 11,            # On/off cycles
    'weather': 9,           # Periodic updates
    'vacuum': 8,           # Status updates
    'device_tracker': 5,    # Location updates
    'person': 5,           # Presence changes
    
    # LOW (<5/day in production)
    'scene': 4,             # Manual activations
    'select': 3,           # Configuration changes
    'automation': 10,      # Trigger events (minimum)
    'switch': 3,          # Manual toggles (minimum)
    'button': 2,          # Manual presses (minimum)
    'event': 2,           # System events (minimum)
    'remote': 2,          # Remote control (minimum)
    'zone': 2,            # Zone changes (minimum)
    'number': 2,          # Number inputs (minimum)
    'update': 2,          # Update checks (minimum)
    
    # Default for unknown types
    'default': 7.5        # Average across all devices
}
```

### Implementation Strategy

**Option 1: Device-Type-Specific Scaling (Recommended)**
```python
def get_events_per_device_per_day(device_type: str) -> float:
    """Get recommended events per day for device type"""
    frequencies = DEVICE_TYPE_EVENT_FREQUENCIES
    return frequencies.get(device_type, frequencies['default'])
```

**Option 2: Category-Based Scaling**
```python
def get_events_per_device_per_day(device_type: str) -> float:
    """Get recommended events per day based on category"""
    if device_type in ['image', 'sun']:
        return 120  # VERY HIGH
    elif device_type in ['binary_sensor', 'sensor', 'media_player']:
        return 30   # HIGH
    elif device_type in ['light', 'weather', 'vacuum']:
        return 10   # MEDIUM
    else:
        return 3    # LOW (minimum)
```

---

## Comparison: Current vs Recommended

### Current Implementation
- **Fixed**: 7.5 events/device/day (regardless of type)
- **Problem**: Treats all devices the same
- **Impact**: Unrealistic patterns (switches get too many, sensors get too few)

### Recommended Implementation
- **Device-Type-Specific**: Varies by device type
- **Range**: 2-140 events/device/day
- **Benefit**: Realistic event patterns matching production

### Example Impact

**Small Home (14 devices):**
- Current: 14 × 7.5 = 105 events/day
- Recommended: 
  - 2 lights × 11 = 22
  - 3 sensors × 26 = 78
  - 1 binary_sensor × 36 = 36
  - 1 media_player × 28 = 28
  - 7 others × 3 = 21
  - **Total: ~185 events/day** (more realistic)

---

## Top Entities by Event Count (Production)

1. **sensor.vgk_team_tracker**: 694.7/day (sports tracker - very high)
2. **sensor.presence_sensor_fp2_8b8a_light_sensor_light_level**: 538.6/day (light sensor)
3. **binary_sensor.hue_outdoor_motion_sensor_1_motion**: 386.1/day (motion sensor)
4. **sensor.dal_team_tracker**: 386.1/day (sports tracker)
5. **binary_sensor.backyard_motion**: 386.0/day (motion sensor)
6. **image.roborock_downstairs**: 383.9/day (vacuum camera)
7. **sensor.roborock_cleaning_time**: 243.4/day (vacuum sensor)
8. **image.roborock_map_0**: 226.4/day (vacuum map)
9. **image.roborock_upstairs**: 226.4/day (vacuum map)
10. **sensor.slzb_06p7_coordinator_zigbee_chip_temp**: 224.4/day (temperature sensor)

**Insights:**
- Sports trackers generate very high event counts (not typical)
- Motion sensors generate high event counts (expected)
- Vacuum cameras generate very high event counts (expected)
- Light sensors generate high event counts (expected)

---

## Recommendations

### 1. Implement Device-Type-Specific Event Generation

**Update `generate_synthetic_events()` to use device-type-specific frequencies:**

```python
def get_events_per_device_per_day(device_type: str) -> float:
    """Get recommended events per day for device type (50% of production)"""
    frequencies = {
        'image': 140,
        'sun': 106,
        'binary_sensor': 36,
        'sensor': 26,
        'media_player': 28,
        'light': 11,
        'weather': 9,
        'vacuum': 8,
        'device_tracker': 5,
        'person': 5,
        'scene': 4,
        'select': 3,
        'automation': 10,  # Minimum
        'switch': 3,       # Minimum
        'button': 2,       # Minimum
        'default': 7.5
    }
    return frequencies.get(device_type, frequencies['default'])
```

### 2. Weighted Event Distribution

**Distribute events proportionally to device types:**

```python
# Calculate total events per day based on device types
total_events_per_day = sum(
    get_events_per_device_per_day(device.get('device_type', 'default'))
    for device in devices
)
```

### 3. Realistic Event Patterns

**Add realistic sequences:**
- Motion sensor → Light (within 30 seconds)
- Door opens → Alarm (within 2 minutes)
- Thermostat adjusts → Fan (within 1 minute)

---

## home-assistant-datasets Repository Structure

### Key Directories
- **`datasets/`**: Synthetic home, device, and action definitions
- **`generation/`**: Jupyter notebooks for LLM-based generation
- **`home_assistant_datasets/`**: Python library for dataset loading
- **`tests/`**: Evaluation tests for AI models

### Generation Process (from README)
1. Generate home descriptions
2. Generate areas for the home
3. Generate devices in each area
4. Generate device-entity mappings
5. Generate actions that can be performed
6. **NOT**: Generate event state changes over time

**Conclusion:** The repository focuses on **static device definitions** and **action evaluation**, not **dynamic event patterns**. We must derive event frequencies from production data.

---

## Next Steps

1. ✅ **Research Complete**: Production data analyzed, repository reviewed
2. **Implement**: Device-type-specific event generation
3. **Test**: Validate patterns match production
4. **Document**: Update test documentation with device-type frequencies

---

## References

- [home-assistant-datasets Repository](https://github.com/allenporter/home-assistant-datasets)
- Production HA Analysis: `scripts/analyze_device_type_event_frequency.py`
- Home Assistant Events Documentation: [data.home-assistant.io](https://data.home-assistant.io/docs/events/)

