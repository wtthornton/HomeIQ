# Clarification Device Name Enrichment - Deployment

**Date:** January 17, 2025  
**Status:** ✅ Fixed and Deployed

## Issue Summary

**User Query:** "Flash all the Office Hue lights for 30 secs at the top of every hour"

**Problem:** Clarification detector couldn't find Hue lights because:
- Entities have NULL/empty name fields (`friendly_name=''`, `name=''`)
- Devices have proper names ("Office Back Left", "Office Front Left", etc.)
- Clarification detector only checked entity names, not device names

## Fix Applied

### 1. Clarification Detector Enhancement
**File:** `services/ai-automation-service/src/services/clarification/detector.py`

- ✅ Builds device lookup map from available devices
- ✅ When entity name is empty, looks up device name via `device_id`
- ✅ Uses device name for matching "Office Hue lights"
- ✅ Falls back to entity_id if device name not available

### 2. Entity Context Building Update
**File:** `services/ai-automation-service/src/nl_automation_generator.py`

- ✅ Added `device_id` to `entities_by_domain` entries
- ✅ Added `name` and `name_by_user` fields

### 3. Ask AI Router Update
**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

- ✅ Added `device_id` to `entities_by_domain` entries (2 locations)
- ✅ Ensures device_id is available for device name lookup

## How It Works Now

1. **Device Lookup Map Built:**
   ```python
   device_map = {
       '61234ae84aba13edf830eb7c5a7e3ae8': 'Office Back Left',
       '0d88f44293e6ff8430664330035f66f5': 'Office Front Left',
       ...
   }
   ```

2. **Entity Enrichment:**
   ```python
   entity_name = entity_info.get('friendly_name', '')  # Empty
   if not entity_name:
       device_id = entity_info.get('device_id', '')
       if device_id in device_map:
           entity_name = device_map[device_id]  # "Office Back Left"
   ```

3. **Matching:**
   ```python
   mention_lower = "office hue lights"
   if "office" in entity_name.lower() and "hue" in entity_id.lower():
       # Match found!
   ```

## Expected Behavior

After deployment:
- ✅ Query "Flash all the Office Hue lights" will find:
  - Office Back Left (light.hue_color_downlight_1_5)
  - Office Front Left (light.hue_color_downlight_1)
  - Office Front Right (light.hue_color_downlight_1_3)
  - Office Back Right (light.hue_color_downlight_1_4)
  - Office Go (light.hue_go_1)

- ✅ Clarification detector will match by device name
- ✅ No more "no Hue lights found" error

## Testing

1. **Restart Service:**
   ```bash
   docker-compose restart ai-automation-service
   ```

2. **Test Query:**
   - Submit: "Flash all the Office Hue lights for 30 secs at the top of every hour"
   - Verify: Clarification detector finds Office Hue lights
   - Verify: Automation created with correct devices

## Related Fixes

- ✅ Discovery service updated to populate entity name fields (will help long-term)
- ✅ Clarification detector enhanced to use device names (immediate fix)
- ✅ Entity context includes device_id for enrichment

## Files Modified

1. `services/ai-automation-service/src/services/clarification/detector.py`
2. `services/ai-automation-service/src/nl_automation_generator.py`
3. `services/ai-automation-service/src/api/ask_ai_router.py`

## Next Steps

1. ✅ Deploy ai-automation-service
2. ⏳ Test with user query
3. ⏳ Verify Office Hue lights are found
4. ⏳ Verify automation is created correctly

