# Device Selection Fix - Implementation Complete

## Summary

Fixed the issue where only 1 device was selected instead of 3 (presence sensor, ceiling lights, WLED) for the user query about flashing office lights and WLED fireworks.

## Changes Made

### 1. Enhanced Domain Extraction (`services/ai-automation-service/src/services/entity_validator.py`)

**Added "presence", "presence sensor", "occupancy", "contact" to binary_sensor keywords:**
- Line 418: Updated `binary_sensor` keywords to include presence-related terms
- This ensures presence sensors are detected when user mentions "presence sensor"

**Added new method `_extract_all_domains_from_query`:**
- Lines 431-466: New method that extracts ALL domains from query (not just one)
- Returns list of domains instead of single domain
- Example: "presence sensor triggers lights" → ["binary_sensor", "light"]

### 2. Multi-Domain Entity Fetching (`services/ai-automation-service/src/api/ask_ai_router.py`)

**Updated entity fetching to query ALL domains:**
- Lines 2474-2525: Changed from single-domain to multi-domain fetching
- Now fetches entities for each domain found in query (binary_sensor, light, etc.)
- Combines results from all domains
- Falls back to location-only fetch if no domains found

**Before:**
```python
query_domain = entity_validator._extract_domain_from_query(query)  # Returns "light" only
available_entities = await entity_validator._get_available_entities(
    domain=query_domain,  # Only "light" domain
    area_id=query_location
)
```

**After:**
```python
query_domains = entity_validator._extract_all_domains_from_query(query)  # Returns ["binary_sensor", "light"]
for domain in query_domains:
    available_entities = await entity_validator._get_available_entities(
        domain=domain,
        area_id=query_location
    )
    all_available_entities.extend(available_entities)
```

### 3. Fixed Entity Filtering Logic (`services/ai-automation-service/src/api/ask_ai_router.py`)

**Added generic term detection to prevent over-filtering:**
- Lines 2631-2678: Added logic to detect generic domain terms vs. specific device names
- Generic terms (e.g., "lights", "sensor", "led") don't trigger filtering
- Only specific device names (e.g., "Office Ceiling Light 1") trigger filtering
- If all extracted names are generic, includes ALL query-context entities

**Before:**
- Filtered entity context to only entities matching extracted names
- "lights" didn't match "Office Ceiling Light 1", so ceiling lights were excluded
- "sensor" didn't match "PS FP2 - Desk", so presence sensor was excluded

**After:**
- Detects that "lights", "sensor", "led" are generic terms
- Doesn't filter when names are generic
- Includes ALL entities from query context (location + domains)

### 4. Enhanced WLED Fireworks Effect Detection (`services/ai-automation-service/src/api/ask_ai_router.py`)

**Added effect extraction for WLED devices:**
- Lines 2307-2319: Added logic to detect WLED effects from action summary
- Checks for common WLED effects: fireworks, sparkle, rainbow, strobe, pulse, etc.
- Properly populates service calls with effect parameter

**Before:**
- Fireworks effect mentioned in query but not captured in technical prompt

**After:**
- Detects "fireworks" in action summary/description
- Adds service call: `light.turn_on` with `effect: "fireworks"`

## Expected Results

After these fixes, the system should now:

1. **Extract ALL domains from query:**
   - "presence sensor triggers lights" → ["binary_sensor", "light"]

2. **Fetch entities for ALL domains:**
   - Binary sensors in office (including `binary_sensor.ps_fp2_desk`)
   - Lights in office (including ceiling lights and WLED)

3. **Include ALL query-context entities when names are generic:**
   - All office lights (ceiling lights + WLED)
   - All office sensors (presence sensor at desk)

4. **Properly detect WLED fireworks effect:**
   - Technical prompt includes `effect: "fireworks"` for WLED entity

## Testing

To verify the fix:

1. Submit query: "When the presents sensor triggers at my desk flash office lights for 15 secs - Flash them fast and muti-color then return them to their original attributes. Also make the office led show fireworks for 30 secs."

2. Check debug panel:
   - Should show 3+ devices selected:
     - Presence sensor: `binary_sensor.ps_fp2_desk`
     - Office lights: Multiple ceiling light entities
     - Office LED: `light.wled` (or similar)

3. Check technical prompt:
   - Trigger: `binary_sensor.ps_fp2_desk` state change
   - Actions: Flash office lights (multi-color, 15s) + WLED fireworks effect (30s)
   - Service calls: `light.turn_on` with effect="fireworks" for WLED

## Files Modified

1. `services/ai-automation-service/src/services/entity_validator.py`
   - Added "presence", "presence sensor", "occupancy", "contact" to binary_sensor keywords
   - Added `_extract_all_domains_from_query` method

2. `services/ai-automation-service/src/api/ask_ai_router.py`
   - Updated entity fetching to query all domains
   - Fixed entity filtering to not over-filter on generic terms
   - Enhanced WLED effect detection in technical prompt generation

3. `implementation/analysis/DEVICE_SELECTION_ISSUE_ANALYSIS.md`
   - Created analysis document explaining root causes

## Status

✅ **FIXED AND DEPLOYED**

Service rebuilt and restarted. Ready for testing.

