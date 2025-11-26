# Event Scaling Doubled - Update

**Date:** November 25, 2025  
**Change:** Doubled events per device per day from 3.75 to 7.5

---

## Update Summary

### Events Per Device Per Day
- **Old**: 3.75 events/device/day (25% of production)
- **New**: 7.5 events/device/day (50% of production)
- **Production**: 15 events/device/day

### Rationale
- Better accuracy for pattern detection
- More realistic event density
- Still manageable for test execution
- Better matches production patterns

---

## Updated Scaling Examples

### Small Home (14 devices, 9 areas)
- **Area Multiplier**: 1.8x (1.0 + 8 × 0.1)
- **Events/Day**: 14 × 7.5 × 1.8 = **189 events/day**
- **Total (7 days)**: 1,323 events

### Medium Home (20 devices, 12 areas)
- **Area Multiplier**: 2.0x (capped)
- **Events/Day**: 20 × 7.5 × 2.0 = **300 events/day**
- **Total (7 days)**: 2,100 events

### Large Home (50 devices, 15 areas)
- **Area Multiplier**: 2.0x (capped)
- **Events/Day**: 50 × 7.5 × 2.0 = **750 events/day**
- **Total (7 days)**: 5,250 events

---

## Retention Status

### Production Bucket (`home_assistant_events`)
- **Retention**: 365 days (8760h)
- **Purpose**: Production event storage
- **Status**: ✅ Healthy

### Test Bucket (`home_assistant_events_test`)
- **Retention**: 7 days (168h)
- **Purpose**: Test event storage
- **Test Data**: 7 days
- **Status**: ✅ Test data fits within retention

### Pattern Aggregate Buckets
- **pattern_aggregates_daily**: 90 days retention
- **pattern_aggregates_weekly**: 365 days retention
- **Purpose**: Pattern aggregates (not raw events)

**Note**: We are NOT loading 90 days of data per database. The test generates 7 days of data, which matches the test bucket retention of 7 days.

---

## Impact Analysis

### Total Events for All 37 Homes

**Old (3.75 events/device/day):**
- Estimated average: ~150 events/day per home
- 37 homes × 1,050 events = ~38,850 total events

**New (7.5 events/device/day):**
- Estimated average: ~300 events/day per home
- 37 homes × 2,100 events = ~77,700 total events
- **2x more events**, but still manageable

### Execution Time
- **Old**: ~40 seconds (estimated)
- **New**: ~80 seconds (estimated)
- Still fast enough for CI/CD

### Pattern Detection Impact

**Events per Device per Day:**

**Old (3.75 events/device/day):**
- Small home: 95 events/day ÷ 14 devices = 6.79 events/device/day
- ⚠️ Moderate - may work with min_support=5

**New (7.5 events/device/day):**
- Small home: 189 events/day ÷ 14 devices = 13.5 events/device/day
- ✅ Good - should work well with min_support=5
- Large home: 750 events/day ÷ 50 devices = 15 events/device/day
- ✅ Excellent - matches production ratio

---

## Comparison: Old vs New vs Production

| Metric | Old (3.75) | New (7.5) | Production (15) |
|--------|-----------|-----------|-----------------|
| **Events/Device/Day** | 3.75 | 7.5 | 15.01 |
| **Small Home (14 devices)** | 95/day | 189/day | ~210/day |
| **Large Home (50 devices)** | 375/day | 750/day | ~750/day |
| **Ratio to Production** | 25% | 50% | 100% |

---

## Conclusion

**Doubled events per device per day:**
- ✅ Better accuracy (50% of production)
- ✅ More realistic event density
- ✅ Better pattern detection
- ✅ Still fast enough for CI/CD
- ✅ Test data fits within 7-day bucket retention

**Retention Status:**
- ✅ Production: 365 days (not 90 days)
- ✅ Test: 7 days (matches test data)
- ✅ Pattern aggregates: 90 days (separate buckets)

**We are NOT loading 90 days of data.** The test generates 7 days of data, which matches the test bucket retention.

