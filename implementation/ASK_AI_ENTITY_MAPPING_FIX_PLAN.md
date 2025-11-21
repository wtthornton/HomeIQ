# Ask AI Entity Mapping Fix Plan

**Date**: 2025-11-20  
**Session**: clarify-542c5c2d  
**Status**: Ready for Implementation

## Executive Summary

OpenAI successfully generated 2 suggestions for the WLED automation request, but **both were discarded** due to entity validation failures. The system has 37 enriched entities available but cannot map the generic device names ['WLED', 'led'] from OpenAI's response to actual Home Assistant entities.

## Root Cause Analysis

### Primary Issue: Overly Aggressive Device Name Filtering

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py`, line 1489  
**Function**: `_pre_consolidate_device_names()`

**Problem**:
```python
# Line 1489 - Hardcoded generic terms list
generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
                 'fan', 'lock', 'wled', 'hue', 'mqtt', 'zigbee', 'zwave'}
```

**Flow**:
1. OpenAI returns `devices_involved: ['WLED', 'led']`
2. Pre-consolidation removes 'WLED' (matches 'wled' in generic_terms)
3. Pre-consolidation removes 'led' (< 3 chars or generic term)
4. Result: Empty devices list → No entity mapping → Suggestions skipped
5. User sees: "Failed to generate automation suggestions"

**Why Context-Aware Preservation Failed**:
- User clarification answer: "Turn the brightness up"
- Neither 'wled' nor 'led' appear in this answer
- Context preservation logic (lines 1491-1510) didn't trigger

**Log Evidence**:
```
INFO: Generated 2 suggestions
ERROR: ❌ CRITICAL: validated_entities is empty for suggestion 1
ERROR: ❌ devices_involved: ['WLED', 'led']
ERROR: ❌ Skipping suggestion 1 - no validated entities
ERROR: ❌ Skipping suggestion 2 - no validated entities
INFO: Generated 0 suggestions (final)
```

### Secondary Issue: Variable Name Error

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py`, line 3893  
**Function**: `generate_suggestions_from_query()`

**Problem**:
```python
# Line 3893 - NameError
relevance_scores = await _score_entities_by_relevance(
    enriched_entities=[{'entity_id': eid} for eid in resolved_entity_ids],
    enriched_data=enriched_data,
    query=enriched_query,  # ❌ Variable doesn't exist in this scope
    clarification_context=clarification_context,
    mentioned_locations=mentioned_locations,
    mentioned_domains=mentioned_domains
)
```

**Impact**: Non-fatal (caught and logged) but degrades entity relevance scoring

**Log Evidence**:
```
WARNING: ⚠️ Error resolving/enriching entities for suggestions: name 'enriched_query' is not defined
NameError: name 'enriched_query' is not defined
```

## Downstream Issues

### Issue 1: Entity Mapping Logic Brittle
**Problem**: Relies on exact string matching between OpenAI responses and enriched entity data  
**Impact**: Any mismatch in terminology causes complete failure  
**Affected Users**: Anyone using device type names (WLED, Hue, Zigbee, etc.)

### Issue 2: No Fallback Mechanism
**Problem**: When entity validation fails, there's no fallback to fuzzy matching or user confirmation  
**Impact**: Complete failure instead of degraded service  
**Current Behavior**: Returns 0 suggestions → 500 error

### Issue 3: Poor Error Messaging
**Problem**: Generic error message doesn't explain entity mapping failure  
**Impact**: User has no actionable feedback  
**Current Message**: "Failed to generate automation suggestions after clarification..."  
**Better Message**: "Couldn't map 'WLED' and 'led' to your devices. Available WLED devices: light.hue_go_1, ..."

### Issue 4: Context-Aware Preservation Too Narrow
**Problem**: Only checks clarification answers, not the original query  
**Impact**: Misses context when user doesn't repeat device names in answers  
**Example**: Query mentions "led in the office", answer is just "Turn the brightness up"

## Fix Strategy

### Phase 1: Immediate Fixes (Critical - Deploy ASAP)

#### Fix 1.1: Remove 'wled' from Generic Terms
**File**: `ask_ai_router.py`, line 1489  
**Change**:
```python
# BEFORE (line 1489)
generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
                 'fan', 'lock', 'wled', 'hue', 'mqtt', 'zigbee', 'zwave'}

# AFTER
generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
                 'fan', 'lock', 'mqtt', 'zigbee', 'zwave'}  # Removed 'wled', 'hue' - they're specific device types
```

