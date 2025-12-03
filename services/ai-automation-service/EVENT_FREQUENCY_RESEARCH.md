# Event Frequency Research: Home Assistant 2025

**Based on research into typical Home Assistant household event volumes**

---

## Research Summary

### Key Finding

There is **no official published "events per day"** number for typical Home Assistant homes. However, based on reasonable assumptions and device counts, a typical moderately automated HA home generates:

**1,000 - 3,000 events per day**

---

## Event Volume Estimates

### Research-Based Estimates

| Usage Level | Events/Day | Description |
|-------------|------------|-------------|
| **Light Usage** | 200-500 | Fewer devices, minimal automation |
| **Moderate Usage** | 1,000-2,000 | Standard automation, moderate device count |
| **Heavy Automation** | 2,000-3,000+ | Fully instrumented, automation-heavy |

### Baseline Recommendations

- **1,000 events/day** (~40 per hour) = baseline for "light-to-moderate" smart house
- **2,000-3,000 events/day** = baseline for "fully instrumented, automation-heavy" houses

---

## Factors Affecting Event Volume

### 1. Sampling vs. State-Change Logging

Many events are **periodic sampling**, not user-driven:
- Temperature sensors: Every 5-15 minutes
- Power monitors: Every 5-15 minutes
- Statistics integration: Samples every 5 minutes

### 2. Device Count

More devices → more events:
- 45-70 devices = typical HA home
- Each device generates events at different frequencies

### 3. Automation Density

More automations → more triggers → more actuator events:
- Presence-driven automation
- Time-based automation
- Condition-based automation

### 4. Configuration Settings

- Polling frequency
- Sensor reporting intervals
- Whether every change is logged
- Statistics integration settings

---

## Estimation Model (Typical HA Home)

### Assumptions

For a **typical HA home with 58 devices**:

**Active Sensors/Actuators (~25 devices):**
- Motion sensors, lights, switches, contact sensors
- Average: **5-10 events per day** per device
- Total: 25 × 7.5 = **~190 events/day**

**Statistical Sampling Devices (~10 devices):**
- Temperature, power, energy monitors
- Sample every 15 minutes = 96 samples/day
- Total: 10 × 96 = **~960 events/day**

**High-Frequency Devices (~15 devices):**
- Binary sensors (motion), media players, power sensors
- Average: **30-50 events/day** per device
- Total: 15 × 40 = **~600 events/day**

**Low-Frequency Devices (~8 devices):**
- Locks, switches, scenes, automations
- Average: **2-5 events/day** per device
- Total: 8 × 3 = **~24 events/day**

**Total Estimate: ~1,774 events/day** (moderate automation)

---

## Current Implementation Analysis

### Current Event Frequencies (Per Device Type)

| Device Type | Events/Day | Category |
|-------------|------------|----------|
| `image` (cameras) | 140 | Very High |
| `sun` | 106 | Very High |
| `binary_sensor` | 36 | High |
| `sensor` | 26 | High |
| `media_player` | 28 | High |
| `light` | 11 | Medium |
| `vacuum` | 8 | Medium |
| `weather` | 9 | Medium |
| `automation` | 10 | Medium |
| `switch` | 3 | Low |
| `climate` | 3 | Low |
| `lock` | 2 | Low |
| `scene` | 4 | Low |

### Current Generation for Typical Home (58 devices)

**Based on research device distribution:**

| Category | Device Count | Avg Events/Device/Day | Total Events/Day |
|----------|--------------|----------------------|------------------|
| Lighting (22) | 22 | 11 | 242 |
| Sensors (15) | 15 | 26-36* | 465 |
| Media/AV (7) | 7 | 28 | 196 |
| Energy/Power (6) | 6 | 26 | 156 |
| Security (4) | 4 | 36-140* | 144 |
| Presence (3) | 3 | 36 | 108 |
| Climate (3) | 3 | 3 | 9 |
| Appliances (2) | 2 | 8 | 16 |
| Networking (1) | 1 | 5 | 5 |
| Misc (3) | 3 | 7.5 | 23 |
| **TOTAL** | **58** | **~24** | **~1,364** |

*Sensors vary: motion (36), temp/power (26)
*Security varies: cameras (140), motion (36)

**Current Estimated Total: ~1,364 events/day**

This falls within the **moderate usage range (1,000-2,000 events/day)**.

---

## Validation Against Research

### Comparison

