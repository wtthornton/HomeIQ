# AI Telemetry Call Patterns Fix Plan

**Date:** 2025-11-19  
**Status:** Plan for Review  
**Issue:** Direct Calls and Orchestrated Calls showing zero in Health Dashboard

## Problem Analysis

### Root Cause
The `MultiModelEntityExtractor` (currently active extractor) tracks `stats` (total_queries, ner_success, etc.) but does NOT track `call_stats` (direct_calls, orchestrated_calls). The `/stats` endpoint incorrectly maps `total_queries` to `direct_calls`, which means:

1. **Call pattern tracking is missing**: `MultiModelEntityExtractor` doesn't have `call_stats` dictionary
2. **Incorrect mapping**: `/stats` endpoint maps `total_queries` → `direct_calls` (line 262 in health.py)
3. **No actual tracking**: Even if queries are processed, call patterns aren't being tracked

### Current State
- ✅ `ModelOrchestrator` has proper `call_stats` tracking (but not used)
- ❌ `MultiModelEntityExtractor` lacks `call_stats` tracking
- ❌ `/stats` endpoint incorrectly reads call patterns
- ❌ Dashboard shows zeros because no tracking occurs

### Evidence
- `MultiModelEntityExtractor.extract_entities()` tracks `stats['total_queries']` but not call patterns
- `/stats` endpoint at line 262: `"direct_calls": _multi_model_extractor.stats.get('total_queries', 0)`
- `ModelOrchestrator` has `call_stats` with proper tracking (lines 52-59, 92-97, 114-119, 134-139)

## Solution

### Phase 1: Add Call Pattern Tracking to MultiModelEntityExtractor

**File:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`

**Changes:**
1. Add `call_stats` dictionary to `__init__` (similar to `ModelOrchestrator`)
2. Track call patterns in `extract_entities()` method:
   - All calls are "direct" (NER, OpenAI, pattern matching are all direct service calls)
   - Track latency for each call type
   - Update `call_stats` after each successful extraction

**Implementation Details:**
```python
# In __init__:
self.call_stats = {
    'direct_calls': 0,
    'orchestrated_calls': 0,  # Reserved for future orchestrated workflows
    'avg_direct_latency': 0.0,
    'avg_orch_latency': 0.0,
    'total_direct_time': 0.0,
    'total_orch_time': 0.0
}

# In extract_entities() after each successful path:
processing_time_ms = processing_time * 1000
self.call_stats['direct_calls'] += 1
self.call_stats['total_direct_time'] += processing_time_ms
self.call_stats['avg_direct_latency'] = (
    self.call_stats['total_direct_time'] / self.call_stats['direct_calls']
)
```

### Phase 2: Update /stats Endpoint

**File:** `services/ai-automation-service/src/api/health.py`

**Changes:**
1. Update `/stats` endpoint to read from `call_stats` instead of incorrectly mapping `total_queries`
2. Check for `call_stats` attribute before falling back to old behavior
3. Ensure proper latency calculation (already in milliseconds)

**Implementation:**
```python
# Line 259-270: Update to use call_stats
if _multi_model_extractor and hasattr(_multi_model_extractor, 'call_stats'):
    return {
        "call_patterns": {
            "direct_calls": _multi_model_extractor.call_stats.get('direct_calls', 0),
            "orchestrated_calls": _multi_model_extractor.call_stats.get('orchestrated_calls', 0)
        },
        "performance": {
            "avg_direct_latency_ms": _multi_model_extractor.call_stats.get('avg_direct_latency', 0.0),
            "avg_orch_latency_ms": _multi_model_extractor.call_stats.get('avg_orch_latency', 0.0)
        },
        "model_usage": _multi_model_extractor.stats
    }
```

### Phase 3: Add Logging (Optional Enhancement)

**File:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`

**Changes:**
- Add logging similar to `ModelOrchestrator` (line 97, 119, 139)
- Log call pattern, service type, latency, and success status
- Format: `SERVICE_CALL: pattern=direct, service=ner, latency=45.23ms, success=True`

## Implementation Steps

1. **Update MultiModelEntityExtractor.__init__()**
   - Add `call_stats` dictionary initialization
   - Place after `stats` initialization (around line 74)

2. **Update MultiModelEntityExtractor.extract_entities()**
   - Add call pattern tracking after NER success (around line 433)
   - Add call pattern tracking after OpenAI success (around line 452)
   - Add call pattern tracking after pattern fallback (around line 470)
   - Add logging for each call pattern

3. **Update /stats endpoint in health.py**
   - Change line 259 to check for `call_stats` attribute
   - Update lines 261-263 to read from `call_stats` instead of `stats`
   - Update lines 265-267 to read from `call_stats` for latency

4. **Testing**
   - Verify call patterns increment when queries are processed
   - Verify dashboard displays correct counts
   - Verify latency calculations are correct
   - Test with multiple query types (NER, OpenAI, pattern)

## Expected Outcome

After implementation:
- ✅ Direct Calls counter increments with each query
- ✅ Orchestrated Calls remains at 0 (not yet implemented)
- ✅ Average Direct Latency shows correct values
- ✅ Dashboard displays real-time telemetry
- ✅ Logs show call pattern tracking

## Files to Modify

1. `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`
   - Add `call_stats` initialization
   - Add tracking in `extract_entities()` method
   - Add logging

2. `services/ai-automation-service/src/api/health.py`
   - Update `/stats` endpoint to read from `call_stats`

## Testing Checklist

- [ ] Call patterns increment when processing queries
- [ ] Dashboard shows non-zero direct calls after queries
- [ ] Latency metrics are calculated correctly
- [ ] Logs show call pattern tracking messages
- [ ] No errors in service logs
- [ ] Dashboard auto-refresh updates counts correctly

## Notes

- All current calls are "direct" (NER, OpenAI, pattern matching are direct service calls)
- "Orchestrated" calls are reserved for future multi-step workflows
- This fix aligns `MultiModelEntityExtractor` with `ModelOrchestrator` tracking pattern
- No breaking changes - only adds tracking, doesn't change behavior

