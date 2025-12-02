# OpenAI Prompt Updates - Home Assistant Best Practices

**Date:** January 2025  
**Status:** Completed  
**Based On:** Review of "Best Practices for Home Assistant Setup and Automations" PDF

---

## Summary

All OpenAI prompts used for automation generation have been updated to incorporate Home Assistant best practices identified in the best practices document. These updates ensure generated automations are more reliable, maintainable, and follow industry standards.

---

## Changes Made

### 1. ✅ UNIFIED_SYSTEM_PROMPT (`unified_prompt_builder.py`)

**Added comprehensive best practices section:**

- **Automation Reliability:**
  - Always set `initial_state: true` explicitly
  - Add entity availability checks before using entities in conditions
  - Use error handling (`continue_on_error: true` or `choose` blocks) for non-critical actions
  - For time-based automations, set `max_exceeded: silent`

- **Automation Mode Selection:**
  - Use "single" for one-time actions
  - Use "restart" for automations that should cancel previous runs (motion-activated with delays)
  - Use "queued" for sequential automations
  - Use "parallel" only for independent, non-conflicting actions

- **Target Optimization:**
  - Prefer `target.area_id` or `target.device_id` over multiple `entity_id` entries

- **Automation Organization:**
  - Add descriptive descriptions with device friendly names
  - Add tags for categorization (energy, security, comfort, convenience, ai-generated)

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

---

### 2. ✅ YAML Generation Prompt (`yaml_generation_service.py`)

**Added comprehensive best practices section with:**

1. **Initial State (CRITICAL):**
   - Always set `initial_state: true` explicitly
   - Prevents automations from being disabled after Home Assistant restarts

2. **Automation Mode Selection:**
   - Intelligent mode selection guidance
   - Examples for when to use each mode

3. **Max Exceeded:**
   - Set `max_exceeded: silent` for time-based automations
   - Prevents queue buildup when Home Assistant is unavailable

4. **Error Handling:**
   - Add `continue_on_error: true` for non-critical actions
   - Use `choose` blocks for conditional error handling
   - Examples provided

5. **Entity Availability Checks:**
   - Check entity state is not "unavailable" or "unknown" before using in conditions
   - Example conditions provided

6. **Target Optimization:**
   - Prefer `target.area_id` or `target.device_id` over multiple `entity_id` entries
   - Example showing before/after

7. **Descriptive Descriptions:**
   - Include trigger conditions, expected behavior, and time ranges
   - Use device friendly names

8. **Automation Tags:**
   - Add tags for categorization
   - Common tags listed

**Updated validation checklist** to include all best practices checks.

**File:** `services/ai-automation-service/src/services/automation/yaml_generation_service.py`

---

### 3. ✅ build_yaml_generation_prompt (`unified_prompt_builder.py`)

**Updated requirements section to include:**

- `initial_state: true` in required fields
- Intelligent mode selection guidance
- Best practices section with all 8 key practices
- Examples and explanations for each practice

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

---

### 4. ✅ NL Automation Generator (`nl_automation_generator.py`)

**Updated instructions to include:**

- `initial_state: true` in required fields
- Intelligent mode selection
- `max_exceeded: silent` for time-based automations
- Tags for categorization
- Entity availability checks
- Error handling
- Target optimization (area_id/device_id)

**File:** `services/ai-automation-service/src/nl_automation_generator.py`

---

### 5. ✅ Description Generator (`description_generator.py`)

**Updated system prompt to:**

- Mention reliability features when relevant
- Include example mentioning availability checks
- Keep focus on human-readable descriptions (no YAML)

**File:** `services/ai-automation-service/src/llm/description_generator.py`

---

## Best Practices Covered

All 8 improvements from the best practices analysis are now included in prompts:

1. ✅ **Add `initial_state` Field** - Explicitly set in all prompts
2. ✅ **Add Proper Error Handling and Recovery** - Guidance and examples provided
3. ✅ **Validate Entity States Before Using in Conditions** - Availability checks included
4. ✅ **Improve Automation Mode Selection Logic** - Intelligent selection guidance
5. ✅ **Add `max_exceeded` for Time-Based Automations** - Included in prompts
6. ✅ **Use Device IDs and Area IDs Instead of Entity IDs** - Target optimization guidance
7. ✅ **Enhance Automation Descriptions with Context** - Descriptive description requirements
8. ✅ **Add Automation Tags and Categories** - Tag requirements included

---

## Impact

### Before Updates:
- Prompts focused on basic YAML generation
- No guidance on reliability best practices
- No mode selection intelligence
- No error handling guidance
- No entity availability checks

### After Updates:
- Comprehensive best practices guidance in all prompts
- Intelligent mode selection based on automation type
- Error handling patterns included
- Entity availability validation guidance
- Target optimization recommendations
- Tag categorization requirements
- Descriptive description requirements

---

## Testing Recommendations

1. **Generate test automations** and verify:
   - `initial_state: true` is always set
   - Mode is selected appropriately
   - `max_exceeded: silent` appears for time-based automations
   - Error handling is included for non-critical actions
   - Tags are present
   - Descriptions are descriptive

2. **Review generated YAML** for compliance with all best practices

3. **Monitor automation reliability** after deployment to validate improvements

---

## Files Modified

1. `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
   - Updated `UNIFIED_SYSTEM_PROMPT`
   - Updated `build_yaml_generation_prompt` method

2. `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
   - Added comprehensive best practices section
   - Updated validation checklist

3. `services/ai-automation-service/src/nl_automation_generator.py`
   - Updated instructions with best practices

4. `services/ai-automation-service/src/llm/description_generator.py`
   - Updated system prompt with reliability mentions

---

## Next Steps

1. ✅ All prompts updated with best practices
2. ⏳ Monitor generated automations for compliance
3. ⏳ Collect feedback on automation quality improvements
4. ⏳ Consider adding automated validation for best practices compliance

---

## Related Documents

- `implementation/analysis/HOME_ASSISTANT_BEST_PRACTICES_IMPROVEMENTS.md` - Original analysis
- `docs/research/Best Practices for Home Assistant Setup and Automations.pdf` - Source document

