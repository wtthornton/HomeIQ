# Scene Entity Validation Error Analysis

**Date:** November 20, 2025  
**Issue:** Automation created successfully but validation error shown for dynamically created scene entity

---

## Summary

An automation for a WLED strip called "Dishes" was successfully created in Home Assistant, but a validation error was displayed: `"Invalid entity IDs in YAML: scene.wled_dishes_pre_random_snapshot"`.

**Status:** ✅ Automation created successfully (works correctly)  
**Error:** ⚠️ False positive validation error (scene entity doesn't exist yet)

---

## What Happened

### 1. User Request
User requested an automation for a WLED strip "Dishes" that:
- Runs every 15 minutes (24/7)
- Takes a snapshot of current state (brightness, color, effect)
- Turns on and sets brightness to 100%
- Applies a random WLED color and effect
- Restores the snapshot after 15 minutes

### 2. YAML Generation
The system generated YAML with a `scene.create` service call that dynamically creates a scene entity:

**2025 Home Assistant Format:**
```yaml
action:
  # Step 1: Create scene snapshot (dynamic scene creation)
  - service: scene.create
    data:
      scene_id: wled_dishes_pre_random_snapshot
      snapshot_entities:
        - light.wled_dishes
  
  # Step 2: Turn on and set brightness
  - service: light.turn_on
    target:
      entity_id: light.wled_dishes
    data:
      brightness_pct: 100
  
  # Step 3: Apply random color and effect
  # ... (random color/effect logic)
  
  # Step 4: Wait 15 minutes
  - delay: '00:15:00'
  
  # Step 5: Restore snapshot
  - service: scene.turn_on
    target:
      entity_id: scene.wled_dishes_pre_random_snapshot
```

**Key 2025 Pattern:**
- Top level: `action:` (singular)
- Inside actions: `service:` field (NOT `action:`)
- `scene.create` creates a scene entity dynamically at runtime
- Created scenes become entities with format `scene.{scene_id}`

### 3. Validation Process
The validation code (`ask_ai_router.py` lines 8378-8552) extracts ALL entity IDs from the YAML and validates them against Home Assistant:

```8378:8391:services/ai-automation-service/src/api/ask_ai_router.py
                    # Validate each unique entity ID exists in HA
                    invalid_entities = []
                    connection_error = None
                    for entity_id in unique_entity_ids:
                        try:
                            entity_state = await ha_client.get_entity_state(entity_id)
                            if not entity_state:
                                invalid_entities.append(entity_id)
                        except ConnectionError as e:
                            # Connection error - stop validation and return early
                            connection_error = str(e)
                            logger.error(f"❌ Connection error during entity validation: {connection_error}")
                            break
                        except Exception as e:
                            # Other errors - treat as entity not found
                            logger.warning(f"⚠️ Error validating entity {entity_id}: {e}")
                            invalid_entities.append(entity_id)
```

### 4. The Problem
The validation extracted `scene.wled_dishes_pre_random_snapshot` from the YAML (line 8608 action that references it), but this scene entity **doesn't exist yet** because:

**Home Assistant 2025 Behavior:**
- `scene.create` service creates a scene entity dynamically at runtime
- The scene entity ID is formatted as `scene.{scene_id}` (e.g., `scene.wled_dishes_pre_random_snapshot`)
- Scenes created via `scene.create` don't exist in Home Assistant until the automation runs
- The scene is created in Step 1, then referenced in Step 5
- At validation time, the scene doesn't exist in Home Assistant yet

**2025 Documentation Pattern:**
According to Home Assistant 2025 patterns:
- Scenes created by `scene.create` are runtime entities
- They exist only after the service call executes
- Pre-validation against Home Assistant will always fail for dynamically created scenes

### 5. Error Flow
Looking at the code flow:

```8537:8552:services/ai-automation-service/src/api/ask_ai_router.py
                        else:
                            # No replacements found, return error
                            error_msg = f"Invalid entity IDs in YAML: {', '.join(invalid_entities)}"
                            logger.error(f"❌ {error_msg}")
                            return {
                                "suggestion_id": suggestion_id,
                                "query_id": query_id,
                                "status": "error",
                                "safe": False,
                                "message": "Automation contains invalid entity IDs",
                                "error_details": {
                                    "type": "invalid_entities",
                                    "message": error_msg,
                                    "invalid_entities": invalid_entities
                                }
                            }
```

**However**, the automation was still created successfully! This suggests:
- The validation error was logged/displayed but didn't prevent creation
- OR there's an exception handler that allowed creation to proceed
- OR the error occurred after successful creation (async flow)

---

## Root Cause

**Issue:** The entity ID validation logic doesn't distinguish between:
1. **Static entities** - Must exist at validation time (e.g., `light.wled_dishes`)
2. **Dynamic entities** - Created at runtime via service calls (e.g., `scene.wled_dishes_pre_random_snapshot`)

**Problem Location:** `services/ai-automation-service/src/services/entity_id_validator.py`

The `_extract_all_entity_ids()` method extracts ALL entity IDs from YAML, including:
- Entity IDs referenced in `scene.turn_on` service calls (should exist if static)
- Entity IDs that are created by `scene.create` service calls (don't exist yet - created at runtime)

**2025 Home Assistant Pattern:**
- `scene.create` service creates scene entities dynamically
- These scenes become valid entities only after the service executes
- Validation before execution will always fail for dynamically created scenes
- This is expected Home Assistant 2025 behavior, not a bug in the automation

---

## Impact

- ✅ **Automation works correctly** - The scene is created at runtime and used successfully
- ⚠️ **False positive error** - Confusing error message shown to user
- ⚠️ **User confusion** - Both success and error notifications shown simultaneously

---

## Solution

The validation logic should skip validation for scene entities that are:
1. Created by a `scene.create` action in the same automation
2. Referenced only after the `scene.create` action

### Implementation Options

#### Option 1: Track Scene Creation (RECOMMENDED - Aligns with 2025 Patterns)
Modify `_extract_all_entity_ids()` to track which scenes are created:

```python
def _extract_all_entity_ids(self, yaml_data: dict) -> tuple[list[tuple[str, str]], set[str]]:
    """
    Extract entity IDs and track which scenes are created dynamically.
    
    Returns:
        (entity_ids, created_scenes)
        - entity_ids: List of (entity_id, location) tuples
        - created_scenes: Set of scene entity IDs created by scene.create service calls
    """
    entity_ids = []
    created_scenes = set()
    
    # Extract actions to check for scene.create (2025 format: action: -> service:)
    actions = yaml_data.get('action', yaml_data.get('actions', []))
    if actions:
        self._extract_scenes_created(actions, created_scenes)
    
    # ... rest of extraction logic ...
    
    return entity_ids, created_scenes

def _extract_scenes_created(self, actions: Any, created_scenes: set[str]) -> None:
    """
    Extract scene IDs created by scene.create service calls.
    
    Home Assistant 2025 format:
    - action: (top level, singular)
    - service: scene.create (inside action items)
    - data.scene_id: The scene ID (becomes scene.{scene_id} entity)
    """
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict):
                # Check for scene.create service (2025 format: service: field)
                service = action.get('service')
                if service == 'scene.create':
                    scene_id = action.get('data', {}).get('scene_id')
                    if scene_id:
                        # Convert scene_id to entity_id format (Home Assistant 2025 pattern)
                        if not scene_id.startswith('scene.'):
                            scene_entity_id = f"scene.{scene_id}"
                        else:
                            scene_entity_id = scene_id
                        created_scenes.add(scene_entity_id)
                
                # Recursively check nested structures (sequence, repeat.sequence, choose)
                if 'sequence' in action:
                    self._extract_scenes_created(action['sequence'], created_scenes)
                if 'repeat' in action and isinstance(action['repeat'], dict):
                    if 'sequence' in action['repeat']:
                        self._extract_scenes_created(action['repeat']['sequence'], created_scenes)
                if 'choose' in action:
                    for branch in action['choose']:
                        if isinstance(branch, dict) and 'sequence' in branch:
                            self._extract_scenes_created(branch['sequence'], created_scenes)
```

Then filter out created scenes during validation:

```python
# In ask_ai_router.py validation (around line 8368-8373)
entity_id_tuples = entity_id_extractor._extract_all_entity_ids(parsed_yaml)
all_entity_ids_in_yaml = [eid for eid, _ in entity_id_tuples] if entity_id_tuples else []

# Get scenes created dynamically by scene.create service calls
created_scenes = entity_id_extractor._extract_scenes_created(parsed_yaml.get('action', []))

# Filter out dynamically created scenes from validation (2025 pattern: scenes created at runtime)
entities_to_validate = [eid for eid in unique_entity_ids if eid not in created_scenes]

logger.info(f"🔍 Excluding {len(created_scenes)} dynamically created scenes from validation: {created_scenes}")
logger.info(f"🔍 Validating {len(entities_to_validate)} static entities")
```

#### Option 2: Action Order Analysis (Alternative)
Track the order of actions and only validate scene entities if they're referenced before being created. This is more complex but handles edge cases where scenes might be referenced conditionally.

#### Option 3: Whitelist Pattern (Less Robust)
Skip validation for scene entities matching patterns like `*_snapshot`, `*_restore_scene`, etc. This works but relies on naming conventions rather than actual YAML structure.

**2025 Home Assistant Recommendation:**
Option 1 is the most robust and aligns with Home Assistant 2025 patterns. It:
- ✅ Accurately identifies dynamically created scenes from `scene.create` service calls
- ✅ Works regardless of naming conventions
- ✅ Handles nested action structures (sequence, repeat, choose)
- ✅ Follows 2025 YAML format (`action:` → `service:`)

---

## Recommended Fix

**Option 1** is the most robust solution and aligns with Home Assistant 2025 patterns. It:
- ✅ Accurately identifies dynamically created scenes from `scene.create` service calls
- ✅ Works for any scene creation pattern
- ✅ Doesn't rely on naming conventions
- ✅ Handles nested action structures (sequence, repeat, choose)
- ✅ Follows 2025 YAML format (`action:` → `service:`)
- ✅ Complies with Home Assistant 2025 documentation patterns

**2025 Home Assistant Compliance:**
This fix ensures validation respects the 2025 Home Assistant pattern where:
- Scenes created by `scene.create` are runtime entities
- These entities don't exist until the service executes
- Pre-validation should exclude dynamically created entities
- This prevents false-positive validation errors

---

## Testing

After implementing the fix, test with:

1. **Scene snapshot automation** (current issue)
   - Verify no validation error for dynamically created scene
   - Verify automation still creates successfully

2. **Multiple scene creation**
   - Automation that creates multiple scenes
   - Verify all created scenes are skipped in validation

3. **Static scene reference**
   - Automation that references an existing scene (should still validate)

4. **Nested scene creation**
   - Scene created inside a `choose` or `repeat` sequence
   - Verify scene is still tracked correctly

---

## Related Files

- `services/ai-automation-service/src/services/entity_id_validator.py` - Entity extraction logic
- `services/ai-automation-service/src/api/ask_ai_router.py:8370-8552` - Entity validation logic
- `implementation/STATE_RESTORATION_AUTOMATION_FIX_PLAN.md` - Scene creation pattern documentation
- `implementation/ASK_AI_APPROVAL_FIX_PLAN.md` - 2025 YAML format reference (note: uses correct `service:` format)
- `services/ai-automation-service/src/api/ask_ai_router.py:2315-2362` - 2025 format documentation in prompt

## 2025 Home Assistant Format Notes

**Correct 2025 Format:**
```yaml
action:
  - service: scene.create  # ✅ CORRECT: service: field
    data:
      scene_id: wled_dishes_pre_random_snapshot
```

**Incorrect Format (used in some docs):**
```yaml
action:
  - action: scene.create  # ❌ WRONG: action: field doesn't exist
```

**Reference:** The actual prompt builder uses `service:` format (see `ask_ai_router.py:2344`), which is correct for Home Assistant 2025.

---

## Status

- **Issue Identified:** ✅
- **Root Cause:** ✅ Scene entities created dynamically are being validated
- **Solution:** ⏳ Pending implementation
- **Testing:** ⏳ Pending

