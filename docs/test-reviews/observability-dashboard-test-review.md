# Observability Dashboard Test Review

**Date**: March 2, 2026
**Reviewer**: Frontend Test Reviewer
**App Location**: `domains/frontends/observability-dashboard/`
**App Type**: Python Streamlit (internal observability tool)
**Framework**: Streamlit 1.54+, Plotly 5.17+, httpx, asyncio

---

## Executive Summary

**Current State**: 12 Python files (1,200+ LOC), **ZERO test coverage**

The observability dashboard is a **production-ready Streamlit application** with **CRITICAL test gaps**. Key components handling distributed trace visualization, real-time monitoring, and service health analytics have no test coverage.

**Status**: 🔴 **0 Test Files | 0% Coverage**

---

## App Location & Structure

### Directory Layout
```
domains/frontends/observability-dashboard/
├── src/
│   ├── main.py                                  # Streamlit entry point (96 LOC)
│   ├── pages/
│   │   ├── trace_visualization.py              # Traces dashboard (420 LOC)
│   │   ├── automation_debugging.py             # Automation traces (275 LOC)
│   │   ├── service_performance.py              # Service health (304 LOC)
│   │   └── real_time_monitoring.py             # Live monitoring (295 LOC)
│   ├── services/
│   │   └── jaeger_client.py                    # Jaeger API client (320 LOC)
│   └── utils/
│       └── async_helpers.py                    # Async utilities (42 LOC)
├── Dockerfile
├── requirements.txt                            # ✅ Well-structured
└── README.md                                   # ✅ Complete documentation
```

### File Count & Complexity
| Module | Files | LOC | Complexity | Test Status |
|--------|-------|-----|-----------|------------|
| main.py | 1 | 96 | Low | ❌ No tests |
| pages/ | 4 | 1,294 | High | ❌ No tests |
| services/ | 1 | 320 | High | ❌ No tests |
| utils/ | 1 | 42 | Medium | ❌ No tests |
| __init__.py | 3 | ~6 | None | N/A |
| **TOTAL** | **12** | **1,758** | **-** | **0 tests** |

---

## Test Infrastructure Status

### ❌ Critical Missing Infrastructure

1. **Test Framework Setup**
   - No `pytest.ini` or `pyproject.toml [tool.pytest]`
   - No `conftest.py` for shared fixtures
   - No test dependencies in `requirements.txt`

2. **Required Test Dependencies (NOT installed)**
   - `pytest>=8.0.0`
   - `pytest-asyncio>=0.24.0` (for async testing)
   - `pytest-httpx>=0.30.0` (for mocking httpx)
   - `responses>=0.24.0` (alternative HTTP mocking)
   - `pytest-mock>=3.14.0`

3. **Streamlit Testing Support (NOT installed)**
   - `streamlit.testing.v1` (built-in, not in requirements)
   - No fixtures for `st.session_state` mocking

4. **Missing Test Files**
   - No `tests/` directory
   - No `test_*.py` files
   - No fixtures in conftest.py

---

## Component Analysis & Test Gaps

### 1. **services/jaeger_client.py** (320 LOC) — CRITICAL 🔴

**Purpose**: Async HTTP client for Jaeger Query API

**Complexity**: High (async, caching, error handling)

**Public API** (7 async methods):
```python
async def get_traces(service, operation, limit, start_time, end_time) -> list[Trace]
async def get_trace(trace_id) -> Trace | None
async def get_services(force_refresh) -> list[Service]
async def get_dependencies(start_time, end_time) -> list[Dependency]
async def search_traces(query_params) -> list[Trace]
```

**Key Features Untested**:
- `get_traces()` with filters — API foundation
- `get_services()` + 5-minute cache TTL
- `get_trace()` by ID — Single trace lookup
- `get_dependencies()` — Dependency graph
- HTTP error handling (500, timeouts, parsing)
- Pydantic model validation

---

### 2. **pages/trace_visualization.py** (420 LOC) — HIGH 🟠

**Purpose**: Distributed trace visualization dashboard

**Untested Functions**:
- `show()` — Main dashboard UI (167 LOC)
- `_create_timeline_chart()` — Bubble chart (70 LOC)
- `_create_dependency_graph()` — Sankey diagram (60 LOC)
- `_create_trace_dataframe()` — Trace→DataFrame (22 LOC)
- Filter logic: service selection, time range presets
- Error detection in span tags

---

### 3. **pages/automation_debugging.py** (275 LOC) — HIGH 🟠

**Purpose**: Debug automation execution traces

**Untested Logic**:
- Filter matching by automation ID, home ID, correlation ID
- Success detection (error tags vs. status tags)
- Performance metrics aggregation
- Timeline visualization with "why" explanations

---

