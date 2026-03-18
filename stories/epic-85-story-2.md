# Story 85.2 -- Device Database, Recommender & Statistics Metadata Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering the device data access layer, recommendation engine, and statistics metadata service, **so that** query logic and recommendation accuracy are validated independently of HTTP transport

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that device_database.py (~150 LOC), device_recommender.py (~130 LOC), and statistics_metadata.py (~160 LOC) have unit tests exercising query construction, similarity matching, and metadata management logic — three data-facing modules with zero test coverage.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**device_database.py** — Data access layer for device queries. Builds SQL/InfluxDB queries, handles pagination, caching. Called by device endpoints.

**device_recommender.py** — Generates device recommendations based on usage patterns and similarity matching between devices.

**statistics_metadata.py** — Manages statistics metadata (units, sources, measurement types). Used by analytics endpoints.

All three modules contain logic that should be tested at the unit level — query builders, similarity algorithms, metadata CRUD.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/services/device_database.py`
- `domains/core-platform/data-api/src/services/device_recommender.py`
- `domains/core-platform/data-api/src/services/statistics_metadata.py`
- `domains/core-platform/data-api/tests/test_device_database_unit.py` (new)
- `domains/core-platform/data-api/tests/test_device_recommender_unit.py` (new)
- `domains/core-platform/data-api/tests/test_statistics_metadata_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read device_database.py and map all query-building functions
- [ ] Write tests for device query construction with various filter combinations
- [ ] Write tests for pagination logic (offset, limit, edge cases)
- [ ] Write tests for cache key generation and cache hit/miss paths
- [ ] Read device_recommender.py and map recommendation algorithm
- [ ] Write tests for similarity matching — identical devices score highest
- [ ] Write tests for similarity matching — different device types score low
- [ ] Write tests for recommendation with empty device pool
- [ ] Write tests for recommendation result ordering and limits
- [ ] Read statistics_metadata.py and map CRUD operations
- [ ] Write tests for metadata creation with valid inputs
- [ ] Write tests for metadata retrieval by measurement type
- [ ] Write tests for metadata update and unit handling
- [ ] Write tests for edge cases (unknown measurement, duplicate entries)
- [ ] Verify all tests pass: `pytest tests/test_device_database_unit.py tests/test_device_recommender_unit.py tests/test_statistics_metadata_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] device_database.py has 5+ unit tests covering query construction and pagination
- [ ] device_recommender.py has 5+ unit tests covering similarity and ranking logic
- [ ] statistics_metadata.py has 5+ unit tests covering CRUD and edge cases
- [ ] Database I/O mocked at the connection level (not the service level)
- [ ] All tests pass without external services

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_device_query_no_filters` -- Default query returns all devices
2. `test_device_query_with_area_filter` -- Area filter applied correctly to query
3. `test_device_query_pagination` -- Offset and limit produce correct query bounds
4. `test_device_query_pagination_edge` -- Zero limit or negative offset handled
5. `test_device_cache_key_generation` -- Same filters produce same cache key
6. `test_recommender_identical_devices` -- Identical devices have highest similarity
7. `test_recommender_different_types` -- Different device types score low
8. `test_recommender_empty_pool` -- Empty device pool returns empty results
9. `test_recommender_result_ordering` -- Results ordered by similarity descending
10. `test_recommender_limit_respected` -- Result count respects limit parameter
11. `test_statistics_metadata_create` -- Create metadata with valid measurement type
12. `test_statistics_metadata_retrieve` -- Retrieve metadata by measurement type
13. `test_statistics_metadata_update_unit` -- Update metadata unit field
14. `test_statistics_metadata_unknown_type` -- Unknown measurement type handled gracefully
15. `test_statistics_metadata_duplicate` -- Duplicate entry handling

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- device_database.py likely constructs raw SQL or InfluxDB Flux queries — test the query strings, not execution
- device_recommender.py similarity algorithm may use cosine distance or Jaccard — verify formula in code
- Mock only the database session/connection, keep all business logic real

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None — standalone service modules

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No dependency on other stories
- [x] **N**egotiable -- Test count adjustable per module complexity
- [x] **V**aluable -- Protects data access and recommendation accuracy
- [x] **E**stimable -- Clear scope: 3 files, ~440 LOC
- [x] **S**mall -- 5 points, deliverable in a single session
- [x] **T**estable -- Direct unit tests with measurable line coverage

<!-- docsmcp:end:invest -->
