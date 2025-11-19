# State Restoration Automation Fix Plan

**Date:** November 18, 2025  
**Status:** Planning  
**Priority:** HIGH  
**Issue:** Automations that should restore lights to original state are incorrectly turning them off

---

## Problem Analysis

### Current Behavior (BROKEN)

When users request automations that should "return to original state" or "restore previous brightness", the system generates YAML that simply turns lights off:

```yaml
# ❌ INCORRECT - Generated automation
action:
  - service: light.turn_on
    target:
      entity_id: light.hue_office_back_left
    data:
      effect: strobe
  - delay: '00:00:10'
  - service: light.turn_off  # ❌ WRONG - loses original state
    target:
      entity_id: light.hue_office_back_left
```

### Expected Behavior (CORRECT)

The automation should capture the current state before the effect, then restore it:

```yaml
# ✅ CORRECT - Should generate this
action:
  # 1. Capture current light states
  - action: scene.create
    data:
      scene_id: office_light_show_restore_scene
      snapshot_entities:
        - light.hue_office_back_left
        - light.hue_color_downlight_1_7
        - light.hue_color_downlight_2_2
        - light.hue_color_downlight_1_6
  
  # 2. Apply effect
  - action: light.turn_on
    target:
      entity_id:
        - light.hue_office_back_left
        - light.hue_color_downlight_1_7
        - light.hue_color_downlight_2_2
        - light.hue_color_downlight_1_6
    data:
      effect: strobe
  
  # 3. Wait for effect duration
  - delay: "00:00:10"
  
  # 4. Restore original states
  - action: scene.turn_on
    target:
      entity_id: scene.office_light_show_restore_scene
```

---

## Root Cause

The YAML generation prompt in `services/ai-automation-service/src/api/ask_ai_router.py` lacks:

1. **No examples of state restoration patterns** - The prompt doesn't show how to use `scene.create` with `snapshot_entities`
2. **No pattern recognition** - The LLM doesn't recognize phrases like "return to original", "restore previous state", "back to original brightness"
3. **No best practices section** - Missing guidance on when and how to preserve state

---

## Solution Strategy

### Phase 1: Add State Restoration Examples to Prompt

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py`  
**Function:** `generate_automation_yaml()`  
**Line Range:** ~1894-2056 (YAML examples section)

**Changes:**
1. Add new example showing state restoration pattern
2. Add pattern recognition keywords to prompt
3. Add explicit best practices section

### Phase 2: Enhance Pattern Recognition

**Detection Keywords:**
- "return to original"
- "restore previous state"
- "back to original brightness"
- "restore original levels"
- "return to previous state"
- "restore to original"
- "revert to original"

**Action:** When these phrases are detected in the description or action_summary, the prompt should emphasize using scene-based restoration.

---

## Implementation Plan

### Step 1: Add State Restoration Example

Add a new example after Example 2 (around line 1995) showing the correct pattern:

```yaml
Example 3 - State Restoration Pattern (CRITICAL for "return to original" requests):
```yaml
id: 'office_light_show_restore_2025'
alias: Office Light Show (Restores Original State)
description: >
  Every 5 minutes, perform a 10-second strobe effect on all office lights,
  then restore them to their exact previous states.
mode: single
triggers:
  - trigger: time_pattern
    minutes: "/5"
conditions: []
actions:
  # 1. Capture current light states in a temporary scene
  - action: scene.create
    data:
      scene_id: office_light_show_restore_scene
      snapshot_entities:
        - light.hue_office_back_left
        - light.hue_color_downlight_1_7
        - light.hue_color_downlight_2_2
        - light.hue_color_downlight_1_6
  
  # 2. Activate strobe effect on all lights
  - action: light.turn_on
    target:
      entity_id:
        - light.hue_office_back_left
        - light.hue_color_downlight_1_7
        - light.hue_color_downlight_2_2
        - light.hue_color_downlight_1_6
    data:
      effect: strobe
  
  # 3. Let strobe run for 10 seconds
  - delay: "00:00:10"
  
  # 4. Restore all lights exactly to previous states
  - action: scene.turn_on
    target:
      entity_id: scene.office_light_show_restore_scene
```

**KEY POINTS:**
- Use `scene.create` with `snapshot_entities` BEFORE applying effects
- Use unique `scene_id` (suggest: `{automation_alias}_restore_scene`)
- Use `scene.turn_on` to restore (NOT `light.turn_off`)
- This preserves brightness, color, color_temp, and all other attributes
```

### Step 2: Add Pattern Recognition Section

Add after the examples section (around line 1996):

```yaml
═══════════════════════════════════════════════════════════════════════════════
STATE RESTORATION PATTERN RECOGNITION
═══════════════════════════════════════════════════════════════════════════════

