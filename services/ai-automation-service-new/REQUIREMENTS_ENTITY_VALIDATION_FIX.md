# Requirements: Fix Entity Validation in YAML Generation

**Date:** December 31, 2025  
**Service:** ai-automation-service-new  
**Priority:** 🔴 **CRITICAL**  
**Status:** Requirements Document

## Problem Statement

The `ai-automation-service-new` service generates Home Assistant automation YAML with **fictional entity IDs** that don't exist in the deployed system. This causes automations to fail when executed.

### Example Issue

**Generated YAML References:**
- `binary_sensor.office_motion_1` ❌ (doesn't exist)
- `binary_sensor.office_motion_2` ❌ (doesn't exist)
- `binary_sensor.office_motion_3` ❌ (doesn't exist)
- `light.office_main` ❌ (doesn't exist)
- `light.office_desk_lamp` ❌ (doesn't exist)
- `light.office_accent_strip` ❌ (doesn't exist)
- `counter.office_motion_burst` ❌ (doesn't exist)
- `binary_sensor.office_occupied_90min` ❌ (doesn't exist)

**Actual System Entities:**
- `binary_sensor.office_motion_area` ✅ (exists)
- `binary_sensor.ps_fp2_office` ✅ (exists)
- `light.office` ✅ (exists)
- `light.hue_office_back_left` ✅ (exists)

### Root Cause

1. **No Entity Context in LLM Prompts**: The OpenAI client generates YAML without knowledge of actual entities
2. **Post-Generation Validation Only**: Entity validation happens AFTER generation, only logs warnings
3. **No Entity Resolution**: No mechanism to suggest similar/real entities when fictional ones are detected
4. **Validation Not Mandatory**: Entity validation failures don't prevent YAML generation

## Requirements

### R1: Entity Context Fetching

**Requirement ID:** R1  
**Priority:** P0 (Critical)

**Description:**
The service MUST fetch real entities from Data API BEFORE generating YAML.

**Acceptance Criteria:**
- [ ] `YAMLGenerationService.generate_automation_yaml()` fetches entities before LLM call
- [ ] Entities are cached for the duration of the generation request
- [ ] Entity fetch failures are handled gracefully (log warning, continue with empty context)
- [ ] Entity fetch includes: entity_id, domain, area_id, friendly_name, device_class

**Implementation Notes:**
- Use existing `DataAPIClient.fetch_entities()` method
- Cache entities in memory for request duration
- Filter entities by domain if needed (e.g., only lights, binary_sensors)

---

### R2: Entity Context in LLM Prompts

**Requirement ID:** R2  
**Priority:** P0 (Critical)

**Description:**
LLM prompts MUST include real entity context so the model uses actual entity IDs.

**Acceptance Criteria:**
- [ ] `OpenAIClient.generate_homeiq_automation_json()` receives entity context
- [ ] `OpenAIClient.generate_structured_plan()` receives entity context
- [ ] `OpenAIClient.generate_yaml()` receives entity context (legacy)
- [ ] Entity context includes:
  - List of available entities by domain
  - Entity-friendly names and descriptions
  - Area mappings (which entities are in which areas)
- [ ] System prompt instructs LLM to ONLY use entities from provided context

**Implementation Notes:**
- Add `entity_context: dict[str, Any] | None` parameter to all generation methods
- Format entity context as structured JSON in prompt
- Include example: "Available lights in office: light.office, light.hue_office_back_left"
- Update system prompts to emphasize using ONLY provided entities

---

### R3: Mandatory Entity Validation

**Requirement ID:** R3  
**Priority:** P0 (Critical)

**Description:**
Entity validation MUST be mandatory and MUST fail YAML generation if invalid entities are found.

**Acceptance Criteria:**
- [ ] `YAMLGenerationService.validate_entities()` is called after YAML generation
- [ ] If invalid entities found, generation fails with `YAMLGenerationError`
- [ ] Error message includes list of invalid entities
- [ ] Validation happens for all generation paths:
  - HomeIQ JSON → YAML
  - Structured Plan → YAML
  - Direct YAML generation (legacy)
- [ ] Validation extracts entities from:
  - `entity_id` fields
  - Template expressions (e.g., `{{ states('light.office') }}`)
  - Area-based targets (validate area exists)

**Implementation Notes:**
- Update `_generate_yaml_from_homeiq_json()` to validate after rendering
- Update `_generate_yaml_from_structured_plan()` to validate after rendering
- Update `_generate_yaml_direct()` to validate after generation
- Improve `_extract_entity_ids()` to handle template expressions
- Add area validation (check if `area_id: office` exists)

---

### R4: Entity Resolution and Suggestions

**Requirement ID:** R4  
**Priority:** P1 (High)

**Description:**
When invalid entities are detected, suggest similar/real entities to help fix the automation.

**Acceptance Criteria:**
- [ ] Entity resolution service suggests similar entities based on:
  - Name similarity (fuzzy matching)
  - Domain matching (e.g., `light.office_main` → `light.office`)
  - Area matching (e.g., office entities)
  - Device class matching (e.g., motion sensors)
- [ ] Suggestions are included in error messages
- [ ] Suggestions can be used to auto-fix YAML (optional feature)

**Implementation Notes:**
- Create `EntityResolutionService` class
- Use fuzzy string matching (e.g., `difflib.SequenceMatcher`)
- Match by domain + area + device_class
- Return top 3 suggestions per invalid entity

---

### R5: Enhanced Entity Extraction

**Requirement ID:** R5  
**Priority:** P1 (High)

**Description:**
Entity extraction MUST handle all YAML patterns where entities appear.

**Acceptance Criteria:**
- [ ] Extract entities from:
  - `entity_id` fields (single and lists)
  - Template expressions: `{{ states('entity_id') }}`
  - Template conditions: `{{ is_state('entity_id', 'on') }}`
  - Area targets: `area_id: office` (validate area exists)
  - Scene snapshots: `snapshot_entities: [entity_id, ...]`
  - Counter references: `counter.entity_id`
  - Group references: `group.entity_id` (validate group exists)
- [ ] Handle nested structures (choose blocks, repeat blocks, etc.)
- [ ] Extract from both YAML and HomeIQ JSON formats

**Implementation Notes:**
- Enhance `_extract_entity_ids()` method
- Add regex patterns for template expressions
- Recursively traverse all YAML structures
- Validate areas via Data API (if area endpoint exists)

---

### R6: Entity Context Formatting

**Requirement ID:** R6  
**Priority:** P1 (High)

**Description:**
Entity context MUST be formatted optimally for LLM consumption.

**Acceptance Criteria:**
- [ ] Entity context is grouped by domain (lights, binary_sensors, etc.)
- [ ] Entity context includes:
  - Entity ID
  - Friendly name
  - Area (if assigned)
  - Device class (if applicable)
  - Platform (if useful)
- [ ] Context is limited to relevant entities (e.g., filter by area if automation mentions area)
- [ ] Context size is optimized (max 2000 tokens for entity list)

**Implementation Notes:**
- Format as structured JSON or markdown
- Group by domain for easier LLM parsing
- Include examples: "Office lights: light.office (Office), light.hue_office_back_left (Hue Office Back Left)"
- Limit to top 100 entities per domain to avoid token limits

---

### R7: Error Messages and Logging

**Requirement ID:** R7  
**Priority:** P2 (Medium)

**Description:**
Error messages MUST be clear and actionable when entity validation fails.

**Acceptance Criteria:**
- [ ] Error messages include:
  - List of invalid entities
  - Suggested replacements (if R4 implemented)
  - Context about where entities were used (trigger, action, condition)
- [ ] Logging includes:
  - Entity validation results
  - Entity context used in generation
  - Entity resolution suggestions

**Implementation Notes:**
- Create structured error messages
- Include entity usage context in errors
- Log entity validation at INFO level
- Log entity context at DEBUG level

---

## Implementation Plan

### Phase 1: Critical Fixes (R1, R2, R3)

**Estimated Time:** 4-6 hours

1. **Update `YAMLGenerationService`** (2 hours)
   - Add entity fetching before generation
   - Pass entity context to OpenAI client methods
   - Make entity validation mandatory

2. **Update `OpenAIClient`** (1-2 hours)
   - Add `entity_context` parameter to all generation methods
   - Update system prompts to include entity context
   - Format entity context in prompts

3. **Enhance Entity Validation** (1-2 hours)
   - Improve `_extract_entity_ids()` to handle templates
   - Add area validation
   - Make validation fail on invalid entities

### Phase 2: Enhancements (R4, R5, R6)

**Estimated Time:** 4-6 hours

4. **Entity Resolution Service** (2-3 hours)
   - Create `EntityResolutionService` class
   - Implement fuzzy matching
   - Add suggestion logic

5. **Enhanced Entity Extraction** (1-2 hours)
   - Handle all YAML patterns
   - Extract from templates
   - Validate areas and groups

6. **Entity Context Formatting** (1 hour)
   - Format entity context optimally
   - Group by domain
   - Limit context size

### Phase 3: Polish (R7)

**Estimated Time:** 1-2 hours

7. **Error Messages and Logging** (1-2 hours)
   - Improve error messages
   - Add structured logging
   - Include suggestions in errors

## Testing Requirements

### Unit Tests

- [ ] Test entity context fetching
- [ ] Test entity context formatting
- [ ] Test entity extraction from YAML
- [ ] Test entity extraction from templates
- [ ] Test entity validation (pass and fail cases)
- [ ] Test entity resolution suggestions

### Integration Tests

- [ ] Test YAML generation with entity context
- [ ] Test YAML generation fails on invalid entities
- [ ] Test entity resolution suggestions
- [ ] Test with real Data API entities

### Manual Testing

- [ ] Generate automation for office area
- [ ] Verify only real entities are used
- [ ] Verify validation fails for fictional entities
- [ ] Verify suggestions are helpful

## Success Criteria

1. ✅ **Zero Fictional Entities**: All generated YAML uses only real entity IDs
2. ✅ **Validation Blocks Invalid YAML**: Generation fails if invalid entities detected
3. ✅ **Entity Context in Prompts**: LLM receives real entity context
4. ✅ **Helpful Error Messages**: Users understand which entities are invalid and get suggestions

## Related Files

- `src/services/yaml_generation_service.py` - Main YAML generation service
- `src/clients/openai_client.py` - OpenAI client for LLM generation
- `src/clients/data_api_client.py` - Data API client for entity fetching
- `src/services/plan_parser.py` - Plan parser (may need entity context)
- `shared/homeiq_automation/validator.py` - HomeIQ validator (may need entity validation)

## References

- Analysis Document: `implementation/analysis/OFFICE_AUTOMATION_ENTITY_ANALYSIS.md`
- Service README: `services/ai-automation-service-new/README.md`
- Implementation Status: `services/ai-automation-service-new/IMPLEMENTATION_STATUS.md`
