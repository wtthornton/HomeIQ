# Scene Error Fix Implementation

**Date:** January 15, 2026  
**Troubleshooting ID:** `6c7d7e3c-f99f-4705-95bd-7a72cc3d2002`  
**Automation:** "Office Welcome Effect with Weekly Variations"  
**Status:** ✅ **FIXED**

## Problem Summary

The automation used `scene.create` to dynamically create scenes, causing "Unknown entity" warnings in Home Assistant UI because the scene entity didn't exist until runtime.

## Root Cause

1. **Automation YAML was correct** - scene ID format matched correctly
2. **Home Assistant API doesn't validate scene entities** - allows dynamic scene creation
3. **UI validates before runtime** - shows warnings for entities that don't exist yet

## Solution Implemented

### 1. Scene Pre-Creation (`services/ha-ai-agent-service/src/tools/ha_tools.py`)

**Added Methods:**
- `_extract_scene_create_actions()` - Extracts scenes from automation YAML
- `_pre_create_scenes()` - Pre-creates scenes in Home Assistant before deployment

**Integration:**
- Updated `_create_automation_in_ha()` to:
  1. Extract scenes from automation YAML
  2. Pre-create scenes with current entity states
  3. Create automation in Home Assistant
  4. Return scene pre-creation results

**How It Works:**
1. Extracts `scene.create` actions from automation YAML (handles nested actions)
2. Calls `/api/services/scene/create` with `scene_id` and `snapshot_entities`
3. Captures current state of entities and creates scene
4. Scene entity exists when automation is deployed (eliminates UI warnings)
5. At runtime, `scene.create` updates the scene with new state if needed

### 2. Validation Warnings (`services/ha-ai-agent-service/src/services/validation/basic_validation_strategy.py`)

**Added Method:**
- `_detect_scene_creation_pattern()` - Detects dynamic scene creation patterns

**Features:**
- Warns about scenes activated but not created
- Informs users that scenes will be pre-created automatically
- Validates scene ID matching between `scene.create` and `scene.turn_on`

### 3. System Prompt Update (`services/ha-ai-agent-service/src/prompts/system_prompt.py`)

**Added Documentation:**
- Scene pre-creation happens automatically
- No manual scene creation required
- If pre-creation fails, automation still works (fallback to dynamic creation)

## Code Changes

### Files Modified:
1. `services/ha-ai-agent-service/src/tools/ha_tools.py`
   - Added `_extract_scene_create_actions()` method
   - Added `_pre_create_scenes()` method
   - Updated `_create_automation_in_ha()` to pre-create scenes

2. `services/ha-ai-agent-service/src/services/validation/basic_validation_strategy.py`
   - Added `_detect_scene_creation_pattern()` method
   - Integrated into validation flow

3. `services/ha-ai-agent-service/src/prompts/system_prompt.py`
   - Updated State Restoration Pattern section
   - Added Scene Pre-Creation documentation

## Benefits

1. ✅ **Eliminates UI Warnings** - Scenes exist when automation is deployed
2. ✅ **No Manual Work** - Automatic scene pre-creation
3. ✅ **Backward Compatible** - Automation still works if pre-creation fails
4. ✅ **User Informed** - Validation warnings explain behavior
5. ✅ **Correct at Runtime** - Scenes updated with new state when automation runs

## Testing

To test the fix:
1. Create an automation with `scene.create` action
2. Verify scene is pre-created before automation deployment
3. Check Home Assistant UI - no "Unknown entity" warning
4. Verify automation works correctly at runtime

## Future Enhancements

1. Verify scene creation before automation deployment
2. Retry logic for scene pre-creation failures
3. Update scenes if entities change
4. Handle scene deletion when automation is deleted
