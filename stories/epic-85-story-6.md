# Story 85.6 -- Sports InfluxDB Writer Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering the sports InfluxDB writer, **so that** game status and team stats are serialized and written correctly to InfluxDB

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that sports_influxdb_writer.py has unit tests verifying data serialization, point construction, and write error handling — currently at zero test coverage.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**sports_influxdb_writer.py** — Writes sports data (game statuses, team stats) to InfluxDB. Constructs InfluxDB points with tags and fields, handles write errors and retries.

This module is self-contained with clear input/output — game data in, InfluxDB points out. Mock only the InfluxDB write client.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/sports_influxdb_writer.py`
- `domains/core-platform/data-api/tests/test_sports_influxdb_writer_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read sports_influxdb_writer.py and map all write functions
- [ ] Write tests for `write_game_status()` — valid game data produces correct InfluxDB point
- [ ] Write tests for `write_team_stats()` — team stats serialized with correct tags/fields
- [ ] Write tests for point construction — tags and fields have expected types
- [ ] Write tests for write error handling — InfluxDB connection failure
- [ ] Write tests for write retry logic (if applicable)
- [ ] Write tests for empty/null game data handling
- [ ] Verify all tests pass: `pytest tests/test_sports_influxdb_writer_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] sports_influxdb_writer.py has 8+ unit tests
- [ ] Point construction verified (measurement name, tags, fields, timestamp)
- [ ] Error and retry paths tested
- [ ] InfluxDB client mocked — no real writes

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_write_game_status_valid` -- Valid game data produces correct InfluxDB point
2. `test_write_game_status_tags` -- Point has correct tags (team, league, game_id)
3. `test_write_game_status_fields` -- Point has correct fields (score, status, period)
4. `test_write_team_stats_valid` -- Team stats serialized correctly
5. `test_write_team_stats_fields` -- Stats fields have correct types (int/float)
6. `test_write_connection_failure` -- InfluxDB failure handled gracefully
7. `test_write_empty_game_data` -- Empty/null input handled without crash
8. `test_write_point_timestamp` -- Timestamp set correctly on points

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Mock `influxdb_client.WriteApi` — verify `write()` called with expected point structure
- Use `influxdb_client.Point` assertions to check measurement, tags, fields

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Standalone writer module
- [x] **N**egotiable -- Test count adjustable
- [x] **V**aluable -- Ensures sports data integrity in InfluxDB
- [x] **E**stimable -- Single file, clear I/O boundaries
- [x] **S**mall -- 2 points, quick session
- [x] **T**estable -- Mock InfluxDB client, verify point construction

<!-- docsmcp:end:invest -->
