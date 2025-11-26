# Production Home Assistant Event Analysis

**Date:** November 25, 2025  
**Analysis Period:** 7 days (2025-11-18 to 2025-11-25)  
**Purpose:** Compare production HA event patterns with test dataset configuration

---

## Executive Summary

**Key Finding:** Production HA generates **150x more events** than current test configuration.

- **Production**: 7,534 events/day, 502 entities, 15 events/entity/day
- **Test**: 50 events/day, 14 entities, 3.5 events/entity/day

**Recommendation:** Increase test events to **100-150 events/day** (not 7,534) for realistic pattern detection while maintaining test speed.

---

## Production Statistics

### Event Volume
- **Total Events (7 days)**: 52,736
- **Events per Day**: 7,533.7
- **Events per Hour**: 313.9
- **Events per Minute**: 5.23

### Device/Entity Statistics
- **Unique Entities**: 502
- **Events per Entity/Day**: 15.01

### Top Entities (by event count)
1. `sensor.vgk_team_tracker` - 4,862 events (9.22%)
2. `sensor.presence_sensor_fp2_8b8a_light_sensor_light_level` - 3,767 (7.14%)
3. `sensor.dal_team_tracker` - 2,702 (5.12%)
4. `image.roborock_downstairs` - 2,685 (5.09%)
5. `binary_sensor.hue_outdoor_motion_sensor_1_motion` - 2,666 (5.06%)

### Domain Distribution
- **sensor**: 23,080 events (43.77%)
- **light**: 6,106 events (11.58%)
- **binary_sensor**: 6,048 events (11.47%)
- **image**: 5,851 events (11.09%)
- **automation**: 5,265 events (9.98%)

### Hourly Distribution
- Peak hours: 3:00 AM (4,147 events), 10:00 AM (3,518 events)
- Low hours: 4:00 PM (1,427 events), 8:00 PM (1,418 events)
- **Pattern**: Higher activity during night/early morning (automated routines)

---

## Comparison: Production vs Test

| Metric | Production | Test (Current) | Ratio |
|--------|-----------|----------------|-------|
| **Events per Day** | 7,533.7 | 50 | **150.7x** |
| **Total (7 days)** | 52,736 | 350 | **150.7x** |
| **Unique Entities** | 502 | 14 | **35.9x** |
| **Events per Entity/Day** | 15.01 | 3.57 | **4.2x** |

---

## Analysis

### Why Production Has More Events

1. **More Devices**
   - Production: 502 entities
   - Test: 14 entities (home1-us)
   - **35.9x more entities**

2. **High-Frequency Sensors**
   - Sports trackers (VGK, DAL teams) - 7,564 events (14.3%)
   - Light sensors - 3,767 events (7.1%)
   - Motion sensors - 2,666 events (5.1%)
   - Roborock images - 5,851 events (11.1%)

3. **Automated Systems**
   - Roborock vacuum updates
   - Hue motion sensors
   - Time-based automations
   - System monitoring (CPU, temperature)

4. **Real Usage Patterns**
   - Actual user interactions
   - Scheduled automations
   - Device state changes
   - System updates

### Why Test Shouldn't Match Production Exactly

1. **Test Purpose**
   - Validate pattern detection algorithms
   - Not replicate exact production volume
   - Focus on realistic relationships, not volume

2. **Test Speed**
   - 7,534 events/day × 37 homes = 279,000 events/day
   - Would take hours to generate and process
   - Slows down CI/CD pipelines

3. **Test Focus**
   - Pattern detection needs co-occurrences, not volume
   - 100-150 events/day is sufficient for pattern detection
   - More important: realistic patterns (motion → light)

---

## Recommendations

### ✅ Recommended Test Configuration

**For Individual Home Testing:**
```python
days = 7
events_per_day = 100-150  # Increased from 50
# Total: 700-1,050 events per home
```

**Rationale:**
- **10-15 events/entity/day** (matches production ratio)
- **Sufficient for pattern detection** (min_support=5)
- **Fast execution** (~35 seconds for all 37 homes)
- **Realistic density** without excessive volume

### ⚠️ Current Test Issues

1. **Too Low Event Density**
   - 3.5 events/entity/day is sparse
   - May not generate enough co-occurrences
   - Pattern detection may return 0 patterns

2. **Random Event Generation**
   - No realistic patterns (motion → light)
   - Doesn't test actual pattern detection
   - Should add realistic sequences

3. **Entity Count Mismatch**
   - Test: 14 entities (small home)
   - Production: 502 entities (large home)
   - **OK for testing** - tests single-home scenarios

### 🎯 Pattern Detection Implications

**Production:**
- ✅ 15 events/entity/day = High density
- ✅ min_support=5 is appropriate
- ✅ Pattern detection works well

**Test (Current):**
- ⚠️ 3.5 events/entity/day = Sparse
- ⚠️ min_support=5 may be too high
- ⚠️ May need min_support=2-3 for testing

**Test (Recommended 100-150/day):**
- ✅ 7-10 events/entity/day = Moderate density
- ✅ min_support=5 is reasonable
- ✅ Pattern detection should work

---

## Action Plan

### Immediate (Quick Fix)
1. **Increase test events to 100-150/day**
   - Better pattern detection
   - Still fast execution
   - More realistic density

2. **Keep entity count at 14** (matches test home)
   - Tests single-home scenarios
   - Don't need 502 entities for testing

### Short-Term (Better Testing)
3. **Add realistic pattern generation**
   - Motion → Light sequences
   - Time-based patterns
   - Area-based correlations

4. **Stratified testing**
   - Small homes: 50-100 events/day
   - Medium homes: 100-150 events/day
   - Large homes: 150-200 events/day

### Long-Term (Comprehensive)
5. **Match production patterns**
   - High-frequency sensors (sports trackers)
   - Automated systems (vacuum, lights)
   - Real usage patterns

---

## Conclusion

**Production HA generates 150x more events than test**, but this is expected:
- Production has 502 entities vs test's 14
- Production has high-frequency sensors and automations
- Production has real user interactions

**Test doesn't need to match production volume**, but should:
- ✅ Use realistic event density (100-150/day)
- ✅ Generate realistic patterns (motion → light)
- ✅ Test pattern detection effectively

**Recommended:** Increase test to **100-150 events/day** for better pattern detection while maintaining test speed.