| Metric | Research Target | Current Implementation | Status |
|--------|----------------|----------------------|--------|
| Moderate home | 1,000-2,000/day | ~1,364/day | ✅ **Within range** |
| Heavy automation | 2,000-3,000/day | Can scale to ~2,500/day* | ✅ **Achievable** |
| Light usage | 200-500/day | Can scale down to ~400/day* | ✅ **Achievable** |

*With device count adjustments

---

## Distribution Models (Recommended)

### Light Usage (200-500 events/day)

**Device Profile:**
- 20-30 devices
- Minimal automation
- Basic sensors
- Few high-frequency devices

**Characteristics:**
- Fewer motion sensors
- Basic lighting
- Minimal media devices
- No camera systems

### Moderate Usage (1,000-2,000 events/day) ← **Current Default**

**Device Profile:**
- 45-70 devices (58 average)
- Standard automation
- Moderate sensor density
- Balanced device mix

**Characteristics:**
- Standard motion sensors
- Full lighting setup
- Media devices
- Basic security

### Heavy Automation (2,000-3,000+ events/day)

**Device Profile:**
- 70-100+ devices
- Automation-heavy
- High sensor density
- Multiple cameras

**Characteristics:**
- Many motion sensors
- Extensive lighting
- Multiple media zones
- Full security system
- Energy monitoring
- Multiple cameras (high frequency)

---

## Recommended Updates

### 1. Create Usage Level Distribution

Add usage level parameter to generation:

```python
USAGE_LEVELS = {
    'light': {
        'events_per_day_range': (200, 500),
        'device_count_range': (20, 30),
        'automation_density': 0.3,
        'multiplier': 0.4
    },
    'moderate': {
        'events_per_day_range': (1000, 2000),
        'device_count_range': (45, 70),
        'automation_density': 1.0,
        'multiplier': 1.0
    },
    'heavy': {
        'events_per_day_range': (2000, 3000),
        'device_count_range': (70, 100),
        'automation_density': 1.5,
        'multiplier': 1.5
    }
}
```

### 2. Add Sampling Events

Currently missing explicit sampling events:
- Temperature sensors: Every 5-15 minutes
- Power monitors: Every 5-15 minutes
- Statistics integration: Every 5 minutes

**Recommendation:** Add periodic sampling events to sensor devices.

### 3. Adjust Event Frequencies

Some adjustments based on research:

| Device Type | Current | Research-Based | Action |
|-------------|---------|----------------|--------|
| Motion sensors | 36/day | 30-50/day | ✅ Keep |
| Temperature sensors | 26/day | ~96/day (sampling) | ⚠️ Add sampling |
| Power sensors | 26/day | ~96/day (sampling) | ⚠️ Add sampling |
| Lights | 11/day | 5-20/day | ✅ Keep (within range) |
| Media players | 28/day | 30-50/day | ✅ Keep |

### 4. Add Usage Level Parameter

Allow generation with different usage levels:

```python
generate_synthetic_homes(
    count=400,
    days=30,
    usage_level='moderate'  # 'light', 'moderate', 'heavy'
)
```

---

## Event Volume Targets (30 Days)

### Light Usage Homes (10% of dataset)

- **Events/Day:** 200-500
- **Events/30 Days:** 6,000-15,000 per home
- **Total (40 homes):** 240,000-600,000 events

### Moderate Usage Homes (70% of dataset) ← **Default**

- **Events/Day:** 1,000-2,000
- **Events/30 Days:** 30,000-60,000 per home
- **Total (280 homes):** 8,400,000-16,800,000 events

### Heavy Automation Homes (20% of dataset)

- **Events/Day:** 2,000-3,000
- **Events/30 Days:** 60,000-90,000 per home
- **Total (80 homes):** 4,800,000-7,200,000 events

### Total (400 Homes, 30 Days)

- **Total Events:** ~13,440,000 - 24,600,000 events
- **Average:** ~33,600 - 61,500 events per home (30 days)

---

## Key Insights

### 1. Current Implementation is Reasonable

- ✅ Falls within moderate usage range (1,364/day)
- ✅ Can scale up/down with device counts
- ✅ Device-type-specific frequencies are realistic

### 2. Missing Components

- ⚠️ Explicit sampling events (5-15 min intervals)
- ⚠️ Usage level distribution (light/moderate/heavy)
- ⚠️ Automation density factors

### 3. Validation Needed

- Verify actual generated events match targets
- Test with different device distributions
- Validate against real HA home data (if available)

---

**Last Updated:** December 2, 2025  
**Status:** Research applied, implementation plan created

