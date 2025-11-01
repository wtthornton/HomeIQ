# Plan: Enhance Original Suggestions Before Reverse Engineering

**Date:** November 1, 2025  
**Status:** Draft Plan  
**Objective:** Improve initial suggestion quality to reduce need for reverse engineering corrections

## Problem Analysis

The current flow has a critical gap between suggestion generation and YAML generation:

1. **Suggestion Generation** (`generate_suggestions_from_query`):
   - Creates suggestions with friendly names in `devices_involved` (e.g., "WLED", "Office Light")
   - Maps these to entity IDs AFTER generation (`validated_entities`)
   - But the LLM that generates suggestions doesn't know the exact entity IDs

2. **YAML Generation** (`generate_automation_yaml`):
   - Receives suggestions with friendly names in description (e.g., "turn on wled")
   - Tries to map friendly names to entity IDs
   - LLM generates YAML but sometimes uses incomplete IDs (e.g., "wled" instead of "wled.office")

3. **Reverse Engineering**:
   - Attempts to fix YAML after generation
   - But should be unnecessary if initial YAML is perfect

## Root Causes

1. **Friendly Name Usage in Suggestions**: Suggestions use friendly names in descriptions, which LLM translates to incomplete entity IDs
2. **Delayed Entity Mapping**: Entity ID mapping happens AFTER suggestion generation, not during
3. **Weak Entity Context**: LLM doesn't have strong enough entity ID context when generating YAML
4. **No Pre-validation**: Suggestions aren't validated for entity ID completeness before YAML generation

## Solution Architecture

Implement **pre-emptive entity ID integration** at three stages:

### Stage 1: Enhanced Suggestion Generation
- Include actual entity IDs directly in suggestion structure
- Pre-map all mentioned devices to entity IDs during suggestion creation
- Embed entity IDs in suggestion descriptions/templates

### Stage 2: Suggestion Post-Processing
- Scan suggestion descriptions for device mentions
- Replace friendly names with entity IDs where safe
- Add entity ID annotations to suggestions

### Stage 3: YAML Generation Pre-Processing
- Pre-validate all mentioned devices have entity IDs
- Pre-populate suggestion descriptions with entity IDs
- Enhance prompt with concrete entity ID examples matching the specific suggestion

## Implementation Plan

### Phase 1: Enhance Suggestion Generation with Entity IDs

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes**:
1. **Pre-resolve entity IDs during suggestion generation** (lines 1468-1489):
   - After LLM generates suggestions, immediately map ALL device mentions to entity IDs
   - Use fuzzy matching to find entity IDs for devices mentioned in descriptions
   - Add `entity_ids_used` field to suggestions with actual entity IDs

2. **Enhance device-to-entity mapping** (lines 314-358):
   - Improve `map_devices_to_entities` to handle partial matches
   - Add fuzzy matching for device names mentioned in descriptions
   - Query HA for domain entities if device name is ambiguous (e.g., "wled" could match multiple wled.office, wled.kitchen)

3. **Add entity ID pre-population**:
   - Create function `pre_populate_entity_ids_in_suggestion(suggestion, validated_entities, enriched_data)`
   - Scans suggestion description, trigger_summary, action_summary for device mentions
   - Replaces or annotates with entity IDs where possible

### Phase 2: Suggestion Description Enhancement

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes**:
1. **Create suggestion enhancer function**:
   ```python
   async def enhance_suggestion_with_entity_ids(
       suggestion: Dict[str, Any],
       validated_entities: Dict[str, str],
       enriched_data: Dict[str, Dict[str, Any]],
       ha_client: Optional[HomeAssistantClient]
   ) -> Dict[str, Any]:
       """
       Enhance suggestion by:
       1. Adding entity_ids_used field with actual entity IDs
       2. Creating entity_id_annotations mapping friendly names to IDs
       3. Optionally enriching description with entity IDs in parentheses
       """
   ```

2. **Add entity_id_annotations field** to suggestions:
   - Maps friendly names → entity IDs
   - Example: {"WLED": "wled.office", "Office Light": "light.office"}

3. **Enhance description with entity IDs**:
   - Optionally append entity IDs in parentheses: "turn on WLED (wled.office)"
   - Or add annotation field that YAML generator can use

### Phase 3: YAML Generation Pre-Processing

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes**:
1. **Pre-validate suggestion before YAML generation** (before line 395):
   ```python
   async def pre_validate_suggestion_for_yaml(
       suggestion: Dict[str, Any],
       validated_entities: Dict[str, str],
       ha_client: Optional[HomeAssistantClient]
   ) -> Dict[str, Any]:
       """
       Pre-validate and enhance suggestion before YAML generation:
       1. Extract all device mentions from description/trigger/action summaries
       2. Map each mention to entity IDs using validated_entities + fuzzy matching
       3. Query HA for domain entities if device name is incomplete (e.g., "wled")
       4. Create comprehensive entity_id_map for the LLM
       """
   ```

2. **Enhance validated_entities_text with suggestion-specific mappings**:
   - Build entity ID mapping table based on devices mentioned in THIS suggestion
   - Include reverse mapping (friendly name → entity ID) for each device
   - Add concrete examples: "Description mentions 'wled' → use wled.office"

3. **Pre-populate suggestion description with entity IDs**:
   - Optionally modify suggestion description to include entity IDs
   - Example: "turn on WLED" → "turn on WLED (entity: wled.office)"
   - Or create enhanced_description field

