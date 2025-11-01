# Automation Entity Validation Fix Plan

**Date:** October 21, 2025  
**Status:** Analysis Complete - Fix Plan Ready

## Problem Summary

Automation creation is failing with "Entity not found" errors for:
- `wled.office` (appears twice)
- `light.lr_back_left_ceiling`
- `light.lr_front_right_ceiling`
- `light.lr_back_right_ceiling`
- `light.lr_front_left_ceiling`
- `binary_sensor.office_motion`

**Natural Language Query:** "sit at my desk in my office I want the w all four ceiling lights to Natural light"

**Root Cause:** The LLM (OpenAI) is generating fake entity IDs instead of using real Home Assistant entities, despite entity validation existing in the codebase.

## Root Cause Analysis

### Issue 1: Entity Resolution Produces Low-Confidence Matches

**Evidence from Logs:**
```
🔍 SCORING WARNING: Low confidence (0.147) for 'LR Front Left Ceiling' -> light.hue_color_downlight_1_6
🔍 SCORING WARNING: Low confidence (0.235) for 'LR Back Right Ceiling' -> light.hue_color_downlight_2_2
```

**Problem:** The `map_query_to_entities` method finds potential matches but with very low confidence scores (14.7%, 23.5%). These low-confidence matches are likely being filtered out or ignored, causing the LLM to generate fake entity IDs.

**Location:** `services/ai-automation-service/src/services/entity_validator.py:600-700` (matching logic)

### Issue 2: LLM Ignores Validated Entities in Prompt

**Evidence:** Despite `validated_entities` being passed to the prompt, the LLM generates entities like:
- `light.lr_back_left_ceiling` (fake)
- `wled.office` (fake, should be `light.wled_office` or similar)

**Problem:** The OpenAI prompt doesn't strongly enforce using ONLY validated entities. The LLM interprets "use realistic entity IDs" as "create new entity IDs" rather than "use only the provided validated entity IDs."

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:1112-1160` (prompt building)

### Issue 3: Validation Happens But Doesn't Block Creation

**Evidence from Logs:**
```
❌ Entity NOT FOUND in HA: wled.office
❌ Entity NOT FOUND in HA: binary_sensor.office_motion
❌ Invalid entity IDs in test YAML: binary_sensor.office_motion, wled.office, ...
INFO: "POST /api/v1/ask-ai/query/.../approve HTTP/1.1" 200 OK
```

**Problem:** The validation correctly identifies invalid entities and logs errors, but the automation is still created (HTTP 200 OK). The validation should BLOCK creation when invalid entities are found.

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:3450-3493` (test validation) and `3524-3579` (approve validation)

### Issue 4: WLED Entity Domain Confusion

**Problem:** The query mentions "wled" but WLED devices in Home Assistant are typically exposed as `light.wled_*` entities, not `wled.*`. The LLM is generating `wled.office` instead of finding the actual `light.wled_*` entity.

### Issue 5: Hardcoded Entity IDs in Prompts (CRITICAL)

**Problem:** The prompts contain many hardcoded entity IDs in examples that don't exist in the user's Home Assistant:
- `light.office` (appears ~20+ times in examples)
- `light.kitchen` (appears ~10+ times)
- `light.living_room` (appears ~10+ times)
- `binary_sensor.front_door` (appears ~5+ times)
- `binary_sensor.office_motion` (appears ~5+ times)
- `wled.office` (appears ~5+ times)
- `light.office_lights` (appears ~3+ times)
- `light.office_light_placeholder` (hardcoded placeholder suggestion)

**Impact:** These hardcoded examples teach the LLM to generate fake entity IDs. The LLM sees "use `light.office`" in examples and assumes it should generate similar entity IDs.

**Locations:**
- `services/ai-automation-service/src/api/ask_ai_router.py:1117-1430` (prompt examples)
- `services/ai-automation-service/src/api/ask_ai_router.py:1130,1157` (placeholder suggestions)
- `services/ai-automation-service/src/llm/yaml_generator.py:60-185` (YAML generator examples)

## Fix Plan

### Fix 1: Improve Entity Resolution Confidence Scoring

**Goal:** Increase matching confidence for similar entity names.

**Changes:**
1. **Normalize entity names better:** Split underscores, handle abbreviations (LR = Living Room)
2. **Improve location matching:** "all four ceiling lights" should match multiple ceiling lights in the same area
3. **Handle WLED entities:** Map "wled" queries to `light.wled_*` domain entities
4. **Lower confidence threshold:** Accept matches down to 10% confidence instead of filtering them out

