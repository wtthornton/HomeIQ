# Story 85.5 -- Metrics Buffer & State Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering the metrics buffer and state modules, **so that** request metrics collection and aggregation logic is verified independently

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that metrics_buffer.py and metrics_state.py have unit tests verifying request recording, buffer management, and metrics aggregation — currently at zero test coverage despite being called on every API request.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**metrics_buffer.py** — Buffers request metrics (latency, status codes, error counts) before flush. Called by middleware on every request. Functions include `record_request()` for latency/error tracking.

**metrics_state.py** — Manages aggregated metrics state. Accumulates per-endpoint and per-status-code counts, computes percentiles, handles state reset.

These modules run on every request path but have zero tests. Bugs here silently corrupt metrics data.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/metrics_buffer.py`
- `domains/core-platform/data-api/src/metrics_state.py`
- `domains/core-platform/data-api/tests/test_metrics_buffer_unit.py` (new)
- `domains/core-platform/data-api/tests/test_metrics_state_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read metrics_buffer.py and map all functions and buffer behavior
- [ ] Write tests for `record_request()` — normal request recording
- [ ] Write tests for buffer accumulation — multiple requests buffered correctly
- [ ] Write tests for buffer flush — buffer cleared after flush
- [ ] Write tests for buffer overflow handling (if applicable)
- [ ] Read metrics_state.py and map state management functions
- [ ] Write tests for per-endpoint count tracking
- [ ] Write tests for per-status-code aggregation
- [ ] Write tests for percentile computation (p50, p95, p99)
- [ ] Write tests for state reset
- [ ] Write tests for concurrent access safety (if applicable)
- [ ] Verify all tests pass: `pytest tests/test_metrics_buffer_unit.py tests/test_metrics_state_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] metrics_buffer.py has 5+ unit tests covering record/flush/overflow
- [ ] metrics_state.py has 5+ unit tests covering aggregation and percentiles
- [ ] All tests pass without external services
- [ ] No dependency on actual HTTP requests — test functions directly

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_record_request_basic` -- Single request recorded with correct latency and status
2. `test_record_multiple_requests` -- Multiple requests accumulated in buffer
3. `test_buffer_flush_clears` -- Flush returns buffered data and clears buffer
4. `test_buffer_empty_flush` -- Flush on empty buffer returns empty/zero
5. `test_record_error_request` -- Error status codes tracked separately
6. `test_metrics_endpoint_counts` -- Per-endpoint request counts accurate
7. `test_metrics_status_code_counts` -- Per-status-code aggregation correct
8. `test_metrics_percentile_p50` -- p50 latency computed correctly
9. `test_metrics_percentile_p99` -- p99 latency computed correctly
10. `test_metrics_state_reset` -- State reset clears all counters

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Metrics modules may use thread-safe data structures — verify in code before writing concurrent tests
- Percentile computation may use sorted arrays or streaming algorithms — adapt test expectations accordingly

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Standalone metrics modules
- [x] **N**egotiable -- Specific test cases adjustable
- [x] **V**aluable -- Runs on every request — silent corruption risk
- [x] **E**stimable -- Clear scope: 2 files, well-defined behavior
- [x] **S**mall -- 3 points, half-session
- [x] **T**estable -- Pure state management, easy to verify

<!-- docsmcp:end:invest -->
