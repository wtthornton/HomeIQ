# Team Tracker Entity ID Pattern Fix

**Date:** January 2025  
**Status:** ✅ Completed  
**Issue:** Detection not finding Team Tracker entities with prefix patterns

## Problem

Team Tracker is installed in Home Assistant with entities:
- `sensor.dal_team_tracker`
- `sensor.vgk_team_tracker`

But our detection was only matching patterns like:
- `sensor.team_tracker_*` (expects team_tracker at the start)
- `sensor.teamtracker_*`

The actual entity IDs have prefixes before `team_tracker`:
- `sensor.dal_team_tracker` (DAL = Dallas)
- `sensor.vgk_team_tracker` (VGK = Vegas Golden Knights)

## Root Cause

The detection pattern matching was too restrictive:
- Only matched `sensor.team_tracker_*` (team_tracker must be at start)
- Didn't account for entity IDs like `sensor.*_team_tracker` (prefix before team_tracker)

## Solution

### Updated Pattern Matching

**File:** `services/device-intelligence-service/src/api/team_tracker_router.py`

**Changes:**

1. **More Flexible Entity ID Matching:**
   ```python
   entity_id_match = (
       "team_tracker" in entity_id or  # Matches dal_team_tracker, vgk_team_tracker, team_tracker_cowboys
       "teamtracker" in entity_id or   # Matches teamtracker_* variations
       entity_id.endswith("_team_tracker") or  # Exact suffix match
       entity_id.startswith("sensor.team_tracker") or  # Starts with team_tracker
       entity_id.startswith("sensor.teamtracker")  # Starts with teamtracker
   )
   ```

2. **Updated SQL Query for Local Database Fallback:**
   ```python
   or_(
       DeviceEntity.platform.in_(platform_variations),
       DeviceEntity.platform.ilike("%team%tracker%"),
       DeviceEntity.entity_id.ilike("%team_tracker%"),  # Matches any entity_id containing team_tracker
       DeviceEntity.entity_id.ilike("%teamtracker%"),   # Matches any entity_id containing teamtracker
       DeviceEntity.entity_id.like("%_team_tracker"),    # Matches entities ending with _team_tracker
       DeviceEntity.entity_id.like("sensor.team_tracker%"),  # Matches sensor.team_tracker*
       DeviceEntity.entity_id.like("sensor.teamtracker%")    # Matches sensor.teamtracker*
   )
   ```

## Patterns Now Matched

✅ `sensor.dal_team_tracker` - Matches via `"team_tracker" in entity_id`  
✅ `sensor.vgk_team_tracker` - Matches via `"team_tracker" in entity_id`  
✅ `sensor.team_tracker_cowboys` - Matches via `startswith("sensor.team_tracker")`  
✅ `sensor.teamtracker_saints` - Matches via `"teamtracker" in entity_id`  
✅ `sensor.any_prefix_team_tracker` - Matches via `endswith("_team_tracker")`  

## Testing

After this fix, detection should find:
- `sensor.dal_team_tracker`
- `sensor.vgk_team_tracker`
- Any other entity with `team_tracker` or `teamtracker` in the entity_id

## Files Modified

1. `services/device-intelligence-service/src/api/team_tracker_router.py`
   - Updated entity_id pattern matching in data-api query
   - Updated SQL query for local database fallback

## Expected Results

- Detection should now find 2 Team Tracker entities
- Status should change from "Not Installed" to "Installed"
- Teams should be configured in the database
- Frontend should show "2 teams configured • 2 active"

