# Clarification Device Name Enrichment Fix

**Date:** January 17, 2025  
**Issue:** Clarification detector couldn't find "Office Hue lights" because entities have NULL names but devices have proper names

## Problem

### Root Cause
1. **Devices have names**: "Office Back Left", "Office Front Left", "Office Front Right", "Office Back Right", "Office Go"
2. **Entities have NULL names**: `friendly_name=''`, `name=''`, `name_by_user=''`
3. **Entities link to devices**: Entities have `device_id` that links to devices with names
4. **Clarification detector only checked entity names**: When entity names were NULL, it couldn't find matches

### User Query
"Flash all the Office Hue lights for 30 secs at the top of every hour. Use the Hue Flash action, set the brightness from zero to 100% when flashing."

### Expected Behavior
- Should find: Office Back Left, Office Front Left, Office Front Right, Office Back Right, Office Go
- Actually found: Nothing (because entity names are NULL)

## Solution

### Changes Made

1. **Updated Clarification Detector** (`detector.py`)
   - Builds device lookup map from `available_devices['devices']`
   - When checking entities, if entity name is empty, looks up device name via `device_id`
   - Uses device name for matching and display

2. **Updated Entity Context Building** (`nl_automation_generator.py`)
   - Added `device_id` to `entities_by_domain` entries
   - Added `name` and `name_by_user` fields for completeness

3. **Updated Ask AI Router** (`ask_ai_router.py`)
   - Added `device_id` to `entities_by_domain` entries (2 locations)
   - Ensures device_id is available for device name lookup

### Code Changes

**Before:**
```python
entities_by_domain[domain].append({
    'entity_id': entity_id,
    'friendly_name': entity.get('friendly_name', entity_id),
    'area': entity.get('area_id', 'unknown')
})
```

**After:**
```python
entities_by_domain[domain].append({
    'entity_id': entity_id,
    'friendly_name': entity.get('friendly_name', entity_id),
    'name': entity.get('name', ''),
    'name_by_user': entity.get('name_by_user', ''),
    'device_id': entity.get('device_id', ''),  # Include device_id for device name lookup
    'area': entity.get('area_id', 'unknown')
})
```

**Clarification Detector Enhancement:**
```python
# Build device lookup map
device_map = {}
for device_info in devices_list:
    device_id = device_info.get('device_id', device_info.get('id', ''))
    device_name = device_info.get('name', device_info.get('friendly_name', ''))
    if device_id and device_name:
        device_map[device_id] = device_name

# When checking entities, enrich with device names
if not entity_name:
    device_id = entity_info.get('device_id', '')
    if device_id and device_id in device_map:
        entity_name = device_map[device_id]
```

## Expected Results

After this fix:
1. ✅ Clarification detector will find "Office Hue lights" by checking device names
2. ✅ Entities with NULL names will be enriched with device names
3. ✅ User query "Flash all the Office Hue lights" will match:
   - Office Back Left (via device name)
   - Office Front Left (via device name)
   - Office Front Right (via device name)
   - Office Back Right (via device name)
   - Office Go (via device name)

## Testing

To verify the fix works:
1. Restart ai-automation-service
2. Submit query: "Flash all the Office Hue lights for 30 secs at the top of every hour"
3. Verify clarification detector finds Office Hue lights
4. Verify automation is created with correct devices

## Related Issues

- Entity name fields are NULL (discovery needs to run to populate them)
- This fix provides a workaround by using device names
- Once discovery runs and populates entity names, both will work

## Files Modified

1. `services/ai-automation-service/src/services/clarification/detector.py`
   - Added device name enrichment logic

2. `services/ai-automation-service/src/nl_automation_generator.py`
   - Added device_id to entities_by_domain

3. `services/ai-automation-service/src/api/ask_ai_router.py`
   - Added device_id to entities_by_domain (2 locations)

