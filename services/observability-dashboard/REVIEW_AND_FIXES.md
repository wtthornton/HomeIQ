# Observability Dashboard - Deep Code Review

**Service:** observability-dashboard (Tier 7 - Specialized)
**Port:** 8501
**Technology:** Python 3.11+, Streamlit, httpx, Plotly, Pydantic
**Reviewed:** 2026-02-06

## Service Overview

The Observability Dashboard is a Streamlit-based internal admin tool providing distributed trace visualization, automation debugging, service performance monitoring, and real-time observability via the Jaeger Query API. It is a read-only dashboard intended for internal/admin use, not customer-facing.

---

## Findings

### Critical

#### C1. `time.sleep()` blocks the entire Streamlit server thread

**File:** `src/pages/real_time_monitoring.py:84-86`
**Impact:** The auto-refresh feature calls `time.sleep(refresh_interval)` (5-60 seconds) which blocks the entire Streamlit server thread, making the application completely unresponsive to all users during the sleep period.

```python
# CURRENT (lines 84-86)
if auto_refresh:
    import time
    time.sleep(refresh_interval)
    st.rerun()
```

**Fix:** Use Streamlit's built-in `st.fragment` with `run_every` parameter (Streamlit 1.33+), or use `streamlit-autorefresh` as an external component, or at minimum use `st_autorefresh` from `streamlit_autorefresh`. Alternatively, use `time.sleep` in a much shorter interval with early-exit logic:

```python
# RECOMMENDED: Use streamlit-autorefresh or st.fragment
# Option A: streamlit_autorefresh (add to requirements.txt)
from streamlit_autorefresh import st_autorefresh
if auto_refresh:
    st_autorefresh(interval=refresh_interval * 1000, key="realtime_refresh")

# Option B: Use Streamlit's native auto_rerun (1.33+)
# Wrap the data-fetching section in a fragment with run_every
```

---

#### C2. Duplicate traces in anomaly detection due to trace-level error check inside span loop

**File:** `src/pages/real_time_monitoring.py:189-215`
**Impact:** The `_detect_anomalies` function calls `_has_errors(trace)` inside the per-span loop, meaning if a trace has N spans and an error, it generates N duplicate "Error" anomaly entries for the same trace. This produces misleading anomaly counts and clutters the anomaly table.

```python
# CURRENT (lines 205-215)
for trace in traces:
    for span in trace.spans:
        duration_ms = span.duration / 1000
        # ...latency check is correct (per-span)...

        # BUG: This checks the entire trace for errors once per span
        if _has_errors(trace):
            anomalies.append({
                "Type": "Error",
                "Trace ID": trace.traceID[:16] + "...",
                ...
            })
```

**Fix:** Move the error check outside the span loop, or check the specific span for errors instead of the entire trace:

```python
for trace in traces:
    for span in trace.spans:
        duration_ms = span.duration / 1000
        if duration_ms > 1000:
            anomalies.append({"Type": "High Latency", ...})

        # Check THIS span for errors, not the whole trace
        span_has_error = any(
            tag.get("key") == "error" and tag.get("value")
            for tag in span.tags
        )
        if span_has_error:
            anomalies.append({"Type": "Error", ...})
```

---

### High

#### H1. Admin API port mismatch: code says 8004, MEMORY.md and other services reference 8003

**File:** `src/main.py:35`
**Impact:** The admin-api default port is set to `http://admin-api:8004` but the project memory documents admin-api as port 8003. The docker-compose.yml also maps to 8004, so the code matches docker-compose, but this inconsistency with documentation could cause confusion. Verify which is correct and reconcile.

```python
# CURRENT (line 35)
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://admin-api:8004")
```

**Note:** docker-compose.yml line 213 confirms `8004:8004`, but `services/admin-api/src/stats_endpoints.py:27` references `http://localhost:8003`. This needs project-wide reconciliation.

---

#### H2. Automation trace filtering logic returns no results when no filter is specified

**File:** `src/pages/automation_debugging.py:174-193`
**Impact:** The `_query_automation_traces` function only adds traces to `filtered_traces` when one of the filter fields matches. If no filters are provided (all three are `None`), the inner condition is never true, and the function returns an empty list - even though traces were fetched successfully.

