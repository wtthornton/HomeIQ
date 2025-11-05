# Device Selection Issue Analysis

## Problem Summary

User query: "When the presents sensor triggers at my desk flash office lights for 15 secs - Flash them fast and muti-color then return them to their original attributes. Also make the office led show fireworks for 30 secs."

**Expected Devices:**
1. Presence sensor at desk: `binary_sensor.ps_fp2_desk` (Presence-Sensor-FP2-8B8A)
2. Office lights (ceiling lights): Multiple office light entities
3. Office LED (WLED): `light.wled` (for fireworks effect)

**Actual Result:**
- Only 1 device selected: "Office" (mapped to `light.wled`)
- Missing: Presence sensor, ceiling lights
- Missing: Fireworks effect in technical prompt

## Root Causes

### 1. Domain Extraction Too Narrow (CRITICAL)
**Location:** `services/ai-automation-service/src/services/entity_validator.py:392-422`

**Issue:** The `_extract_domain_from_query` function only extracts "light" from the query, missing "binary_sensor" for "presence sensor triggers at my desk".

**Current Logic:**
```python
domain_keywords = {
    "light": ["light", "lamp", "bulb", "led", "brightness", "dim", "bright", "illuminate"],
    "binary_sensor": ["motion", "door sensor", "window sensor", "door", "window"],
    # ...
}
```

**Problem:** "presence sensor" is not in the keywords list, so binary_sensor entities are never fetched.

**Fix:** Add "presence", "presence sensor", "occupancy" to binary_sensor keywords.

### 2. Entity Filtering Too Aggressive (CRITICAL)
**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:2603-2632`

**Issue:** The pre-filtering logic filters entity context to only include entities matching extracted device names. But extracted names are generic ("lights", "led", "sensor"), which don't match specific friendly names.

**Current Logic:**
```python
extracted_device_names = [e.get('name', '').lower() for e in entities if e.get('name')]
# extracted_device_names = ["lights", "led", "sensor"]  # Generic names from NER
for entity_id in resolved_entity_ids:
    # Check if entity matches any extracted device name
    if (device_name in friendly_name or friendly_name in device_name):
        matching_entity_ids.add(entity_id)
```

**Problem:** 
- "lights" doesn't match "Office Ceiling Light 1", "Office Ceiling Light 2"
- "sensor" doesn't match "PS FP2 - Desk" (friendly_name for binary_sensor.ps_fp2_desk)
- Only "led" matches "Office" (WLED friendly_name)

**Fix:** 
- Don't filter by generic extracted names (domain terms like "lights", "sensor", "led")
- Only filter if we have very specific device names (e.g., "Office Ceiling Light 1")
- Include all entities from the query context (location + domain) when extracted names are generic

### 3. Missing Multi-Domain Support (CRITICAL)
**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:2474-2484`

**Issue:** The code only extracts ONE domain from the query, but the user's query mentions both "light" AND "binary_sensor" domains.

**Current Logic:**
```python
query_domain = entity_validator._extract_domain_from_query(query)  # Returns "light" only
available_entities = await entity_validator._get_available_entities(
    domain=query_domain,  # Only "light" domain
    area_id=query_location  # "office"
)
```

**Problem:** Binary sensor entities are never fetched because domain is limited to "light".

**Fix:**
- Extract ALL domains from query (not just one)
- Fetch entities for all domains
- Combine results

### 4. Trigger Entity Not Extracted (HIGH)
**Location:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`

**Issue:** The entity extraction doesn't properly identify "presence sensor at desk" as a specific binary_sensor entity.

**Problem:** Even if binary_sensor domain is queried, the specific entity `binary_sensor.ps_fp2_desk` might not be identified because:
- NER extracts generic "sensor" or "presence sensor"
- Fuzzy matching might not find "PS FP2 - Desk" friendly_name

**Fix:**
- Improve entity extraction to recognize "presence sensor at desk" → binary_sensor.ps_fp2_desk
- Add better fuzzy matching for "desk" location context

### 5. WLED Fireworks Effect Not Captured (MEDIUM)
**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:2128-2432`

**Issue:** The technical prompt generation doesn't properly extract the "fireworks" effect from the action summary.

**Current Logic:**
```python
# Extract service calls from action_summary
if "fireworks" in action_summary.lower():
    # Should extract effect="fireworks" but might not
```

**Fix:**
- Improve service call extraction to recognize "fireworks" as an effect
- Ensure effect is properly populated in technical prompt

## Solution Plan

### Phase 1: Fix Domain Extraction (IMMEDIATE)
1. Add "presence", "presence sensor", "occupancy" to binary_sensor keywords
2. Modify `_extract_domain_from_query` to return ALL domains (not just one)
3. Update entity fetching to query all domains

### Phase 2: Fix Entity Filtering (IMMEDIATE)
1. Add logic to detect generic vs. specific device names
2. Only filter entity context if extracted names are specific (not generic domain terms)
3. Include all query-context entities when names are generic

### Phase 3: Improve Trigger Entity Extraction (HIGH)
1. Enhance entity extraction to better handle "presence sensor at {location}"
2. Add location-aware fuzzy matching for binary_sensor entities
3. Ensure trigger entities are included in enriched_data

### Phase 4: Fix WLED Fireworks Effect (MEDIUM)
1. Improve service call extraction to recognize effects
2. Ensure effect is properly captured in technical prompt

## Expected Outcome

After fixes:
- **3 devices selected:**
  1. Presence sensor: `binary_sensor.ps_fp2_desk`
  2. Office lights: All office light entities (ceiling lights)
  3. Office LED: `light.wled`
- **Technical prompt includes:**
  - Trigger: `binary_sensor.ps_fp2_desk` state change
  - Actions: Flash office lights (multi-color, 15s) + WLED fireworks effect (30s)
  - Service calls: `light.turn_on` with effect="fireworks" for WLED

