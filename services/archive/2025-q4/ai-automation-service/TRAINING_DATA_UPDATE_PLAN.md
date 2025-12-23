# Training Data Update Plan: Event Frequency Research

**Plan to align synthetic home generation with Home Assistant 2025 event frequency research**

---

## Executive Summary

Based on research, typical HA homes generate **1,000-3,000 events/day**. Current implementation generates ~1,364 events/day for a typical 58-device home, which falls within the moderate range. This plan outlines updates to:

1. Add usage level distribution (light/moderate/heavy)
2. Enhance event generation with sampling events
3. Validate and adjust event frequencies
4. Update documentation

---

## Phase 1: Research Integration (Completed)

✅ Research document created: `EVENT_FREQUENCY_RESEARCH.md`
✅ Current implementation analyzed
✅ Gap analysis completed
✅ Recommendations documented

**Status:** Complete

---

## Phase 2: Usage Level Distribution

### 2.1 Add Usage Level Model

**File:** `services/ai-automation-service/src/training/synthetic_home_generator.py`

**Add:**

```python
USAGE_LEVEL_DISTRIBUTION = {
    'light': {
        'percentage': 10,        # 10% of homes
        'events_per_day_range': (200, 500),
        'device_count_multiplier': 0.4,  # 40% of normal device count
        'automation_density': 0.3,
        'description': 'Light automation, basic sensors'
    },
    'moderate': {
        'percentage': 70,        # 70% of homes (default)
        'events_per_day_range': (1000, 2000),
        'device_count_multiplier': 1.0,  # Normal device count
        'automation_density': 1.0,
        'description': 'Standard automation, moderate device count'
    },
    'heavy': {
        'percentage': 20,        # 20% of homes
        'events_per_day_range': (2000, 3000),
        'device_count_multiplier': 1.5,  # 150% of normal device count
        'automation_density': 1.5,
        'description': 'Fully instrumented, automation-heavy'
    }
}
```

**Estimated Time:** 2 hours

---

### 2.2 Update Home Generation to Include Usage Level

**File:** `services/ai-automation-service/src/training/synthetic_home_generator.py`

**Changes:**
- Add `usage_level` parameter to `generate_homes()` method
- Assign usage level based on distribution
- Store usage level in home metadata
- Adjust device counts based on usage level multiplier

**Estimated Time:** 3 hours

---

## Phase 3: Event Generation Enhancements

### 3.1 Add Sampling Event Support

**File:** `services/ai-automation-service/src/training/synthetic_event_generator.py`

**Add sampling events for:**
- Temperature sensors: Every 5-15 minutes (96-288 samples/day)
- Power monitors: Every 5-15 minutes (96-288 samples/day)
- Energy monitors: Every 15 minutes (96 samples/day)
- Humidity sensors: Every 15 minutes (96 samples/day)

**Implementation:**
```python
SAMPLING_INTERVALS = {
    'sensor.temperature': 15,  # minutes
    'sensor.humidity': 15,
    'sensor.power': 5,
    'sensor.energy': 15,
    'sensor.battery': 60,  # hourly
}
```

**Estimated Time:** 4 hours

---

### 3.2 Add Usage Level Multiplier to Event Generation

**File:** `services/ai-automation-service/src/training/synthetic_event_generator.py`

**Changes:**
- Accept `usage_level` parameter
- Apply multiplier to event frequencies based on usage level
- Adjust automation trigger frequency

**Example:**
```python
def generate_events(
    self,
    devices: list[dict[str, Any]],
    days: int = 7,
    usage_level: str = 'moderate',
    ...
):
    # Get usage level multiplier
    usage_config = USAGE_LEVELS.get(usage_level, USAGE_LEVELS['moderate'])
    multiplier = usage_config['automation_density']
    
    # Apply to event frequencies
    adjusted_frequencies = {
        device_type: base_freq * multiplier
        for device_type, base_freq in EVENT_FREQUENCIES.items()
    }
```

**Estimated Time:** 3 hours

---

## Phase 4: Validation and Testing

### 4.1 Create Validation Script

**File:** `services/ai-automation-service/scripts/validate_event_volumes.py`

**Checks:**
- Total events per day per home
- Events per device type
- Comparison to research targets
- Usage level distribution

**Output:**
- Validation report
- Event volume statistics
- Recommendations for adjustments

**Estimated Time:** 4 hours

---