```python
# CURRENT (lines 183-191)
if automation_id and tag_key == "automation_id" and tag_value == automation_id:
    filtered_traces.append(trace)
    break
elif home_id and tag_key == "home_id" and tag_value == home_id:
    filtered_traces.append(trace)
    break
elif correlation_id and tag_key == "correlation_id" and tag_value == correlation_id:
    filtered_traces.append(trace)
    break
```

**Fix:** Return all traces when no filters are specified:

```python
# If no filters provided, return all traces
if not automation_id and not home_id and not correlation_id:
    return traces

# Otherwise, filter by provided criteria
filtered_traces = []
for trace in traces:
    for span in trace.spans:
        matched = False
        for tag in span.tags:
            # ...existing filter logic...
            if matched:
                break
        if matched:
            break
```

---

#### H3. `httpx.AsyncClient` is never closed - resource leak

**File:** `src/services/jaeger_client.py:70`
**Impact:** `JaegerClient.__init__` creates an `httpx.AsyncClient` but `close()` is never called. The client is stored in `st.session_state` and persists for the lifetime of the session without cleanup. This can lead to connection pool exhaustion over time.

```python
# CURRENT (line 70)
self.client = httpx.AsyncClient(timeout=30.0)
```

**Fix:** Implement `__aenter__`/`__aexit__` for context manager support, or add cleanup logic. Since Streamlit sessions are long-lived, consider at minimum adding a finalizer or using `atexit`:

```python
def __del__(self):
    """Cleanup HTTP client on garbage collection."""
    if hasattr(self, 'client') and not self.client.is_closed:
        try:
            asyncio.get_event_loop().run_until_complete(self.client.aclose())
        except Exception:
            pass
```

---

#### H4. No tests exist at all

**File:** `tests/` (empty directory)
**Impact:** The `tests/` directory is completely empty. Zero test coverage for any of the service's functionality - no unit tests for the Jaeger client, no tests for data transformation functions, no tests for anomaly detection logic.

**Fix:** Add tests for at minimum:
- `JaegerClient` methods (mock httpx responses)
- `_has_errors()` utility function
- `_detect_anomalies()` logic
- `_calculate_service_metrics()` computation
- `_is_automation_success()` logic
- `run_async_safe()` helper
- DataFrame creation functions

---

#### H5. Plotly `px.timeline` misuse in automation flow visualization

**File:** `src/pages/automation_debugging.py:250-257`
**Impact:** `px.timeline` expects `x_start` and `x_end` to be datetime columns, but the code passes `0` as `x_start` and `"Duration (ms)"` as `x_end`. This will raise a runtime error when executed.

```python
# CURRENT (lines 250-256)
fig = px.timeline(
    steps_df,
    x_start=0,         # BUG: expects datetime column name, not integer
    x_end="Duration (ms)",  # BUG: expects datetime column name
    y="Step",
    title="Automation Execution Timeline",
)
```

**Fix:** Either convert to actual datetime objects or use `px.bar` (horizontal) instead:

```python
fig = px.bar(
    steps_df,
    x="Duration (ms)",
    y="Step",
    orientation="h",
    title="Automation Execution Timeline",
)
```

---

### Medium

#### M1. Six unused dependencies in requirements.txt

**File:** `requirements.txt`
**Impact:** The following packages are declared in requirements.txt but never imported anywhere in the source code, adding unnecessary container image size and potential security surface:

| Package | Lines | Used? |
|---------|-------|-------|
| `opentelemetry-api` | 8 | No |
| `opentelemetry-sdk` | 9 | No |
| `opentelemetry-exporter-otlp-proto-grpc` | 10 | No |
| `networkx` | 16 | No |
| `aiohttp` | 22 | No |
| `websockets` | 23 | No |
| `nest-asyncio` | 28 | No |
| `influxdb-client` | 18 | No (URL configured but client never used) |

**Fix:** Remove unused dependencies:

