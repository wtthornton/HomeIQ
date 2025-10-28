# Test Button - What It Should Do

**Date:** January 2025  
**Current Status:** Analysis & Brainstorming

---

## Short Summary

The **Test button** should give users a **quick preview** of what the automation will do **before** committing to creating it. It should:

1. **Create a temporary automation** in HA with [TEST] prefix
2. **Trigger it immediately** to show the effect
3. **Auto-disable** the automation after execution
4. **Let user verify** it works before clicking "Approve & Create"

This allows users to "try before they buy" - seeing the automation in action before making it permanent.

---

## Current Problem

### What Test Button Does Now ❌
- Uses HA Conversation API (can't handle complex commands)
- Doesn't create automations
- Doesn't actually flash lights
- Returns success even when it fails

### What It SHOULD Do ✅

1. **Generate YAML** for the suggestion
2. **Create automation** in HA with prefix `[TEST]`
3. **Trigger it immediately** via HA API
4. **Disable automation** after execution
5. **Show user** what happened
6. **Let user decide** to approve or delete

---

## Brainstorming: What Test Should Do

### User Intent
The user wants to **verify** that an automation will work correctly **before** making it permanent.

### What "Test" Means in This Context

**Option A: Preview Without Execution**
- Show what the automation will do
- Show the YAML that will be created
- Let user review before approving
- **Issue:** Doesn't actually verify it works

**Option B: Create Temporary & Execute**
- Create temporary automation
- Execute it immediately
- Show the effect to the user
- **Benefit:** Actually verifies the automation works

**Option C: Simulate Execution**
- Generate YAML
- Parse what it would do
- Show user a preview
- **Issue:** Doesn't test with real devices

---

## Recommended Approach

### Test Button Flow

1. **Generate YAML** (same as Approve button)
2. **Create automation** with id: `test_{suggestion_id}_{timestamp}`
3. **Create automation** with alias: `[TEST] {original_alias}`
4. **Trigger it** via HA API (if possible)
5. **Wait for execution**
6. **Auto-disable** the automation
7. **Return results** to user

### User Experience

**User clicks Test:**
```
1. "Creating test automation..." (loading)
2. "Test automation created: test_abc123"
3. "Triggering automation..."
4. "Automation executed! Check your devices."
5. "Test automation disabled. Approve this suggestion to make it permanent."
```

**Result:**
- User sees the lights flash
- User knows it works
- User can approve or delete

---

## Implementation Changes Needed

### Modify Test Endpoint

**Current:** Quick test via HA Conversation API
```python
@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")
async def test_suggestion_from_query(...):
    # Simplify command
    # Send to HA Conversation API
    # Return result
```

**New:** Create temporary automation
```python
@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")
async def test_suggestion_from_query(...):
    # Generate YAML
    # Create automation with [TEST] prefix
    # Trigger it immediately
    # Disable after execution
    # Return automation_id and results
```

### Key Changes

1. **Add YAML generation** (reuse from approve endpoint)
2. **Add `[TEST]` prefix** to automation ID/alias
3. **Add trigger call** to execute automation immediately
4. **Add auto-disable** logic
5. **Return automation_id** so user can delete it

---

## Benefits

### For Users ✅
- See automation in action before committing
- Verify it works with their actual devices
- Catch issues before creating permanent automation
- Build confidence in the AI suggestions

### For System ✅
- Reduces bad automations being created
- Better user experience
- Higher approval rate
- More user trust

---

## Summary

**What Test Should Do:**
Create a temporary automation, trigger it, show the results, and disable it - giving users a **"try before you approve"** experience.

**Current:** Uses HA Conversation API (doesn't work for complex commands)  
**Should:** Create temporary automation and execute it (actually works)

---

**Last Updated:** January 2025  
**Status:** Brainstorming Complete  
**Recommendation:** Modify Test button to create temporary automations

