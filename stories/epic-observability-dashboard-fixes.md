---
epic: observability-dashboard-fixes
priority: high
status: open
estimated_duration: 1-2 weeks
risk_level: medium
source: REVIEW_AND_FIXES.md (2026-02-06), TAPPS quality review
---

# Epic: Observability Dashboard Fixes & Testing

**Status:** Open
**Priority:** High (P1)
**Duration:** 1-2 weeks
**Risk Level:** Medium
**Predecessor:** None — can start immediately
**Affects:** domains/frontends/observability-dashboard

## Context

The observability dashboard (Streamlit + Plotly) has critical blocking bugs —
`time.sleep()` freezes the entire server thread, making the app unresponsive
for all users. The automation debugging page has broken visualizations and
empty-by-default results. Zero test coverage exists. TAPPS quality review
shows all 7 Python files passing lint but high cyclomatic complexity (CC 18-22).

## Stories

### Story 1: Fix time.sleep() Blocking (Critical)

**Priority:** Critical | **Estimate:** 3h | **Risk:** Low

**Problem:** `time.sleep(refresh_interval)` in `real_time_monitoring.py:84-86` blocks
the entire Streamlit server thread for 5-60 seconds. Application is completely
unresponsive to ALL users during sleep.

**Fix:** Replace with Streamlit's `@st.fragment(run_every=timedelta(seconds=N))` decorator
which runs the fragment on a schedule without blocking the main thread.

**Acceptance Criteria:**
- [ ] `time.sleep()` removed from all Streamlit code
- [ ] Auto-refresh uses `@st.fragment(run_every=...)` pattern
- [ ] App remains responsive during refresh cycle (manual test)
- [ ] Refresh interval configurable from sidebar (existing slider preserved)

---

### Story 2: Fix Automation Debugging Page Bugs

**Priority:** High | **Estimate:** 4h | **Risk:** Low

**Problem:** Multiple bugs make the page non-functional:
- `_query_automation_traces()` returns empty list when no filter is specified (H2)
- `px.timeline` called with wrong column types — `x_start=0` (int) and `x_end="Duration (ms)"` (string) instead of datetime columns (H5)
- `query_params` dict built but never passed to any function (M6)

**Acceptance Criteria:**
- [ ] Default query returns recent traces when no filter is applied
- [ ] Timeline visualization renders correctly with proper datetime columns
- [ ] Dead `query_params` block removed
- [ ] Page loads without errors when accessed with no filters

---

### Story 3: Fix Anomaly Detection Duplicates

**Priority:** High | **Estimate:** 2h | **Risk:** Low

**Problem:** `_detect_anomalies()` calls `_has_errors(trace)` inside the per-span loop.
N spans with an error generates N duplicate anomaly entries for the same trace.

**Also:** `_has_errors()` logic duplicated across 3 files (M2).

**Acceptance Criteria:**
- [ ] Anomaly detection de-duplicated — one entry per trace, not per span
- [ ] `_has_errors()` extracted to shared utility in `src/utils/`
- [ ] Total trace duration uses `max(start+duration) - min(start)` not sum of all spans (M4)

---

### Story 4: Fix Resource Leaks & Connection Management

**Priority:** High | **Estimate:** 3h | **Risk:** Low

**Problem:**
- `httpx.AsyncClient` created in `__init__` but never closed (H3) — connection pool exhaustion
- Sequential HTTP calls in `_get_service_operations` (30+ requests) and `service_performance` (10+ requests)

**Acceptance Criteria:**
- [ ] `httpx.AsyncClient` uses context manager or explicit cleanup on session end
- [ ] `_get_service_operations` uses `asyncio.gather` for parallel requests
- [ ] Service performance queries parallelized with `asyncio.gather`
- [ ] Connection pool size limits configured

---

### Story 5: Clean Up Dead Code & Dependencies

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Problem:**
- 8 unused dependencies in `requirements.txt` (M1)
- `sys.path.append()` in every file instead of proper package structure (M3)
- Dead InfluxDB configuration (configured but never used) (M5)
- Unused `import asyncio` (M7), unused `python-dotenv` (M8)
- Empty `src/components/__init__.py` skeleton (L7)
- `.ruff_cache/` directories committed to source (L8)
- Stale README showing Phases 2-5 as "In Progress" (L1)
- Rollback script with hardcoded Windows paths (L2)

**Acceptance Criteria:**
- [ ] Unused dependencies removed from `requirements.txt`
- [ ] `sys.path.append()` replaced with proper relative imports or package install
- [ ] Dead InfluxDB config removed
- [ ] Unused imports removed
- [ ] `.ruff_cache/` added to `.gitignore` and removed from git
- [ ] README status updated to reflect actual state

---

### Story 6: Fix Port Configuration Conflict

**Priority:** Medium | **Estimate:** 1h | **Risk:** Low

**Problem:** Admin API default port is `8004` in code but some references show `8003`.
`stats_endpoints.py:27` references `localhost:8003`.

**Acceptance Criteria:**
- [ ] All admin-api port references consistent (8004)
- [ ] `stats_endpoints.py` corrected
- [ ] Port documented in service README

---

### Story 7: Establish Test Coverage

**Priority:** High | **Estimate:** 2-3 days | **Risk:** Low

**Problem:** Zero tests exist. `tests/` directory is completely empty.
No coverage for Jaeger client, anomaly detection, service metrics, or any utility.

**Acceptance Criteria:**
- [ ] pytest + pytest-asyncio configured
- [ ] Unit tests for `JaegerClient` (mock httpx responses)
- [ ] Unit tests for `_detect_anomalies()` (with dedup fix from Story 3)
- [ ] Unit tests for `_has_errors()` shared utility
- [ ] Unit tests for trace duration calculation
- [ ] Unit tests for percentile calculation (fix off-by-one L4: use `numpy.percentile`)
- [ ] Integration test for each Streamlit page (smoke test rendering)
- [ ] Coverage threshold: 50% (first target)
- [ ] CI runs `pytest --cov` and fails below threshold

---

### Story 8: Add Resource Limits & Monitoring

**Priority:** Low | **Estimate:** 1h | **Risk:** Low

**Problem:**
- No `deploy.resources` limits in docker-compose for Streamlit+Plotly (L6)
- Container runs as root (L5)

**Acceptance Criteria:**
- [ ] Memory limit set (e.g., 512MB) in compose
- [ ] CPU limit set in compose
- [ ] `USER` directive in Dockerfile (non-root)
