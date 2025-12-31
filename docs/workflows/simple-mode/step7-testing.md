# Step 7: Testing Plan

**Date:** December 31, 2025  
**Workflow:** Entity Validation Fix for ai-automation-service-new  
**Step:** 7 of 7

## Test Plan

### Unit Tests Required

#### 1. `_fetch_entity_context()` Tests
- ✅ Test successful entity fetch
- ✅ Test empty result handling
- ✅ Test Data API failure handling
- ✅ Test entity grouping by domain
- ✅ Test entity info extraction (entity_id, friendly_name, area_id)

#### 2. `_format_entity_context_for_prompt()` Tests
- ✅ Test formatting with entities
- ✅ Test empty context handling
- ✅ Test domain grouping
- ✅ Test entity limit (50 per domain)
- ✅ Test friendly name and area inclusion

#### 3. Enhanced `_extract_entity_ids()` Tests
- ✅ Test direct entity_id extraction
- ✅ Test entity_id list extraction
- ✅ Test template expression extraction (`{{ states('entity_id') }}`)
- ✅ Test template condition extraction (`{{ is_state('entity_id', 'on') }}`)
- ✅ Test scene snapshot extraction
- ✅ Test nested structure traversal
- ✅ Test area_id handling (not added to entity_ids)

#### 4. Entity Validation Tests
- ✅ Test validation with valid entities
- ✅ Test validation with invalid entities
- ✅ Test validation failure raises YAMLGenerationError
- ✅ Test error message includes invalid entity list

#### 5. Integration Tests
- ✅ Test full flow: fetch → generate → validate
- ✅ Test validation blocks invalid YAML
- ✅ Test entity context passed to OpenAI client
- ✅ Test all generation paths (HomeIQ JSON, structured plan, direct)

### Test Files to Create

1. `tests/services/test_yaml_generation_service_entity_validation.py`
2. `tests/clients/test_openai_client_entity_context.py`
3. `tests/integration/test_entity_validation_flow.py`

### Test Coverage Goals

- **Target:** 80% coverage for new code
- **Critical Paths:** 100% coverage
  - Entity fetching
  - Entity validation
  - Entity context formatting
  - Entity extraction

### Manual Testing

1. Generate automation for office area
2. Verify only real entities used
3. Verify validation fails for fictional entities
4. Verify error messages are helpful