```txt
# Observability Dashboard Service Dependencies
# Python 3.11+

# Streamlit Framework
streamlit>=1.28.0,<2.0.0

# Data & Visualization
pandas>=2.0.0,<3.0.0
plotly>=5.17.0,<6.0.0

# HTTP Clients
httpx>=0.25.0,<1.0.0

# Utilities
python-dotenv>=1.0.0,<2.0.0
pydantic>=2.5.0,<3.0.0
```

---

#### M2. `_has_errors()` function is duplicated across three files

**Files:**
- `src/pages/trace_visualization.py:251-257`
- `src/pages/real_time_monitoring.py:168-174`
- `src/pages/automation_debugging.py:196-212` (as `_is_automation_success`, similar logic)

**Impact:** DRY violation. The same error-checking logic is copy-pasted across three files. Any bug fix or logic change must be applied in all three places.

**Fix:** Extract to a shared utility in `src/utils/trace_helpers.py`:

```python
def has_errors(trace: Trace) -> bool:
    """Check if any span in the trace has error tags."""
    for span in trace.spans:
        for tag in span.tags:
            if tag.get("key") == "error" and tag.get("value"):
                return True
    return False
```

---

#### M3. `sys.path.append()` used for imports instead of proper package structure

**Files:** `src/main.py:19`, `src/pages/automation_debugging.py:16`, `src/pages/real_time_monitoring.py:16`, `src/pages/service_performance.py:17`, `src/pages/trace_visualization.py:19`

**Impact:** Every file manually manipulates `sys.path` for imports. This is fragile and can cause import confusion, particularly if the service is imported from different working directories.

```python
# CURRENT - in main.py (line 19)
sys.path.append(str(Path(__file__).parent.parent.parent / "shared"))

# CURRENT - in every page file
sys.path.append(str(Path(__file__).parent.parent))
```

**Fix:** Use proper package installation. Add a `pyproject.toml` or `setup.py` and install the package in development mode (`pip install -e .`). The Dockerfile `CMD` already uses `src/main.py` as the entry point, so the import paths would work correctly with a proper package.

---

#### M4. Incorrect total duration calculation in multiple places

**Files:**
- `src/pages/real_time_monitoring.py:236`
- `src/pages/automation_debugging.py:268`

**Impact:** Total duration is computed by summing all span durations, but spans can overlap (parallel execution). Summing durations overstates the actual wall-clock time of a trace.

```python
# CURRENT (real_time_monitoring.py:236)
total_duration = sum(span.duration for span in trace.spans) / 1000
```

**Fix:** Calculate wall-clock duration as `max(span.startTime + span.duration) - min(span.startTime)`:

```python
if trace.spans:
    start = min(span.startTime for span in trace.spans)
    end = max(span.startTime + span.duration for span in trace.spans)
    total_duration = (end - start) / 1000  # microseconds to ms
```

---

#### M5. InfluxDB URL configured but never used

**File:** `src/main.py:33,43`
**Impact:** `INFLUXDB_URL` is read from environment and stored in session state, but no code in the service actually connects to InfluxDB. The `influxdb-client` package is in requirements.txt but never imported.

```python
# CURRENT (lines 33, 43)
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
# ...stored in config but never used
```

**Fix:** Either implement InfluxDB integration for metrics or remove the dead configuration to avoid confusion.

---

#### M6. `query_params` dictionary built but never used in `_query_automation_traces`

**File:** `src/pages/automation_debugging.py:157-164`
**Impact:** A `query_params` dict is built with `limit`, `start`, and `end` keys, but it is never passed to any function. The actual query on line 167 uses keyword arguments instead.

```python
# CURRENT (lines 157-164) - query_params is dead code
query_params = {
    "limit": 100,
}
if start_time:
    query_params["start"] = int(start_time.timestamp() * 1000000)
if end_time:
    query_params["end"] = int(end_time.timestamp() * 1000000)

# This does NOT use query_params:
traces = await client.get_traces(
    service="ai-automation-service",
    start_time=start_time,
    end_time=end_time,
    limit=100,
)
```

**Fix:** Remove the dead `query_params` code block (lines 157-164).

---

#### M7. `asyncio` imported but unused in `trace_visualization.py`

