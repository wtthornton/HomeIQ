# AI Automation Service Modal Telemetry Fix Plan

**Date:** 2025-11-24  
**Status:** Plan  
**Issue:** AI Automation Service modal showing zeros for call patterns and empty model comparison data

## Problem Summary

The AI Automation Service modal in the Health Dashboard is displaying:
- **Call Patterns**: Both "Direct Calls" and "Orchestrated Calls" showing `0`
- **Model Comparison**: Empty state message "No model usage data available yet"

### Root Cause Analysis

Based on code review, potential issues:

1. **Extractor Not Initialized**: The `MultiModelEntityExtractor` may not be properly initialized or registered with the health endpoint
2. **Instance Mismatch**: The extractor instance used for processing queries may be different from the one registered for stats
3. **No Query Activity**: Service may not have processed any queries yet (expected behavior)
4. **Model Comparison Service**: May not be finding model usage data from tracking sources
5. **API Endpoint Issues**: Endpoints may be returning empty data or errors

## Investigation Steps

### Phase 1: Verify Current State

#### Step 1.1: Check Service Initialization
- [ ] Verify `MultiModelEntityExtractor` is created in `main.py`
- [ ] Verify `set_multi_model_extractor()` is called during startup
- [ ] Check service logs for initialization errors
- [ ] Verify extractor has `call_stats` dictionary initialized

**Files to Check:**
- `services/ai-automation-service/src/main.py` (lines 181-200)
- `services/ai-automation-service/src/api/health.py` (lines 29-32, 259-291)

#### Step 1.2: Test API Endpoints
- [ ] Test `/stats` endpoint: `GET http://localhost:8018/stats`
  - Expected: JSON with `call_patterns`, `performance`, `model_usage`
  - Check if `_multi_model_extractor` is set
  - Check if `call_stats` exists and has data
- [ ] Test `/api/suggestions/models/compare` endpoint: `GET http://localhost:8018/api/suggestions/models/compare`
  - Expected: JSON with `models`, `summary`, `recommendations`
  - Check if `ModelComparisonService` finds any model instances
- [ ] Check for API errors in response

#### Step 1.3: Verify Extractor Usage
- [ ] Check where `MultiModelEntityExtractor.extract_entities()` is called
- [ ] Verify the same instance is used for processing and stats
- [ ] Check if extractor is being used at all (may be using different extractor)
- [ ] Review service logs for query processing activity

**Files to Check:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (extractor usage)
- `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py` (tracking code)

#### Step 1.4: Check Model Comparison Service
- [ ] Verify `ModelComparisonService` is finding model instances
- [ ] Check if `OpenAIClient` has usage stats
- [ ] Verify `CostTracker` is tracking model usage
- [ ] Check database for `ModelComparisonMetrics` records

**Files to Check:**
- `services/ai-automation-service/src/services/model_comparison_service.py`
- `services/ai-automation-service/src/llm/cost_tracker.py`

## Fix Implementation

### Phase 2: Fix Extractor Registration (If Needed)

#### Issue: Extractor Not Registered
**Symptoms:** `/stats` endpoint returns `{"error": "No extractor initialized"}`

**Fix:**
1. Ensure extractor is created before registration
2. Add error handling and logging
3. Verify extractor instance is the same one used for processing

**Files to Modify:**
- `services/ai-automation-service/src/main.py` (lines 181-200)

**Changes:**
```python
# Ensure extractor is created and valid before registration
extractor = get_multi_model_extractor()
if extractor and hasattr(extractor, 'call_stats'):
    set_multi_model_extractor(extractor)
    logger.info(f"✅ Multi-model extractor registered: call_stats={extractor.call_stats}")
else:
    logger.warning("⚠️ Multi-model extractor not available or missing call_stats")
```

### Phase 3: Fix Instance Mismatch (If Needed)

#### Issue: Different Extractor Instances
**Symptoms:** Extractor processes queries but stats show zero

**Fix:**
1. Ensure single extractor instance is used throughout
2. Use dependency injection or singleton pattern
3. Verify extractor reference is consistent

**Files to Check:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (extractor creation)
- `services/ai-automation-service/src/main.py` (extractor registration)

**Solution:**
- Ensure `_multi_model_extractor` in `ask_ai_router.py` is the same instance registered in `health.py`
- Add logging to verify instance identity

### Phase 4: Fix Model Comparison Service (If Needed)

#### Issue: Model Comparison Returns Empty Data
**Symptoms:** `/api/suggestions/models/compare` returns empty models array

**Fix:**
1. Ensure `ModelComparisonService` can find model instances
2. Check if `OpenAIClient` has usage tracking enabled
3. Verify `CostTracker` is collecting data
4. Add fallback to show at least summary stats even if no models found

