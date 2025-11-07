# Ask AI Device Resolution Fix - Ambiguity Prompt Enhancement

**Date:** November 6, 2025  
**Status:** ✅ Implemented  
**Issue:** Ambiguity prompt showed generic device names ("hue lights") instead of specific devices ("Office Front Left", "Office Front Right", etc.)

## Problem Analysis

The second prompt (ambiguity resolution) was not running full device resolution logic. It only showed generic device names extracted from the query, not the specific devices that would be used in the automation.

### Root Cause

1. **Entity Extraction** (line 3433): Extracted generic entities like `["hue lights", "office"]` (device type, not specific devices)
2. **Ambiguity Detection** (line 3496-3500): Ran using generic entities
3. **Ambiguity Message** (line 3685-3688): Built message showing generic device names: `"hue lights"`
4. **Full Device Resolution** (line 3135-3140): Happened LATER in `generate_suggestions_from_query()` - too late for the ambiguity prompt

### Impact

Users couldn't see or confirm which specific devices would be used in the automation during the clarification phase. The system would show "hue lights" but then use specific devices like "Office Front Left" without user confirmation.

## Solution

Implemented **early device resolution** that runs BEFORE ambiguity detection:

1. **New Function**: `resolve_entities_to_specific_devices()` (lines 2084-2236)
   - Extracts location and device domain from entities
   - Queries Home Assistant for all devices in that area matching the domain
   - Expands generic device types to specific device names
   - Returns updated entities list with specific devices

2. **Updated Query Flow** (line 3590-3600):
   - Added Step 1.5: Early device resolution BEFORE ambiguity detection
   - Resolves generic entities to specific devices
   - Continues gracefully if resolution fails

3. **Enhanced Message Building** (line 3848-3872):
   - Updated ambiguity message to use specific device names from resolved entities
   - Shows friendly names (e.g., "Office Front Left") instead of generic types (e.g., "hue lights")
   - Falls back to generic names if resolution fails

## Implementation Details

### New Function: `resolve_entities_to_specific_devices()`

```python
async def resolve_entities_to_specific_devices(
    entities: List[Dict[str, Any]], 
    ha_client: Optional[HomeAssistantClient] = None
) -> List[Dict[str, Any]]
```

**Logic:**
1. Extracts location and device domain from entities
2. Queries HA for all devices in that area matching the domain
3. Normalizes location names (tries multiple formats: "office", "office_", "Office", etc.)
4. Maps generic device types to specific device names
5. Replaces generic device entities with specific ones
6. Returns updated entities list

**Example:**
- Input: `[{"type": "device", "name": "hue lights"}, {"type": "area", "name": "office"}]`
- Output: `[{"type": "device", "name": "Office Front Left", "entity_id": "light.office_front_left", ...}, {"type": "device", "name": "Office Front Right", ...}, ...]`

### Updated Query Processing Flow

**Before:**
```
1. Extract entities → ["hue lights", "office"]
2. Detect ambiguities → uses generic entities
3. Build ambiguity message → "I detected these devices: hue lights"
4. Generate suggestions → resolves to specific devices (too late)
```

**After:**
```
1. Extract entities → ["hue lights", "office"]
2. Resolve to specific devices → ["Office Front Left", "Office Front Right", ...]
3. Detect ambiguities → uses specific devices
4. Build ambiguity message → "I detected these devices: Office Front Left, Office Front Right, ..."
5. Generate suggestions → already has specific devices
```

## Benefits

1. **User Clarity**: Users can see exactly which devices will be used before confirming
2. **Early Validation**: Device resolution happens upfront, catching issues early
3. **Better UX**: Specific device names are more meaningful than generic types
4. **Consistent**: Same device resolution logic used in both ambiguity detection and suggestion generation

## Testing

### Test Case 1: Basic Device Resolution
**Query:** "I want to flash the hue lights in my office when I sit at my desk"

**Expected Behavior:**
- Ambiguity prompt shows: "I detected these devices: Office Front Left, Office Front Right, Office Back Left, Office Back Right"
- NOT: "I detected these devices: hue lights"

### Test Case 2: Multiple Devices
**Query:** "Turn on all lights in the living room"

**Expected Behavior:**
- Ambiguity prompt shows all specific light entities in living room
- Each device listed by friendly name

### Test Case 3: No Location
**Query:** "Turn on the lights"

**Expected Behavior:**
- Early resolution skipped (no location found)
- Falls back to generic device names
- System continues normally

## Code Changes

### Files Modified
- `services/ai-automation-service/src/api/ask_ai_router.py`
  - Added `resolve_entities_to_specific_devices()` function (lines 2084-2236)
  - Updated `process_natural_language_query()` to call early resolution (lines 3590-3600)
  - Enhanced ambiguity message building (lines 3848-3872)

### Lines Changed
- **+153 lines** (new function)
- **+10 lines** (early resolution call)
- **+15 lines** (enhanced message building)

## Rollback Plan

If issues arise, the early resolution can be safely disabled by:
1. Commenting out lines 3590-3600 (early resolution call)
2. The system will fall back to generic device names (original behavior)

## Future Enhancements

1. **Device Selection Questions**: Add explicit device selection questions when multiple devices match
2. **Confidence Scoring**: Score device matches and show confidence in ambiguity prompt
3. **User Preferences**: Remember user's device preferences for future queries
4. **Smart Filtering**: Filter devices by capability (e.g., only lights that support color)

## Related Issues

- Fixes issue where ambiguity prompt showed wrong/generic device names
- Improves user experience by showing specific devices upfront
- Aligns ambiguity detection with suggestion generation device resolution

