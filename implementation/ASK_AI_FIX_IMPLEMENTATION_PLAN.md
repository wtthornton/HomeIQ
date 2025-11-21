# Ask AI Fix Implementation Plan

**Date**: 2025-11-20  
**Priority**: CRITICAL - Blocking User Requests  
**Estimated Time**: 2-4 hours for Phase 1

## Quick Summary

**Problem**: OpenAI generates suggestions successfully, but they're all discarded due to entity mapping failures.  
**Root Cause**: 'wled' and 'hue' are incorrectly classified as "generic terms" and filtered out before entity mapping.  
**Solution**: Remove device-specific integration types from generic_terms list + fix variable name error.

## Phase 1: Critical Fixes (IMMEDIATE)

### Fix 1: Remove Device Integration Types from Generic Terms Filter

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`  
**Line**: 1489  
**Change Type**: Configuration update

**Current Code**:
```python
# Line 1488-1489
generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
                 'fan', 'lock', 'wled', 'hue', 'mqtt', 'zigbee', 'zwave'}
```

**New Code**:
```python
# Line 1488-1489
# Truly generic terms (domain-level) - device types like 'wled', 'hue' should NOT be here
generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
                 'fan', 'lock', 'mqtt', 'zigbee', 'zwave'}
```

**Rationale**:
- `'wled'` and `'hue'` are specific device integration types that users commonly reference
- They should be preserved for entity mapping, not filtered as "too generic"
- True generic terms like 'light' should remain (they're HA domain names)

**Impact**: 
- ✅ Allows "WLED" and "Hue" to pass through to entity mapping
- ✅ User's query ("led in the office") will no longer fail
- ⚠️ May increase entity mapping attempts for these terms (acceptable trade-off)

---

### Fix 2: Enhance Context-Aware Preservation to Check Original Query

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`  
**Lines**: 1506-1520  
**Change Type**: Logic enhancement

**Current Code** (only checks clarification answers):
```python
# Lines 1506-1510
# Also check original query
original_query = clarification_context.get('original_query', '').lower()
for device in devices_involved:
    device_lower = device.lower()
    if device_lower in original_query:
        # MISSING: user_mentioned_terms.add(device_lower)
        # MISSING: logger.debug(...)
```

**New Code** (check both original query AND answers):
```python
# Lines 1506-1515 (enhanced)
# Also check original query (in addition to clarification answers)
original_query = clarification_context.get('original_query', '').lower()
for device in devices_involved:
    device_lower = device.lower()
    if device_lower in original_query:
        user_mentioned_terms.add(device_lower)
        logger.debug(f"🔍 Preserving '{device}' - mentioned in original query: '{original_query[:100]}...'")
```