### 4. **pages/service_performance.py** (304 LOC) — HIGH 🟠

**Purpose**: Service health and latency monitoring

**Untested Functions**:
- `_calculate_service_metrics()` — p50/p95/p99 percentile calculation
- `_create_health_dataframe()` — Health status (🟢/🟡/🔴)
- Health thresholds: >10% errors = critical, >5% = warning, >1000ms p95 = warning
- Error rate computation

---

### 5. **pages/real_time_monitoring.py** (295 LOC) — HIGH 🟠

**Purpose**: Real-time trace streaming and anomaly detection

**Untested Functions**:
- `_detect_anomalies()` — High latency (>1000ms), error detection
- `_calculate_service_health()` — Health score formula: `100 - (error_rate * 2) - (latency_penalty)`
- Auto-refresh with `st.rerun()` and sleep

---

### 6. **utils/async_helpers.py** (42 LOC) — MEDIUM 🟡

**Purpose**: Safe async execution in Streamlit context

**Untested Logic**:
- `run_async_safe()` — Event loop detection
- ThreadPoolExecutor fallback when loop running
- Timeout handling (30s default)

---

## Current Test Coverage

**0 of 12 files have any test coverage**

| Category | Files | Status |
|----------|-------|--------|
| Services (API clients) | 1 | 🔴 0% |
| Pages (dashboards) | 4 | 🔴 0% |
| Utilities | 1 | 🔴 0% |
| Entry point | 1 | 🔴 0% |
| **TOTAL** | **12** | **0%** |

---

## Recommended Test Epics & Stories

### Epic 1: JaegerClient Unit Tests (P0 - CRITICAL)
**Rationale**: Foundation for all dashboards; async API with caching

- Story 1.1: `get_services()` with caching + TTL logic
- Story 1.2: `get_traces()` with filters (service, operation, time range)
- Story 1.3: `get_trace()` single trace retrieval
- Story 1.4: `get_dependencies()` time range queries
- Story 1.5: Error handling (HTTPError, parsing, timeout)

**Effort**: 40-60 hours

---

### Epic 2: Page Integration Tests (P1 - HIGH)
**Rationale**: User-facing dashboards with complex state management

- Story 2.1: `trace_visualization.show()` — filters, charts, state
- Story 2.2: `automation_debugging.show()` — filtering, success detection
- Story 2.3: `service_performance.show()` — metrics calculation, health status
- Story 2.4: `real_time_monitoring.show()` — anomaly detection, health scoring

**Effort**: 50-70 hours

---

### Epic 3: Utilities & Helpers (P2 - MEDIUM)
**Rationale**: Edge cases in async handling and data transformation

- Story 3.1: `run_async_safe()` — event loop detection, timeouts
- Story 3.2: DataFrame builders — empty data, outliers
- Story 3.3: Chart builders — visualization correctness

**Effort**: 15-25 hours

---

### Epic 4: Test Infrastructure (P3 - FOUNDATIONAL)
**Rationale**: Prerequisites for all tests

- Story 4.1: `pytest.ini` + `conftest.py` setup
- Story 4.2: Jaeger API mock fixtures
- Story 4.3: Streamlit session_state fixtures
- Story 4.4: CI integration (pytest in GitHub Actions)

**Effort**: 10-15 hours

---

## Test Infrastructure Needs

### Required Dependencies
```txt
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-httpx>=0.30.0
pytest-mock>=3.14.0
```

### Required Test Structure
```
tests/
├── conftest.py                      # Shared fixtures
├── fixtures/
│   ├── jaeger_responses.py         # Mock Jaeger API responses
│   └── streamlit_context.py        # Session state mocking
├── unit/
│   └── test_jaeger_client.py       # JaegerClient tests
└── integration/
    ├── test_trace_visualization.py
    ├── test_automation_debugging.py
    ├── test_service_performance.py
    └── test_real_time_monitoring.py
```

---

## Risk Assessment

| Risk | Severity | Impact | Likelihood |
|------|----------|--------|-----------|
| JaegerClient API errors not caught | CRITICAL | Dashboard crashes | HIGH |
| Cache bug (5min TTL) | HIGH | Stale data | MEDIUM |
| Chart rendering failures | HIGH | UI breakage | MEDIUM |
| Empty data handling | MEDIUM | Exceptions | MEDIUM |
| Async timeout issues | MEDIUM | Hanging UI | LOW |

---

## Summary

| Metric | Value |
|--------|-------|
| Total Lines of Code | 1,758 |
| Test Files | 0 |
| Coverage | 0% |
| Components Untested | 12 |
| Recommended Epics | 4 |
| Estimated Effort | 115-170 hours |

---

**Status**: Ready for epic/story creation
**Next Steps**: Approve P0-P3 epics, set up test infrastructure, build test cases
