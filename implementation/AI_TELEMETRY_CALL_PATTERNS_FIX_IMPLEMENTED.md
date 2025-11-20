# AI Telemetry Call Patterns Fix - Implemented

**Date:** 2025-11-19  
**Status:** ✅ Complete  
**Issue:** Direct Calls and Orchestrated Calls showing zero in Health Dashboard

## Changes Made

### 1. Added Call Pattern Tracking to MultiModelEntityExtractor

**File:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`

#### Added `call_stats` Dictionary (lines 76-84)
```python
# Call pattern tracking
self.call_stats = {
    'direct_calls': 0,
    'orchestrated_calls': 0,  # Reserved for future orchestrated workflows
    'avg_direct_latency': 0.0,
    'avg_orch_latency': 0.0,
    'total_direct_time': 0.0,
    'total_orch_time': 0.0
}
```

#### Added Tracking in NER Success Path (lines 444-451)
- Tracks direct calls when NER extraction succeeds
- Calculates latency in milliseconds
- Updates average direct latency
- Logs call pattern: `SERVICE_CALL: pattern=direct, service=ner, latency=X.XXms, success=True`

#### Added Tracking in OpenAI Success Path (lines 464-471)
- Tracks direct calls when OpenAI extraction succeeds
- Calculates latency in milliseconds
- Updates average direct latency
- Logs call pattern: `SERVICE_CALL: pattern=direct, service=openai, latency=X.XXms, success=True`

#### Added Tracking in Pattern Fallback Path (lines 482-489)
- Tracks direct calls when pattern matching fallback is used
- Calculates latency in milliseconds
- Updates average direct latency
- Logs call pattern: `SERVICE_CALL: pattern=direct, service=pattern_fallback, latency=X.XXms, success=True`

### 2. Updated /stats Endpoint

**File:** `services/ai-automation-service/src/api/health.py`

#### Fixed Endpoint to Read from `call_stats` (lines 259-270)
- Changed from checking `hasattr(_multi_model_extractor, 'stats')` to `hasattr(_multi_model_extractor, 'call_stats')`
- Updated to read `direct_calls` from `call_stats` instead of incorrectly mapping `total_queries`
- Updated to read `orchestrated_calls` from `call_stats`
- Updated to read `avg_direct_latency` from `call_stats` (already in milliseconds)
- Updated to read `avg_orch_latency` from `call_stats`
- Maintains backward compatibility by checking for `stats` attribute for model_usage

## How It Works

1. **When a query is processed:**
   - `extract_entities()` is called
   - Processing time is measured
   - After successful extraction (NER, OpenAI, or pattern), call pattern tracking is updated:
     - `direct_calls` is incremented
     - Latency is added to `total_direct_time`
     - Average latency is recalculated
     - Log entry is created

2. **When dashboard requests stats:**
   - `/stats` endpoint checks for `call_stats` attribute
   - Returns `direct_calls` and `orchestrated_calls` from `call_stats`
   - Returns latency metrics from `call_stats`
   - Dashboard displays real-time telemetry

## Expected Behavior

After this fix:
- ✅ **Direct Calls** counter increments with each query processed
- ✅ **Orchestrated Calls** remains at 0 (reserved for future multi-step workflows)
- ✅ **Average Direct Latency** shows correct values in milliseconds
- ✅ **Dashboard** displays real-time telemetry that updates every 30 seconds
- ✅ **Logs** show call pattern tracking messages for debugging

## Testing

To verify the fix:
1. Process a query through the AI Automation Service (e.g., via Ask AI)
2. Check the Health Dashboard → AI Automation Service → Service Details
3. Verify that "Direct Calls" shows a non-zero value
4. Verify that "Average Direct Latency" shows a value in milliseconds
5. Check service logs for `SERVICE_CALL:` messages

## Files Modified

1. `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`
   - Added `call_stats` initialization
   - Added tracking in all three extraction paths
   - Added logging for call patterns

2. `services/ai-automation-service/src/api/health.py`
   - Updated `/stats` endpoint to read from `call_stats`

## Notes

- All current calls are classified as "direct" (NER, OpenAI, and pattern matching are all direct service calls)
- "Orchestrated" calls are reserved for future multi-step workflows that coordinate multiple services
- This fix aligns `MultiModelEntityExtractor` with the tracking pattern used in `ModelOrchestrator`
- No breaking changes - only adds tracking, doesn't change existing behavior
- Backward compatible - gracefully handles cases where `call_stats` might not exist