### Phase 4: LLM Prompt Enhancement for Specific Suggestions

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes**:
1. **Add suggestion-specific entity ID mapping section** (lines 536-575):
   - Build entity ID mapping table based on devices mentioned in THIS specific suggestion
   - For each device mentioned, show: friendly_name → entity_id
   - Add explicit instructions: "In this automation, when you see 'wled', use 'wled.office'"

2. **Add concrete YAML examples using suggestion's entities**:
   - Generate example YAML snippets using the actual entity IDs from this suggestion
   - Show correct usage in context similar to the suggestion description

3. **Add entity ID validation checklist**:
   - "Before generating YAML, verify: All entity IDs are in format domain.entity"
   - "If description mentions 'wled', check entity_id_annotations for the exact ID"

### Phase 5: Suggestion Structure Enhancement

**Files**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes**:
1. **Add new fields to suggestion structure**:
   ```python
   {
       'suggestion_id': ...,
       'description': ...,
       'trigger_summary': ...,
       'action_summary': ...,
       'devices_involved': [...],  # Friendly names (keep for display)
       'validated_entities': {...},  # Mapping friendly_name → entity_id
       'entity_ids_used': [...],  # NEW: Actual entity IDs directly (e.g., ["wled.office", "light.office"])
       'entity_id_annotations': {...},  # NEW: Detailed mapping with context
       'device_mentions': {...},  # NEW: Maps description terms → entity IDs
   }
   ```

2. **Extract device mentions from description**:
   - Parse description/trigger/action summaries for device names
   - Match against validated_entities using fuzzy matching
   - Create device_mentions map

### Phase 6: Pre-YAML Validation

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes**:
1. **Add pre-YAML validation step** (before calling generate_automation_yaml):
   ```python
   async def validate_suggestion_entity_completeness(
       suggestion: Dict[str, Any],
       ha_client: Optional[HomeAssistantClient]
   ) -> Tuple[bool, Dict[str, str], List[str]]:
       """
       Validate that all devices mentioned in suggestion have entity IDs.
       Returns: (is_complete, entity_id_map, missing_devices)
       """
   ```

2. **Query HA for missing entities**:
   - If device mention doesn't have entity ID, query HA for domain matches
   - Use fuzzy matching to find closest entity
   - Add to validated_entities if found

## Implementation Details

### Key Functions to Create

1. **`pre_populate_entity_ids_in_suggestion`**:
   - Input: suggestion dict, validated_entities, enriched_data
   - Output: enhanced suggestion with entity_ids_used and entity_id_annotations
   - Logic: Scan all text fields, extract device mentions, map to entity IDs

2. **`extract_device_mentions_from_text`**:
   - Input: text (description, trigger_summary, etc.), validated_entities
   - Output: dict mapping mention → entity_id
   - Logic: Tokenize text, match against validated_entities using fuzzy matching

3. **`enhance_validated_entities_for_suggestion`**:
   - Input: suggestion, validated_entities, ha_client
   - Output: enhanced validated_entities with all mentions mapped
   - Logic: Extract mentions, query HA if needed, add to mapping

4. **`build_suggestion_specific_entity_mapping`**:
   - Input: suggestion, validated_entities
   - Output: formatted text for LLM prompt
   - Logic: Create explicit mapping table for devices in THIS suggestion

### Enhanced Prompt Structure

Add to YAML generation prompt:

```
SUGGESTION-SPECIFIC ENTITY ID MAPPINGS:
For THIS specific automation suggestion, use these exact mappings:

Description: "turn on WLED when office desk presence is detected"
Trigger mentions: "office desk presence"
Action mentions: "WLED"

ENTITY ID MAPPINGS FOR THIS AUTOMATION:
- "WLED" or "wled" → wled.office
- "office desk presence" → binary_sensor.office_motion
- "office light" → light.office

CRITICAL: When generating YAML, use the entity IDs above. If you see "WLED" in the description, use "wled.office" (NOT just "wled").
```

## Success Criteria

1. All suggestions have `entity_ids_used` field populated with actual entity IDs
2. All device mentions in suggestions are mapped to entity IDs before YAML generation
3. YAML generation prompt includes suggestion-specific entity ID mappings
4. Zero incomplete entity IDs (like "wled") in generated YAML
5. Reverse engineering similarity > 95% on first attempt (reduced need for iterations)

## Files to Modify

1. `services/ai-automation-service/src/api/ask_ai_router.py`
   - Lines 1468-1489: Enhance suggestion creation with entity IDs
   - Lines 314-358: Improve device-to-entity mapping
   - Lines 395-476: Add pre-validation and entity ID pre-population
   - Lines 536-575: Enhance prompt with suggestion-specific mappings

2. New helper functions:
   - `pre_populate_entity_ids_in_suggestion`
   - `extract_device_mentions_from_text`
   - `enhance_validated_entities_for_suggestion`
   - `build_suggestion_specific_entity_mapping`
   - `validate_suggestion_entity_completeness`

## Testing Strategy

1. Generate suggestions with device mentions
2. Verify `entity_ids_used` is populated
3. Verify `entity_id_annotations` maps all mentions
4. Generate YAML and verify no incomplete entity IDs
5. Measure reverse engineering similarity (should be > 95% on first attempt)

## Risk Mitigation

1. **Fallback to current behavior**: If pre-population fails, continue with current mapping
2. **Fuzzy matching tolerance**: Use conservative thresholds to avoid wrong mappings
3. **Validation**: Re-validate entity IDs exist in HA before adding to mapping
4. **Logging**: Comprehensive logging of all mappings for debugging

