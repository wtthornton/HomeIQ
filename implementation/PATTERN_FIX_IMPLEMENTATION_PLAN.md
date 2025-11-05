# Pattern Detection Fix - Implementation Plan

**Date:** October 2025  
**Goal:** Reduce 1,222 low-quality patterns to ~50-100 high-quality actionable patterns

## Simple Plan (No Over-Engineering)

### Phase 1: Quick Fixes (1-2 hours)

1. **Add Filtering Constants** (5 min)
   - Define excluded domains/prefixes
   - Define actionable domains

2. **Update Pattern Storage** (15 min)
   - Add validation function before storing
   - Filter out non-actionable entities

3. **Increase Thresholds** (10 min)
   - Update min_occurrences in daily_analysis.py
   - Change from 5 to 10 for most detectors

4. **Fix Confidence Calculation** (20 min)
   - Update time_of_day detector confidence
   - Make it based on actual metrics, not binary

### Phase 2: Cleanup (30 min)

1. **Database Cleanup Script** (15 min)
   - Remove low-quality patterns
   - Remove excluded domains/prefixes
   - Remove low occurrences

2. **Test & Verify** (15 min)
   - Run cleanup
   - Check pattern count
   - Verify quality

## Implementation Order

1. ✅ Add filtering constants
2. ✅ Update pattern validation
3. ✅ Update thresholds
4. ✅ Fix confidence
5. ✅ Create cleanup script
6. ✅ Test

## Success Criteria

- Pattern count: 50-200 (down from 1,222)
- Only actionable devices (lights, switches, covers, climate)
- Minimum 10 occurrences per pattern
- Confidence based on actual metrics

