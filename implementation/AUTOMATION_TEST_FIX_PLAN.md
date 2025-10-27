# Automation Test Fix Plan

**Issue:** Test automations generate YAML with placeholder entities that don't exist in Home Assistant (e.g., `light.office_light_placeholder`), causing automations to fail silently.

**Date:** October 27, 2025

---

## Problem Summary

### Current Behavior
1. User submits query with real device names: "Flash the living room lights"
2. AI generates automation YAML with placeholder entity: `light.office_light_placeholder`
3. Automation is created in HA successfully
4. Automation triggers but does nothing (target entity doesn't exist)
5. Automation stays enabled (not properly disabled)

### Root Causes
1. **Entity extraction not working**: Query doesn't extract real entity IDs from HA
2. **YAML generation uses placeholders**: AI doesn't have access to real entity list
3. **Automation not properly disabled**: `turn_off` service doesn't prevent automation from running
4. **No validation feedback**: System reports success even when automation fails

---

## Fix Plan

### Phase 1: Entity Extraction (HIGH PRIORITY)
**Goal:** Extract real entity IDs from user queries and Home Assistant

**Tasks:**
1. [ ] Query Home Assistant for available entities when processing query
2. [ ] Use fuzzy matching to map natural language to entity IDs
3. [ ] Include real entity list in YAML generation prompt
4. [ ] Update `generate_automation_yaml()` to use real entities

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
- `services/ai-automation-service/src/openai_client.py`
- `services/ai-automation-service/src/clients/ha_client.py` (add `get_entities()` method)

**Example Fix:**
```python
# In ask_ai_router.py query endpoint
async def create_query(query: str, user_id: str):
    # Get available entities from HA
    ha_entities = await ha_client.get_entities()
    
    # Extract entities from query using fuzzy matching
    extracted_entities = extract_entities_from_query(query, ha_entities)
    
    # Include real entities in suggestion generation
    suggestions = await generate_suggestions(query, extracted_entities)
```

**Expected Result:**
- Query "Flash the living room lights" extracts `light.living_room`
- YAML uses real entity: `entity_id: light.living_room`
- Automation actually controls the lights

---

### Phase 2: Fix Disable Logic (HIGH PRIORITY)
**Goal:** Properly disable test automations so they don't re-trigger

**Tasks:**
1. [ ] Update automation YAML to set `mode: single` for test automations
2. [ ] Or: Add state condition to prevent re-triggering
3. [ ] Verify disable_automation() actually prevents triggers
4. [ ] Add cleanup endpoint to delete test automations

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (test endpoint)
- `services/ai-automation-service/src/clients/ha_client.py` (disable method)

**Example Fix:**
```python
# In test endpoint
automation_data = yaml_lib.safe_load(automation_yaml)
automation_data['mode'] = 'single'  # Run once and stop
automation_data['id'] = f"test_{suggestion_id}"
automation_data['alias'] = f"[TEST] {automation_data.get('alias', 'Test')}"
```

**Expected Result:**
- Test automations run once and stop
- No accumulation of disabled automations
- Clean state after each test

---

### Phase 3: Add Entity Validation (MEDIUM PRIORITY)
**Goal:** Validate that entities exist before creating automation

**Tasks:**
1. [ ] Add entity existence check in validation step
2. [ ] Return clear error if entity not found
3. [ ] Suggest similar entities if exact match fails
4. [ ] Show entity list to user for selection

**Files to Modify:**
- `services/ai-automation-service/src/clients/ha_client.py` (validation)
- `services/ai-automation-service/src/api/ask_ai_router.py` (test endpoint)

**Example Fix:**
```python
# In validate_automation()
async def validate_automation(self, automation_yaml: str) -> Dict:
    # Parse YAML
    # Check each entity_id exists in HA
    # Return warnings/errors for missing entities
    pass
```

**Expected Result:**
- System catches missing entities before execution
- Clear error messages to user
- Suggestion to use correct entity

---

### Phase 4: Add Test Automation Cleanup (LOW PRIORITY)
**Goal:** Automatically clean up test automations

**Tasks:**
1. [ ] Add cleanup endpoint to delete test automations
2. [ ] Add scheduled job to delete old test automations
3. [ ] Add "Clean up all test automations" button in UI

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (new cleanup endpoint)
- `services/ai-automation-service/src/clients/ha_client.py` (delete method)

---

## Implementation Order

### Week 1: Critical Fixes
1. **Day 1-2**: Implement Phase 1 (Entity Extraction)
   - Query HA for entities
   - Map natural language to entity IDs
   - Update YAML generation to use real entities
   
2. **Day 3**: Implement Phase 2 (Fix Disable Logic)
   - Change test automation mode to 'single'
   - Verify automations don't re-trigger
   
3. **Day 4**: Testing
   - Test with "Flash living room lights" query
   - Verify lights actually flash
   - Verify automation doesn't re-trigger

### Week 2: Enhancements
4. **Day 1-2**: Implement Phase 3 (Entity Validation)
   - Add entity existence checks
   - Return helpful error messages
   
5. **Day 3-4**: Implement Phase 4 (Cleanup)
   - Add cleanup endpoint
   - Add UI button

---

## Success Criteria

### Must Have (Phase 1 & 2)
- ✅ Query "Flash the living room lights" extracts `light.living_room`
- ✅ YAML uses real entity IDs (not placeholders)
- ✅ Test automation actually flashes the lights
- ✅ Test automation runs once and stops
- ✅ No duplicate test automations piling up

### Nice to Have (Phase 3 & 4)
- ✅ System validates entities before creating automation
- ✅ Clear error messages for missing entities
- ✅ One-click cleanup of all test automations

---

## Testing Plan

### Test Case 1: Basic Functionality
**Input:** "Flash the living room lights every minute"  
**Expected:**
1. Query extracts `light.living_room` entity
2. YAML generated with correct entity ID
3. Test automation created with correct entity
4. Lights flash when test runs
5. Automation runs once and stops

### Test Case 2: Entity Not Found
**Input:** "Flash the nonexistent room lights"  
**Expected:**
1. Query doesn't find matching entity
2. System returns error with available entities
3. User can select correct entity from list

### Test Case 3: Multiple Entities
**Input:** "Turn on living room and kitchen lights"  
**Expected:**
1. Query extracts both `light.living_room` and `light.kitchen`
2. YAML includes both entities in sequence
3. Both lights turn on

---

## Files to Create/Modify

### New Files
- `services/ai-automation-service/src/utils/entity_extractor.py` - Entity matching logic
- `implementation/AUTOMATION_TEST_FIX_COMPLETE.md` - Completion summary

### Modified Files
- `services/ai-automation-service/src/api/ask_ai_router.py` - Add entity extraction
- `services/ai-automation-service/src/openai_client.py` - Update YAML generation
- `services/ai-automation-service/src/clients/ha_client.py` - Add entity methods

### Tests
- `tests/integration/test_entity_extraction.py` - Entity extraction tests
- `tests/integration/test_automation_test_endpoint.py` - Updated test endpoint tests

---

## Quick Wins

### Immediate Fix (Can do now)
1. Check if `light.office_light_placeholder` actually exists
2. If not, update test to use `light.living_room` directly
3. Verify lights flash with correct entity

### Short-term Fix (Today)
1. Add entity extraction to query endpoint
2. Pass real entities to YAML generation
3. Test with real "living room" query

---

## Risk Assessment

**Low Risk:**
- Entity extraction (straightforward mapping)
- Fixing disable logic (simple mode change)

**Medium Risk:**
- Fuzzy matching for entity names (need to handle typos/variations)
- Handling complex queries with multiple entities

**High Risk:**
- Ensuring backward compatibility with existing automations
- Performance impact of querying all HA entities on each request

---

## Next Steps

1. **Start with Phase 1**: Implement entity extraction
2. **Test immediately**: Verify lights actually flash
3. **Iterate**: Add validation and cleanup as needed

**Priority:** Fix entity extraction FIRST, then everything else follows.

---

## References

- [Home Assistant Entity Registry API](https://developers.home-assistant.io/docs/api/rest/#get-api-statedomainentity)
- [FuzzyWuzzy Python Library](https://github.com/seatgeek/fuzzywuzzy) for entity matching
- Current entity list: See output of `light.*` entities in HA
