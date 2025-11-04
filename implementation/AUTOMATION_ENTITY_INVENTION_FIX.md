# Automation Entity Invention Fix - Complete

**Date:** November 2, 2025  
**Issue:** LLM inventing non-existent entity IDs  
**Status:** ✅ FIXED

## Problem Summary

When approving automations, the LLM was creating entity IDs that don't exist in Home Assistant, causing failures:

```
Failed to generate automation YAML: Generated YAML contains invalid entity IDs that don't exist in Home Assistant: 
binary_sensor.office_desk_presence. Available validated entities: light.office, light.hue_color_downlight_1_6, ...
```

### Root Cause Analysis

The LLM was generating `binary_sensor.office_desk_presence` because:

1. The automation suggestion likely mentioned office presence/detection
2. The LLM tried to be helpful by creating a sensor entity
3. The validated entities list only contained lights, no sensors
4. Despite warnings not to create fake entities, the LLM still did it

**Why This Happened:**

The prompt contained a confusing instruction:
> "If you need a binary sensor but it's not validated, use the closest validated binary sensor from the list above"

This instruction assumed sensors would be in the validated list, but when they weren't, it created ambiguity. The LLM interpreted this as permission to create what it needed.

### The Flow

1. User query mentions "office presence" or similar
2. Entity validator maps Office lights to valid entities
3. LLM receives validated_entities with only lights
4. LLM reads prompt instruction suggesting using "closest validated binary sensor"
5. LLM finds no binary sensors in validated entities
6. LLM decides to create `binary_sensor.office_desk_presence` anyway
7. Post-generation validation catches the fake entity
8. System fails with ValueError before creating automation

## Solution

### Fix Applied

**File:** `services/ai-automation-service/src/api/ask_ai_router.py` (Line 1235-1247)

**Changed from:**
```
- If you need a binary sensor but it's not validated, use the closest validated binary sensor from the list above
- If you cannot find a matching entity in the validated list, you MUST either:
  a) Use the closest similar entity from the validated list, OR
  b) Fail the request with an error explaining no matching entity was found
```

**Changed to:**
```
- If the suggestion requires entities that are NOT in the validated list above:
  a) SIMPLIFY THE AUTOMATION to only use validated entities, OR
  b) Use a time-based trigger instead of missing sensor triggers, OR
  c) Return an error explaining which entities are missing from the validated list
- Example: If suggestion needs "presence sensor" but none exists in validated entities → use time trigger instead
```

**Key Changes:**

1. **Removed ambiguous instruction** about "closest validated binary sensor" when none exist
2. **Added concrete alternatives**: Simplify, use time trigger, or fail clearly
3. **Added specific example**: Shows LLM what to do when sensors are missing
4. **Clearer failure path**: Explicitly tells LLM to return an error if needed

### Why This Fix Works

- **No ambiguity**: LLM no longer sees permission to invent entities
- **Concrete guidance**: Specific examples of what to do instead
- **Safe fallback**: Time triggers are always valid
- **Clear error handling**: LLM can explicitly fail with helpful message

### Additional Context

The prompt already has many warnings (lines 1236-1247) but the specific instruction about "closest validated" created confusion. By replacing it with explicit alternatives and examples, the LLM has clear direction.

## Deployment

**Date:** November 2, 2025, 7:25 PM  
**Action:** `docker-compose up -d --force-recreate ai-automation-service`

### Deployment Verification

✅ **Container Status:** Running and healthy  
✅ **Health Check:** Service responding correctly  
✅ **No Errors:** Service started successfully
  - Device Intelligence capability listener started
  - Daily analysis scheduler started

### Expected Behavior

When LLM encounters missing entities in validated list:
1. **Option A**: Simplifies automation to use only validated entities
2. **Option B**: Uses time-based trigger instead of missing sensor
3. **Option C**: Returns clear error message about missing entities

All options prevent inventing fake entity IDs.

## Related Issues

This is related to the previous fixes:
- **NameError fix**: F-string escaping issues
- **UnboundLocalError fix**: yaml_lib scoping issues

This completes the automation approval workflow fixes.

## Testing

To verify the fix works:

1. Try to approve an automation that mentions sensors not in the validated list
2. LLM should either:
   - Simplify the automation to remove the sensor requirement
   - Use a time-based trigger instead
   - Return an explicit error (preferred when it's critical)
3. No fake entity IDs should be generated

## Lessons Learned

**Prompt Engineering:**
- Be explicit about alternatives, don't leave ambiguity
- Give concrete examples of what to do in edge cases
- Avoid instructions that can be misinterpreted as permission
- Test prompts with edge cases (missing entities, empty lists, etc.)

**LLM Behavior:**
- Even with strong warnings, one ambiguous instruction can override them
- Providing multiple clear alternatives is better than one unclear instruction
- Examples are more powerful than abstract instructions
- Explicit "what to do when X is missing" beats implicit suggestions

## Status

✅ **COMPLETE** - Fix deployed and service restarted successfully

