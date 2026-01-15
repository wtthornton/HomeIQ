# Automation Scene Error Analysis

**Date:** January 15, 2026  
**Troubleshooting ID:** `6c7d7e3c-f99f-4705-95bd-7a72cc3d2002`  
**Automation:** "Office Welcome Effect with Weekly Variations"  
**Error:** "Unknown entity" on "Scene: Activate" action

## Problem Summary

The automation was created successfully but shows an "Unknown entity" error in Home Assistant UI when trying to activate a scene. This error was not caught during automation creation.

## Root Cause Analysis

### Issue Identified

1. **Scene Entity Mismatch**: The automation references a scene entity in `scene.turn_on` that doesn't exist
2. **Home Assistant API Behavior**: Home Assistant API doesn't validate scene entity existence during automation creation - it only validates at runtime
3. **Validation Gap**: Our validation chain doesn't catch dynamically created scenes vs. referenced scenes

### Why Home Assistant Didn't Throw an Error

Home Assistant's automation API (`POST /api/config/automation/config/{config_id}`) only validates:
- YAML syntax
- Required fields (trigger, action)
- Basic structure

It does NOT validate:
- Scene entity existence (scenes can be created dynamically)
- Entity availability at creation time
- Runtime entity resolution

This is by design - Home Assistant allows automations to reference entities that may not exist yet or may be created dynamically.

## Root Cause - CONFIRMED

After analysis using TappsCodingAgents debugger, the root cause is:

**The automation YAML is actually CORRECT!** The issue is:

1. **Scene ID Format**: ✅ Correct
   - `scene.create` uses: `office_welcome_effect_with_weekly_variations_restore`
   - `scene.turn_on` uses: `scene.office_welcome_effect_with_weekly_variations_restore`
   - Format matches correctly (scene_id vs entity_id)

2. **The Real Issue**: The scene entity doesn't exist until the automation runs
   - `scene.create` creates a scene dynamically when the automation executes
   - The scene entity `scene.office_welcome_effect_with_weekly_variations_restore` doesn't exist until `scene.create` executes
   - Home Assistant UI validates entities when you open the editor (before runtime)
   - Since the scene doesn't exist yet, it shows "Unknown entity" warning

3. **Why Home Assistant API Didn't Catch This**:
   - Home Assistant API intentionally doesn't validate scene entities during automation creation
   - Scenes can be created dynamically (by design)
   - Validation only happens at runtime, not at creation time
   - This allows automations to reference entities that don't exist yet

## Solutions

### Option 1: Ignore the Warning (Recommended)
The automation will work correctly at runtime. The UI warning is a **false positive**.

### Option 2: Create Scene Manually
Create the scene before the automation runs:
- Go to Home Assistant → Scenes → Create Scene
- Entity ID: `scene.office_welcome_effect_with_weekly_variations_restore`
- Add entities: `light.office`, `light.office_desk`, `light.office_wled`

### Option 3: Update Validation Chain (Long-term)
Update our validation chain to detect this pattern and either:
1. Warn the user that the scene will be created dynamically
2. Pre-create the scene before automation deployment
3. Use a different pattern that doesn't require dynamic scene creation

## Status

1. ✅ Retrieved automation YAML from Home Assistant
2. ✅ Analyzed scene.create vs scene.turn_on entity IDs  
3. ✅ Used TappsCodingAgents debugger to identify root cause
4. ✅ Confirmed automation YAML is correct (false positive warning)
5. ⏳ Update validation chain to handle dynamic scene creation (optional enhancement)
