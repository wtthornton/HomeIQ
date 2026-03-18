# Story 85.1 -- Entity Enrichment & Device Classifier Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering entity enrichment and device classification logic, **so that** changes to these core service modules are caught before they break device-related features downstream

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that entity_enrichment.py (~270 LOC) and device_classifier.py (~200 LOC) have direct unit tests exercising their internal logic — attribute injection, domain-specific enrichment, classification pattern matching, and fallback behavior — rather than being tested only indirectly through mocked HTTP endpoints.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

These two service modules contain the core business logic for how devices and entities are enriched and classified. Currently they have near-zero line coverage because Epic 83 tested them only at the HTTP contract level with mocked dependencies.

**entity_enrichment.py** — Adds missing attributes to entity objects: area assignment, label inference, state enrichment. Called by multiple endpoint handlers.

**device_classifier.py** — Classifies devices by analyzing entity domain patterns (e.g., `light.*`, `sensor.*`, `climate.*`). Uses fallback patterns when the ML classifier is unavailable.

Both modules are pure business logic with minimal I/O — ideal candidates for high-coverage unit testing.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/services/entity_enrichment.py`
- `domains/core-platform/data-api/src/services/device_classifier.py`
- `domains/core-platform/data-api/tests/test_entity_enrichment_unit.py` (new)
- `domains/core-platform/data-api/tests/test_device_classifier_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read entity_enrichment.py and map all public functions and branches
- [ ] Write tests for `enrich_entity()` — happy path with complete entity
- [ ] Write tests for `enrich_entity()` — entity missing area_id (should infer or leave None)
- [ ] Write tests for `enrich_entity()` — entity missing labels (should apply defaults)
- [ ] Write tests for `enrich_entity()` — domain-specific enrichment (light vs sensor vs climate)
- [ ] Write tests for enrichment with None/empty input values
- [ ] Read device_classifier.py and map all public functions and branches
- [ ] Write tests for `classify_device()` — single-domain device (e.g., all light entities)
- [ ] Write tests for `classify_device()` — multi-domain device (mixed entity types)
- [ ] Write tests for `classify_device_from_domains()` — known domain patterns
- [ ] Write tests for `classify_device_from_domains()` — unknown domain (fallback)
- [ ] Write tests for classifier with empty entity list
- [ ] Write tests for classifier when ML classifier unavailable (fallback path)
- [ ] Verify all tests pass with `pytest tests/test_entity_enrichment_unit.py tests/test_device_classifier_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] entity_enrichment.py has 10+ unit tests covering all public functions
- [ ] device_classifier.py has 10+ unit tests covering all classification paths
- [ ] Both error/fallback branches are tested
- [ ] No mocked HTTP — tests call functions directly
- [ ] All tests pass without external services (InfluxDB, PostgreSQL)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_enrich_entity_complete` -- Enrichment preserves existing attributes on complete entity
2. `test_enrich_entity_missing_area` -- Enrichment handles entity with no area_id
3. `test_enrich_entity_missing_labels` -- Enrichment applies default labels when none exist
4. `test_enrich_entity_light_domain` -- Light entities get light-specific enrichment
5. `test_enrich_entity_sensor_domain` -- Sensor entities get sensor-specific enrichment
6. `test_enrich_entity_climate_domain` -- Climate entities get climate-specific enrichment
7. `test_enrich_entity_none_input` -- None/empty entity handles gracefully
8. `test_classify_device_single_domain` -- Device with all-light entities classified correctly
9. `test_classify_device_multi_domain` -- Device with mixed entity types classified correctly
10. `test_classify_device_from_known_domains` -- Known domain patterns return expected class
11. `test_classify_device_from_unknown_domain` -- Unknown domain returns fallback classification
12. `test_classify_device_empty_entities` -- Empty entity list returns default/unknown
13. `test_classify_device_ml_unavailable` -- ML fallback path exercised when classifier down

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- entity_enrichment.py may depend on database queries for area lookup — mock only the DB call, not the enrichment logic
- device_classifier.py uses `(entity.get("area_id") or "").lower()` pattern — test None vs empty string
- Classification fallback patterns are hardcoded — test each pattern explicitly

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None — standalone service modules with minimal I/O

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No dependency on other stories
- [x] **N**egotiable -- Test count and specific cases are adjustable
- [x] **V**aluable -- Core business logic protection for device features
- [x] **E**stimable -- Clear scope: 2 files, ~470 LOC
- [x] **S**mall -- 5 points, deliverable in a single session
- [x] **T**estable -- Direct unit tests with measurable line coverage

<!-- docsmcp:end:invest -->
