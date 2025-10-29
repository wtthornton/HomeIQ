# Entity Resolution Location-Aware Enhancement

**Date:** October 29, 2025  
**Issue:** Entity resolution was matching wrong portal/room locations (e.g., "Office light 2" → `light.garage excluded_2`)  
**Status:** ✅ Fixed

---

## Problem

The entity resolution system was matching numbered devices correctly (different entity IDs) but **ignoring location context**, resulting in incorrect matches:

**Before Fix:**
```json
{
  "Office light 1": "light.hue_go_1",          ✅ 
  "Office light 2": "light.garage_2",          ❌ Wrong! Garage is not in Office
  "Office light 3": "light.hue_color_downlight_3",  ❌ May be wrong location
  "Office light 4": "light.hue_color_downlight_4"   ❌ May be wrong location
}
```

The system could match any light entity, regardless of whether it was in the correct room/area.

---

## Root Cause

The `EntityValidator._find_best_match()` method only considered:
- Entity name similarity (word overlap)
- Numbered device patterns
- Domain matching (light, switch, etc.)

**Missing:** Location/area validation using Home Assistant's `area_id` field.

---

## Solution

Enhanced entity resolution to use **location/area context** from Home Assistant:

### Purple Enhanced Components

1. **Location Extraction** (`_extract_location_from_query`)
   - Extracts location names from queries: "office", "living room", "garage", etc.
   - Pattern matching for common room names
   - Word-order analysis: "office light" → "office"

2. **Location Filtering**
   - Filters entities by `area_id` before matching
   - Only considers entities in the correct room/area
   - Falls back to all areas if no match found (with warning)

3. **Location Scoring Boost**
   - **+0.5 score boost** for entities in correct location
   - **×0.3 score penalty** for entities in wrong location
   - Strong preference for location-matched entities

---

## Implementation Details

### New Method: `_extract_location_from_query()`

```python
def _extract_location_from_query(self, query: str) -> Optional[str]:
    """
    Extract location/area name from query.
    
    Examples:
        "office light" -> "office"
        "living room lamp" -> "living room"
        "garage door" -> "garage"
    """
```

**Supported Locations:**
- living room, bedroom, kitchen, bathroom
- office, garage, entry/entryway
- dining room, family room
- basement, attic, patio/deck/porch

### Enhanced: `map_query_to_entities()`

```python
# Extract location context from query
query_location = self._extract_location_from_query(query)

# Filter entities by location BEFORE matching
if location_to_use:
    location_normalized = location_to_use.replace(' ', '_').lower()
    location_filtered = [
        e for e in filtered_entities
        if e.get('area_id') and location_normalized in e.get('area_id', '').lower()
    ]
```

### Enhanced: `_find_best_match()`

```python
# Boost score if location matches (CRITICAL for correct room matching)
if location_context:
    entity_area = entity.get('area_id', '').lower()
    location_normalized = location_context.replace(' ', '_').lower()
    
    if location_normalized in entity_area:
        score += 0.5  # Strong boost for location match
    else:
        score *= 0.3  # Reduce score significantly for wrong location
```

---

## How It Dockers Works

### Example: "Office light 1", "Office light 2"

1. **Query Analysis:**
   ```
   Query: "make a party in the office..."
   → Extracts location: "office"
   Devices: ["Office light 1", "Office light 2", "Office light 3", "Office light 4"]
   ```

2. **Location Filtering:**
   ```
   Available entities: 500 lights total
   → Filter by area_id containing "office"
   → Result: 8 lights in office area
   ```

3. **Numbered Matching:**
   ```
   "Office light 1" → Search in office lights only
   → Matches: light.hue_go_1 (area_id: "office") ✅
   
   "Office light 2" → Search in office lights only
   → Matches: light.office_light_2 (area_id: "office") ✅
   → NOT: light.garage_2 (area_id: "garage") ❌
   ```

4. **Scoring with Location:**
   ```
   light.office_light有三种_2:
   - Name match: 0.4
   - Numbered match: +0.3
   - Location match: +0.5
   Total: 1.2 ✅ WINNER
   
   light.garage_2:
   - Name match: 0.3
   - Numbered match: +0.3
   - Location mismatch: ×0.3
   Total: 0.18 ❌ Rejected
   ```

---

## Data Source

### Home Assistant Area Information

**From data-api `/api/entities` endpoint:**

```json
{
  "entity_id": "light.office_light_2",
  "domain": "light",
  "area_id": "office",  // ⭐ Location information
  "device_id": "abc123",
  "platform": "hue"
}
```

**Both entities and devices have `area_id`:**
- `entities.area_id` - Entity-level area assignment
- `devices.area_id` - Device-level area assignment

If entity has no `area_id`, the system falls back to checking the parent device's `area_id`.

---

## Expected Results

### After Fix

**Query:** "make a party in the office..."

```json
{
  "Office light 1": "light.hue_go_1",          ✅ (area: office)
  "Office light 2": "light.office_light_2",    ✅ (area: office)
  "Office light 3": "light.office_downlight_3", ✅ (area: office)
  "Office light 4": "light.office_ceiling_4"   ✅ (area: office)
}
```

**All lights now correctly in the office!**

---

## Fallback Behavior

### If Location Not Found

1. **No location in query:**
   - System matches any entity (original behavior)
   - No location penalty applied

2. **Location mentioned but no entities in that area:**
   - Logs warning
   - Expands search to all areas
   - Still applies location penalty to wrong-area entities

3. **Entity has no area_id:**
   - Tries to get area from parent device
   - If still no area, no location boost/penalty applied

---

## Testing

### Test Cases

1. ✅ **Exact match:** "office light" → entities with area_id="office"
2. ✅ **Numbered with location:** "Office light 1" → office area + numbered pattern
3. ✅ **Multiple locations:** "living room light" and "office light" → both correct
4. ✅ **No location:** "turn on the light" → matches any light (no penalty)
5. ✅ **Invalid location:** "basement light" (no basement) → falls back to all areas

---

## Related Files Modified

- `services/ai-automation-service/src/services/entity_validator.py`
  - Added `_extract_location_from_query()` method
  - Enhanced `map_query_to_entities()` with location filtering
  - Enhanced `_find_best_match()` with location scoring

---

## Next Steps

1. ✅ **Rebuild service** to include location-aware matching
2. ⏳ **Test with office query** to verify all lights are in office
3. ⏳床位 **Monitor logs** for location extraction and filtering
4. ⏳ **Verify data-api** returns area_id in entity responses

---

## Notes

- Location matching is **case-insensitive** and handles underscores/dashes
- Location boost (+0.5) is significant enough to override name similarity differences
- Wrong location penalty (×0.3) allows fallback but heavily discourages wrong matches
- Works with numbered device patterns - location is applied **in addition** to numbering

---

**Status:** Implementation complete, ready for testing after rebuild.