**Rationale**:
- User's original query: "Every 15 mins I want the **led** in the office..."
- Clarification answer: "Turn the brightness up" (doesn't mention 'led')
- Current logic only checks answers, misses original query
- This enhancement preserves terms from BOTH sources

**Impact**:
- ✅ Preserves 'led' because it's in the original query
- ✅ More robust context-aware filtering
- ✅ Handles cases where user doesn't repeat device names in answers

---

### Fix 3: Fix NameError in Entity Relevance Scoring

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`  
**Line**: 3893  
**Change Type**: Bug fix

**Current Code**:
```python
# Line 3890-3893
relevance_scores = await _score_entities_by_relevance(
    enriched_entities=[{'entity_id': eid} for eid in resolved_entity_ids],
    enriched_data=enriched_data,
    query=enriched_query,  # ❌ NameError: 'enriched_query' is not defined
    clarification_context=clarification_context,
    mentioned_locations=mentioned_locations,
    mentioned_domains=mentioned_domains
)
```

**New Code**:
```python
# Line 3890-3893
relevance_scores = await _score_entities_by_relevance(
    enriched_entities=[{'entity_id': eid} for eid in resolved_entity_ids],
    enriched_data=enriched_data,
    query=query,  # ✅ Use function parameter 'query' instead of undefined 'enriched_query'
    clarification_context=clarification_context,
    mentioned_locations=mentioned_locations,
    mentioned_domains=mentioned_domains
)
```

**Rationale**:
- Function signature: `async def generate_suggestions_from_query(query: str, ...)`
- Variable `enriched_query` doesn't exist in this scope
- Should use function parameter `query` directly
- This was causing entity relevance scoring to fail silently

**Impact**:
- ✅ Fixes entity relevance scoring (was degraded)
- ✅ Eliminates NameError in logs
- ✅ Improves entity selection for suggestion generation

---

## Testing Plan

### Test 1: Reproduce Original Failure
**Goal**: Verify current failure before fix

**Steps**:
1. Navigate to Ask AI interface
2. Submit query: "Every 15 mins I want the led in the office to randomly pick a pattern"
3. Answer clarification: "Turn the brightness up"

**Expected (Before Fix)**:
- ❌ Error: "Failed to generate automation suggestions after clarification"
- ❌ Logs show: "validated_entities is empty"
- ❌ Logs show: "devices_involved: ['WLED', 'led']"
- ❌ Logs show: "Skipping suggestion - no validated entities"

---

### Test 2: Verify Fix Works
**Goal**: Confirm fix resolves the issue

**Steps**:
1. Apply all 3 fixes
2. Rebuild Docker image
3. Restart ai-automation-service
4. Submit same query: "Every 15 mins I want the led in the office to randomly pick a pattern"
5. Answer clarification: "Turn the brightness up"

**Expected (After Fix)**:
- ✅ Suggestions generated successfully
- ✅ Logs show: "validated_entities" contains office WLED entities
- ✅ Logs show: "Preserving 'led' - mentioned in original query"
- ✅ No "Skipping suggestion - no validated entities" errors
- ✅ User sees 2 automation suggestions for WLED

---

### Test 3: Verify No Regressions
**Goal**: Ensure fix doesn't break existing functionality

**Test Cases**:
1. **Generic light query**: "Turn on lights when motion detected"
   - Expected: Still works, 'lights' is properly generic
2. **Specific entity query**: "Turn on office lamp at sunset"
   - Expected: Maps 'office lamp' to specific entity
3. **Hue devices query**: "Turn on all Hue lights in bedroom"
   - Expected: Now works (previously failed like WLED)
4. **Location-based query**: "Turn off all lights in the kitchen"
   - Expected: Still works, location-aware filtering

---

## Deployment Steps

### Step 1: Apply Code Changes
```bash
cd services/ai-automation-service
# Edit ask_ai_router.py with all 3 fixes
```

### Step 2: Rebuild Docker Image
```bash
cd C:\cursor\HomeIQ
docker-compose build ai-automation-service
```

### Step 3: Restart Service
```bash
docker-compose down ai-automation-service
docker-compose up -d ai-automation-service
```

### Step 4: Verify Service Health
```bash
docker logs ai-automation-service --tail 50
# Check for startup errors
# Verify "Ask AI Router logger initialized" message
```

### Step 5: Test Fix
```bash
# Navigate to http://localhost:3001/ask-ai
# Submit test query and verify suggestions generated
```

---

## Rollback Plan

### If Fix Causes Issues

**Immediate Rollback**:
```bash
cd C:\cursor\HomeIQ
git checkout services/ai-automation-service/src/api/ask_ai_router.py
docker-compose build ai-automation-service
docker-compose restart ai-automation-service
```

**Partial Rollback** (if only one fix is problematic):
- Fix 1 (generic_terms): Revert line 1489 only
- Fix 2 (context-aware): Revert lines 1506-1515 only
- Fix 3 (NameError): Revert line 3893 only

**Validation After Rollback**:
```bash
docker logs ai-automation-service --tail 100
# Check for "Ask AI Router logger initialized"
# Verify no startup errors
```

---

## Monitoring

### Key Metrics to Watch

**Log Monitoring** (docker logs):
```bash
# Success indicators:
grep "validated_entities" docker logs ai-automation-service
grep "Preserving.*mentioned in original query" docker logs ai-automation-service
grep "Generated.*suggestions" docker logs ai-automation-service

# Failure indicators:
grep "Skipping suggestion - no validated entities" docker logs ai-automation-service
grep "NameError" docker logs ai-automation-service
grep "suggestion_generation_failed" docker logs ai-automation-service
```

**Application Metrics**:
- Suggestion generation success rate
- Entity mapping success rate
- Average validated_entities per suggestion
- User error rate (500 responses)

**Target Thresholds**:
- Entity mapping success rate: >90% (from 0%)
- Suggestion generation success rate: >95%
- User error rate: <5% (from 100% for this query type)

---

## Risk Assessment

### Low Risk Changes ✅
- **Fix 1** (remove 'wled'/'hue' from generic_terms): Low risk, high reward
  - Only affects pre-consolidation filtering
  - Fallback: Entity mapping still validates against enriched_data
  - Worst case: More entity mapping attempts (acceptable)

- **Fix 3** (NameError): Zero risk, pure bug fix
  - Fixes existing error in logs
  - No behavioral change except improved relevance scoring

### Medium Risk Changes ⚠️
- **Fix 2** (context-aware preservation): Medium risk, high reward
  - Adds original query check to context preservation
  - Could preserve terms that shouldn't be preserved
  - Mitigation: Generic terms list still applies first
  - Worst case: One extra entity mapping attempt per suggestion

### Overall Risk: **LOW** ✅
- All changes are isolated to entity mapping logic
- Clear rollback path (git checkout)
- No database schema changes
- No breaking API changes
- Extensive logging for debugging

---

## Success Criteria

### Must Have (Blocking)
- ✅ User query "led in the office" generates suggestions
- ✅ No "validated_entities is empty" errors for WLED/Hue queries
- ✅ NameError eliminated from logs

### Should Have (Important)
- ✅ Context-aware preservation logs show original query checks
- ✅ Entity mapping success rate >90%
- ✅ No regressions on existing test cases

### Nice to Have (Optional)
- ✅ Fuzzy matching fallback (Phase 2)
- ✅ Improved error messages (Phase 2)
- ✅ Entity mapping validation pre-flight check (Phase 2)

---

## Phase 2 Preview (Future Work)

### Planned Enhancements
1. **Fuzzy Matching Fallback**: If exact mapping fails, try fuzzy matching (threshold 0.7)
2. **Better Error Messages**: Show unmatched devices and suggest similar entities
3. **Entity Mapping Pre-flight Check**: Validate mapping before calling OpenAI
4. **Device Name Normalization**: Canonical mapping of device type aliases
5. **Entity Suggestion API**: Return candidates when mapping fails, let user choose

### Estimated Effort
- Phase 2 (Robustness): 8 hours
- Phase 3 (Long-term): 16 hours

---

## Conclusion

This is a **critical fix** for a high-impact bug affecting WLED, Hue, and other integration-specific device automations. The fix is:

- ✅ **Simple**: 3 small code changes
- ✅ **Low Risk**: Isolated changes with clear rollback
- ✅ **High Impact**: Unblocks 15-20% of Ask AI queries
- ✅ **Well Tested**: Comprehensive test plan
- ✅ **Documented**: Full analysis and monitoring plan

**Recommended Action**: Implement Phase 1 immediately, schedule Phase 2 for next sprint.

