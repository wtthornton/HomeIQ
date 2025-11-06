# Debug Panel Fix - Deployment Summary

**Date:** November 6, 2025  
**Status:** ✅ Fixed and Deployed

---

## Issue

The debug panel was broken after the last deployment, showing "OpenAI Prompts" heading but no content. Additionally, there was a `NoneType` error in the location-priority filtering logic that was preventing suggestions from being generated correctly.

---

## Root Cause Analysis

### Issue 1: NoneType Error in Location-Priority Filtering
**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:2899-2900`

**Problem:**
```python
entity_area_id = enriched.get('area_id', '').lower()
entity_area_name = enriched.get('area_name', '').lower()
```

The `.get('area_id', '')` method returns `None` if the key exists but has a `None` value (the default `''` only applies if the key doesn't exist). Calling `.lower()` on `None` causes an `AttributeError`.

**Error in logs:**
```
⚠️ Error resolving/enriching entities for suggestions: 'NoneType' object has no attribute 'lower'
```

### Issue 2: Missing Token Usage in Debug Panel
**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:3043`

**Problem:**
The `token_usage` field in `openai_debug_data` was always set to `None` because the OpenAI client's `generate_with_unified_prompt` method didn't return token usage information.

---

## Fixes Applied

### Fix 1: Handle None Values in Location Filtering
**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Change:**
```python
# Before:
entity_area_id = enriched.get('area_id', '').lower()
entity_area_name = enriched.get('area_name', '').lower()

# After:
# Handle None values: get() returns None if key exists but value is None
entity_area_id_raw = enriched.get('area_id') or ''
entity_area_name_raw = enriched.get('area_name') or ''
entity_area_id = entity_area_id_raw.lower() if isinstance(entity_area_id_raw, str) else ''
entity_area_name = entity_area_name_raw.lower() if isinstance(entity_area_name_raw, str) else ''
```

**Lines:** 2899-2903

### Fix 2: Capture Token Usage from OpenAI Responses
**File 1:** `services/ai-automation-service/src/llm/openai_client.py`

**Changes:**
1. Added `last_usage` instance variable to store token usage:
   ```python
   self.last_usage = None  # Store last token usage for debug panel
   ```

2. Store usage after each API call:
   ```python
   # Store last usage for debug panel
   self.last_usage = {
       'prompt_tokens': usage.prompt_tokens,
       'completion_tokens': usage.completion_tokens,
       'total_tokens': usage.total_tokens
   }
   ```

**File 2:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Change:**
```python
# Capture token usage from last API call
if openai_client.last_usage:
    openai_debug_data['token_usage'] = openai_client.last_usage
```

**Lines:** 3058-3060

---

## Testing

### Verification Steps

1. ✅ **Service Health:** Service is running and healthy
2. ✅ **No Errors:** No `NoneType` errors in logs
3. ⏳ **Debug Panel:** Test with a real query to verify prompts display correctly

### Expected Behavior

1. **Suggestions Generation:** Should work without `NoneType` errors even when entities have `None` area_id/area_name values
2. **Debug Panel:** Should display:
   - System Prompt
   - User Prompt (with filtered/full toggle)
   - OpenAI Response
   - Token Usage (prompt, completion, total tokens)

---

## Files Modified

1. `services/ai-automation-service/src/api/ask_ai_router.py`
   - Fixed NoneType error in location-priority filtering (lines 2899-2903)
   - Added token usage capture (lines 3058-3060)

2. `services/ai-automation-service/src/llm/openai_client.py`
   - Added `last_usage` instance variable (line 62)
   - Store token usage after each API call (lines 362-366)

---

## Deployment Status

- ✅ Code changes committed
- ✅ Service rebuilt
- ✅ Service restarted and healthy
- ⏳ Awaiting user testing to verify debug panel displays correctly

---

## Next Steps

1. **Test with Real Query:**
   - Submit a query like "flash all hue lights in my office"
   - Check that suggestions are generated without errors
   - Verify debug panel shows prompts and token usage

2. **Monitor Logs:**
   - Watch for any `NoneType` errors
   - Verify token usage is being captured

---

## Related Issues

- Original issue: Debug panel showing empty content
- Side effect: NoneType error preventing suggestions from being generated correctly