🔍 DETECT THESE PHRASES (indicates state restoration needed):
- "return to original" / "return to original state"
- "restore previous state" / "restore previous brightness"
- "back to original brightness" / "back to original levels"
- "restore original" / "restore to original"
- "revert to original" / "revert to previous"

✅ WHEN DETECTED: Use scene.create + scene.turn_on pattern (see Example 3 above)
❌ NEVER: Use light.turn_off (loses original brightness/color/state)

SCENE ID NAMING CONVENTION:
- Format: {automation_alias_lowercase}_restore_scene
- Example: "Office Light Show" → scene_id: "office_light_show_restore_scene"
- Must be unique per automation (scene.create overwrites existing scenes)
```

### Step 3: Add Best Practices Section

Add to ADVANCED FEATURES section (around line 2048):

```yaml
STATE RESTORATION BEST PRACTICES:
- ALWAYS use scene.create + scene.turn_on when user requests "return to original"
- Capture state BEFORE applying effects (scene.create first)
- Use snapshot_entities to capture multiple lights at once
- scene.turn_on restores ALL attributes (brightness, color, color_temp, effect, etc.)
- light.turn_off only turns off - does NOT restore previous state
- Scene IDs must be unique (use automation alias in scene_id)
```

### Step 4: Update System Message

Enhance the system message (around line 2119) to emphasize state restoration:

```python
"content": (
    "You are a Home Assistant 2025 YAML automation expert. "
    "Your output is production-ready YAML that passes Home Assistant validation. "
    "You NEVER invent entity IDs - you ONLY use entity IDs from the validated list. "
    "You ALWAYS use 2025 format: triggers: (plural), actions: (plural), action: (not service:). "
    "When users request 'return to original state' or 'restore previous state', "
    "you MUST use scene.create with snapshot_entities followed by scene.turn_on. "
    "NEVER use light.turn_off when state restoration is requested. "
    "Return ONLY valid YAML starting with 'id:' - NO markdown, NO explanations."
)
```

---

## Testing Plan

### Test Case 1: Office Light Show (Original Issue)

**Input Query:**
> "Every 5 minutes, all four lights in the office will perform a fast strobe effect for 10 seconds, and then return immediately to their original brightness levels."

**Expected Output:**
- Uses `scene.create` with `snapshot_entities` for all 4 lights
- Applies strobe effect
- Waits 10 seconds
- Uses `scene.turn_on` to restore (NOT `light.turn_off`)

### Test Case 2: Single Light Flash

**Input Query:**
> "Flash the office light for 5 seconds, then restore its previous state."

**Expected Output:**
- Uses `scene.create` with single light
- Applies flash effect
- Waits 5 seconds
- Uses `scene.turn_on` to restore

### Test Case 3: Multiple Lights with Different States

**Input Query:**
> "When motion is detected, flash all kitchen lights for 3 seconds, then restore them to their original brightness and color."

**Expected Output:**
- Uses `scene.create` with all kitchen lights
- Applies flash effect
- Waits 3 seconds
- Uses `scene.turn_on` to restore (preserves individual brightness/color per light)

---

## Files to Modify

1. **`services/ai-automation-service/src/api/ask_ai_router.py`**
   - Function: `generate_automation_yaml()` (line ~1720)
   - Add Example 3 (state restoration) around line 1995
   - Add pattern recognition section around line 1996
   - Update ADVANCED FEATURES section around line 2048
   - Update system message around line 2119

---

## Success Criteria

✅ **Automations with "return to original" language generate scene.create + scene.turn_on**  
✅ **No more light.turn_off when state restoration is requested**  
✅ **Scene IDs follow naming convention (automation_alias_restore_scene)**  
✅ **All light attributes (brightness, color, etc.) are preserved**  
✅ **Test cases pass with correct YAML output**

---

## Implementation Notes

1. **Scene ID Uniqueness:** Since `scene.create` overwrites existing scenes, using the automation alias in the scene_id ensures uniqueness per automation.

2. **Multiple Lights:** The `snapshot_entities` list can capture multiple lights at once, preserving each light's individual state.

3. **All Attributes Preserved:** `scene.turn_on` restores brightness, color, color_temp, effect, and all other light attributes automatically.

4. **Backward Compatibility:** This change only affects automations that request state restoration. Other automations continue to work as before.

---

## Next Steps

1. ✅ Create this plan document
2. ⏳ Implement Step 1: Add Example 3 to prompt
3. ⏳ Implement Step 2: Add pattern recognition section
4. ⏳ Implement Step 3: Add best practices
5. ⏳ Implement Step 4: Update system message
6. ⏳ Test with all test cases
7. ⏳ Verify with original Office Light Show scenario