### 4.2 Test with Sample Homes

**Test Cases:**
1. Light usage home (20-30 devices, 200-500 events/day)
2. Moderate usage home (58 devices, 1,000-2,000 events/day)
3. Heavy automation home (80-100 devices, 2,000-3,000 events/day)

**Validation Criteria:**
- Events/day within research range
- Device-type frequencies match expectations
- Sampling events present for sensors

**Estimated Time:** 3 hours

---

## Phase 5: Documentation Updates

### 5.1 Update Generation Script Help

**File:** `services/ai-automation-service/scripts/generate_synthetic_homes.py`

**Add:**
- `--usage-level` parameter (light/moderate/heavy)
- Usage level documentation
- Event volume estimates

**Estimated Time:** 1 hour

---

### 5.2 Update Documentation

**Files to Update:**
- `docs/TEST_DATA_GENERATION_GUIDE.md`
- `DEVICE_TYPE_BREAKDOWN.md`
- Create `EVENT_FREQUENCY_GUIDE.md`

**Content:**
- Event volume by usage level
- How to generate different usage levels
- Expected event counts

**Estimated Time:** 2 hours

---

## Phase 6: Integration Testing

### 6.1 Generate Test Dataset

**Generate:**
- 10 light usage homes (30 days)
- 10 moderate usage homes (30 days)
- 10 heavy automation homes (30 days)

**Validate:**
- Event volumes match targets
- Device counts are correct
- No generation errors

**Estimated Time:** 2 hours (generation) + 1 hour (validation)

---

### 6.2 Update 400-Home Generation

**Update batch script:**
- Apply usage level distribution (10%/70%/20%)
- Verify event volumes
- Test generation

**Estimated Time:** 2 hours

---

## Implementation Timeline

| Phase | Task | Hours | Priority |
|-------|------|-------|----------|
| **Phase 1** | Research Integration | ✅ Complete | P0 |
| **Phase 2** | Usage Level Distribution | 5 hours | P1 |
| **Phase 3** | Event Generation Enhancements | 7 hours | P1 |
| **Phase 4** | Validation and Testing | 7 hours | P1 |
| **Phase 5** | Documentation Updates | 3 hours | P2 |
| **Phase 6** | Integration Testing | 5 hours | P1 |
| **TOTAL** | | **~27 hours** | |

---

## Priority Ranking

### P0 (Critical - Must Have)
- ✅ Research integration (complete)

### P1 (High Priority)
- Usage level distribution
- Event generation enhancements
- Validation scripts
- Integration testing

### P2 (Medium Priority)
- Documentation updates
- Usage level parameter in CLI

---

## Expected Outcomes

### After Implementation

1. **Usage Level Distribution:**
   - 10% light usage homes (200-500 events/day)
   - 70% moderate usage homes (1,000-2,000 events/day)
   - 20% heavy automation homes (2,000-3,000 events/day)

2. **Event Generation:**
   - Sampling events for sensors
   - Usage-level-adjusted frequencies
   - Validation against research targets

3. **Documentation:**
   - Clear event volume expectations
   - Usage level guides
   - Validation reports

### For 400 Homes, 30 Days

**Current (before update):**
- ~1,364 events/day/home average
- ~16.4M events total (400 homes × 30 days)

**After Update:**
- **Light (40 homes):** 200-500 events/day = 240K-600K events (30d)
- **Moderate (280 homes):** 1,000-2,000 events/day = 8.4M-16.8M events (30d)
- **Heavy (80 homes):** 2,000-3,000 events/day = 4.8M-7.2M events (30d)
- **Total:** ~13.4M - 24.6M events (30 days)

**Range matches research targets!**

---

## Risk Assessment

### Low Risk
- Adding usage level parameter (non-breaking)
- Documentation updates

### Medium Risk
- Changing event generation logic (may affect existing datasets)
- Sampling event implementation (complexity)

### Mitigation
- Make usage level optional (default to 'moderate')
- Maintain backward compatibility
- Test thoroughly before deploying
- Generate new datasets rather than modifying existing

---

## Success Criteria

✅ Usage levels implemented and working
✅ Event volumes match research targets (1,000-3,000/day range)
✅ Validation script confirms volumes
✅ Documentation updated
✅ 400-home generation uses distribution
✅ No breaking changes to existing functionality

---

**Last Updated:** December 2, 2025  
**Status:** Plan ready for implementation

