# Prompt Investigation Report: Office Lights Device Mismatch

## Issue Summary

**Problem**: Suggestion mentions "all four Hue lights in the office" but only shows "Hue lightstrip outdoor 1" (which is an OUTDOOR light, not an office light).

**Query**: "I want to flash the hue lights in my office when I set at my desk. Flash the hue lights for 15 sec fast and return to the previous setting after the 15 secs is over."

## Root Cause Analysis

### 1. Entity Extraction Phase

The initial entity extraction likely only extracted:
- Generic terms: "hue lights" or "lights"
- Location: "office" (may or may not have been properly extracted)

**Problem**: The system did not expand "hue lights in my office" to find ALL lights in the office area.

### 2. Entity Resolution Phase

Looking at the code in `ask_ai_router.py` lines 2758-2785:

```python
# If we have extracted entities with names, try to match them
if entities:
    extracted_device_names = [e.get('name', '').lower().strip() for e in entities if e.get('name')]
    if extracted_device_names:
        # Check if extracted names are generic domain terms
        specific_names = [name for name in extracted_device_names if name not in generic_terms]
        
        if specific_names:
            # We have specific device names, filter to match them
            matching_entity_ids = set()
            for entity_id in resolved_entity_ids:
                enriched = enriched_data.get(entity_id, {})
                friendly_name = enriched.get('friendly_name', '').lower()
                # Check if entity matches any specific extracted device name
                for device_name in specific_names:
                    if (device_name in friendly_name or 
                        friendly_name in device_name or
                        device_name in entity_id_lower):
                        matching_entity_ids.add(entity_id)
                        break
```

**Problem**: 
- The filtering only matches against entities that were already resolved in `resolved_entity_ids`
- If the initial resolution only found one light (the outdoor light), that's all that gets included
- The system doesn't expand to find ALL lights in the office area based on location context

### 3. Enriched Entity Context

From the database investigation:
- **Enriched Entity Context contains**: Only 1 entity - "Hue lightstrip outdoor 1" (entity_id: `light.hue_lightstrip_outdoor_1_2`)
- **Missing**: All other office lights (should be 4 total based on the suggestion)

**Problem**: The enriched context sent to OpenAI only includes ONE light, and it's the wrong one (outdoor instead of office).

### 4. Clarification Context

**Status**: Need to check if clarification questions were asked and answered.

**Impact**: If clarification was provided (e.g., "all four lights in office"), the system should have:
1. Rebuilt the enriched query
2. Re-extracted entities including the clarification
3. Expanded to find ALL office lights based on the clarification

## Code Flow Issues

### Issue 1: Location-Based Entity Expansion Missing

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Problem**: When the query mentions "office", the system should:
1. Extract "office" as a location/area
2. Query Home Assistant for ALL entities in the "office" area
3. Filter to lights only
4. Include ALL matching lights in the enriched context

**Current Behavior**: The system only includes entities that match the extracted device names (e.g., "hue lights"), not entities that match the location context.

### Issue 2: Entity Filtering Too Aggressive

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py` lines 2764-2785

**Problem**: The filtering logic filters entities based on extracted names, but:
- If extracted names are generic ("hue lights"), it should expand to ALL Hue lights in the specified area
- If location is specified ("office"), it should filter by location FIRST, then by device type/name

**Current Behavior**: Filtering happens without location awareness, so it might match the wrong entities (outdoor light instead of office lights).

### Issue 3: Clarification Context Not Properly Applied

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py` - `provide_clarification` endpoint

**Problem**: Even if clarification was provided (e.g., user selected "all four lights in office"), the system may not have:
1. Properly expanded to find all four office lights
2. Included all four lights in the enriched context
3. Filtered out non-office lights

## Recommended Fixes

### Fix 1: Location-Aware Entity Expansion

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Change**: Add location-based entity expansion when location is mentioned in the query or clarification:

```python
# After entity extraction, check for location context
location_keywords = ['office', 'living room', 'bedroom', 'kitchen', etc.]
mentioned_location = None
for keyword in location_keywords:
    if keyword in query.lower():
        mentioned_location = keyword
        break

# If location is mentioned, expand entities to include ALL devices in that area
if mentioned_location and ha_client:
    # Query HA for all entities in the mentioned area
    area_entities = await ha_client.get_entities_by_area(mentioned_location)
    # Filter to matching domain (e.g., lights)
    area_lights = [e for e in area_entities if e.get('domain') == 'light']
    # Add to resolved_entity_ids if not already present
    for light in area_lights:
        if light.get('entity_id') not in resolved_entity_ids:
            resolved_entity_ids.append(light.get('entity_id'))
```

### Fix 2: Improve Entity Filtering Logic

**File**: `services/ai-automation-service/src/api/ask_ai_router.py` lines 2764-2785

**Change**: When filtering entities, prioritize location matching:

```python
# If location is mentioned, filter by location FIRST
if mentioned_location:
    location_filtered = []
    for entity_id in resolved_entity_ids:
        enriched = enriched_data.get(entity_id, {})
        entity_area = enriched.get('area_name', '').lower()
        if mentioned_location.lower() in entity_area:
            location_filtered.append(entity_id)
    
    if location_filtered:
        # Use location-filtered entities
        filtered_entity_ids_for_prompt = location_filtered
        logger.info(f"🔍 Filtered by location '{mentioned_location}': {len(location_filtered)} entities")
```

### Fix 3: Enhance Clarification Context Handling

**File**: `services/ai-automation-service/src/api/ask_ai_router.py` - `_re_enrich_entities_from_qa`

**Change**: When clarification mentions "all four lights in office", expand to find ALL office lights:

```python
async def _re_enrich_entities_from_qa(
    entities: List[Dict[str, Any]],
    clarification_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Re-enrich entities based on selected entities from Q&A answers.
    
    NEW: If clarification mentions "all X lights in Y area", expand to find ALL matching lights.
    """
    # ... existing code ...
    
    # NEW: Check for "all X lights in Y area" patterns
    for qa in qa_list:
        answer = qa.get('answer', '').lower()
        # Pattern: "all four lights in office"
        import re
        all_pattern = re.search(r'all (\d+) lights? in ([\w\s]+)', answer)
        if all_pattern:
            count = int(all_pattern.group(1))
            area = all_pattern.group(2).strip()
            
            # Find ALL lights in that area
            area_lights = await ha_client.get_entities_by_area(area, domain='light')
            if len(area_lights) >= count:
                # Add all matching lights to entities
                for light in area_lights[:count]:
                    entity_id = light.get('entity_id')
                    if entity_id not in [e.get('entity_id') for e in entities]:
                        entities.append({
                            'entity_id': entity_id,
                            'friendly_name': light.get('friendly_name'),
                            'name': light.get('friendly_name'),
                            'domain': 'light',
                            'selected_from_clarification': True
                        })
```

## Testing Recommendations

1. **Test Case 1**: Query with location + generic device type
   - Query: "flash all hue lights in my office"
   - Expected: All office Hue lights included in enriched context
   - Actual: Check if all office lights are included

2. **Test Case 2**: Clarification with "all X lights in Y area"
   - Query: "flash lights in office"
   - Clarification: "all four lights in office"
   - Expected: All four office lights included
   - Actual: Check if all four are included

3. **Test Case 3**: Location mismatch detection
   - Query: "flash lights in office"
   - Enriched context includes outdoor light
   - Expected: System should detect mismatch and filter out outdoor light
   - Actual: Check if location filtering works

## Next Steps

1. ✅ Identify root cause (this document)
2. ⏳ Implement location-aware entity expansion
3. ⏳ Improve entity filtering with location priority
4. ⏳ Enhance clarification context handling
5. ⏳ Add tests for location-based queries
6. ⏳ Verify fix with actual query

## Database Query for Verification

To check if the issue is resolved, query the database:

```sql
SELECT query_id, original_query, suggestions 
FROM ask_ai_queries 
WHERE original_query LIKE '%office%' 
ORDER BY created_at DESC 
LIMIT 5;
```

Then check the `suggestions` JSON for:
- `debug.user_prompt` - Should contain ALL office lights in enriched context
- `debug.entity_context_stats` - Should show all office lights included
- `validated_entities` - Should include all office lights, not outdoor lights