**Files to Modify:**
- `services/ai-automation-service/src/services/entity_validator.py`
  - Update `_find_best_match` method (lines 600-700)
  - Add WLED-specific matching logic
  - Improve location-based matching for multiple entities

### Fix 2: Remove ALL Hardcoded Entity IDs from Prompts (CRITICAL)

**Goal:** Replace all hardcoded entity IDs with dynamic examples based on validated entities or generic placeholders.

**Changes:**
1. **Remove hardcoded entity IDs from examples:**
   - Replace `light.office` with `{validated_entity_id}` or first validated light entity
   - Replace `light.kitchen` with validated entity from user's setup
   - Replace all hardcoded examples with dynamic ones using actual validated entities

2. **Remove placeholder suggestions:**
   - Remove `'light.office_light_placeholder'` suggestions (lines 1130, 1157)
   - Instead, fail with clear error if no validated entities found
   - Never suggest creating placeholder entity IDs

3. **Make examples dynamic:**
   - If validated entities exist, use them in examples
   - If no validated entities, use generic format like `light.{location}_{device_type}` (NOT actual entity IDs)
   - Use comments like `# Replace with validated entity ID from list above`

4. **Update fallback values:**
   - Remove hardcoded fallbacks like `'light.office'` (line 1117) and `'wled.office'` (line 1123)
   - Use `{EXAMPLE_ENTITY_ID}` or similar placeholder format
   - Or use first validated entity if available

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
  - Remove hardcoded entity IDs from prompt examples (lines 1117-1430)
  - Replace with dynamic examples using validated entities
  - Remove placeholder suggestions (lines 1129-1161)
  
- `services/ai-automation-service/src/llm/yaml_generator.py`
  - Remove hardcoded entity IDs from examples (lines 60-185)
  - Use generic placeholders or validated entities

### Fix 3: Strengthen LLM Prompt to Enforce Validated Entities

**Goal:** Make the OpenAI prompt absolutely clear: ONLY use provided validated entities, never create new ones.

**Changes:**
1. **Add explicit prohibition:** "DO NOT create entity IDs. ONLY use the validated entity IDs provided below."
2. **Remove ambiguous language:** Remove phrases like "use realistic entity IDs" that imply creation
3. **Add validation enforcement:** "If you cannot find a match in the validated entities list, you MUST use the closest match from the list or fail the request."
4. **Add examples:** Show correct vs incorrect entity ID usage using actual validated entities (not hardcoded ones)
5. **Emphasize:** "The examples below use {validated_entity_id} - replace this with your actual validated entity IDs from the list above."

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
  - Update prompt building (lines 1112-1160)
  - Strengthen entity mapping section
  - Use dynamic entity examples

### Fix 4: Block Automation Creation on Invalid Entities

**Goal:** Prevent automation creation when validation finds invalid entities.

**Changes:**
1. **Check validation BEFORE creation:** Ensure validation runs and returns errors BEFORE calling `ha_client.create_automation()`
2. **Return proper error response:** Return HTTP 400 with detailed error message listing invalid entities
3. **Provide suggestions:** Include list of similar valid entities in error response
4. **Fail if no validated entities:** If no validated entities found AND automation needs entities, fail early with clear error

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
  - Fix validation blocking (lines 3450-3493 for test, 3524-3579 for approve)
  - Ensure early return on validation failure
  - Add check for missing validated entities before YAML generation

### Fix 5: Add Post-Generation Entity Replacement

**Goal:** As a safety net, automatically replace invalid entities in generated YAML with valid ones.

**Changes:**
1. **Extract all entity IDs from generated YAML:** After LLM generates YAML, extract all entity IDs
2. **Validate each entity:** Check each entity ID against Home Assistant
3. **Auto-replace invalid entities:** If invalid entity found, find closest valid match from validated entities list and replace it
4. **Log replacements:** Log all entity replacements for debugging
5. **Block if replacement fails:** If no valid replacement found, fail instead of using invalid entity

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
  - Add post-generation validation (after line 1640)
  - Implement entity replacement logic using validated entities

### Fix 6: Improve Location-Based Entity Matching

**Goal:** Better match "all four ceiling lights" to actual ceiling lights in the office/living room.

**Changes:**
1. **Extract "all four ceiling lights":** Parse query to extract "ceiling lights" + count
2. **Match multiple entities:** Find all ceiling lights in the mentioned location
3. **Return list of entities:** Return multiple entity IDs when query mentions "all" or a count

