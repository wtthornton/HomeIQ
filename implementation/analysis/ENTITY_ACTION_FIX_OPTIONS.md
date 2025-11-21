# Entity ID and Action Fix Options

**Date:** November 20, 2025  
**Issue:** Device "Office" correctly identified, but wrong entity ID or action associated with device

---

## Problem Summary

From the error notification and automation details:
- ✅ **Device correctly identified:** "Office" 
- ❌ **Entity ID issue:** Using `light.wled` but actual entity might be `light.wled_office` or similar
- ❌ **Scene entity validation:** `scene.office_wled_before_random` flagged as invalid (but it's created dynamically)
- ⚠️ **Scene ID inconsistency:** Error mentions `scene.office_wled_before_random` but YAML shows `office_wled_before_show`

---

## Fix Options

### Option 1: Improve Entity ID Mapping Accuracy (RECOMMENDED)

**Problem:** The `map_devices_to_entities()` function might be mapping "Office" to `light.wled` instead of the actual entity like `light.wled_office`.

**Solution:** Enhance entity matching to prioritize area + device type combinations.

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:1176-1621`

**Changes:**
1. **Add area-aware matching priority:**
   ```python
   # When device name is "Office" and area is "office", prioritize entities with:
   # - area_id == "office" 
   # - entity_id contains "office" or "wled"
   # - friendly_name contains "Office"
   ```

2. **Improve fuzzy matching for location-based devices:**
   ```python
   # Current: Matches "Office" → any entity with "office" in name
   # Enhanced: Matches "Office" → entities in "office" area + WLED domain
   ```

3. **Add entity ID validation feedback loop:**
   ```python
   # After mapping, verify the entity actually exists and works
   # If validation fails, try alternative mappings with higher area/type priority
   ```

**Pros:**
- ✅ Fixes root cause of wrong entity ID
- ✅ Improves accuracy for all location-based device queries
- ✅ Prevents future similar issues

**Cons:**
- ⚠️ Requires testing with various device/area combinations
- ⚠️ May need adjustment for edge cases

---

### Option 2: Post-YAML Entity ID Correction

**Problem:** YAML is generated with wrong entity ID (`light.wled`), but we can detect and fix it.

**Solution:** After YAML generation, scan for entity IDs that don't match validated_entities and replace them.

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:8778-8800`

**Changes:**
1. **Enhanced entity replacement logic:**
   ```python
   # After YAML generation, extract all entity IDs
   # Compare against validated_entities
   # If entity ID in YAML doesn't match any validated_entity:
   #   - Find best match from validated_entities
   #   - Replace in YAML
   #   - Log the correction
   ```

2. **Use entity similarity matching:**
   ```python
   # If YAML has "light.wled" but validated_entities has "light.wled_office":
   #   - Calculate similarity (domain match + partial name match)
   #   - Replace if similarity > threshold
   ```

**Pros:**
- ✅ Catches errors after YAML generation
- ✅ Works as safety net for LLM mistakes
- ✅ Can fix multiple entity ID issues at once

**Cons:**
- ⚠️ Doesn't fix root cause (entity mapping)
- ⚠️ May incorrectly replace valid entity IDs in edge cases

---

### Option 3: Exclude Dynamically Created Scenes from Validation

**Problem:** Scene entities created by `scene.create` are being validated, but they don't exist until runtime.

**Solution:** Track which scenes are created dynamically and exclude them from validation.

**Location:** 
- `services/ai-automation-service/src/services/entity_id_validator.py:366-415`
- `services/ai-automation-service/src/api/ask_ai_router.py:8368-8552`

**Changes:**
1. **Extract created scenes before validation:**
   ```python
   # In entity_id_validator.py
   def _extract_scenes_created(self, actions: Any, created_scenes: set[str]) -> None:
       # Already implemented! Just need to use it in validation
   ```

2. **Filter out created scenes during validation:**
   ```python
   # In ask_ai_router.py approval flow
   created_scenes = entity_id_extractor._extract_scenes_created(parsed_yaml.get('action', []))
   entities_to_validate = [eid for eid in unique_entity_ids if eid not in created_scenes]
   logger.info(f"🔍 Excluding {len(created_scenes)} dynamically created scenes from validation")
   ```

**Reference:** See `implementation/analysis/SCENE_ENTITY_VALIDATION_ERROR_ANALYSIS.md` for detailed implementation.

**Pros:**
- ✅ Fixes false positive validation errors
- ✅ Already partially implemented (extraction method exists)
- ✅ Aligns with Home Assistant 2025 patterns

**Cons:**
- ⚠️ Only fixes scene validation, not entity ID mapping issue

---

### Option 4: Improve LLM Prompt for Entity ID Usage

**Problem:** LLM might be generating entity IDs that don't match validated_entities exactly.

**Solution:** Strengthen the prompt to emphasize using EXACT entity IDs from validated_entities.

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:2219-2231`

**Changes:**
1. **Add explicit entity ID examples:**
   ```python
   validated_entities_text = f"""
   VALIDATED ENTITIES (ALL verified to exist in Home Assistant - use these EXACT entity IDs):
   {chr(10).join(entity_id_list)}
   {mapping_text}
   
   CRITICAL RULES:
   1. Use ONLY the entity IDs listed above - DO NOT modify them
   2. If device is "Office" and mapping shows "Office": "light.wled_office", 
      use EXACTLY "light.wled_office" - NOT "light.wled" or "light.office"
   3. Entity IDs are case-sensitive and format-sensitive
   4. Scene IDs should be derived from the entity ID (e.g., "light.wled_office" → "office_wled_before_show")
   """
   ```

2. **Add validation examples:**
   ```python
   # Show examples of correct vs incorrect usage
   EXAMPLES:
   ✅ CORRECT: entity_id: light.wled_office (from validated list)
   ❌ WRONG: entity_id: light.wled (not in validated list)
   ❌ WRONG: entity_id: light.office (not in validated list)
   ```

**Pros:**
- ✅ Prevents LLM from generating wrong entity IDs
- ✅ Low risk, high impact
- ✅ Easy to implement

**Cons:**
- ⚠️ LLM might still make mistakes despite clear instructions
- ⚠️ Doesn't fix existing entity mapping issues

---

### Option 5: Scene ID Consistency Fix

**Problem:** Scene ID in YAML (`office_wled_before_show`) doesn't match error message (`scene.office_wled_before_random`).

**Solution:** Ensure scene IDs are consistently generated from entity IDs and device names.

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:2143-2300` (YAML generation prompt)

**Changes:**
1. **Add scene ID generation guidelines:**
   ```python
   SCENE ID GENERATION RULES:
   - Scene IDs should be derived from the entity ID being snapshotted
   - Format: {entity_name_without_domain}_{purpose}
   - Example: entity_id "light.wled_office" → scene_id "office_wled_before_show"
   - Use consistent naming: "before_show", "before_random", "restore", etc.
   - Scene entity ID format: scene.{scene_id}
   ```

2. **Add validation for scene ID consistency:**
   ```python
   # After YAML generation, verify scene IDs match expected patterns
   # If scene.create uses "office_wled_before_show", 
   # scene.turn_on should use "scene.office_wled_before_show"
   ```

**Pros:**
- ✅ Prevents scene ID mismatches
- ✅ Makes debugging easier
- ✅ Improves automation reliability

**Cons:**
- ⚠️ Requires LLM to follow naming conventions consistently
- ⚠️ May need post-generation validation/correction

---

## Recommended Implementation Order

1. **Option 3 (Scene Validation)** - Quick win, fixes false positive error
2. **Option 1 (Entity Mapping)** - Fixes root cause, most impactful
3. **Option 4 (LLM Prompt)** - Prevents future issues, low risk
4. **Option 2 (Post-YAML Correction)** - Safety net, catches remaining issues
5. **Option 5 (Scene ID Consistency)** - Polish, improves reliability

---

## Testing Strategy

After implementing fixes, test with:

1. **Office WLED automation:**
   - Verify correct entity ID (`light.wled_office` or actual entity)
   - Verify no scene validation errors
   - Verify scene IDs are consistent

2. **Multiple device automation:**
   - Verify all devices map to correct entities
   - Verify area-based matching works

3. **Scene snapshot automation:**
   - Verify dynamically created scenes are excluded from validation
   - Verify scene IDs match between creation and usage

---

## Related Files

- `services/ai-automation-service/src/api/ask_ai_router.py:1176-1621` - Entity mapping
- `services/ai-automation-service/src/api/ask_ai_router.py:2143-2300` - YAML generation
- `services/ai-automation-service/src/api/ask_ai_router.py:8368-8552` - Entity validation
- `services/ai-automation-service/src/services/entity_id_validator.py:366-415` - Scene extraction
- `implementation/analysis/SCENE_ENTITY_VALIDATION_ERROR_ANALYSIS.md` - Scene validation issue

---

## Questions for Review

1. **Which entity ID is correct for "Office" WLED?**
   - Is it `light.wled`, `light.wled_office`, or something else?
   - Can we query Home Assistant to verify?

2. **Priority:**
   - Should we fix entity mapping first (Option 1)?
   - Or fix scene validation first (Option 3) to remove false positive?

3. **Scope:**
   - Should we implement all options?
   - Or focus on specific ones?

