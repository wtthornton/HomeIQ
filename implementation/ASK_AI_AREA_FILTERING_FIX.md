# Ask AI Area Filtering Fix

**Date:** November 18, 2025  
**Issue:** Automation assistant selects devices from all areas instead of only the specified area  
**Status:** ✅ Fixed

## Problem Description

When a user specified an area in their prompt (e.g., "In the office, flash all the Hue lights..."), the automation assistant would:
1. Fetch ALL entities from the entire house (all areas)
2. Pass all entities to OpenAI
3. OpenAI would then select devices from any area, not just the specified one

Result: User requested "office" devices but got suggestions for "LR Back Left Ceiling", "Master Back Left", etc.

## Root Cause

In `nl_automation_generator.py`:
- The `_build_automation_context()` method fetched all entities without area filtering
- The `generate()` method didn't extract the area from the user's request
- The OpenAI prompt didn't emphasize area restrictions

## Solution Implemented

### 1. Area Extraction (`_extract_area_from_request()`)
Added method to detect area/location from user prompt:
- **Single Area Patterns:**
  - Pattern 1: "in the X" or "in X" (e.g., "in the office")
  - Pattern 2: "at the X" or "at X" (e.g., "at the kitchen")
  - Pattern 3: Area name at start (e.g., "office lights")
- **Multiple Area Patterns:**
  - Pattern 1: "in the X and Y" (e.g., "in the office and kitchen")
  - Pattern 2: "X and Y" (e.g., "bedroom and living room lights")
- Supports 30+ common area names: office, kitchen, bedroom, living room, bathroom, etc.
- Normalizes to snake_case (e.g., "living room" → "living_room")
- Returns comma-separated areas for multiple locations (e.g., "office,kitchen")

### 2. Area Filtering in Context Builder
Modified `_build_automation_context(area_filter: Optional[str])`:
- Now accepts optional `area_filter` parameter (supports comma-separated areas)
- **Single Area:** Passes area filter directly to data API
- **Multiple Areas:** Fetches entities for each area separately and combines results
  - Uses pandas to concatenate DataFrames
  - Removes duplicates by device_id/entity_id
- Only entities from specified area(s) are included in context
- Logs detected areas for debugging

### 3. OpenAI Prompt Template Enhancement
Modified `_build_prompt()` to include comprehensive area logic:

**A. Area Restriction Notice (dynamic, shown only when area specified):**

Single area:
```
**IMPORTANT - Area Restriction:**
The user has specified devices in the "Office" area. You MUST use ONLY devices that are located in the Office area. 
The available devices list below has already been filtered to show only Office devices. DO NOT use devices from other areas.
```

Multiple areas:
```
**IMPORTANT - Area Restriction:**
The user has specified devices in these areas: Office and Kitchen. You MUST use ONLY devices that are located in these areas.
The available devices list below has already been filtered to show only devices from these areas. DO NOT use devices from other areas.
```

**B. Area Filtering Instruction (always present in main instructions):**
```
3. **AREA FILTERING:** If the user specifies a location (e.g., "in the office", "kitchen and bedroom"):
   - Use ONLY entities from that area/those areas
   - The available devices list is already filtered by area if specified
   - DO NOT use entities from other areas
   - Verify entity_id matches the specified area(s)
```

This dual approach ensures OpenAI:
1. Gets a prominent notice at the top (if area specified)
2. Has permanent instruction in the numbered list (always)

### 4. Retry Generation Support
Updated `_retry_generation()` to preserve area filter on retry attempts

## Code Changes

**File:** `services/ai-automation-service/src/nl_automation_generator.py`

**Changes:**
1. Added `_extract_area_from_request()` method (lines 427-484)
2. Modified `generate()` to extract and use area filter (lines 93-99)
3. Updated `_build_automation_context()` signature (line 157)
4. Modified `_build_prompt()` to include area notice (lines 227-261)
5. Updated `_retry_generation()` signature (line 662)

## Testing

### Test Case 1: Single Area (Original Issue)
Use the original prompt that failed:
```
"In the office, flash all the Hue lights for 45 secs using the Hue Flash action. 
Do this at the top of every hour. Kick up the brightness to 100% when flashing. 
When 45 secs is over, return all lights back to their original state."
```

**Expected Result:**
- System detects "office" area
- Fetches only office entities
- Suggests only office devices (not LR, Master, etc.)

### Test Case 2: Multiple Areas
Use a multi-area prompt:
```
"Turn on all lights in the office and kitchen at 7 AM"
```

**Expected Result:**
- System detects "office,kitchen" areas
- Fetches entities from both areas
- Suggests devices from office AND kitchen only
- No devices from bedroom, living room, etc.

### Verification Points
1. Check logs for: `📍 Detected area filter: 'office'`
2. Check logs for: `Fetching device context from data-api (area_filter: office)`
3. Verify suggested devices are all from office area
4. Verify no devices from other areas (living room, master bedroom, etc.)

## Supported Area Names

The fix recognizes these common area names:
- office, kitchen, bedroom, living room/living_room
- bathroom, garage, basement, attic, hallway
- dining room/dining_room, master bedroom/master_bedroom
- guest room/guest_room, laundry room/laundry_room
- den, study, library, gym, playroom, nursery
- porch, patio, deck, yard, garden, driveway
- foyer, entryway, closet, pantry

## Backward Compatibility

✅ **Fully backward compatible**
- If no area specified in prompt → fetches all entities (existing behavior)
- If area specified → filters by area (new behavior)
- No breaking changes to API or existing automations

## Future Enhancements

Potential improvements:
1. Learn custom area names from Home Assistant configuration
2. Support multiple areas in one prompt ("kitchen and living room")
3. Add area aliases/synonyms (e.g., "LR" → "living room")
4. Fuzzy matching for area names (typo tolerance)
5. Suggest correct area name if misspelled

## Deployment

**Service:** ai-automation-service  
**Restart Required:** Yes  
**Database Changes:** None  
**Environment Variables:** None  

**Deployment Command:**
```bash
docker-compose restart ai-automation-service
```

## Related Issues

- Issue: User reported "In the office..." prompt selected devices from all areas
- Screenshot shows: Bar, LR Back Left Ceiling, Master Back Left, LR Front Right Ceiling
- All should have been office devices only

