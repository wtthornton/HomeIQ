# Entity Resolution and YAML Generation Fix Plan

**Date:** November 1, 2025  
**Status:** 🔍 Analysis Complete - Ready for Implementation

## Problem Summary

The system is generating YAML with entity IDs that don't exist in Home Assistant, causing automation creation to fail. The errors show:

- `binary_sensor.office_motion` - NOT FOUND
- `wled.office` - NOT FOUND  
- `light.lr_front_left_ceiling` - NOT FOUND
- `light.lr_back_right_ceiling` - NOT FOUND
- `light.lr_front_right_ceiling` - NOT FOUND
- `light.lr_back_left_ceiling` - NOT FOUND

**Root Cause:** The entity resolution process is finding entities with low confidence scores (0.134-0.235) and mapping them incorrectly, OR the LLM is ignoring the validated_entities mapping and generating fake entity IDs.

## Analysis from Logs

1. **Low Confidence Mappings:**
   - `'LR Front Left Ceiling' -> light.hue_color_downlight_1_6` (confidence: 0.147)
   - `'LR Back Right Ceiling' -> light.hue_color_downlight_2_2` (confidence: 0.235)
   - These are probably the CORRECT entities, but with low confidence

2. **Invalid Entity IDs Generated:**
   - The LLM is generating entity IDs like `light.lr_front_left_ceiling` instead of using `light.hue_color_downlight_1_6`
   - This suggests the LLM is creating entity IDs based on friendly names rather than using validated entity IDs

3. **Entity Resolution Flow:**
   ```
   User Query → extract_entities_with_ha() → entities (friendly names)
   → generate_suggestions_from_query() → suggestions with devices_involved
   → enhance_suggestion_with_entity_ids() → maps friendly names to entity IDs
   → generate_automation_yaml() → LLM generates YAML
   → ❌ LLM ignores validated_entities and creates fake IDs
   ```

## Issues Identified

### Issue 1: Entity Resolution Quality
- Low confidence scores (0.134-0.235) suggest fuzzy matching is too lenient
- Entities being resolved might not actually exist in HA
- Need to verify entities exist in HA BEFORE adding to validated_entities

### Issue 2: LLM Ignoring Validated Entities
- The LLM prompt includes validated_entities, but LLM is still generating fake IDs
- The prompt might not be emphatic enough
- Need stronger enforcement in prompt

### Issue 3: Pre-validation Not Strict Enough
- `pre_validate_suggestion_for_yaml()` tries to enhance entities, but might be using low-confidence mappings
- Need to verify entities exist in HA during pre-validation

### Issue 4: Missing Entity Verification
- `validated_entities` contains entity IDs that haven't been verified against HA
- Need to verify ALL entities in `validated_entities` exist in HA before YAML generation

## Fix Strategy

### Fix 1: Verify Entities Against HA Before Adding to validated_entities

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Change:** Modify `map_devices_to_entities()` and `pre_validate_suggestion_for_yaml()` to verify entities exist in HA before including them.

```python
async def verify_entities_exist_in_ha(
    entity_ids: List[str],
    ha_client: Optional[HomeAssistantClient]
) -> Dict[str, bool]:
    """
    Verify which entity IDs actually exist in Home Assistant.
    
    Returns:
        Dictionary mapping entity_id -> exists (True/False)
    """
    verified = {}
    if not ha_client:
        return {eid: False for eid in entity_ids}
    
    for entity_id in entity_ids:
        try:
            state = await ha_client.get_entity_state(entity_id)
            verified[entity_id] = state is not None
        except Exception:
            verified[entity_id] = False
    
    return verified
```

### Fix 2: Filter Low-Confidence Mappings

**Change:** Only include entity mappings with confidence > threshold (e.g., 0.5) in validated_entities, and verify they exist in HA.

### Fix 3: Strengthen LLM Prompt

**Change:** Make the prompt MORE explicit:
- Add explicit examples showing WRONG vs CORRECT entity IDs
- Show that using fake IDs causes FAILURE
- Emphasize using ONLY the validated entity IDs provided
- Add threat: "If you use any entity ID not in the validated list, the automation WILL FAIL"

### Fix 4: Pre-filter validated_entities in YAML Generation

**Change:** In `generate_automation_yaml()`, before building the prompt:
1. Verify ALL entities in `validated_entities` exist in HA
2. Remove any that don't exist
3. Log warnings about removed entities
4. Build prompt with ONLY verified entities

### Fix 5: Add Entity Existence Check Before Final Validation

**Change:** In `pre_validate_suggestion_for_yaml()`, verify entities exist in HA before adding to enhanced_validated_entities.

## Implementation Plan

1. ✅ Add `verify_entities_exist_in_ha()` helper function
2. ✅ Modify `map_devices_to_entities()` to verify entities exist
3. ✅ Modify `pre_validate_suggestion_for_yaml()` to verify entities exist
4. ✅ Strengthen LLM prompt with explicit warnings about fake entity IDs
5. ✅ Add verification step in `generate_automation_yaml()` before prompt building
6. ✅ Filter out low-confidence mappings (confidence < 0.5)

## Expected Outcome

- Only entities that ACTUALLY exist in HA are included in validated_entities
- LLM receives a stronger prompt emphasizing use of ONLY validated entities
- YAML generation uses only verified entity IDs
- Automation creation succeeds with valid entity IDs