**File:** `src/pages/trace_visualization.py:6`

```python
import asyncio  # Never used in this file
```

**Fix:** Remove the unused import.

---

#### M8. `python-dotenv` in requirements but never used

**File:** `requirements.txt:26`
**Impact:** `python-dotenv` is a dependency but is never imported or used. Environment variables are loaded from the OS environment directly via `os.getenv()` and from docker-compose env vars.

**Fix:** Remove from requirements.txt unless future use is planned.

---

### Low

#### L1. README documents implementation phases as incomplete despite code existing

**File:** `README.md:117-139`
**Impact:** README shows Phases 2-5 as "In Progress" or "Planned" with unchecked items, but the actual code for all these phases already exists in the source files. This is misleading documentation.

**Fix:** Update the README to reflect actual implementation status - mark completed items as checked.

---

#### L2. Rollback script in service root is a deployment artifact that should not be committed

**File:** `rollback_influxdb_20260205_141958.sh`
**Impact:** This is a one-off migration rollback script with hardcoded Windows paths. It should not be in the service directory permanently.

```bash
SERVICE_DIR="C:\cursor\HomeIQ\services\observability-dashboard"
BACKUP_DIR="C:\cursor\HomeIQ\services\observability-dashboard\.migration_backup_influxdb_20260205_141957"
```

**Fix:** Remove this file or move it to a `scripts/migrations/` directory. Add `rollback_*.sh` to `.gitignore` if these are auto-generated.

---

#### L3. JaegerClient `_get_service_operations` called N times sequentially in `get_services`

**File:** `src/services/jaeger_client.py:206-208`
**Impact:** When fetching services, the operations for each service are fetched sequentially in a loop. With 30+ services, this means 30+ sequential HTTP requests.

```python
# CURRENT (lines 205-209)
for service_name in data.get("data", []):
    operations = await self._get_service_operations(service_name)
    service = Service(name=service_name, operations=operations)
    services.append(service)
```

**Fix:** Use `asyncio.gather` for parallel fetching:

```python
service_names = data.get("data", [])
operations_list = await asyncio.gather(
    *[self._get_service_operations(name) for name in service_names]
)
services = [
    Service(name=name, operations=ops)
    for name, ops in zip(service_names, operations_list)
]
```

---

#### L4. Percentile calculation is slightly off by one

**File:** `src/pages/service_performance.py:208-210`
**Impact:** Percentiles are calculated using simple index-based lookup, which for small datasets can be imprecise.

```python
# CURRENT
metrics["p50"] = durations[int(len(durations) * 0.50)]
metrics["p95"] = durations[int(len(durations) * 0.95)]
metrics["p99"] = durations[int(len(durations) * 0.99)]
```

**Fix:** Use `numpy.percentile` or at minimum clamp the index to `len-1`:

```python
import numpy as np
metrics["p50"] = np.percentile(durations, 50)
metrics["p95"] = np.percentile(durations, 95)
metrics["p99"] = np.percentile(durations, 99)
```

---

#### L5. No non-root user in Dockerfile

**File:** `Dockerfile`
**Impact:** The container runs as root by default, which is a security best practice violation for containers.

```dockerfile
# CURRENT - no USER directive
CMD ["streamlit", "run", "src/main.py", ...]
```

**Fix:** Add a non-root user:

```dockerfile
RUN useradd --create-home appuser
USER appuser
```

---

#### L6. No resource limits in docker-compose healthcheck

**File:** `docker-compose.yml:104-106`
**Impact:** The healthcheck is defined but the compose entry (lines 76-106) does not include `deploy.resources` limits unlike other services in the compose file. With Streamlit + Plotly, memory usage can spike.

**Fix:** Add resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '1.0'
    reservations:
      memory: 256M
