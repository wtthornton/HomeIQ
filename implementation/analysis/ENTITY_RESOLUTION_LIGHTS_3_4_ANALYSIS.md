# Entity Resolution: Office Lights 3 & 4 Analysis

**Date:** October 29, 2025  
**Status:** ✅ Analysis Complete

---

## Issue

"Office light 3" and "Office light 4" are mapping to `light.hue_color_downlight_2_2` (same as "Office light 2") instead of distinct entities.

---

## Root Cause

### Investigation Findings

**Entities that exist:**
- ✅ `light.hue_color_downlight_1_6` → Device: "Office Front Left" (area: office)
- ✅ `light.hue_color_downlight_2_2` → Device: "Office Back Right" (area: office)
- ❌ `light.hue_color_downlight_3` → Device: "Master Back Left" (area: **master_bedroom**) 
- ❌ `light.hue_color_downlight_4лент` → Device: "Master Front Right" (area: **master_bedroom**)

**The Problem:**
- Lights 3 and 4 exist, but they're in **master_bedroom**, not office
- Query asks for "Office light 3" and "Office light 4"
- System was matching by number only, ignoring location mismatch

---

## Solution Implemented

### 1. Device Area ID Enrichment
- Added `device_area_id` to enriched entities
- Uses device metadata area_id (more reliable than entity area_id)

### 2. Location Mismatch Penalty
- When location is specified ("office") but entity is in different area (master_bedroom):
  - Apply **95% penalty** (score × 0.05)
  - Prevents wrong-room matches

### 3. Enhanced Location Matching
- Checks both `entity_area_id` and `device_area_id`
- Checks location in entity_id, friendly_name, and device_name
- Heavy penalty for mismatches

---

## Expected Behavior

### Current Behavior (After Fix)
- "Office light 1" → `light.hue_color_downlight_1_6` ✅ (office)
- "Office light 2" → `light.hue_color_downlight_2_2` ✅ (office)
- "Office light 3" → **Should fail or use group entity** ⚠️ (no office light 3 exists)
- "Office light 4" → **Should fail or use group entity** ⚠️ (no office light 4 exists)

### The Real Question
**Should we use the group entity `light.office` as a fallback when individual numbered devices don't exist in the correct location?**

**Options:**
1. **Strict matching** - Return no match (current behavior)
2. **Group fallback** - Use `light.office` when individual device not found in location
3. **Best effort** - Use closest numbered device with warning

---

## Recommendation

**Option 2: Group Entity Fallback with Location Check**

When a numbered device doesn't exist in the specified location:
1. Check if group entity exists in that location (e.g., `light.office`)
2. Verify group entity is in the correct location
3. Use group entity as fallback
4. Log warning: "Office light 3 not found, using group entity light.office"

This makes sense because:
- User wants to control "Office lights"
- If specific numbered device doesn't exist, controlling all office lights is acceptable fallback
- Group entities represent all lights in that area

---

## Next Steps

1. ✅ Add location mismatch penalty (DONE)
2. ⚠️ Implement group entity fallback logic
3. ⚠️ Add warning/confirmation for fallback usage
4. ⚠️ Test edge cases