**Files to Modify:**
- `services/ai-automation-service/src/services/entity_validator.py`
  - Add multi-entity matching logic
  - Improve "all X devices" query parsing

## Implementation Priority

1. **CRITICAL PRIORITY:** Fix 2 (Remove Hardcoded Entity IDs) - **MUST DO FIRST** - Hardcoded examples teach LLM to generate fake entities
2. **HIGH PRIORITY:** Fix 3 (Strengthen Prompt) - Prevents LLM from generating fake entities after hardcoded examples removed
3. **HIGH PRIORITY:** Fix 4 (Block Creation) - Prevents broken automations from being created
4. **MEDIUM PRIORITY:** Fix 1 (Improve Resolution) - Improves entity matching accuracy
5. **MEDIUM PRIORITY:** Fix 5 (Post-Generation Replacement) - Safety net for edge cases
6. **LOW PRIORITY:** Fix 6 (Multi-Entity Matching) - Nice-to-have enhancement

## Testing Plan

### Test Case 1: Office WLED + Ceiling Lights
**Query:** "sit at my desk in my office I want the w all four ceiling lights to Natural light"

**Expected:**
- ✅ Validates all entities exist
- ✅ Maps "wled" to actual `light.wled_*` entity
- ✅ Maps "all four ceiling lights" to 4 actual ceiling light entities
- ✅ Creates automation with valid entities only

### Test Case 2: Invalid Entity Detection
**Query:** "turn on fake.light.that.doesnt.exist"

**Expected:**
- ✅ Entity validation fails
- ✅ Automation creation is blocked
- ✅ Error response includes suggestion for similar valid entities

### Test Case 3: Low-Confidence Match Acceptance
**Query:** "turn on LR front left ceiling light"

**Expected:**
- ✅ Finds `light.hue_color_downlight_1_6` with low confidence (15%)
- ✅ Accepts match instead of rejecting
- ✅ Uses the matched entity in automation

## Success Criteria

1. ✅ No "Entity not found" errors in automation creation
2. ✅ All generated automations use real Home Assistant entities
3. ✅ Invalid entity errors block automation creation with helpful error messages
4. ✅ Entity resolution confidence improved (target: >50% for reasonable queries)
5. ✅ WLED entities correctly mapped to `light.wled_*` format

## Files to Modify

1. **CRITICAL:** `services/ai-automation-service/src/api/ask_ai_router.py`
   - Remove ALL hardcoded entity IDs from prompts (lines 1117-1430)
   - Replace with dynamic examples using validated entities
   - Remove placeholder suggestions (lines 1129-1161)
   - Strengthen LLM prompt to enforce validated entities
   - Fix validation blocking (lines 3450-3493, 3524-3579)
   - Add post-generation entity replacement

2. **CRITICAL:** `services/ai-automation-service/src/llm/yaml_generator.py`
   - Remove ALL hardcoded entity IDs from examples (lines 60-185)
   - Use generic placeholders or validated entities

3. `services/ai-automation-service/src/services/entity_validator.py`
   - Improve entity matching logic
   - Add WLED handling
   - Improve location-based matching

4. **Optional:** Add new test file for entity validation scenarios

## Hardcoded Entity IDs to Remove

**From `ask_ai_router.py` prompts:**
- `light.office` (replace with validated entity or `{LIGHT_ENTITY}`)
- `light.kitchen` (replace with validated entity or `{LIGHT_ENTITY}`)
- `light.living_room` (replace with validated entity or `{LIGHT_ENTITY}`)
- `binary_sensor.front_door` (replace with validated entity or `{DOOR_SENSOR}`)
- `binary_sensor.office_motion` (replace with validated entity or `{MOTION_SENSOR}`)
- `binary_sensor.back_door` (replace with validated entity or `{DOOR_SENSOR}`)
- `wled.office` (replace with validated WLED entity or `{WLED_ENTITY}`)
- `light.office_lights` (replace with validated entity or `{LIGHT_ENTITY}`)
- `light.office_light_placeholder` (REMOVE - never suggest placeholders)
- `binary_sensor.door_placeholder` (REMOVE - never suggest placeholders)

**From `yaml_generator.py` examples:**
- All hardcoded entity IDs in YAML examples (lines 104-186)
- Replace with generic placeholders or use validated entities dynamically

## Next Steps

1. Review and approve this plan
2. Implement fixes in priority order
3. Test each fix individually
4. Integration test with real Home Assistant instance
5. Deploy and monitor for entity validation errors

