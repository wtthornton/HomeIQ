# E2E Tests for HomeIQ JSON Automation Workflow

## Overview

Comprehensive end-to-end tests for the HomeIQ JSON Automation layer, verifying the complete workflow from JSON generation to storage and retrieval.

## Test Coverage

### 1. JSON Generation E2E Tests (`test_json_generation_e2e.py`)

**Tests:**
- `test_json_generation_complete_workflow` - Complete flow: suggestion → JSON → validation → conversion → YAML → storage
- `test_json_validation_e2e` - JSON schema validation with entity checking
- `test_json_to_yaml_conversion_e2e` - JSON to AutomationSpec to YAML conversion

**Coverage:**
- ✅ JSON generation from suggestions
- ✅ Pydantic schema validation
- ✅ Entity ID validation
- ✅ Conversion to AutomationSpec
- ✅ Version-aware YAML rendering
- ✅ Database storage with version tracking

### 2. JSON Storage E2E Tests (`test_json_storage_e2e.py`)

**Tests:**
- `test_json_storage_and_retrieval_e2e` - Store and retrieve JSON from database
- `test_json_query_e2e` - Query JSON automations by properties (use_case, entity_id, energy_impact)
- `test_json_update_e2e` - Update JSON in database

**Coverage:**
- ✅ JSON serialization for database storage
- ✅ JSON deserialization from database
- ✅ Query by use_case, entity_id, energy_impact
- ✅ JSON updates and persistence

### 3. JSON Rebuild E2E Tests (`test_json_rebuild_e2e.py`)

**Tests:**
- `test_json_rebuild_from_yaml_e2e` - Rebuild JSON from existing YAML
- `test_json_rebuild_from_description_e2e` - Rebuild JSON from natural language description
- `test_json_rebuild_roundtrip_e2e` - JSON → YAML → JSON roundtrip verification

**Coverage:**
- ✅ Rebuild JSON from YAML structure
- ✅ Rebuild JSON from natural language (simulated LLM)
- ✅ Roundtrip conversion verification
- ✅ Data integrity preservation

## Running Tests

### Run All E2E Tests

```bash
cd services/ai-automation-service-new
python -m pytest tests/e2e/ -v -m e2e
```

### Run Specific Test File

```bash
# JSON generation tests
python -m pytest tests/e2e/test_json_generation_e2e.py -v

# JSON storage tests
python -m pytest tests/e2e/test_json_storage_e2e.py -v

# JSON rebuild tests
python -m pytest tests/e2e/test_json_rebuild_e2e.py -v
```

### Run Specific Test

```bash
python -m pytest tests/e2e/test_json_generation_e2e.py::test_json_generation_complete_workflow -v
```

## Test Results

**Current Status:** ✅ **All 9 tests passing**

```
tests/e2e/test_json_generation_e2e.py::test_json_generation_complete_workflow PASSED
tests/e2e/test_json_generation_e2e.py::test_json_validation_e2e PASSED
tests/e2e/test_json_generation_e2e.py::test_json_to_yaml_conversion_e2e PASSED
tests/e2e/test_json_rebuild_e2e.py::test_json_rebuild_from_yaml_e2e PASSED
tests/e2e/test_json_rebuild_e2e.py::test_json_rebuild_from_description_e2e PASSED
tests/e2e/test_json_rebuild_e2e.py::test_json_rebuild_roundtrip_e2e PASSED
tests/e2e/test_json_storage_e2e.py::test_json_storage_and_retrieval_e2e PASSED
tests/e2e/test_json_storage_e2e.py::test_json_query_e2e PASSED
tests/e2e/test_json_storage_e2e.py::test_json_update_e2e PASSED
```

## Test Architecture

### Database Fixtures

Tests use in-memory SQLite database via `db_session` fixture:
- Fresh database for each test
- Automatic table creation
- Clean isolation between tests

### Test Data

Tests create realistic HomeIQ JSON automations with:
- Complete metadata (use_case, complexity)
- Device context (entity_ids, area_ids)
- Safety checks
- Energy impact estimates
- Triggers and actions

### Assertions

Tests verify:
- JSON schema validity
- Database persistence
- Query filtering accuracy
- Roundtrip conversion integrity
- YAML rendering correctness

## Integration Points Tested

1. **HomeIQ JSON Schema** - Pydantic model validation
2. **JSON Validator** - Schema and entity validation
3. **JSON Converter** - HomeIQ JSON → AutomationSpec
4. **YAML Renderer** - Version-aware YAML generation
5. **Database Models** - JSON storage and retrieval
6. **Query Service** - JSON property filtering
7. **Rebuild Service** - YAML → JSON reconstruction

## Future Enhancements

- [ ] API endpoint E2E tests (with running service)
- [ ] LLM integration tests (with real OpenAI API)
- [ ] Multi-automation combination tests
- [ ] Performance benchmarks
- [ ] Error handling and edge case tests

