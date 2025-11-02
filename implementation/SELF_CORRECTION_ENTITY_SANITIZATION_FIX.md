# Self-Correction Entity Sanitization Fix

**Date:** November 1, 2025  
**Status:** Implemented - Ready for Testing  
**Service:** ai-automation-service

## Problem

When users tried to approve automations, the system failed with errors like:
```
Invalid entity IDs in test YAML: binary_sensor.office_motion, wled.office, 
light.lr_front_left_ceiling, light.lr_back_right_ceiling, light.lr_front_right_ceiling, 
light.lr_back_left_ceiling
```

**Root Cause:** The reverse-engineering self-correction service (`yaml_self_correction.py`) was modifying YAML during refinement but had no validation to ensure entity IDs remained valid. When OpenAI replaced validated entity IDs with invalid ones, the final YAML would fail approval.

**Example:** The system correctly validated `binary_sensor.ps_fp2_office` but self-correction replaced it with `binary_sensor.office_motion`, which doesn't exist in Home Assistant.

## Solution

Implemented a **generic post-refinement entity sanitization** system that:

1. **Extracts all entity IDs** from refined YAML
2. **Validates each entity ID** against available entities
3. **Finds best matching valid entity** if invalid
4. **Replaces invalid IDs** automatically
5. **Logs all replacements** for debugging

### Generic Implementation

The solution is completely generic and works for ANY entity IDs:

- **Domain-aware matching**: Requires domain match (binary_sensor → binary_sensor)
- **Location-aware matching**: Prefers entities in same area/location (office → office)
- **Name similarity matching**: Scores based on common words in entity names
- **Scoring-based selection**: Chooses highest-scoring valid entity

### Key Features

1. **Fetches all Home Assistant entities** when needed (if comprehensive_enriched_data has < 100 entities)
2. **No hardcoding**: Works for any entity type, domain, or location
3. **Graceful degradation**: Returns original YAML if sanitization fails
4. **Non-invasive**: Only runs during self-correction refinement
5. **Comprehensive logging**: Tracks all replacements for debugging

## Code Changes

### File Modified
- `services/ai-automation-service/src/services/yaml_self_correction.py`

### New Methods

#### `_sanitize_entity_ids()`
Post-refinement validator that:
- Extracts entity IDs from refined YAML
- Checks against available entities
- Finds best matches for invalid IDs
- Replaces in YAML

#### `_find_best_entity_match()`
Generic entity matcher that scores candidates based on:
- Domain matching (1.0 point)
- Location matching (2.0 points)
- Name similarity (0.5 points per common word)

#### `_extract_location_from_entity_id()`
Extracts potential location keywords from entity names (office, living_room, kitchen, etc.)

### Integration Point

Sanitization runs after each `_refine_yaml()` call:
```python
# Post-refinement validation: Check and fix entity IDs against available entities
if comprehensive_enriched_data:
    refined_yaml_text = await self._sanitize_entity_ids(
        refined_yaml_text, comprehensive_enriched_data
    )
```

## Testing

### Manual Test Required
1. Navigate to AI Automation Admin UI
2. Create an automation with entities that might not be in initial enrichment
3. Click "Approve & Create"
4. Observe logs for sanitization activity

### Expected Behavior
- If self-correction introduces invalid entity IDs, they should be automatically replaced
- Logs should show: `🔧 Invalid entity ID in refined YAML: <entity_id>`
- Followed by: `✅ Replaced <old> → <new>`
- Final approval should succeed

### Log Monitoring
```bash
docker compose logs -f ai-automation-service | grep -i "sanitized|replaced|Invalid entity"
```

## Edge Cases Handled

1. **Missing HA client**: Sanitization skipped gracefully
2. **Enrichment timeout**: Falls back to basic entity matching
3. **No match found**: Keeps original entity (logs error)
4. **Sanitization failure**: Returns original YAML unchanged
5. **Empty entity pool**: Returns original YAML

## Performance Impact

- **Minimal**: Only runs during self-correction iterations (max 5 times per approve)
- **HA API calls**: Fetches all states once if pool < 100 entities
- **Time complexity**: O(n*m) where n=YAML entities, m=available entities
- **Expected runtime**: < 100ms per sanitization pass

## Related Files

- `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py` - Provides entity data
- `services/ai-automation-service/src/api/ask_ai_router.py` - Calls self-correction with enrichments
- `services/ai-automation-service/src/services/entity_validator.py` - Pre-validation system

## Future Improvements

1. **Cache entity pool**: Don't fetch all states every time
2. **Smarter matching**: Use embeddings for semantic matching
3. **User confirmation**: Ask before replacing entities
4. **Suggestions**: Provide multiple replacement options

## Status

✅ **Implementation Complete**  
✅ **Linter Clean**  
✅ **Service Restarted**  
⏳ **Awaiting Manual Testing**