**Files to Modify:**
- `services/ai-automation-service/src/services/model_comparison_service.py`
- `services/ai-automation-service/src/api/suggestion_router.py` (lines 117-145)

**Changes:**
1. Improve `get_all_model_stats()` to find all model instances
2. Add logging for debugging
3. Return meaningful empty state with helpful message
4. Check `CostTracker` for aggregated stats

### Phase 5: Add Diagnostic Endpoint

#### New Endpoint: `/stats/diagnostic`
**Purpose:** Help diagnose why stats are empty

**Returns:**
```json
{
  "extractor_registered": true/false,
  "extractor_has_call_stats": true/false,
  "call_stats": {...},
  "total_queries_processed": 0,
  "extractor_instance_id": "...",
  "last_query_time": null,
  "model_comparison_service_status": {...}
}
```

**Files to Create/Modify:**
- `services/ai-automation-service/src/api/health.py` (add new endpoint)

### Phase 6: Improve Error Handling

#### Frontend Error Handling
**Issue:** Frontend doesn't show helpful error messages

**Fix:**
1. Add error state display in modal
2. Show diagnostic information when data is empty
3. Add "Test Query" button to trigger a test query

**Files to Modify:**
- `services/health-dashboard/src/components/ServiceDetailsModal.tsx`
- `services/health-dashboard/src/components/ServicesTab.tsx`

**Changes:**
- Display error messages from API responses
- Show helpful message when no data: "Service is running but hasn't processed any queries yet. Try making a query to the AI Automation Service."
- Add diagnostic info display

## Testing Plan

### Test Case 1: Verify Initialization
1. Start AI Automation Service
2. Check logs for extractor registration
3. Call `/stats` endpoint - should return valid JSON (even if zeros)
4. Verify no errors in response

### Test Case 2: Process Test Query
1. Make a query to AI Automation Service (e.g., via Ask AI interface)
2. Wait for processing
3. Call `/stats` endpoint - should show non-zero `direct_calls`
4. Check modal - should show updated counts

### Test Case 3: Model Comparison
1. Process multiple queries using different models
2. Call `/api/suggestions/models/compare` endpoint
3. Verify models array has entries
4. Check modal - should show model comparison data

### Test Case 4: Auto-Refresh
1. Open modal
2. Process a query
3. Wait 30 seconds
4. Verify modal auto-refreshes with new data

## Implementation Checklist

### Investigation
- [ ] Run diagnostic checks (Phase 1)
- [ ] Document findings
- [ ] Identify root cause(s)

### Fixes
- [ ] Fix extractor registration (if needed)
- [ ] Fix instance mismatch (if needed)
- [ ] Fix model comparison service (if needed)
- [ ] Add diagnostic endpoint
- [ ] Improve error handling in frontend

### Testing
- [ ] Test initialization
- [ ] Test query processing
- [ ] Test model comparison
- [ ] Test auto-refresh
- [ ] Verify modal displays correctly

### Documentation
- [ ] Update API documentation
- [ ] Add troubleshooting guide
- [ ] Document diagnostic endpoint

## Expected Outcomes

After fixes:
1. **If service has processed queries:**
   - Call patterns show actual counts
   - Model comparison shows model usage data
   - Performance metrics display correctly

2. **If service hasn't processed queries:**
   - Modal shows helpful message: "Service is running but hasn't processed any queries yet"
   - Diagnostic info available
   - Clear indication this is expected behavior

3. **If there are errors:**
   - Error messages displayed clearly
   - Diagnostic endpoint provides troubleshooting info
   - Logs contain helpful debugging information

## Files to Modify

### Backend
1. `services/ai-automation-service/src/main.py` - Extractor registration
2. `services/ai-automation-service/src/api/health.py` - Stats endpoint + diagnostic
3. `services/ai-automation-service/src/services/model_comparison_service.py` - Model stats collection
4. `services/ai-automation-service/src/api/suggestion_router.py` - Model comparison endpoint

### Frontend
1. `services/health-dashboard/src/components/ServiceDetailsModal.tsx` - Error handling, empty states
2. `services/health-dashboard/src/components/ServicesTab.tsx` - Error handling, diagnostic display

## Success Criteria

- [ ] `/stats` endpoint returns valid data (even if zeros)
- [ ] Modal displays helpful messages when no data
- [ ] Modal updates correctly when queries are processed
- [ ] Model comparison shows data when available
- [ ] Diagnostic endpoint provides useful troubleshooting info
- [ ] No errors in console or logs
- [ ] Auto-refresh works correctly

## Next Steps

1. **Start with Investigation (Phase 1)** - Run diagnostic checks to identify root cause
2. **Implement Fixes** - Based on investigation findings
3. **Test Thoroughly** - Verify all scenarios work
4. **Deploy** - Roll out fixes to production

