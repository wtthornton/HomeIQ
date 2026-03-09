# Epic 45: Observability Dashboard — Full Test Suite

**Sprint:** 10
**Priority:** P1 (High)
**Status:** Open
**Created:** 2026-03-09
**Effort:** 1 week
**Dependencies:** Epic 42, Story 42.4 (pytest setup)
**Source:** `docs/planning/frontend-testing-epics.md` (Epic 53 mapping)

## Objective

Achieve 70%+ coverage for the observability-dashboard by testing the Jaeger client, data processing, and async helpers. Currently at 0% coverage (0 test files / 12 source files).

## Stories

### Story 45.1: JaegerClient Unit Tests (P0)
- Test with mocked httpx: get_traces, get_services (caching, TTL), get_trace (404 handling), get_dependencies, search_traces, close
- Test Pydantic model validation: TraceSpan, Trace, Service, Dependency
- **Target:** 25-30 tests
- **Effort:** 4 hours

### Story 45.2: Data Processing Tests (P0)
- Test trace timeline construction, span tree building, duration calculations
- Test service dependency graph generation
- Test performance metric aggregation
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
