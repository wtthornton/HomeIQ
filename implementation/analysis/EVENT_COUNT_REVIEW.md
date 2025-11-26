# Event Count Review for Individual Home Testing

## Current Configuration

### Per-Home Event Generation
- **Days**: 7 days
- **Events per day**: 50
- **Total per home**: 350 events
- **For 37 homes**: 12,950 total events

### Pattern Detection Requirements

**Co-Occurrence Detector:**
- `min_support`: 5 (default, not set in test)
- `min_confidence`: 0.7
- `window_minutes`: 5

**Time-of-Day Detector:**
- `min_occurrences`: 3
- `min_confidence`: 0.7

## Analysis

### ✅ Adequate Aspects

1. **Storage Efficiency**
   - ~6.3 KB for all 37 homes
   - Fits well within test bucket retention (7 days)
   - Fast generation (~13 seconds for all homes)

2. **Test Speed**
   - 350 events per home = quick test execution
   - Good for CI/CD pipelines
   - Reasonable for smoke testing

### ⚠️ Potential Issues

1. **Low Event Density**
   - **50 events/day** across **14 devices** = **~3.5 events per device per day**
   - This is quite sparse for pattern detection
   - Real homes typically have 100-500 events/day
   - May not generate enough co-occurrences for `min_support=5`

2. **Random Event Generation**
   - Current generator uses `random.choice(devices)` - completely random
   - No realistic patterns (e.g., motion → light sequences)
   - May not create enough co-occurrences within 5-minute windows
   - Pattern detection may return 0 patterns even with valid devices

3. **Co-Occurrence Detection Math**
   - With 14 devices and random events:
     - Probability of device A and B co-occurring within 5 minutes: ~0.5%
     - Expected co-occurrences: 350 × 0.5% = ~1.75 per device pair
   - **Problem**: `min_support=5` requires 5 co-occurrences, but we only expect ~1.75
   - **Result**: Likely 0 patterns detected even with valid relationships

4. **Time-of-Day Detection**
   - `min_occurrences=3` is more achievable
   - But with only 7 days, each device has ~24 events total
   - May struggle to find 3+ occurrences at same time of day

5. **Fetched vs Injected Discrepancy**
   - Test shows: 350 injected, 700 fetched
   - **Issue**: Test bucket contains existing data from previous runs
   - Should clear bucket between tests or use unique entity prefixes

## Recommendations

### Option 1: Increase Event Count (Recommended)

**For Better Pattern Detection:**
```python
days = 7
events_per_day = 150  # Increased from 50
# Total: 1,050 events per home
```

**Benefits:**
- ~10.5 events per device per day (more realistic)
- Better chance of meeting `min_support=5`
- Still fast (~35 seconds for all homes)
- More realistic event density

**Trade-offs:**
- Slightly longer test execution
- More storage (~19 KB for all homes)

### Option 2: Reduce Pattern Detection Thresholds

**For Current Event Count:**
```python
detector = CoOccurrencePatternDetector(
    min_confidence=0.7,
    window_minutes=5,
    min_support=2  # Reduced from 5 (default)
)
```

**Benefits:**
- Works with current 350 events
- Faster test execution
- Lower storage

**Trade-offs:**
- Less strict pattern detection
- May detect weaker patterns
- Not testing production thresholds

### Option 3: Improve Event Generation (Best Long-Term)

**Create Realistic Patterns:**
```python
# Instead of random events, generate realistic sequences:
# - Motion sensor → Light (within 30 seconds)
# - Door opens → Alarm (within 2 minutes)
# - Thermostat adjusts → Fan (within 1 minute)
```

**Benefits:**
- Tests actual pattern detection capabilities
- More realistic test scenarios
- Better validation of algorithms

**Trade-offs:**
- More complex event generator
- Requires pattern definitions

### Option 4: Hybrid Approach (Recommended)

**Combine Options 1 and 3:**
- Increase to 100-150 events/day
- Add realistic pattern generation
- Keep current thresholds

## Current Test Results Analysis

From test execution:
- **Generated**: 350 events ✅
- **Injected**: 350 events ✅
- **Fetched**: 700 events ⚠️ (existing data in bucket)
- **Patterns Detected**: Unknown (test passed but didn't show count)

**Questions:**
1. How many patterns were actually detected?
2. Are patterns realistic or just noise?
3. Is the test validating pattern detection or just that it runs?

## Recommended Action Plan

### Immediate (Quick Fix)
1. **Increase events_per_day to 100-150**
   - Better pattern detection without major changes
   - Still fast execution

2. **Clear test bucket between runs**
   - Use unique entity prefixes or clear bucket
   - Avoid contamination from previous tests

### Short-Term (Better Testing)
3. **Add realistic pattern generation**
   - Motion → Light sequences
   - Time-based patterns (morning routines)
   - Area-based correlations

4. **Report pattern detection results**
   - Show how many patterns detected
   - Validate against expected patterns
   - Track precision/recall

### Long-Term (Comprehensive)
5. **Stratified event generation**
   - Different densities for different home sizes
   - Realistic patterns based on device types
   - Ground truth pattern validation

## Event Count Comparison

| Scenario | Events/Day | Events/Home | Events/Device/Day | Pattern Detection |
|----------|-----------|-------------|-------------------|-------------------|
| **Current** | 50 | 350 | 3.5 | ⚠️ Marginal |
| **Recommended** | 100-150 | 700-1,050 | 7-10.5 | ✅ Good |
| **Realistic** | 200-500 | 1,400-3,500 | 14-35 | ✅ Excellent |
| **Production** | 100-1,000 | 700-7,000 | 7-70 | ✅ Production |

## Conclusion

**Current 350 events per home is too low for reliable pattern detection** with default thresholds (`min_support=5`). 

**Recommendation**: Increase to **100-150 events/day** (700-1,050 per home) for better pattern detection while maintaining test speed.

**Priority**: Medium - Tests will pass but may not validate pattern detection effectively.

