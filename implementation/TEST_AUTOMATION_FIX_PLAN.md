# Test Automation Fix Plan

## Status: ✅ COMPLETE

### Final Result
The entity validation is now working correctly! Test automations now use real Home Assistant entities (e.g., `light.living_room`) instead of placeholder entities.

## Root Cause
The `_find_best_match` method couldn't match "Living Room Light" to "light.living_room" because:
1. **Underscore Not Split**: The entity `light.living_room` was tokenized as a single word `living_room`, so it never matched the query words `{'living', 'room', 'light'}`
2. **No Domain Filtering**: When query mentioned "light", it was matching against ALL entities (including scenes), which resulted in `scene.living_room_natural_light` having a higher score than `light.living_room`

### Latest Findings (Session 2)

1. **✅ File Successfully Copied**: The updated `entity_validator.py` is now in the container (342 lines with new logging)
2. **❌ Method Not Being Called**: The `map_query_to_entities` method is not being executed
3. **Log Evidence**: Only seeing "No valid entities found - mapping was: {}" message
4. **Missing Logs**: No "No entities provided", "Fetching entities", or "Query lower" logs appearing

### Current Hypothesis

The `map_query_to_entities` method may not be called due to:
- Exception occurring before reaching the method
- Entities list being populated (not empty), so the else branch is taken
- The method being called in a different context/module

### Next Debug Steps

1. Add logging at the START of `map_query_to_entities` to confirm it's called
2. Check if `devices_involved` list is populated (not empty)
3. Add exception logging around the entity validation block in `ask_ai_router.py`

## Problem Summary

The test automation is generating YAML with placeholder entities (`light.office_light_placeholder`) instead of real entities from the user's Home Assistant setup (e.g., `light.living_room`).

## Root Cause Analysis

### Issue 1: Docker Build Not Reflecting Changes
- **Problem**: Container has 320 lines, local file has 342 lines
- **Cause**: The Docker build cached the old version of `entity_validator.py`
- **Evidence**: 
  - Container file doesn't have the "Fetching entities from data-api..." logging
  - Local file has living room entity detection logic added

### Issue 2: Entity Mapping Returns Empty Dict
- **Problem**: `entity_mapping = {}` (empty dictionary)
- **Log Evidence**: `⚠️ No valid entities found - mapping was: {}`
- **Cause**: The `map_query_to_entities` method is not finding any entities

### Issue 3: Data API Client Not Returning Entities
- **Problem**: The entity validator is initialized with a DataAPIClient, but entities aren't being fetched
- **Potential Causes**:
  1. DataAPIClient not connecting to data-api service
  2. API endpoint returning empty results
  3. Entity format mismatch

## Investigation Steps

### Step 1: Verify Docker Build
- [ ] Check if local file changes are in the repository
- [ ] Rebuild Docker container with `--no-cache` flag
- [ ] Verify container has the updated file (342 lines)

### Step 2: Debug Entity Validation Flow
- [ ] Add comprehensive logging to track:
  - When `map_query_to_entities` is called
  - What query and entities are passed in
  - What `available_entities` contains
  - What the mapping process produces

### Step 3: Test Data API Connection
- [ ] Verify data-api service is running and healthy
- [ ] Test entity endpoint: `GET http://localhost:8006/api/entities?limit=50&domain=light`
- [ ] Check if entity response format matches what the validator expects

### Step 4: Trace Entity Mapping Logic
- [ ] Check if "living room" detection logic in `map_query_to_entities` is executing
- [ ] Verify entity filtering logic is working correctly
- [ ] Check if entities list is populated before filtering

## Implementation Plan

### Phase 1: Fix Docker Build Issue (HIGH PRIORITY)
```bash
# Force rebuild without cache
docker-compose build --no-cache ai-automation-service

# Restart service
docker-compose restart ai-automation-service
```