**Rationale**:
- 'wled' and 'hue' are specific device integration types, not generic domain terms
- Users often refer to devices by their type (e.g., "my WLED", "the Hue bulb")
- Keep truly generic terms like 'light', 'switch' for proper consolidation

#### Fix 1.2: Improve Context-Aware Preservation
**File**: `ask_ai_router.py`, lines 1491-1520  
**Change**: Check BOTH original query AND clarification answers
```python
# After line 1507 (check original query)
original_query = clarification_context.get('original_query', '').lower()
for device in devices_involved:
    device_lower = device.lower()
    if device_lower in original_query:
        user_mentioned_terms.add(device_lower)
        logger.debug(f"🔍 Preserving '{device}' - mentioned in original query")
```

**Impact**: Would have preserved 'led' from original query: "Every 15 mins I want the led in the office..."

#### Fix 1.3: Fix NameError in Relevance Scoring
**File**: `ask_ai_router.py`, line 3893  
**Change**:
```python
# BEFORE
query=enriched_query,  # ❌ Variable doesn't exist

# AFTER
query=query,  # ✅ Use function parameter
```

**Impact**: Fixes entity relevance scoring during suggestion generation

### Phase 2: Robustness Improvements (High Priority)

#### Fix 2.1: Add Fuzzy Matching Fallback
**Location**: After entity mapping fails (line ~4530)  
**Logic**:
```python
# If exact mapping fails, try fuzzy matching
if not validated_entities and devices_involved:
    for device_name in devices_involved:
        # Try fuzzy matching against enriched entity friendly names
        best_match = _fuzzy_match_entity(device_name, enriched_data, threshold=0.7)
        if best_match:
            validated_entities[device_name] = best_match
            logger.info(f"✅ Fuzzy matched '{device_name}' → {best_match}")
```

#### Fix 2.2: Improve Error Messages
**Location**: Line 6629 (error response)  
**Change**: Include specific entity mapping details
```python
# If no suggestions due to entity mapping, provide helpful error
detail={
    "error": "suggestion_generation_failed",
    "message": "Couldn't match some device names to your Home Assistant entities.",
    "details": {
        "unmatched_devices": unmapped_devices,
        "available_similar": _find_similar_entities(unmapped_devices, enriched_data),
        "suggestion": "Try using more specific device names or locations"
    },
    "session_id": request.session_id
}
```

#### Fix 2.3: Add Entity Mapping Validation Step
**Location**: Before suggestion generation (line ~4320)  
**Logic**:
```python
# Validate we can map at least ONE device before calling OpenAI
if devices_involved and enriched_data:
    test_mapping = await map_devices_to_entities(
        devices_involved[:3],  # Test first 3
        enriched_data,
        ha_client
    )
    if not test_mapping:
        logger.warning(f"⚠️ Pre-flight check: Cannot map any devices {devices_involved[:3]}")
        # Try to enrich device names before OpenAI call
        devices_involved = _enrich_device_names_from_context(devices_involved, enriched_data)
```

### Phase 3: Long-Term Improvements (Medium Priority)

#### Fix 3.1: Device Name Normalization
**Approach**: Create canonical mapping of device type aliases
```python
DEVICE_TYPE_ALIASES = {
    'wled': ['wled', 'led strip', 'led controller'],
    'hue': ['hue', 'philips hue', 'hue bulb'],
    'sonoff': ['sonoff', 'tasmota'],
    # ...
}
```

#### Fix 3.2: Entity Suggestion API
**Approach**: When entity mapping fails, return candidates for user selection
```json
{
  "status": "needs_clarification",
  "question": "Which device did you mean by 'led'?",
  "candidates": [
    {"entity_id": "light.hue_go_1", "name": "Office WLED", "location": "office"},
    {"entity_id": "light.desk_lamp", "name": "Desk Lamp", "location": "office"}
  ]
}
```

#### Fix 3.3: Learning from Successful Mappings
**Approach**: Track which OpenAI device names successfully map to entities
```python
# Store successful mappings for future reference
# If "WLED" → "light.hue_go_1" works, remember it
await store_device_name_mapping(
    openai_device_name="WLED",
    entity_id="light.hue_go_1",
    confidence=0.9,
    context=clarification_context
)
```

