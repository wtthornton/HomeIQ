# Event Volume Summary: 400 Homes with 30 Days of Data

**Quick reference for event volumes based on Home Assistant 2025 research**

---

## Event Volume Ranges (Research-Based)

| Usage Level | Events/Day | Events/30 Days | % of Homes |
|-------------|------------|----------------|------------|
| **Light Usage** | 200-500 | 6,000-15,000 | 10% (40 homes) |
| **Moderate Usage** | 1,000-2,000 | 30,000-60,000 | 70% (280 homes) |
| **Heavy Automation** | 2,000-3,000 | 60,000-90,000 | 20% (80 homes) |

---

## Current Implementation Status

### Typical Home (58 devices, moderate usage)

**Current Generation:** ~1,364 events/day

**Breakdown:**
- Lighting (22 devices): 242 events/day
- Sensors (15 devices): 465 events/day
- Media/AV (7 devices): 196 events/day
- Energy/Power (6 devices): 156 events/day
- Security (4 devices): 144 events/day
- Other (4 devices): 161 events/day

**Status:** ✅ **Within moderate range (1,000-2,000 events/day)**

---

## Total Event Volume (400 Homes, 30 Days)

### Current Implementation

- **Average:** ~1,364 events/day/home
- **Total (400 homes × 30 days):** ~16.4 million events

### After Usage Level Distribution

| Usage Level | Homes | Events/Day Range | Events/30 Days Range | Total Events (30d) |
|-------------|-------|------------------|----------------------|-------------------|
| Light | 40 | 200-500 | 6K-15K | 240K-600K |
| Moderate | 280 | 1,000-2,000 | 30K-60K | 8.4M-16.8M |
| Heavy | 80 | 2,000-3,000 | 60K-90K | 4.8M-7.2M |
| **TOTAL** | **400** | **1,200-2,500 avg** | **36K-75K avg** | **13.4M-24.6M** |

**Range:** 13.4 million - 24.6 million events (30 days)

---

## Key Insights

### 1. Current Implementation is Accurate
- ✅ Generates ~1,364 events/day for typical home
- ✅ Falls within research moderate range (1,000-2,000/day)
- ✅ Device-type-specific frequencies are realistic

### 2. Research Alignment
- ✅ Research: 1,000-3,000 events/day for moderate-heavy homes
- ✅ Current: ~1,364 events/day (within range)
- ✅ Can scale up/down based on usage level

### 3. Distribution Needed
- ⚠️ Currently all homes are moderate usage
- ⚠️ Need light/heavy distribution (10%/70%/20%)
- ⚠️ Usage level parameter not yet implemented

---

## Event Generation by Device Type

### High-Frequency Devices

| Device Type | Events/Day | % of Total Events |
|-------------|------------|-------------------|
| Motion sensors | 36 | ~30% |
| Power sensors | 26-96* | ~15% |
| Media players | 28 | ~14% |
| Temperature sensors | 26-96* | ~15% |
| Lights | 11 | ~16% |

*Power/temp: 26 (state changes) + 96 (sampling) = 122 events/day with sampling

### Medium-Frequency Devices

| Device Type | Events/Day | % of Total Events |
|-------------|------------|-------------------|
| Vacuum | 8 | ~1% |
| Weather | 9 | ~1% |
| Automations | 10 | ~2% |

### Low-Frequency Devices

| Device Type | Events/Day | % of Total Events |
|-------------|------------|-------------------|
| Switches | 3 | ~1% |
| Locks | 2 | <1% |
| Scenes | 4 | <1% |

---

## Recommendations

### Immediate Actions
1. ✅ Research integrated into documentation
2. ⏳ Implement usage level distribution
3. ⏳ Add sampling events for sensors
4. ⏳ Create validation script

### Future Enhancements
1. Add usage level parameter to generation script
2. Validate against real HA home data
3. Adjust frequencies based on usage level
4. Add automation density factors

---

**See:**
- `EVENT_FREQUENCY_RESEARCH.md` - Detailed research and analysis
- `TRAINING_DATA_UPDATE_PLAN.md` - Implementation plan
- `DEVICE_TYPE_BREAKDOWN.md` - Device distribution details

---

**Last Updated:** December 2, 2025

