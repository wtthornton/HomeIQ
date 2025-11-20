# Entity Mapping Regression Analysis

**Date:** January 2025  
**Issue:** Entity mapping fails for generic device names after clarification  
**Status:** 🔍 Root Cause Identified

---

## What Changed

### The Problem

1. **`_pre_consolidate_device_names`** (line 1414-1469) removes "WLED" from the generic_terms set
2. When OpenAI returns `['led', 'WLED']`, the function removes "WLED" as generic
3. This leaves just `['led']` which is too generic to map
4. `map_devices_to_entities` doesn't have clarification context to help resolve generic names

### Why It Used to Work

Previously, the system likely:
- Didn't have aggressive pre-consolidation that removed "WLED"
- Had better fuzzy matching that could resolve "led" to "WLED" entities
- Used clarification context more effectively

---

## Root Cause

**File:** `services/ai-automation-service/src/api/ask_ai_router.py:1414-1469`

**Problem Code:**
```python
# Generic terms to remove (domain names, device types, very short terms)
generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
                 'fan', 'lock', 'wled', 'hue', 'mqtt', 'zigbee', 'zwave'}
```

**Issue:** "wled" is in the generic_terms set, so it gets removed even when it's the specific device the user mentioned.

**Flow:**
1. OpenAI returns: `devices_involved: ['led', 'WLED']`
2. `_pre_consolidate_device_names` removes "WLED" (generic term)
3. Result: `['led']` (too generic)
4. `map_devices_to_entities` can't map "led" → no validated_entities
5. Suggestions skipped → empty array returned

---

## Solution (2025 Patterns)

### Fix 1: Context-Aware Pre-Consolidation

Make `_pre_consolidate_device_names` aware of clarification context so it doesn't remove terms that appear in user clarifications.

### Fix 2: Enhanced Entity Mapping with Context

Pass clarification context to `map_devices_to_entities` and use it to:
- Resolve generic names using location hints ("led" + "office" → "office WLED")
- Use Q&A answers to understand device references
- Improve fuzzy matching with context-aware scoring

### Fix 3: Location-Aware Fuzzy Matching

Enhance fuzzy matching to use:
- Location from clarification context
- Device type hints from Q&A
- Area information from enriched_data

---

## Implementation Plan

1. **Update `_pre_consolidate_device_names`** to accept and use clarification context
2. **Update `map_devices_to_entities`** to accept clarification context and use it for better matching
3. **Pass clarification context** through the call chain
4. **Add context-aware fuzzy matching** that uses location/device hints

---

## 2025 Best Practices

- **Context-Aware Processing:** Use all available context (clarification, location, Q&A) for better accuracy
- **Type-Safe Parameters:** Use dataclasses/Pydantic models for context passing
- **Progressive Enhancement:** Fall back gracefully when context is unavailable
- **Comprehensive Logging:** Log context usage for debugging