## Implementation Priority

### Critical (Fix Immediately - Blocks Users)
1. ✅ Fix 1.1: Remove 'wled', 'hue' from generic_terms
2. ✅ Fix 1.3: Fix NameError in relevance scoring
3. ✅ Fix 1.2: Improve context-aware preservation

### High (Fix This Week - Improves UX)
4. Fix 2.1: Add fuzzy matching fallback
5. Fix 2.2: Improve error messages with actionable details

### Medium (Fix This Sprint - Technical Debt)
6. Fix 2.3: Add entity mapping validation pre-flight check
7. Fix 3.1: Device name normalization

### Low (Future Enhancement)
8. Fix 3.2: Entity suggestion API
9. Fix 3.3: Learning from successful mappings

## Testing Plan

### Test Case 1: Original Failure (WLED)
**Input**: "Every 15 mins I want the led in the office to randomly pick a pattern"  
**Expected**: Successfully maps 'led' and 'WLED' to office WLED entities  
**Validation**: Check validated_entities is not empty

### Test Case 2: Hue Devices
**Input**: "Turn on all Hue lights in the bedroom when I get home"  
**Expected**: Maps 'Hue' to all Philips Hue entities in bedroom  
**Validation**: Check devices_involved includes Hue entity IDs

### Test Case 3: Generic Terms (Should Still Be Filtered)
**Input**: "Turn on lights when motion detected"  
**Expected**: 'lights' is still filtered (too generic)  
**Validation**: Relies on entity extraction, not OpenAI's devices_involved

### Test Case 4: Fuzzy Matching
**Input**: "Turn on the offce lamp" (typo)  
**Expected**: Fuzzy matches "offce lamp" → "office lamp"  
**Validation**: Check fuzzy_match_entity logs

### Test Case 5: Error Message Quality
**Input**: Request with unmappable device name  
**Expected**: Specific error with suggestions  
**Validation**: Check error response contains "unmatched_devices" and "available_similar"

## Rollback Plan

### If Fix Breaks Entity Mapping
**Action**: Revert `_pre_consolidate_device_names()` changes  
**Command**: `git revert <commit-hash>`  
**Validation**: Check logs for "Pre-consolidated devices" messages

### If Fuzzy Matching Too Aggressive
**Action**: Increase threshold from 0.7 to 0.85  
**Config**: Set `ENTITY_FUZZY_MATCH_THRESHOLD=0.85` in env  
**Validation**: Monitor false positive mapping rates

## Metrics to Monitor

### Success Metrics
- **Entity Mapping Success Rate**: % of suggestions with validated_entities > 0
- **Device Name Recognition Rate**: % of OpenAI devices successfully mapped
- **User Error Rate**: % of requests ending in 500 errors

### Before Fix (Baseline - Nov 20, 2025)
- Entity Mapping Success: 0% (for WLED/Hue queries)
- Device Name Recognition: 0% (for device type names)
- User Error Rate: 100% (for this query type)

### After Fix (Target)
- Entity Mapping Success: >90%
- Device Name Recognition: >85%
- User Error Rate: <5%

## Related Issues

### Known Issues to Address
1. Entity Registry API returns 404 (log shows "Entity Registry API not available (404)")
   - Impact: Fallback to state-based friendly names (less accurate)
   - Fix: Ensure Entity Registry endpoint is available or handle gracefully

2. Unclosed aiohttp sessions
   - Impact: Resource leaks
   - Fix: Proper session cleanup in HA client

3. Soft prompt adapter initialization fails
   - Impact: No soft prompt fallback for low-confidence queries
   - Fix: Either fix tokenizer or disable soft prompt feature

## Conclusion

This is a **critical bug** affecting any user trying to automate WLED, Hue, or other integration-specific devices. The fix is straightforward (remove 2 terms from a hardcoded list + fix variable name), but we should also implement robustness improvements to prevent similar issues.

**Estimated Impact**: Unblocks 15-20% of Ask AI queries that mention device integration types.

**Estimated Effort**:
- Phase 1: 2 hours (immediate fix)
- Phase 2: 8 hours (robustness)
- Phase 3: 16 hours (long-term improvements)

**Risk**: Low - Changes are isolated to entity mapping logic with clear rollback path.

