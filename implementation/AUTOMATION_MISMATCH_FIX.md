# Automation Mismatch Fix

**Date:** January 16, 2026  
**Status:** ✅ Root Cause Fixed, ⚠️ Service Startup Issue Remaining

## Root Cause Identified

The mismatch was caused by using the **wrong Home Assistant API endpoint**. The service was calling:
```
GET /api/config/automation/config  ❌ (404 Not Found)
```

But the correct endpoint is:
```
GET /api/states  ✅ (then filter for automation.* entities)
```

## Fix Applied

**File:** `services/ai-automation-service-new/src/clients/ha_client.py`

**Changed:** Updated `list_automations()` method to:
1. Use `/api/states` endpoint instead of `/api/config/automation/config`
2. Filter results for entities starting with `automation.`
3. Add better error handling and logging

**Code Change:**
```python
async def list_automations(self) -> list[dict[str, Any]]:
    """
    List all automations from Home Assistant.
    
    Uses /api/states endpoint and filters for automation.* entities.
    This is the correct Home Assistant API endpoint.
    """
    if not self.ha_url or not self.access_token:
        logger.warning("Home Assistant URL or token not configured - cannot list automations")
        return []
    
    url = f"{self.ha_url}/api/states"  # ✅ Correct endpoint
    
    try:
        response = await self.client.get(url)
        response.raise_for_status()
        all_states = response.json()
        
        # Filter for automation entities
        if isinstance(all_states, list):
            automations = [
                state for state in all_states
                if state.get('entity_id', '').startswith('automation.')
            ]
            logger.info(f"✅ Found {len(automations)} automations in Home Assistant")
            return automations
        else:
            logger.warning(f"Unexpected response format from /api/states: {type(all_states)}")
            return []
    except httpx.HTTPStatusError as e:
        logger.error(f"Home Assistant API error listing automations: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.HTTPError as e:
        logger.error(f"Failed to connect to Home Assistant: {e}")
        return []
```

## Additional Fix

**File:** `services/ai-automation-service-new/src/api/deployment_router.py`

**Changed:** Removed invalid `db: DatabaseSession = None` parameter from `deploy_suggestion()` function (line 35). FastAPI dependencies cannot have `= None` defaults when using `Annotated` types.

## Additional Fix Applied ✅

**File:** `services/ai-automation-service-new/src/api/preference_router.py`

**Issue:** FastAPI type annotation errors with `AsyncSession | None = None` parameters

**Fix:** Removed unused `db: AsyncSession | None = None` parameters from:
- `get_preferences()` function (line 59)
- `update_preferences()` function (line 81)

Since these are stub implementations that don't use the database, the parameters were removed entirely. Also removed the unused `AsyncSession` import.

**Code Review:** ✅ Passed with score 80/100 (above 70 threshold)

## Testing ✅

**Status:** All fixes applied and tested successfully!

1. **Test the endpoint:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8036/api/deploy/automations" | ConvertTo-Json -Depth 3
   ```

2. **Actual Result (Verified):**
   ```json
   {
       "automations": [
           {
               "entity_id": "automation.office_motion_lights_on_off_after_5_minutes_no_motion",
               "state": "on",
               "attributes": {
                   "friendly_name": "Office motion lights on, off after 5 minutes no motion",
                   "id": "office_motion_lights_on__off_after_5_minutes_no_motion",
                   "last_triggered": null,
                   "mode": "restart",
                   "current": 0
               },
               "last_changed": "2026-01-12T21:42:22.553976+00:00",
               ...
           },
           {
               "entity_id": "automation.turn_on_office_lights_on_presence",
               "state": "on",
               "attributes": {
                   "friendly_name": "Turn on Office Lights on Presence",
                   "id": "turn_on_office_lights_on_presence",
                   "last_triggered": "2026-01-14T22:56:41.101100+00:00",
                   "mode": "single",
                   "current": 0
               },
               "last_changed": "2026-01-14T01:54:26.733643+00:00",
               ...
           }
       ]
   }
   ```

3. **UI Status:** The "Deployed Automations" page at `localhost:3001/deployed` should now show both automations when you refresh the page.

## Status: ✅ COMPLETE

All issues have been fixed:
1. ✅ Fixed API endpoint from `/api/config/automation/config` to `/api/states`
2. ✅ Fixed FastAPI dependency errors in `deployment_router.py`
3. ✅ Fixed FastAPI dependency errors in `preference_router.py`
4. ✅ Service rebuilt and restarted successfully
5. ✅ API endpoint verified - returns both automations correctly

## Related Files

- `services/ai-automation-service-new/src/clients/ha_client.py` - Fixed API endpoint
- `services/ai-automation-service-new/src/api/deployment_router.py` - Fixed FastAPI dependency
- `services/ai-automation-service-new/src/api/preference_router.py` - Needs similar fix
- `implementation/AUTOMATION_MISMATCH_DIAGNOSIS.md` - Original diagnosis
