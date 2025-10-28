# Test Button Automated Testing Plan

**Date:** January 2025  
**Status:** In Progress

---

## Problem Statement

The Test button is taking too long to debug manually. We need:
1. Automated test script that validates end-to-end flow
2. Clear understanding of what actually needs to work
3. Systematic approach to debugging

---

## What the Test Button Should Do

Based on conversation history, the Test button should:

1. **Generate YAML** from suggestion
2. **Create automation in HA** using that YAML
3. **Wait 30 seconds** for automation to execute
4. **Delete the test automation**
5. **Return success status**

### Expected Flow:
```
User clicks Test
  ↓
Simplify command (OpenAI)
  ↓
Map entities to entity_ids
  ↓
Generate minimal YAML (stripped of timing)
  ↓
POST to HA /api/config/automation/config/automation_id
  ↓
Trigger automation once
  ↓
Wait 30 seconds
  ↓
Delete automation from HA
  ↓
Return success
```

---

## Current Issues

1. Entity mapping not being passed correctly
2. YAML generation using wrong entity IDs
3. Missing entity_id in database entities
4. No automated validation

---

## Test Script Plan

Create `tests/unit/test_button_automated_test.py`:

### Test Cases:

1. **Test entity extraction and mapping**
   - Input: Query with entities
   - Expected: Entity names → entity_ids mapping
   - Validation: Check that `'Left office light'` maps to `'light.office'`

2. **Test YAML generation for test mode**
   - Input: Suggestion with validated_entities
   - Expected: Valid YAML with full entity IDs
   - Validation: Check that entity_id uses `light.office` not `office`

3. **Test automation creation**
   - Input: Valid YAML
   - Expected: Success response from HA API
   - Validation: Check automation_id is returned

4. **Test automation deletion**
   - Input: automation_id
   - Expected: Success deletion
   - Validation: Check automation is gone from HA

5. **Test end-to-end flow**
   - Input: Query ID and suggestion ID
   - Expected: Complete flow executes
   - Validation: Check logs for all steps

---

## Implementation Steps

1. Create test script with real entity data
2. Mock HA API responses
3. Add assertions for each step
4. Run automatically on code changes
5. Fix issues as they arise

---

## Test Script Structure

```python
async def test_button_flow():
    # 1. Simulate query
    query_id = "test-query"
    suggestion_id = "test-suggestion"
    
    # 2. Call test endpoint
    result = await test_suggestion_from_query(query_id, suggestion_id)
    
    # 3. Validate each step
    assert "simplified_command" in result
    assert "automation_id" in result
    assert "executed" in result
    assert "deleted" in result
    
    # 4. Check HA for automation (should not exist)
    # Automation should be deleted
```

