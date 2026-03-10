# Epic 45: Observability Dashboard — Full Test Suite

**Sprint:** 10
**Priority:** P1 (High)
**Status:** Complete
**Created:** 2026-03-09 | **Completed:** 2026-03-10
**Effort:** 1 week
**Dependencies:** Epic 42, Story 42.4 (pytest setup)
**Source:** `docs/planning/frontend-testing-epics.md` (Epic 53 mapping)

## Objective

Achieve 70%+ coverage for the observability-dashboard by expanding the existing test suite. Currently has 3 test files + conftest with 35 passing tests across 14 source files. JaegerClient and trace helpers are already tested.

## Verified Baseline (2026-03-10)

| File | Tests | Status |
|------|-------|--------|
| test_jaeger_client.py | 12 | All passing |
| test_trace_helpers.py | 16 | All passing |
| test_anomaly_detection.py | 7 | All passing |
| conftest.py | Fixtures | make_span, make_trace, etc. |

## Stories

### Story 45.1: Expand JaegerClient Tests (P0)
- Already has 12 tests covering get_traces, get_trace, get_services, get_dependencies, close
- Add: search_traces tests, cache TTL expiry, concurrent request handling
- Add: Pydantic model validation edge cases (missing fields, type coercion)
- **Target:** +10-15 new tests
- **Effort:** 2 hours

### Story 45.2: Data Processing & Page Logic Tests (P0)
- Test _create_timeline_chart, _create_dependency_graph (trace_visualization.py)
- Test _calculate_service_metrics, _create_health_dataframe (service_performance.py)
- Test _calculate_service_health, _detect_anomalies (real_time_monitoring.py)
- Test run_async_safe (async_helpers.py)
- **Target:** 15-20 tests
- **Effort:** 3 hours

### Story 45.3: Streamlit Component Tests (P1)
- Test page rendering functions with mocked Streamlit session state
- Test filter sidebar logic
- Test chart data preparation
- **Target:** 10-15 tests
- **Effort:** 3 hours

### Story 45.4: Error Handling & Edge Cases (P1)
- Test Jaeger unavailable scenarios
- Test malformed trace data handling
- Test empty state rendering
- **Target:** 8-10 tests
- **Effort:** 2 hours

## Acceptance Criteria
- [ ] 70%+ coverage for observability-dashboard
- [ ] JaegerClient fully tested with mocked HTTP
- [ ] Data processing logic has unit tests
- [ ] Error scenarios covered
