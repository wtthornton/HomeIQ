# Step 3: Architecture Design

**Date:** December 31, 2025  
**Workflow:** Entity Validation Fix for ai-automation-service-new  
**Step:** 3 of 7

## Architecture Overview

### Component Changes

#### 1. YAMLGenerationService
**Changes:**
- Add `_fetch_entity_context()` method (R1)
- Add `_format_entity_context_for_prompt()` method (R6)
- Update `generate_homeiq_json()` to fetch and pass entity context (R1, R2)
- Update `_generate_yaml_from_homeiq_json()` to validate entities (R3)
- Update `_generate_yaml_from_structured_plan()` to fetch context and validate (R1, R2, R3)
- Update `_generate_yaml_direct()` to fetch context and validate (R1, R2, R3)
- Enhance `_extract_entity_ids()` to handle templates and areas (R5)

#### 2. OpenAIClient
**Changes:**
- Add `entity_context` parameter to `generate_homeiq_automation_json()` (R2)
- Add `entity_context` parameter to `generate_structured_plan()` (R2)
- Add `entity_context` parameter to `generate_yaml()` (R2)
- Update system prompts to include entity context instructions (R2)

### Data Flow

```
User Request
    ↓
YAMLGenerationService.generate_automation_yaml()
    ↓
[R1] Fetch entities from Data API
    ↓
[R6] Format entity context
    ↓
[R2] Pass entity context to OpenAI client
    ↓
OpenAI generates YAML/JSON
    ↓
Render to YAML (if needed)
    ↓
[R3] Validate entities (MANDATORY)
    ↓
[R5] Extract entities from all patterns
    ↓
If invalid entities → FAIL with error
    ↓
Return YAML
```

### Entity Context Structure

```python
entity_context = {
    "entities": {
        "light": [
            {"entity_id": "light.office", "friendly_name": "Office", "area_id": "office"},
            ...
        ],
        "binary_sensor": [...],
        ...
    },
    "total_count": 1234
}
```

### Validation Flow

1. **Pre-Generation**: Fetch entity context (R1)
2. **Generation**: Pass context to LLM (R2)
3. **Post-Generation**: Extract all entities (R5)
4. **Validation**: Check against valid entities (R3)
5. **Failure**: Raise YAMLGenerationError if invalid (R3)