### Phase 2: Add Enhanced Logging (HIGH PRIORITY)
Add detailed logging to `map_query_to_entities` method:
- Log when method is called with query and entities
- Log count of available_entities fetched
- Log entities being filtered for each search criteria
- Log final mapping result

### Phase 3: Debug Data API Client (MEDIUM PRIORITY)
- Add connection test to DataAPIClient initialization
- Log the full API response from data-api
- Verify entity data structure matches expectations

### Phase 4: Fix Entity Mapping Logic (MEDIUM PRIORITY)
If entities are fetched but not mapped:
- Check entity format (entity_id, domain fields)
- Verify filtering logic is correct
- Add fallback mapping for common entity patterns

### Phase 5: Add Error Handling (LOW PRIORITY)
- Graceful degradation if entity validation fails
- Retry logic for data-api calls
- Cache entities to reduce API calls

## Testing Plan

### Test 1: Basic Entity Detection
```powershell
# Query should map to living room light
$query = "Flash the living room lights"
# Expected: light.living_room in validated_entities
```

### Test 2: Multiple Entity Types
```powershell
# Query should detect both door and lights
$query = "Turn on living room lights when door opens"
# Expected: binary_sensor.door_contact and light.living_room
```

### Test 3: Fallback Behavior
```powershell
# Query with no specific location
$query = "Flash the lights"
# Expected: Any available light entity as fallback
```

## Expected Outcomes

1. **Immediate**: Docker container has updated code with living room detection
2. **Short-term**: Entity mapping returns `{"living room": "light.living_room", "lights": "light.living_room"}`
3. **Long-term**: Test automation generates YAML with real entity IDs

## Success Criteria

- [ ] Test automation uses `light.living_room` instead of `light.office_light_placeholder`
- [ ] Logs show entity mapping process working
- [ ] Data API returns entities successfully
- [ ] Living room lights flash when test is executed

## Next Steps

1. Rebuild Docker container with --no-cache
2. Add enhanced logging to entity validation
3. Test with "Flash the living room lights" query
4. Verify logs show entity mapping working
5. Confirm test automation uses real entities

## Solutions Implemented

### Fix 1: Split Underscores in Entity Matching
**File**: `services/ai-automation-service/src/services/entity_validator.py`
```python
# Split on underscores and hyphens to handle "living_room" -> ["living", "room"]
entity_words = set()
for word in re.findall(r'\w+', entity_name.lower()):
    # Also split underscores and hyphens
    entity_words.update(word.split('_'))
    entity_words.update(word.split('-'))
```
This allows "living_room" to match queries containing "living" and "room".

### Fix 2: Filter by Domain When Query Mentions Device Type
**File**: `services/ai-automation-service/src/services/entity_validator.py`
```python
# If query mentions "light", prefer light entities
entity_lower = entity.lower()
filtered_entities = available_entities
if 'light' in entity_lower or 'flash' in entity_lower:
    # Try to find lights first
    light_entities = [e for e in available_entities if e.get('domain') == 'light']
    if light_entities:
        print(f"🔍 Filtering to light entities only ({len(light_entities)} found)")
        filtered_entities = light_entities
```
This ensures that "Living Room Light" queries prefer actual light entities over scenes.

### Fix 3: Lower Matching Threshold
Changed similarity threshold from 40% to 25% to catch partial matches:
```python
return best_match if best_score >= 0.25 else None
```

## Test Results

### Before Fix
- Used placeholder entities like `light.office_light_placeholder`
- Lights did not flash during test execution
- Entity mapping returned empty dictionary

### After Fix
- ✅ Uses real entity `light.living_room`
- ✅ Test automation executes successfully
- ✅ Lights flash as expected
- ✅ Entity mapping: `{"Living Room Main Light": "light.living_room"}`

## Success Evidence
```
🔍 Filtering to light entities only (51 found)
✅ Mapped 'Living Room Main Light' to light.living_room
```

**Test automation now correctly uses real Home Assistant entities!**
