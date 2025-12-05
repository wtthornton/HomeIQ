# Office Lights Automation Review

**Date:** December 4, 2025  
**Status:** ⚠️ Issue Identified - Wrong Lights Selected  
**Automation:** "Office area lights flash red every 5 minutes"

---

## Issue Summary

The automation created for "Office area lights flash red every 5 minutes" includes lights that are **NOT in the office area**:

### ❌ Incorrect Lights in Automation

1. **light.wled** - May be office (unconfirmed)
2. **light.hue_play_1** - Likely not office (name suggests living room)
3. **light.bottom_of_stairs** - ❌ **NOT office** (hallway/stairway)
4. **light.front_front_hallway** - ❌ **NOT office** (hallway)
5. **light.living_room_2** - ❌ **NOT office** (living room)

### Expected Office Lights

Based on entity names, likely office lights include:
- `light.hue_office_back_left` (name contains "office")
- Other lights with "office" in name or assigned to office area

---

## Root Cause Analysis

### 1. Missing Area IDs in Database

**Query:** `GET /api/entities?domain=light&area_id=office`

**Result:** 52 lights returned, but **ALL have `area_id: null`**

```json
{
  "entity_id": "light.hue_office_back_left",
  "area_id": null,  // ❌ Should be "office"
  ...
}
```

**Impact:**
- Area filtering doesn't work
- LLM can't identify which lights belong to office
- System falls back to name matching, which is unreliable

### 2. Context Builder Provides All Lights

**Location:** `services/ha-ai-agent-service/src/services/context_builder.py`

**Issue:** The `EntityInventoryService` fetches ALL entities without area filtering:

```python
entities = await self.data_api_client.fetch_entities(limit=10000)
# No area_id filter applied
```

**Impact:**
- LLM receives all lights in context
- No way to filter by area when user specifies "office"
- LLM must guess which lights belong to office

### 3. System Prompt Relies on Area IDs

**Location:** `services/ha-ai-agent-service/src/prompts/system_prompt.py:318`

**Instruction:**
```
1. Use context to find office lights (search for area_id="office" and domain="light")
```

**Problem:**
- If no lights have `area_id="office"`, this instruction fails
- LLM falls back to name matching or random selection
- Results in wrong lights being selected

---

## Verification Steps

### 1. Check Actual Office Lights

**Query Home Assistant directly:**
```powershell
# Get office area ID
$officeArea = (Invoke-RestMethod -Uri "http://localhost:8123/api/config/area_registry" -Headers @{Authorization="Bearer $env:HA_TOKEN"} | Where-Object { $_.name -like "*office*" }).area_id

# Get lights in office area
Invoke-RestMethod -Uri "http://localhost:8123/api/states" -Headers @{Authorization="Bearer $env:HA_TOKEN"} | Where-Object { $_.entity_id -like "light.*" -and $_.attributes.area_id -eq $officeArea } | Select-Object entity_id
```

### 2. Check Data-API Area Mapping

**Verify area_id is being synced from Home Assistant:**
```powershell
# Check if data-api has area_id for office lights
Invoke-RestMethod -Uri "http://localhost:8006/api/entities?domain=light&area_id=office" | Where-Object { $_.area_id -ne $null } | Select-Object entity_id, area_id
```

### 3. Review Automation YAML

**Check the created automation:**
- Verify entity IDs match office area
- Check if `target.area_id: office` was used (should be preferred)
- Review entity selection logic

---

## Recommended Fixes

### Fix 1: Sync Area IDs to Data-API (CRITICAL)

**Priority:** 🔴 **HIGH**

**Issue:** Lights don't have `area_id` in data-api database

**Solution:**
1. Ensure data-api syncs `area_id` from Home Assistant entity registry
2. Verify entity registry sync includes area assignments
3. Check if area_id is being extracted but not stored

**Files to Check:**
- `services/data-api/src/api/routers/entities.py` - Entity sync logic
- `services/data-api/src/services/entity_sync.py` - Area ID extraction
- Database schema - Ensure `area_id` column exists and is populated

### Fix 2: Filter Context by Area (MEDIUM)

**Priority:** 🟡 **MEDIUM**

**Issue:** Context builder provides all lights, not filtered by area

**Solution:**
1. Detect area from user request ("office", "kitchen", etc.)
2. Filter entity inventory by area before sending to LLM
3. Add area-specific context section when area is mentioned

**Implementation:**
```python
# In context_builder.py
async def build_context(self, area_filter: str | None = None) -> str:
    if area_filter:
        # Fetch only entities in specified area
        entities = await self.data_api_client.fetch_entities(
            domain="light",
            area_id=area_filter
        )
```

### Fix 3: Enhance System Prompt (LOW)

**Priority:** 🟢 **LOW**

**Issue:** System prompt assumes area_id exists

**Solution:**
1. Add fallback instructions when area_id is missing
2. Use name-based matching as secondary method
3. Warn LLM to verify area matches before selecting entities

**Example:**
```
If area_id is not available, use name-based matching:
- Look for "office" in entity_id or friendly_name
- Verify entity name suggests correct location
- When in doubt, ask user to clarify
```

---

## Immediate Action Items

1. **✅ Verify Office Lights** - Query Home Assistant to get actual office light entity IDs
2. **🔧 Fix Area ID Sync** - Ensure data-api stores area_id for all entities
3. **🔧 Update Automation** - Manually fix the created automation with correct office lights
4. **📝 Test Area Filtering** - Verify area filtering works after fix

---

## Related Issues

- **Entity Resolution:** Similar issues with location-aware entity matching (see `ENTITY_RESOLUTION_LOCATION_AWARE_FIX.md`)
- **Area Filtering:** Previous fixes for area filtering in ai-automation-service (see `AREA_FILTERING_FIX_SUMMARY.md`)
- **Context Enhancement:** Context builder improvements needed for area-specific queries

---

## Next Steps

1. **User Action:** Manually edit the automation to use correct office lights
2. **Developer Action:** Fix area_id sync in data-api
3. **Testing:** Create new automation with "office" area to verify fix
4. **Documentation:** Update system prompt with fallback instructions

