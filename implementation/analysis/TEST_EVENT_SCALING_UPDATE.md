# Test Event Scaling Update

**Date:** November 25, 2025  
**Change:** Scale test events to 50% of production volume, based on device and area count

---

## New Scaling Strategy

### Production Baseline
- **Production**: 7,534 events/day for 502 devices
- **Events per Device/Day**: ~15 events
- **Test Target (50%)**: ~3.75 events per device per day

### Scaling Formula

```python
events_per_device_per_day = 3.75  # 50% of production
area_multiplier = 1.0 + (area_count - 1) * 0.1  # More rooms = more activity
area_multiplier = min(area_multiplier, 2.0)  # Cap at 2.0x

events_per_day = device_count * events_per_device_per_day * area_multiplier
events_per_day = max(events_per_day, 50)  # Minimum 50/day
```

### Rationale

1. **Device-Based Scaling**
   - Larger homes (more devices) = more events
   - Simulates more people and activity
   - Realistic: 3.75 events/device/day (50% of production)

2. **Area-Based Multiplier**
   - More rooms = more activity
   - Single room: 1.0x
   - 2 rooms: 1.1x
   - 3 rooms: 1.2x
   - 10+ rooms: 2.0x (capped)

3. **Minimum Threshold**
   - At least 50 events/day for very small homes
   - Ensures pattern detection has enough data

---

## Example Scaling

### Small Home (home1-us)
- **Devices**: 14
- **Areas**: 9
- **Area Multiplier**: 1.8x (1.0 + 8 * 0.1)
- **Events/Day**: 14 × 3.75 × 1.8 = **95 events/day**
- **Total (7 days)**: 665 events

### Medium Home (home2-dk)
- **Devices**: 20
- **Areas**: 12
- **Area Multiplier**: 2.0x (capped)
- **Events/Day**: 20 × 3.75 × 2.0 = **150 events/day**
- **Total (7 days)**: 1,050 events

### Large Home (home3-large)
- **Devices**: 50
- **Areas**: 15
- **Area Multiplier**: 2.0x (capped)
- **Events/Day**: 50 × 3.75 × 2.0 = **375 events/day**
- **Total (7 days)**: 2,625 events

---

## Comparison: Old vs New

| Home Size | Devices | Areas | Old (Fixed) | New (Scaled) | Ratio |
|-----------|---------|-------|-------------|--------------|-------|
| Small | 14 | 9 | 50/day (350 total) | 95/day (665 total) | 1.9x |
| Medium | 20 | 12 | 50/day (350 total) | 150/day (1,050 total) | 3.0x |
| Large | 50 | 15 | 50/day (350 total) | 375/day (2,625 total) | 7.5x |

**Benefits:**
- ✅ Larger homes get more events (realistic)
- ✅ Simulates more people and activity
- ✅ Better pattern detection for larger homes
- ✅ Still fast for small homes

---

## Impact on Test Execution

### Total Events for All 37 Homes

**Old (Fixed 50/day):**
- 37 homes × 350 events = 12,950 total events

**New (Scaled):**
- Estimated average: ~150 events/day per home
- 37 homes × 1,050 events = ~38,850 total events
- **3x more events**, but still manageable

**Execution Time:**
- Old: ~13 seconds (estimated)
- New: ~40 seconds (estimated)
- Still fast enough for CI/CD

---

## Pattern Detection Impact

### Events per Device per Day

**Old (Fixed 50/day, 14 devices):**
- 3.57 events/device/day
- ⚠️ Sparse - may struggle with min_support=5

**New (Scaled, 14 devices, 9 areas):**
- 95 events/day ÷ 14 devices = 6.79 events/device/day
- ✅ Better - should work with min_support=5

**New (Scaled, 50 devices, 15 areas):**
- 375 events/day ÷ 50 devices = 7.5 events/device/day
- ✅ Good - matches production ratio

---

## Implementation

### Changes Made

1. **Dynamic Event Calculation**
   - Calculate `events_per_day` based on device and area count
   - Apply area multiplier for more realistic scaling
   - Enforce minimum threshold

2. **Results Tracking**
   - Store `events_per_day` in results
   - Store `events_per_device_per_day` for analysis
   - Store `area_multiplier` for transparency

3. **Enhanced Logging**
   - Show scaling factors in test output
   - Display events per device for each home
   - Better visibility into test configuration

---

## Validation

### Test Against Production

**Production:**
- 502 devices, 7,534 events/day
- 15.01 events/device/day

**Test (Scaled, Large Home):**
- 50 devices, 375 events/day
- 7.5 events/device/day
- **50% of production ratio** ✅

**Test (Scaled, Small Home):**
- 14 devices, 95 events/day
- 6.79 events/device/day
- **45% of production ratio** ✅

---

## Next Steps

1. ✅ **Implemented**: Dynamic event scaling based on devices and areas
2. **Test**: Run tests to validate scaling works correctly
3. **Monitor**: Check pattern detection results across different home sizes
4. **Tune**: Adjust area multiplier if needed based on results

---

## Conclusion

**New scaling strategy:**
- ✅ Scales events to 50% of production volume
- ✅ Larger homes get more events (realistic)
- ✅ Simulates more people and activity
- ✅ Better pattern detection across home sizes
- ✅ Still fast enough for CI/CD

**This approach better matches production patterns while maintaining test efficiency.**

