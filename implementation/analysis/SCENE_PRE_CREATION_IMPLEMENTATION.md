# Scene Pre-Creation Implementation

**Date:** January 15, 2026  
**Issue:** "Unknown entity" warnings for dynamically created scenes  
**Solution:** Pre-create scenes before automation deployment

## Problem

When automations use `scene.create` to dynamically create scenes, the scene entity doesn't exist until the automation runs. This causes "Unknown entity" warnings in Home Assistant UI when you open the automation editor.

## Solution

Automatically pre-create scenes before automation deployment using the `scene.create` service with current entity states.

## Implementation

### 1. Scene Extraction (`_extract_scene_create_actions`)

Extracts all `scene.create` actions from automation YAML, including:
- `scene_id` (without `scene.` prefix)
- `snapshot_entities` (list of entity IDs)
- `scene_entity_id` (full entity ID: `scene.{scene_id}`)

Handles nested actions (choose, repeat, sequences).

### 2. Scene Pre-Creation (`_pre_create_scenes`)

Before automation deployment:
1. Calls `/api/services/scene/create` with `scene_id` and `snapshot_entities`
2. Captures current state of entities
3. Creates the scene entity in Home Assistant
4. Handles errors gracefully (falls back to dynamic creation at runtime)

### 3. Integration (`_create_automation_in_ha`)

Updated automation creation flow:
1. Extract scenes from automation YAML
2. Pre-create scenes with current entity states
3. Create automation in Home Assistant
4. Return scene pre-creation results in response

### 4. Validation Warning (`_detect_scene_creation_pattern`)

Added validation warning to inform users:
- Dynamic scene creation detected
- Scenes will be pre-created automatically
- Pre-creation prevents UI warnings

### 5. System Prompt Update

Updated system prompt to document:
- Scene pre-creation happens automatically
- No manual scene creation required
- If pre-creation fails, automation still works (scene created at runtime)

## API Endpoint

Uses Home Assistant service API:
- **Endpoint:** `POST /api/services/scene/create`
- **Body:**
  ```json
  {
    "scene_id": "scene_id_without_prefix",
    "snapshot_entities": ["entity1", "entity2"]
  }
  ```

## Benefits

1. ✅ Eliminates "Unknown entity" warnings in Home Assistant UI
2. ✅ Scenes exist immediately after automation deployment
3. ✅ Automation works correctly at runtime
4. ✅ No manual scene creation required
5. ✅ Graceful fallback if pre-creation fails

## Error Handling

- If scene already exists (409): Continue (scene will be updated at runtime)
- If pre-creation fails: Log warning, continue with automation creation (scene will be created dynamically)
- Automation creation never fails due to scene pre-creation issues

## Future Enhancements

1. Retry logic for scene pre-creation failures
2. Verify scene creation before automation deployment
3. Update scenes if entities change
4. Handle scene deletion if automation is deleted
