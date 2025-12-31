# Step 4: Component Design

**Date:** December 31, 2025  
**Workflow:** Entity Validation Fix for ai-automation-service-new  
**Step:** 4 of 7

## Component Specifications

### 1. Entity Context Fetching (`_fetch_entity_context`)

**Purpose:** Fetch real entities from Data API before YAML generation (R1)

**Input:** None  
**Output:** `dict[str, Any]` with entities grouped by domain

**Algorithm:**
1. Call `data_api_client.fetch_entities(limit=10000)`
2. Group entities by domain
3. Extract: entity_id, friendly_name, area_id, device_class
4. Return structured dictionary

**Error Handling:**
- Log warning if fetch fails
- Return empty dict (allows generation to continue, but no entity context)

### 2. Entity Context Formatting (`_format_entity_context_for_prompt`)

**Purpose:** Format entity context optimally for LLM consumption (R6)

**Input:** Entity context dictionary  
**Output:** Formatted string for prompt

**Format:**
```
LIGHT entities:
  - light.office (Office) [area: office]
  - light.hue_office_back_left (Hue Office Back Left)
...

BINARY_SENSOR entities:
  - binary_sensor.office_motion_area (Office Motion Area)
  ...
```

**Optimization:**
- Limit to 50 entities per domain (avoid token limits)
- Group by domain for easier parsing
- Include friendly names and areas for context

### 3. Entity Extraction Enhancement (`_extract_entity_ids`)

**Purpose:** Extract entities from all YAML patterns (R5)

**Patterns Handled:**
- `entity_id: "light.office"` (direct)
- `entity_id: ["light.office", "light.desk"]` (list)
- `{{ states('light.office') }}` (template)
- `{{ is_state('binary_sensor.motion', 'on') }}` (template condition)
- `snapshot_entities: [light.office]` (scene snapshots)
- `area_id: office` (areas - validated separately)

**Algorithm:**
1. Recursively traverse YAML structure
2. Check for entity_id fields (single and list)
3. Use regex to extract from template expressions
4. Validate entity format (domain.entity_name)
5. Return deduplicated list

### 4. Mandatory Validation Integration

**Purpose:** Make entity validation mandatory (R3)

**Integration Points:**
- `_generate_yaml_from_homeiq_json()` - Validate after rendering
- `_generate_yaml_from_structured_plan()` - Validate after rendering
- `_generate_yaml_direct()` - Validate after generation

**Behavior:**
- Call `validate_entities()` after YAML generation
- If invalid entities found, raise `YAMLGenerationError`
- Error message includes list of invalid entities