```

---

#### L7. `components/` directory is empty - dead package

**File:** `src/components/__init__.py`
**Impact:** The `components` package exists but contains no actual component code, just an empty `__init__.py`. This is dead code creating false expectations.

**Fix:** Remove the empty directory or add planned visualization components.

---

#### L8. `.ruff_cache` directories present in source tree

**Files:** Multiple `.ruff_cache/` directories under `src/`, `src/components/`, `src/pages/`, `src/services/`, `src/utils/`
**Impact:** Linter cache files committed to the repository add clutter. These should be in `.gitignore`.

**Fix:** Add `.ruff_cache/` to `.gitignore` and remove existing cache directories from version control.

---

#### L9. Service performance page queries services sequentially in a loop

**File:** `src/pages/service_performance.py:75-85`
**Impact:** Performance data is loaded by querying each selected service one at a time in a `for` loop. With 10+ services selected, this creates significant wait time.

```python
# CURRENT (lines 75-85)
for service in services_to_query:
    traces = run_async_safe(
        st.session_state.jaeger_client.get_traces(...),
        timeout=60.0,
    )
    all_traces.extend(traces)
```

**Fix:** Query all services in parallel using `asyncio.gather`:

```python
async def _query_all_services(services, start_time, end_time):
    client = st.session_state.jaeger_client
    tasks = [
        client.get_traces(service=s, start_time=start_time, end_time=end_time, limit=100)
        for s in services
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_traces = []
    for result in results:
        if isinstance(result, list):
            all_traces.extend(result)
    return all_traces
```

---

## Enhancement Suggestions

1. **Add SSRF protection to JaegerClient**: The `api_url` is configurable via environment variable. While this is an internal service, consider validating the URL scheme and host to prevent unintended SSRF if environment variables are misconfigured.

2. **Add structured logging**: The service uses basic `logging.getLogger()` but no log format configuration. Add structured JSON logging with correlation IDs for better observability of the observability service itself.

3. **Add connection retry logic**: The `JaegerClient` has no retry mechanism. Add retry with exponential backoff for transient network failures (e.g., via `httpx` transport with `Retry`).

4. **Add Streamlit caching**: Use `@st.cache_data` or `@st.cache_resource` decorators for expensive computations like `_calculate_service_metrics` and `_calculate_service_health` to avoid recomputation on every interaction.

5. **Add input sanitization for trace/correlation IDs**: Text inputs for trace ID, automation ID, home ID, and correlation ID are passed directly to the Jaeger API. While Jaeger's API should handle this safely, validate that these inputs conform to expected formats (hex strings, UUIDs).

---

## Prioritized Action Plan

### Immediate (Critical/High)
| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | C1 - Fix `time.sleep()` blocking server | Low | Eliminates complete UI freeze during auto-refresh |
| 2 | C2 - Fix duplicate anomaly detection entries | Low | Corrects misleading anomaly counts |
| 3 | H2 - Fix empty results when no filter provided | Low | Makes automation debugging usable without filters |
| 4 | H5 - Fix `px.timeline` misuse | Low | Prevents runtime crash on automation flow |
| 5 | H1 - Reconcile admin-api port (8003 vs 8004) | Low | Prevents connectivity issues |

### Short-term (Medium)
| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 6 | M1 - Remove 6-8 unused dependencies | Low | Reduces image size and attack surface |
| 7 | M2 - Extract duplicated `_has_errors()` | Low | Improves maintainability |
| 8 | M4 - Fix total duration calculation | Low | Corrects misleading metrics |
| 9 | M6 - Remove dead `query_params` code | Trivial | Cleaner code |
| 10 | M7 - Remove unused `asyncio` import | Trivial | Cleaner code |
| 11 | H3 - Add httpx client cleanup | Medium | Prevents connection pool exhaustion |
| 12 | H4 - Add basic test suite | High | Establishes test coverage foundation |

### Long-term (Low / Enhancements)
| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 13 | L1 - Update README implementation status | Low | Accurate documentation |
| 14 | L2 - Remove rollback script | Trivial | Cleaner repo |
| 15 | L3 - Parallelize service operations fetch | Medium | Faster service list loading |
| 16 | L5 - Add non-root user to Dockerfile | Low | Better container security |
| 17 | L8 - Gitignore `.ruff_cache` | Trivial | Cleaner repo |
| 18 | L9 - Parallelize performance queries | Medium | Faster data loading |
| 19 | M3 - Replace sys.path hacks with proper packaging | Medium | More robust imports |
