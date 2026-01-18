# Automation Entity Unknown Error Analysis

**Date:** 2026-01-16  
**Automation ID:** `automation.outside_motion_flashes_office_switch_led_red`  
**User Prompt:** "When the outside presents a sensor goes off, turn the office switches LED to flash bright red for 15 secs and then return to their original states"  
**Status:** ❌ **ISSUES IDENTIFIED** - Unknown entity warnings in Home Assistant UI

## Executive Summary

The automation was successfully created but shows "Unknown entity" warnings for both:
1. **Light entity** (`light.office_go`) in the "Light: Turn on" action
2. **Scene entity** (`scene.outside_motion_flashes_office_switch_led_red_restore`) in the "Scene: Activate" action

The automation **functionality is correct** (entity resolution correctly identified `light.office_go`), but **scene pre-creation failed** or **entity validation during pre-creation failed**, causing UI warnings.

## Root Cause Analysis

### ✅ What Worked

1. **Entity Resolution** - Correctly identified `light.office_go` from "office switches LED"
2. **Automation Creation** - Automation was successfully created and deployed
3. **YAML Structure** - Correct YAML format with scene.create, light.turn_on, delay, scene.turn_on sequence

### ❌ What Failed

1. **Scene Pre-Creation** - Scene entity doesn't exist when automation is viewed in Home Assistant UI
2. **Entity Validation** - Light entity may have been unavailable during scene pre-creation
3. **Error Handling** - Pre-creation failure was silent (didn't prevent automation creation but caused UI warnings)

## Technical Analysis

### Issue 1: Scene Pre-Creation Failure

**Expected Behavior:**
- `_pre_create_scenes()` should call `/api/services/scene/create` before automation deployment
- Scene entity should exist immediately after automation creation

**Actual Behavior:**
- Scene entity shows "Unknown entity" in Home Assistant UI
- Automation was created successfully despite scene pre-creation failure

**Possible Causes:**
1. **Entity Unavailable** - `light.office_go` was unavailable when scene.create was called
2. **API Error** - Scene creation API call failed silently
3. **Timing Issue** - Scene creation happened but entity wasn't visible immediately
4. **Entity ID Format** - Scene entity ID might not match automation's scene.turn_on target

### Issue 2: Light Entity Warning

**Expected Behavior:**
- `light.office_go` should be recognized as valid entity
- No "Unknown entity" warning should appear

**Actual Behavior:**
- "Unknown entity" warning appears for light.office_go in "Light: Turn on" action

**Possible Causes:**
1. **Entity Unavailable** - Light was offline/unavailable during automation deployment
2. **Entity Doesn't Exist** - Entity was removed or renamed after context was fetched
3. **UI Validation Timing** - Home Assistant UI validates entities immediately and entity wasn't available at that moment

## Code Flow Analysis

### Scene Pre-Creation Flow

```python
# services/ha-ai-agent-service/src/tools/ha_tools.py
async def _create_automation_in_ha(...):
    # Step 1: Extract scenes from automation YAML
    scenes_to_precreate = self._extract_scene_create_actions(automation_dict)
    
    # Step 2: Pre-create scenes
    if scenes_to_precreate:
        scene_results = await self._pre_create_scenes(scenes_to_precreate, conversation_id)
        # scene_results contains success/failure info but errors are logged as warnings
    
    # Step 3: Create automation (regardless of scene pre-creation results)
    async with session.post(url, json=automation_config) as response:
        # Automation created even if scene pre-creation failed
```

**Problem:** Scene pre-creation failures are logged as warnings but don't prevent automation creation. This is by design (graceful fallback), but the UI still shows warnings.

### Entity Resolution Flow

```python
# User prompt: "office switches LED"
# Entity resolution correctly identified: light.office_go
# But entity may have been unavailable during scene pre-creation
```

**Problem:** No entity availability check before scene pre-creation. If entity is unavailable, scene creation fails silently.

## Impact Assessment

### User Impact

- **Low** - Automation will work correctly at runtime (scene.create happens dynamically)
- **Medium** - UI warnings are confusing and suggest automation is broken
- **High** - User experience is degraded (warnings in UI, concern about automation validity)

### System Impact

- **Low** - Automation functionality is not affected
- **Medium** - Scene pre-creation feature is not working as intended
- **High** - Entity validation during pre-creation is insufficient

## Improvement Plan

### Priority 1: Fix Scene Pre-Creation Entity Validation

**Problem:** Scene pre-creation attempts to create scene with unavailable entities

**Solution:**
1. **Check entity availability** before scene pre-creation
2. **Validate entity exists** via Home Assistant API before scene.create
3. **Retry logic** for transient unavailability
4. **Clear error messages** when scene pre-creation fails

### Priority 2: Enhance Entity Resolution for "Switch LED" Pattern

**Problem:** "office switches LED" is ambiguous - could mean:
- The LED on the office switch (light.office_go)
- Multiple switches' LEDs
- A switch device with LED indicator

**Solution:**
1. **Improve entity resolution** to handle "switch LED" patterns
2. **Add context** about device relationships (switch → LED indicator)
3. **Better matching** for combined device descriptions

### Priority 3: Improve Error Handling and User Feedback

**Problem:** Silent failures during scene pre-creation

**Solution:**
1. **Explicit warnings** in preview response when entities are unavailable
2. **User notifications** when scene pre-creation fails
3. **Retry mechanism** for scene pre-creation failures
4. **Verification step** after scene creation to confirm success

### Priority 4: System Prompt Improvements

**Problem:** System prompt doesn't emphasize entity validation before scene creation

**Solution:**
1. **Add validation checklist** for entity availability before scene.create
2. **Emphasize** entity existence verification in context
3. **Add guidance** for handling unavailable entities

## Recommended Fixes

### Fix 1: Entity Availability Check Before Scene Pre-Creation

**File:** `services/ha-ai-agent-service/src/tools/ha_tools.py`

**Change:** Add entity availability validation before calling scene.create

```python
async def _pre_create_scenes(...):
    # NEW: Check entity availability before scene creation
    for scene_def in scenes:
        snapshot_entities = scene_def["snapshot_entities"]
        
        # Validate entities exist and are available
        unavailable_entities = []
        for entity_id in snapshot_entities:
            try:
                state = await self.ha_client.get_state(entity_id)
                if state.state in ("unavailable", "unknown"):
                    unavailable_entities.append(entity_id)
            except Exception as e:
                unavailable_entities.append(entity_id)
        
        if unavailable_entities:
            logger.warning(
                f"Scene pre-creation skipped: entities unavailable: {unavailable_entities}"
            )
            # Still attempt creation (may work if entities become available at runtime)
            # But log warning for visibility
```

### Fix 2: Enhanced Entity Resolution for "Switch LED"

**File:** `services/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`

**Change:** Add pattern matching for "switch LED" descriptions

```python
def _extract_device_type_keywords(self, user_prompt: str) -> set[str]:
    # Existing code...
    
    # NEW: Handle "switch LED" pattern (LED indicator on switch)
    prompt_lower = user_prompt.lower()
    if "switch" in prompt_lower and "led" in prompt_lower:
        # Look for light entities associated with switch devices
        found_keywords.add("led")
        found_keywords.add("switch_indicator")  # New keyword type
```

### Fix 3: System Prompt Updates

**File:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`

**Change:** Add entity availability validation to pre-generation checklist

```python
## Pre-Generation Validation Checklist
Before calling `preview_automation_from_prompt`, validate:

| Check | Action if Failed |
|-------|------------------|
| Entity exists | Search context, suggest alternatives if not found |
| **Entity available** | **Check entity state - if unavailable, warn user or wait for availability** |
| Area exists | Verify area_id in context, suggest similar areas |
```

## Testing Plan

1. **Test Scene Pre-Creation with Unavailable Entity**
   - Disable `light.office_go` in Home Assistant
   - Create automation that uses scene.create with this entity
   - Verify scene pre-creation fails gracefully with warning
   - Verify automation still created (runtime scene creation works)

2. **Test Entity Resolution for "Switch LED"**
   - Test prompt: "turn the office switches LED to red"
   - Verify `light.office_go` is correctly identified
   - Verify entity resolution confidence score is high

3. **Test Scene Pre-Creation with Available Entity**
   - Ensure `light.office_go` is available
   - Create automation with scene.create
   - Verify scene entity exists immediately after creation
   - Verify no "Unknown entity" warnings in UI

## Next Steps

1. ✅ **Analysis Complete** - Root causes identified
2. ⏳ **Implement Fixes** - Priority 1-3 improvements
3. ⏳ **Test Improvements** - Verify fixes resolve issues
4. ⏳ **Monitor** - Track scene pre-creation success rate
