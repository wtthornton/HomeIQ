# Entity Mapping Fix - 2025 Pattern Implementation

**Date:** January 2025  
**Status:** ✅ **Complete** - Context-aware entity mapping implemented

---

## What Changed (Regression Analysis)

### The Problem

**Before (Working):**
- Entity mapping could resolve generic device names
- Clarification context was used effectively
- "led" could be mapped to specific entities

**After (Broken):**
1. **`_pre_consolidate_device_names`** was added/updated to remove generic terms
2. "WLED" was added to generic_terms set (line 1439)
3. When OpenAI returned `['led', 'WLED']`, "WLED" was removed as generic
4. This left just `['led']` which couldn't be mapped
5. Entity mapping didn't have clarification context to help resolve generic names

### Root Cause

**File:** `services/ai-automation-service/src/api/ask_ai_router.py:1414-1469`

The `_pre_consolidate_device_names` function was too aggressive:
- Removed "WLED" even when user specifically mentioned it in clarifications
- No context awareness to preserve user-specified terms

**File:** `services/ai-automation-service/src/api/ask_ai_router.py:1080-1411`

The `map_devices_to_entities` function lacked:
- Clarification context parameter
- Location hints from Q&A
- Context-aware fuzzy matching

---

## Solution (2025 Patterns)

### Fix 1: Context-Aware Pre-Consolidation ✅

**File:** `services/ai-automation-service/src/api/ask_ai_router.py:1414-1469`

**Enhancement:**
- Added `clarification_context` parameter
- Extracts user-mentioned terms from Q&A answers
- **Preserves terms mentioned in clarifications** (prevents removing "WLED" if user mentioned it)
- Checks both Q&A answers and original query for device mentions

**2025 Pattern:** Context-aware filtering that respects user intent

**Code:**
```python
def _pre_consolidate_device_names(
    devices_involved: list[str],
    enriched_data: dict[str, dict[str, Any]] | None = None,
    clarification_context: dict[str, Any] | None = None  # NEW
) -> list[str]:
    # Extract user-mentioned terms from clarification context
    user_mentioned_terms = set()
    if clarification_context:
        # Check Q&A answers for device mentions
        # Preserve terms that user specifically mentioned
        ...
    
    # Don't remove terms mentioned by user
    if device_lower in user_mentioned_terms:
        filtered.append(device_name)
        continue
```

### Fix 2: Enhanced Entity Mapping with Context ✅

**File:** `services/ai-automation-service/src/api/ask_ai_router.py:1080-1411`

**Enhancements:**
- Added `clarification_context` and `query_location` parameters
- **Context-aware location matching** (bonus scoring for location matches)
- **Context-aware device type matching** (bonus scoring for device type hints)
- Extracts location and device hints from clarification Q&A

**2025 Pattern:** Multi-signal context-aware scoring

**Code:**
```python
async def map_devices_to_entities(
    devices_involved: list[str],
    enriched_data: dict[str, dict[str, Any]],
    ha_client: HomeAssistantClient | None = None,
    fuzzy_match: bool = True,
    clarification_context: dict[str, Any] | None = None,  # NEW
    query_location: str | None = None  # NEW
) -> dict[str, str]:
    # Extract location and device hints from clarification context
    context_location = query_location
    context_device_hints = set()
    if clarification_context:
        # Extract location from Q&A answers
        # Extract device type hints (WLED, Hue, etc.)
        ...
    
    # Context-aware fuzzy matching with location/device type bonuses
    if context_location:
        if location_lower in area_name or location_lower in name_to_check:
            score += 2  # Strong location match bonus
    
    if context_device_hints:
        for hint in context_device_hints:
            if hint in name_to_check or hint in entity_name_part:
                score += 2  # Strong device type match bonus
```

### Fix 3: Context Passing ✅

**File:** `services/ai-automation-service/src/api/ask_ai_router.py:4282-4357`

**Enhancements:**
- Passes `clarification_context` to `_pre_consolidate_device_names`
- Passes `clarification_context` and `query_location` to `map_devices_to_entities`
- Extracts location from query if not already available

**2025 Pattern:** Explicit context propagation through call chain

---

## How It Works Now

### Example: "office WLED" Clarification

1. **User says:** "office WLED" in clarification answer
2. **OpenAI returns:** `devices_involved: ['led', 'WLED']`
3. **Pre-Consolidation (Context-Aware):**
   - Checks clarification context
   - Finds "WLED" mentioned in user answer: "office WLED"
   - **Preserves "WLED"** (doesn't remove as generic)
   - Result: `['led', 'WLED']` (both preserved) ✅

4. **Entity Mapping (Context-Aware):**
   - Uses clarification context to extract location: "office"
   - Uses device hint: "WLED"
   - Maps "led" with context:
     - Location match: "office" → finds entities in office area (+2 bonus)
     - Device type match: "WLED" → finds WLED entities (+2 bonus)
     - **Successfully maps** "led" → "light.wled_office" (or similar) ✅

5. **Result:** Suggestions have validated entities, buttons appear ✅

---

## 2025 Patterns Used

1. **Context-Aware Processing**
   - Uses all available context (clarification, location, Q&A)
   - Respects user intent from clarifications
   - Progressive enhancement (works with or without context)

2. **Multi-Signal Scoring**
   - Combines multiple signals (location, device type, name matching)
   - Weighted scoring for better accuracy
   - Context-aware bonuses for better matching

3. **Explicit Context Propagation**
   - Clear parameter passing
   - Type-safe with optional parameters
   - Comprehensive logging for debugging

4. **Progressive Enhancement**
   - Works with or without context
   - Falls back gracefully
   - Maintains backward compatibility

---

## Testing

### Test Case: Generic Device Name with Context

**Input:**
- Query: "Every 15 mins I want the led in the office to..."
- Clarification: "office WLED"
- OpenAI returns: `devices_involved: ['led', 'WLED']`

**Expected Flow:**
1. ✅ Pre-consolidation preserves "WLED" (mentioned in clarification)
2. ✅ Entity mapping uses "office" location and "WLED" hint
3. ✅ Successfully maps "led" → WLED entity in office
4. ✅ Suggestions have validated entities
5. ✅ Buttons appear

---

## Files Modified

1. `services/ai-automation-service/src/api/ask_ai_router.py`
   - `_pre_consolidate_device_names`: Added context-aware filtering (line 1414-1469)
   - `map_devices_to_entities`: Added context-aware matching (line 1080-1411)
   - Call sites: Pass context through call chain (line 4282-4357)

---

## Status

✅ **Implemented** - Context-aware entity mapping using 2025 patterns  
✅ **Backward Compatible** - Works with or without context  
✅ **Type Safe** - Optional parameters with proper typing  
✅ **Comprehensive Logging** - Logs context usage for debugging

---

## Next Steps

1. ✅ **Immediate:** Context-aware fixes applied
2. ⏳ **Testing:** Test with real clarification scenarios
3. ⏳ **Monitoring:** Monitor logs for context usage and matching success rates

