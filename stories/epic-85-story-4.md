# Story 85.4 -- Flux Utilities Security & Sanitization Tests

<!-- docsmcp:start:user-story -->

> **As a** security engineer, **I want** comprehensive unit tests for InfluxDB Flux query sanitization, **so that** injection attacks against the data-api's query layer are validated as blocked

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that flux_utils.py — the security-critical module that sanitizes all InfluxDB Flux queries — has boundary tests for malicious inputs, unicode attacks, special characters, and injection patterns. This is the single point of defense against InfluxDB injection in the entire platform.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**flux_utils.py** handles Flux query building and value sanitization for all InfluxDB queries in data-api. Functions include `sanitize_flux_value()` which prevents injection by escaping/rejecting dangerous inputs.

Epic 83 discovered that energy endpoints have a bug where `HTTPException` from `sanitize_flux_value()` is swallowed by broad `except Exception` blocks. This makes sanitization testing even more critical — we need to verify the sanitizer itself works correctly even if callers mishandle exceptions.

Existing `test_flux_security.py` (122 lines) provides some coverage but is incomplete — it doesn't test unicode, multi-byte characters, nested injection, or all query builder functions.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/flux_utils.py`
- `domains/core-platform/data-api/tests/test_flux_security.py` (existing, extend)
- `domains/core-platform/data-api/tests/test_flux_utils_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read flux_utils.py and map all public functions and sanitization rules
- [ ] Write tests for `sanitize_flux_value()` — normal string inputs (alphanumeric, spaces)
- [ ] Write tests for `sanitize_flux_value()` — SQL injection patterns (`'; DROP TABLE --`)
- [ ] Write tests for `sanitize_flux_value()` — Flux injection patterns (pipe operators, function calls)
- [ ] Write tests for `sanitize_flux_value()` — unicode/multi-byte characters
- [ ] Write tests for `sanitize_flux_value()` — null bytes, control characters
- [ ] Write tests for `sanitize_flux_value()` — empty string, None, numeric inputs
- [ ] Write tests for Flux query builder functions — valid measurement names
- [ ] Write tests for Flux query builder — time range construction
- [ ] Write tests for Flux query builder — filter construction with multiple fields
- [ ] Write tests for Flux query builder — aggregation window construction
- [ ] Write tests for query builder with special characters in bucket/measurement names
- [ ] Verify all tests pass: `pytest tests/test_flux_utils_unit.py tests/test_flux_security.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] `sanitize_flux_value()` has 8+ boundary tests including injection patterns
- [ ] Flux query builder functions have 7+ tests covering construction logic
- [ ] Unicode and multi-byte character handling verified
- [ ] All injection patterns raise HTTPException or return sanitized output
- [ ] Tests document the expected behavior for each attack vector

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_sanitize_normal_string` -- Alphanumeric string passes through unchanged
2. `test_sanitize_string_with_spaces` -- Spaces preserved in sanitized output
3. `test_sanitize_sql_injection` -- SQL injection pattern rejected or escaped
4. `test_sanitize_flux_pipe_injection` -- Flux pipe operator (`|>`) in value blocked
5. `test_sanitize_flux_function_injection` -- Flux function call in value blocked
6. `test_sanitize_unicode_characters` -- Unicode characters handled safely
7. `test_sanitize_null_bytes` -- Null bytes stripped or rejected
8. `test_sanitize_empty_string` -- Empty string handled gracefully
9. `test_sanitize_none_input` -- None input raises or returns safe default
10. `test_sanitize_numeric_input` -- Numeric values handled correctly
11. `test_query_builder_valid_measurement` -- Valid measurement name produces correct Flux
12. `test_query_builder_time_range` -- Time range parameters produce correct `range()` call
13. `test_query_builder_filters` -- Multiple filters produce correct `filter()` chain
14. `test_query_builder_aggregation` -- Aggregation window produces correct `aggregateWindow()`
15. `test_query_builder_special_chars` -- Special chars in bucket name handled

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- This is the highest-priority security module in data-api — treat test failures as blockers
- Refer to OWASP NoSQL injection patterns for test inspiration
- `sanitize_flux_value()` may raise HTTPException(400) for rejected inputs — verify both raise and sanitize paths
- Epic 83 bug: energy endpoints catch this exception — tests should verify sanitizer behavior independently

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Standalone security module
- [x] **N**egotiable -- Attack patterns can be expanded based on threat model
- [x] **V**aluable -- Single point of injection defense for all InfluxDB queries
- [x] **E**stimable -- Clear scope: 1 file, well-defined sanitization rules
- [x] **S**mall -- 5 points, focused on boundary testing
- [x] **T**estable -- Pure functions with clear pass/fail criteria

<!-- docsmcp:end:invest -->
