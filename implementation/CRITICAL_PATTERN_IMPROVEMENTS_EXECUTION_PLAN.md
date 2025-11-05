# Critical Pattern Improvements - Execution Plan

**Date:** January 2025  
**Status:** 🚀 **IN PROGRESS**  
**Priority:** 🔥 Critical - Execute Immediately

---

## Overview

This plan executes all three critical recommendations from the Patterns Relevance Review:

1. ✅ Enable Missing Pattern Detectors (Sequence, Contextual, Room-Based, Day-Type)
2. ✅ Filter System Noise from Co-occurrence Detector
3. ✅ Add Time Variance Threshold to Co-occurrence Detector

**Expected Impact:** Transform from 1200+ noisy patterns to 50-100 high-quality, actionable patterns

---

## Task 1: Enable Missing Pattern Detectors

### Objective
Integrate Sequence, Contextual, Room-Based, and Day-Type detectors into daily analysis pipeline.

### Files to Modify
- `services/ai-automation-service/src/scheduler/daily_analysis.py`

### Current State
- ✅ Detectors are imported
- ✅ Some detectors (Session, Duration, DayType) are already in the pipeline
- ❌ SequenceDetector, ContextualDetector, RoomBasedDetector are NOT being called

### Implementation Steps
1. Add SequenceDetector call after co-occurrence patterns
2. Add ContextualDetector call after sequence patterns
3. Add RoomBasedDetector call after contextual patterns
4. Verify DayTypeDetector is properly integrated (may already be there)
5. Update pattern_summary to include new pattern types

### Code Changes
- Add detector initialization and execution in `run_daily_analysis()`
- Follow existing pattern: initialize → detect → extend → log

---

## Task 2: Filter System Noise from Co-occurrence

### Objective
Exclude system sensors, trackers, images, and events from co-occurrence pattern detection.

### Files to Modify
- `services/ai-automation-service/src/pattern_analyzer/co_occurrence.py`

### Implementation Steps
1. Add `EXCLUDED_ENTITY_PREFIXES` constant list
2. Create `is_actionable_pattern()` helper function
3. Filter events DataFrame before co-occurrence detection
4. Optionally: Add `filter_system_noise` parameter (default: True)

### Excluded Prefixes
```python
EXCLUDED_ENTITY_PREFIXES = [
    'sensor.home_assistant_',  # System sensors
    'sensor.slzb_',            # Coordinator sensors
    'image.',                  # Images/maps (Roborock, cameras)
    'event.',                  # System events
    'binary_sensor.system_',   # System binary sensors
]

# Patterns to match (using regex or contains)
EXCLUDED_PATTERNS = [
    '_tracker',                # External API trackers (sports, etc.)
    '_cpu_',                   # CPU/monitoring sensors
    '_temp',                   # Temperature sensors (system)
]
```

### Code Changes
- Add filtering method to `CoOccurrencePatternDetector`
- Filter both device_id fields in pair detection
- Log number of filtered events for visibility

---

## Task 3: Add Time Variance Threshold

### Objective
Reject co-occurrence patterns with variance >30 minutes (meaningless for automation).

### Files to Modify
- `services/ai-automation-service/src/pattern_analyzer/co_occurrence.py`

### Implementation Steps
1. Calculate time variance for each co-occurrence pair
2. Add `max_variance_minutes` parameter (default: 30)
3. Filter patterns during pattern creation
4. Store variance in metadata for reference

### Code Changes
- Track time deltas for each pair occurrence
- Calculate standard deviation/variance of time deltas
- Filter patterns where variance > threshold
- Include variance in pattern metadata for debugging

---

## Testing Strategy

### Unit Tests
- Test system noise filtering (verify excluded entities are filtered)
- Test variance threshold (verify high-variance patterns are rejected)
- Test new detector integration (verify patterns are detected and stored)

### Integration Tests
- Run daily analysis manually
- Verify pattern counts (should be significantly lower)
- Verify new pattern types appear in database
- Check pattern quality (no system sensors, reasonable variance)

### Validation
- Check pattern list in UI
- Verify actionable patterns only
- Confirm new pattern types visible

---

## Rollback Plan

If issues occur:
1. Revert daily_analysis.py changes (disable new detectors)
2. Revert co_occurrence.py changes (remove filtering)
3. Restore previous behavior temporarily

---

## Success Criteria

✅ **All 4 missing detectors enabled** and producing patterns  
✅ **Co-occurrence patterns reduced by 80%+** (from ~1200 to <250)  
✅ **No system sensors/trackers/images in patterns**  
✅ **All co-occurrence patterns have variance <30 minutes**  
✅ **Pattern quality improved** (actionable, user-initiated events only)

---

## Execution Order

1. **Task 2** - Filter System Noise (foundation, improves existing patterns)
2. **Task 3** - Add Variance Threshold (refines Task 2 results)
3. **Task 1** - Enable Missing Detectors (adds new pattern types)

This order ensures existing patterns are cleaned up first, then new types are added.

---

**Ready to Execute** ✅
