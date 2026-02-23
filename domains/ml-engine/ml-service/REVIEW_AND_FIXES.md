# ML Service - Deep Code Review & Fixes

**Reviewed:** 2026-02-06
**Reviewer:** Claude Opus 4.6 (automated deep review)
**Service:** ml-service (Tier 3 AI/ML Core, Port 8020 internal / 8025 external)
**Files Reviewed:** 6 source files, 3 test files, Dockerfile, requirements.txt, pytest.ini

---

## 1. Service Overview

The ML Service provides classical machine learning algorithms via a stateless FastAPI REST API:

- **Clustering:** KMeans and DBSCAN via scikit-learn
- **Anomaly Detection:** Isolation Forest via scikit-learn
- **Batch Processing:** Multi-operation endpoint for combining clustering and anomaly detection

**Architecture:**
```
Client Request
     |
     v
FastAPI (main.py)          -- validation, routing, timeout enforcement
     |
     +---> _run_cpu_bound() -- offloads to thread executor with timeout
              |
              v
     ClusteringManager      -- KMeans, DBSCAN with per-request StandardScaler
     AnomalyDetectionManager -- Isolation Forest with per-request StandardScaler
```

The service is stateless with no database dependency. Managers are initialized as module-level globals during the FastAPI lifespan event. CPU-bound sklearn operations are offloaded to the default thread pool executor via `asyncio.run_in_executor`.

---

## 2. Code Quality Score: 7.0 / 10

**Justification:**

| Category | Score | Notes |
|----------|-------|-------|
| Structure & Organization | 8/10 | Clean separation of algorithms, good module layout |
| Error Handling | 7/10 | Good HTTP error handling, missing NaN/Inf validation |
| Input Validation | 7/10 | Solid dimension/size limits, gaps in numeric edge cases |
| Security | 7/10 | CORS restricted, errors sanitized, missing rate limiting |
| Performance | 7/10 | Thread offloading and timeouts good, batch is sequential |
| API Design | 7/10 | Clean REST design, batch endpoint uses untyped dicts |
| Test Quality | 5/10 | Mixed integration/unit tests, low actual code coverage |
| Documentation | 8/10 | Thorough README, good docstrings |
| Configuration | 7/10 | Env-var driven with sensible defaults |
| Logging | 6/10 | Basic logging, no structured format, no request tracing |

---

## 3. Critical Issues (Must Fix)

### CRITICAL-1: No NaN/Inf Validation in Input Data

The `_validate_data_matrix` function checks that values are `int` or `float`, but Python's `float('nan')` and `float('inf')` both pass `isinstance(value, float)`. scikit-learn's StandardScaler and algorithms will produce garbage output or raise cryptic errors when fed NaN/Inf values.

**Impact:** Silent data corruption, misleading ML results, or unhandled sklearn exceptions leaking to clients.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`, lines 77-84

**Before:**
```python
for index, row in enumerate(data):
    if not isinstance(row, list):
        raise ValueError("Each data row must be a list of floats.")
    if len(row) != first_row_length:
        raise ValueError("All rows must have the same number of features.")
    for value in row:
        if not isinstance(value, (int, float)):
            raise ValueError("All feature values must be numbers.")
```

**After:**
```python
import math

for index, row in enumerate(data):
    if not isinstance(row, list):
        raise ValueError("Each data row must be a list of floats.")
    if len(row) != first_row_length:
        raise ValueError("All rows must have the same number of features.")
    for value in row:
        if not isinstance(value, (int, float)):
            raise ValueError("All feature values must be numbers.")
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            raise ValueError("Data contains NaN or Inf values which are not supported.")
```

### CRITICAL-2: Port Mismatch Between Dockerfile and `__main__` Block

The Dockerfile CMD runs on port 8020 (correct), but the `if __name__ == "__main__"` block uses port 8020 -- which matches. However, `test_ml_service.py` connects to port 8021, which is neither the internal port (8020) nor the external port (8025).

**File:** `c:\cursor\HomeIQ\services\ml-service\tests\test_ml_service.py`, line 12

**Before:**
```python
ML_SERVICE_URL = "http://localhost:8021"
```

**After:**
```python
ML_SERVICE_URL = "http://localhost:8020"
```

### CRITICAL-3: `pytest-asyncio` Version 1.3.0 Does Not Exist / Is Severely Outdated

The `requirements.txt` pins `pytest-asyncio==1.3.0`. There was never a 1.3.0 release -- the last 0.x release before the 1.0 series was `0.25.x`. The comment says "Phase 2 upgrade - BREAKING" but the version is wrong. Meanwhile, `pytest.ini` sets `asyncio_mode = auto`, which requires `pytest-asyncio>=0.18`. This will cause installation failures or import errors.

**File:** `c:\cursor\HomeIQ\services\ml-service\requirements.txt`, line 29

**Before:**
```
pytest-asyncio==1.3.0  # Phase 2 upgrade - BREAKING: new async patterns
```

**After:**
```
pytest-asyncio>=0.25.0,<0.26.0  # Compatible with asyncio_mode=auto in pytest.ini
```

---

## 4. High Priority Issues (Should Fix)

### HIGH-1: Global Manager Variables Typed as `None`, Not `Optional`

The global manager variables are initialized as `None` without proper type annotations. This means type checkers will flag every usage as a potential `NoneType` error and IDE autocompletion is broken.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`, lines 114-116

**Before:**
```python
# Global managers
clustering_manager: ClusteringManager = None
anomaly_manager: AnomalyDetectionManager = None
```

**After:**
```python
# Global managers
clustering_manager: ClusteringManager | None = None
anomaly_manager: AnomalyDetectionManager | None = None
```

### HIGH-2: Batch Endpoint Processes Operations Sequentially

The `/batch/process` endpoint iterates through operations sequentially with `for operation in request.operations`. Each operation individually offloads to the executor, but they await one at a time. For a batch of 100 operations, this means serialized execution.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`, lines 333-408

**Recommendation:** For true batch efficiency, process independent operations concurrently using `asyncio.gather` with the existing per-operation timeout. Alternatively, document clearly that batch is sequential and the benefit is reduced HTTP overhead rather than parallel execution.

**Sketch (concurrent approach):**
```python
async def _process_single_operation(operation: dict) -> dict:
    """Process a single batch operation."""
    op_type = operation.get("type")
    op_data = operation.get("data", {})
    # ... same per-operation logic as today, returns a result dict ...

results = await asyncio.gather(
    *[_process_single_operation(op) for op in request.operations],
    return_exceptions=True,
)
# Convert exceptions to error results
```

**Caution:** Concurrent execution with the default thread pool could exhaust threads. Would need to configure a bounded `ThreadPoolExecutor` or use `ProcessPoolExecutor` with a pool size cap.

### HIGH-3: Batch Endpoint Uses Untyped `dict[str, Any]` for Operations

The `BatchProcessRequest.operations` field is typed as `list[dict[str, Any]]` which bypasses Pydantic validation entirely. The batch operation data is accessed via `.get()` calls with no validation before being passed to algorithm managers. This defeats the purpose of having Pydantic models.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`, lines 178-188

**Recommendation:** Define typed Pydantic models for batch operations:

```python
from pydantic import BaseModel, Field
from typing import Literal, Union

class BatchClusterOperation(BaseModel):
    type: Literal["cluster"]
    data: ClusteringRequest

class BatchAnomalyOperation(BaseModel):
    type: Literal["anomaly"]
    data: AnomalyRequest

class BatchProcessRequest(BaseModel):
    operations: list[Union[BatchClusterOperation, BatchAnomalyOperation]] = Field(
        ...,
        min_length=1,
        max_length=MAX_BATCH_SIZE,
    )
```

### HIGH-4: Anomaly Detection Calls `fit_predict` Then `decision_function` Separately

In `anomaly_detection.py`, `isolation_forest.fit_predict(X_scaled)` is called first, then `isolation_forest.decision_function(X_scaled)` is called separately. The `decision_function` re-traverses all trees, doubling the computation. Instead, use `fit(X)` then `predict(X)` and `decision_function(X)`, or better yet, use `score_samples` which is more efficient.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\algorithms\anomaly_detection.py`, lines 47-54

**Before:**
```python
isolation_forest = IsolationForest(
    contamination=contamination,
    random_state=42,
    n_estimators=100,
)

labels = isolation_forest.fit_predict(X_scaled)
scores = isolation_forest.decision_function(X_scaled)
```

**After:**
```python
isolation_forest = IsolationForest(
    contamination=contamination,
    random_state=42,
    n_estimators=100,
)

isolation_forest.fit(X_scaled)
labels = isolation_forest.predict(X_scaled)
scores = isolation_forest.decision_function(X_scaled)
```

Note: `fit_predict` calls `fit` + `predict` internally. Then `decision_function` re-scores. Using `fit` once and then both `predict` and `decision_function` avoids redundant fitting. The savings are modest for small data but meaningful at scale.

### HIGH-5: DBSCAN Auto-eps Uses Only k=2 Neighbors, May Be Too Aggressive

The DBSCAN auto-eps calculation uses `NearestNeighbors(n_neighbors=2)`, which means it only looks at the nearest single neighbor (index 1). This is a very aggressive epsilon choice. The standard "elbow method" typically uses `k = min_samples` (which is also hardcoded to 2 for DBSCAN). For higher-dimensional data, k=2 neighbors will produce very small eps values, causing most points to be labeled as noise.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\algorithms\clustering.py`, lines 88-96

**Recommendation:** Use `n_neighbors = min_samples + 1` (so `n_neighbors=3` when `min_samples=2`), and use a percentile-based approach rather than mean:

```python
k = 3  # min_samples + 1
nbrs = NearestNeighbors(n_neighbors=k).fit(X_scaled)
distances, _ = nbrs.kneighbors(X_scaled)
# Use the 90th percentile of k-th neighbor distances (elbow heuristic)
eps = max(1e-3, float(np.percentile(distances[:, k - 1], 90)))
```

---

## 5. Medium Priority Issues (Nice to Fix)

### MED-1: Duplicated `_scale_features` Implementation

Both `ClusteringManager._scale_features` and `AnomalyDetectionManager._scale_features` are identical static methods. This violates DRY.

**Fix:** Extract to a shared utility function in `algorithms/__init__.py`:

```python
# In algorithms/__init__.py
import numpy as np
from sklearn.preprocessing import StandardScaler

def scale_features(data: list[list[float]]) -> np.ndarray:
    """Scale features using per-request StandardScaler."""
    scaler = StandardScaler()
    return scaler.fit_transform(np.array(data, dtype=np.float64))
```

### MED-2: README Documents Algorithms Not Implemented

The README mentions these algorithms as supported:
- **Local Outlier Factor** - not implemented
- **Random Forest** (Feature Importance) - not implemented
- **PCA** (Dimensionality Reduction) - not implemented

The health endpoint also does not mention these. README should only document what is actually implemented, or the algorithms should be marked as "planned."

**File:** `c:\cursor\HomeIQ\services\ml-service\README.md`, lines 225-231

### MED-3: No Request ID or Correlation Tracking

There is no request-level tracing. When diagnosing issues across logs, there is no way to correlate a specific request to its processing logs. FastAPI middleware could inject a request ID.

**Recommendation:** Add a middleware or dependency that generates and logs a request ID:

```python
import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    logger.info("Request started", extra={"request_id": request_id, "path": request.url.path})
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### MED-4: `_validate_data_matrix` Performance on Large Datasets

The validation function iterates through every element of every row in pure Python (`for index, row in enumerate(data): for value in row:`). For the maximum allowed 50,000 rows x 1,000 dimensions, this is 50 million Python-level type checks.

**Recommendation:** After the type-safety check on a sample of rows, convert to numpy array and use numpy's built-in checks:

```python
# Quick type-check on first few rows (or all if small)
sample_size = min(len(data), 100)
for row in data[:sample_size]:
    # ... existing per-element validation ...

# Then do a fast numpy conversion check
try:
    arr = np.array(data, dtype=np.float64)
except (ValueError, TypeError):
    raise ValueError("All feature values must be numbers.")

if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
    raise ValueError("Data contains NaN or Inf values.")

if arr.ndim != 2 or arr.shape[1] != first_row_length:
    raise ValueError("All rows must have the same number of features.")
```

### MED-5: KMeans `n_init` Parameter Not Configurable

KMeans is initialized with `n_init=10` which is the scikit-learn default. For large datasets near the 50,000 point limit, running 10 initializations multiplied by the default `max_iter=300` can be very slow. This should be configurable or adaptively reduced for larger datasets.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\algorithms\clustering.py`, line 61

### MED-6: No Graceful Degradation on Batch Failures

If any operation in a batch fails, the entire batch request returns an error (due to the `raise HTTPException`). There is no partial success reporting.

**Recommendation:** Return per-operation results, marking failed operations with error details:

```python
results.append({
    "type": op_type,
    "status": "error",
    "error": str(e),
})
```

---

## 6. Low Priority Issues (Improvements)

### LOW-1: `del kmeans` / `del isolation_forest` Explicit Deletion Unnecessary

The explicit `del kmeans` and `del isolation_forest` calls are not harmful but are unnecessary in Python -- the objects will be garbage collected when the function returns and the local variable goes out of scope. These lines add minor confusion.

**Files:**
- `c:\cursor\HomeIQ\services\ml-service\src\algorithms\clustering.py`, lines 63, 100
- `c:\cursor\HomeIQ\services\ml-service\src\algorithms\anomaly_detection.py`, line 55

### LOW-2: KMeans Auto-cluster Heuristic Is Simplistic

The auto-cluster formula `max(2, len(data) // 10)` followed by `n_clusters = auto_clusters or 2` is redundant. `max(2, ...)` already ensures the value is at least 2, so `or 2` is dead code. The heuristic itself (data_points / 10) is very rough and may produce poor results.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\algorithms\clustering.py`, lines 55-57

**Before:**
```python
if n_clusters is None:
    auto_clusters = max(2, len(data) // 10)
    n_clusters = auto_clusters or 2
```

**After:**
```python
if n_clusters is None:
    n_clusters = max(2, min(int(len(data) ** 0.5), 20))  # sqrt heuristic, capped at 20
```

### LOW-3: f-string in Logger Call

The lifespan function uses an f-string in the logger call, which means the string is always formatted even if the log level is above ERROR.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`, line 130

**Before:**
```python
logger.error(f"Failed to start ML Service: {e}")
```

**After:**
```python
logger.error("Failed to start ML Service: %s", e)
```

### LOW-4: `allow_headers=["*"]` in CORS Configuration

While CORS origins are restricted, `allow_headers=["*"]` permits any custom header. This is generally fine for an internal service but is broader than necessary.

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`, line 152

### LOW-5: README Dependency Versions Do Not Match `requirements.txt`

The README "Dependencies" section lists specific versions (e.g., `fastapi==0.121.2`, `numpy==2.3.4`) that don't match what's in `requirements.txt` (e.g., `fastapi>=0.123.0,<0.124.0`, `numpy>=1.26.0,<1.27.0`). This creates confusion about actual dependency versions.

**File:** `c:\cursor\HomeIQ\services\ml-service\README.md`, lines 339-368

### LOW-6: Missing `__init__.py` in tests directory

The `tests/` directory has no `__init__.py` file. While pytest doesn't require one, its absence can cause import resolution issues in some configurations.

---

## 7. Security Review

### 7.1 Input Validation (Good, with Gaps)

| Check | Status | Notes |
|-------|--------|-------|
| Data size limits | PASS | MAX_DATA_POINTS (50k), MAX_DIMENSIONS (1k) |
| Payload byte estimate | PASS | MAX_PAYLOAD_BYTES (10MB) enforced |
| Batch size limits | PASS | MAX_BATCH_SIZE (100) via Pydantic + explicit check |
| Row consistency | PASS | All rows checked for same length |
| Type checking | PARTIAL | int/float checked, NaN/Inf NOT checked |
| Algorithm whitelist | PASS | Only kmeans/dbscan/isolation_forest accepted |
| Numeric range limits | MISSING | No check for extreme float values (1e308) |

### 7.2 CORS (Good)

Origins are restricted to localhost:3000 and 3001 by default, configurable via `ML_ALLOWED_ORIGINS`. Credentials are allowed (`allow_credentials=True`), which is appropriate for the dashboard.

### 7.3 Error Information Leakage (Good)

Generic error messages are returned for 500 errors. Stack traces are logged server-side only.

### 7.4 Rate Limiting (Missing)

There is no rate limiting. A client can send unlimited requests. For an internal service behind a reverse proxy this is acceptable, but any direct exposure would be a denial-of-service vector.

### 7.5 Resource Exhaustion

- **Thread pool:** Uses the default `asyncio` thread pool (typically 5 * CPU count workers). Concurrent requests with large datasets could exhaust all threads.
- **Memory:** Each request allocates a numpy array (float64). Max payload = 50,000 x 1,000 x 8 bytes = 400MB per request. Multiple concurrent requests could exhaust memory.
- **CPU:** Algorithm timeout (8s default) provides a safety net, but does not cancel the underlying thread -- the thread continues running until completion even after timeout.

### 7.6 Data Poisoning

Since the service is stateless (no model persistence), data poisoning in the traditional ML sense is limited. However, adversarial data could:
- Trigger excessive memory allocation via maximum-size payloads
- Cause degenerate algorithm behavior (e.g., all identical points for KMeans)
- Produce NaN/Inf propagation through scaling and algorithms

---

## 8. Performance Review

### 8.1 Algorithm Efficiency

| Algorithm | Complexity | Bottleneck | Assessment |
|-----------|-----------|------------|------------|
| KMeans | O(n * k * i * d) | 10 restarts (n_init=10) | Acceptable for <50k points |
| DBSCAN | O(n^2) worst case | Distance matrix | May struggle >10k points |
| Isolation Forest | O(n * t * log(n)) | 100 trees | Good for stated scale |
| DBSCAN auto-eps | O(n * k) | NearestNeighbors | Acceptable |

### 8.2 Memory Usage

- **StandardScaler:** Creates a copy of the data as float64. For 50k x 1000 = ~400MB.
- **Input data:** Already in memory as Python list of lists (more memory than numpy).
- **Peak memory per request:** ~3x the input data size (Python lists + numpy copy + algorithm internal).
- **Recommendation:** For the NUC deployment target, consider lowering MAX_DATA_POINTS to 10,000 to prevent OOM.

### 8.3 Thread Offloading (Good)

CPU-bound operations are correctly offloaded via `asyncio.run_in_executor(None, partial)`. The timeout mechanism prevents indefinite blocking.

**Caveat:** `asyncio.wait_for` on executor tasks does NOT cancel the underlying thread. If a timeout fires, the thread continues consuming CPU until completion. The executor just stops waiting.

### 8.4 Batch Processing

Batch operations run sequentially (one await per operation). This means a batch of 100 operations takes the sum of all individual processing times. For true batch efficiency, operations should be parallelized or combined at the numpy level.

---

## 9. Test Coverage Assessment

### 9.1 Coverage Numbers (from coverage_html/status.json)

| File | Statements | Missing | Coverage |
|------|-----------|---------|----------|
| `src/algorithms/__init__.py` | 3 | 0 | **100%** |
| `src/algorithms/anomaly_detection.py` | 23 | 13 | **43%** |
| `src/algorithms/clustering.py` | 42 | 31 | **26%** |
| `src/main.py` | 211 | 88 | **58%** |
| **Total** | **279** | **132** | **53%** |

Coverage is below the configured `fail_under = 70` threshold in pytest.ini.

### 9.2 Test File Analysis

**`test_ml_service.py` (Integration Tests)**
- Connects to `localhost:8021` (wrong port -- see CRITICAL-2)
- All tests require a running service instance
- Cannot run in CI without deploying the service
- Tests are well-structured but are integration tests, not unit tests

**`test_main_unit.py` (Unit Tests)**
- Good coverage of helper/validation functions
- Mock-based endpoint tests have overly permissive assertions (`assert response.status_code in [200, 503]`)
- The mock test for KMeans patches `clustering_manager` but still may get 503 due to how the global variable is checked
- Missing tests for:
  - DBSCAN endpoint
  - Batch processing endpoint
  - Error paths (timeout, algorithm failure)
  - Edge cases (single data point, all identical points, very high dimensions)

### 9.3 Missing Test Scenarios

| Scenario | Priority | Current Coverage |
|----------|----------|-----------------|
| NaN/Inf input data | Critical | None |
| Algorithm timeout handling | High | None |
| DBSCAN auto-eps path | High | None |
| KMeans auto-cluster path | High | None |
| Batch with mixed success/failure | High | None |
| Single data point edge case | Medium | None |
| Maximum data size (50k points) | Medium | None |
| Concurrent request handling | Medium | None |
| All identical data points | Medium | None |
| Empty batch operations | Low | None |
| Invalid algorithm name | Low | None |

---

## 10. Specific Code Fixes

### Fix 1: Add NaN/Inf Validation (CRITICAL-1)

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`

Add `import math` at the top of the file (after line 16), then update `_validate_data_matrix`:

```python
# Add to imports at top of file
import math

# Update the inner loop in _validate_data_matrix (lines 77-84)
for index, row in enumerate(data):
    if not isinstance(row, list):
        raise ValueError("Each data row must be a list of floats.")
    if len(row) != first_row_length:
        raise ValueError("All rows must have the same number of features.")
    for value in row:
        if not isinstance(value, (int, float)):
            raise ValueError("All feature values must be numbers.")
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            raise ValueError("Data contains NaN or Inf values which are not supported.")
```

### Fix 2: Fix Global Manager Type Annotations (HIGH-1)

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`

```python
# Lines 114-116: Change to
clustering_manager: ClusteringManager | None = None
anomaly_manager: AnomalyDetectionManager | None = None
```

### Fix 3: Fix Anomaly Detection Double Computation (HIGH-4)

**File:** `c:\cursor\HomeIQ\services\ml-service\src\algorithms\anomaly_detection.py`

```python
# Lines 47-54: Replace fit_predict + decision_function with fit + predict + decision_function
isolation_forest = IsolationForest(
    contamination=contamination,
    random_state=42,
    n_estimators=100,
)

isolation_forest.fit(X_scaled)
labels = isolation_forest.predict(X_scaled)
scores = isolation_forest.decision_function(X_scaled)
```

### Fix 4: Fix Redundant Auto-cluster Logic (LOW-2)

**File:** `c:\cursor\HomeIQ\services\ml-service\src\algorithms\clustering.py`

```python
# Lines 55-57: Replace with
if n_clusters is None:
    n_clusters = max(2, min(int(len(data) ** 0.5), 20))
```

### Fix 5: Fix f-string in Logger (LOW-3)

**File:** `c:\cursor\HomeIQ\services\ml-service\src\main.py`

```python
# Line 130: Replace
logger.error(f"Failed to start ML Service: {e}")
# With
logger.error("Failed to start ML Service: %s", e)
```

---

## 11. Enhancement Recommendations

### Enhancement 1: Add Prometheus Metrics

The README mentions "metrics exposed" (request latency, algorithm usage, etc.) but no metrics instrumentation exists. Add `prometheus-fastapi-instrumentator` or manual `prometheus_client` counters:

```python
from prometheus_client import Counter, Histogram

REQUEST_LATENCY = Histogram(
    "ml_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint", "algorithm"],
)
ALGORITHM_USAGE = Counter(
    "ml_algorithm_invocations_total",
    "Total algorithm invocations",
    ["algorithm"],
)
```

### Enhancement 2: Add Model Caching for Repeated Configurations

For workloads that repeatedly cluster with the same parameters, consider a small LRU cache for fitted models (keyed by data hash + parameters). This would avoid refitting on identical inputs.

### Enhancement 3: Add `/ready` Endpoint

Separate liveness (`/health`) from readiness (`/ready`). The health endpoint should always return 200 if the process is alive. The ready endpoint should check that managers are initialized:

```python
@app.get("/ready")
async def readiness_check():
    if clustering_manager is None or anomaly_manager is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}
```

### Enhancement 4: Structured Logging (JSON)

Replace `logging.basicConfig` with structured JSON logging for better log aggregation:

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        return json.dumps(log_entry)
```

### Enhancement 5: Add Feature Importance Endpoint

The README documents Random Forest feature importance as a capability, but it is not implemented. Either implement it or remove from documentation:

```python
@app.post("/feature-importance")
async def feature_importance(request: FeatureImportanceRequest):
    """Rank feature importance using Random Forest."""
    # Implementation using sklearn.ensemble.RandomForestClassifier/Regressor
    ...
```

---

## 12. Dependency Audit

### requirements.txt Analysis

| Dependency | Pinned Version | Assessment | Risk |
|-----------|---------------|------------|------|
| `fastapi>=0.123.0,<0.124.0` | Range-pinned | Good | Low |
| `uvicorn[standard]>=0.32.0,<0.33.0` | Range-pinned | Good | Low |
| `pydantic==2.12.4` | Exact-pinned | Good | Low |
| `pydantic-settings==2.12.0` | Exact-pinned | Not used in code | **Unused** |
| `httpx>=0.28.1,<0.29.0` | Range-pinned | Not used in service code (only tests) | **Unused in prod** |
| `scikit-learn>=1.5.0,<2.0.0` | Wide range | Could allow breaking changes | Medium |
| `pandas>=2.2.0,<3.0.0` | Wide range | Not imported anywhere in code | **Unused** |
| `numpy>=1.26.0,<1.27.0` | Range-pinned | Good | Low |
| `scipy>=1.16.3,<2.0.0` | Wide range | Transitive dependency only | Low |
| `python-dotenv==1.2.1` | Exact-pinned | Not used in code | **Unused** |
| `tenacity==9.1.2` | Exact-pinned | Not used in code | **Unused** |
| `pytest==9.0.2` | Exact-pinned | Should be dev-only | Medium |
| `pytest-asyncio==1.3.0` | **Invalid version** | **BROKEN** -- see CRITICAL-3 | **Critical** |

### Key Findings

1. **4 unused production dependencies:** `pydantic-settings`, `pandas`, `python-dotenv`, `tenacity`. These increase image size and attack surface.
2. **Test dependencies in production requirements:** `pytest` and `pytest-asyncio` are included in the main `requirements.txt`, bloating the production Docker image. These should be in a separate `requirements-test.txt`.
3. **`pandas` is listed but never imported:** The service uses numpy directly. Pandas adds ~50MB to the Docker image for no benefit.
4. **`scikit-learn>=1.5.0,<2.0.0`** is too wide. A minor version bump in scikit-learn could change algorithm behavior (e.g., default parameters).

### Recommended requirements.txt

**Production (`requirements.txt`):**
```
# Web Framework
fastapi>=0.123.0,<0.124.0
uvicorn[standard]>=0.32.0,<0.33.0

# Data Validation
pydantic==2.12.4

# Machine Learning
scikit-learn>=1.5.0,<1.6.0
numpy>=1.26.0,<1.27.0
scipy>=1.16.3,<1.17.0
```

**Testing (`requirements-test.txt`):**
```
-r requirements.txt
httpx>=0.28.1,<0.29.0
pytest>=9.0.0,<10.0.0
pytest-asyncio>=0.25.0,<0.26.0
pytest-cov>=6.0.0,<7.0.0
```

---

## 13. Docker Configuration Review

### Dockerfile Analysis

| Aspect | Assessment | Notes |
|--------|-----------|-------|
| Multi-stage build | GOOD | Builder stage for compilation, slim production image |
| Non-root user | GOOD | `appuser:appgroup` with UID 1001 |
| Health check | GOOD | Curl-based, 30s interval, 30s start period |
| Pip cache mount | GOOD | `--mount=type=cache,target=/root/.cache/pip` |
| Base image | GOOD | `python:3.12-slim` |
| `--no-cache-dir` + cache mount | MINOR | Both `--no-cache-dir` and cache mount used simultaneously -- redundant |

### Issues

1. **Test dependencies installed in production image:** Since `pytest` and `pytest-asyncio` are in `requirements.txt`, they are installed in the production image. This adds unnecessary size.

2. **`PYTHONPATH=/app:/app/src`:** Having both `/app` and `/app/src` can cause confusing import resolution. When running `from src.main import app`, Python will find `src` as a package under `/app`. Having `/app/src` also in the path means `import main` (without the `src` prefix) would also work, creating ambiguous imports.

3. **Missing `.dockerignore` entries:** The `.dockerignore` excludes `tests/` (good) and `*.md` (good, except README). However, it also excludes `Dockerfile*` and `.dockerignore` itself, which is correct Docker practice.

---

## 14. Action Items (Prioritized Checklist)

### Immediate (This Sprint)

- [ ] **CRITICAL-1:** Add NaN/Inf validation to `_validate_data_matrix`
- [ ] **CRITICAL-3:** Fix `pytest-asyncio` version in `requirements.txt`
- [ ] **CRITICAL-2:** Fix test URL port from 8021 to 8020 in `test_ml_service.py`
- [ ] **HIGH-1:** Fix global manager type annotations to use `| None`
- [ ] **HIGH-4:** Fix anomaly detection double computation (`fit_predict` + `decision_function`)

### Short-term (Next 2 Sprints)

- [ ] **HIGH-3:** Define typed Pydantic models for batch operations
- [ ] **HIGH-5:** Improve DBSCAN auto-eps heuristic
- [ ] **MED-1:** Extract shared `_scale_features` to avoid duplication
- [ ] **MED-2:** Remove undocumented/unimplemented algorithms from README
- [ ] Move test dependencies to separate `requirements-test.txt`
- [ ] Remove unused dependencies (`pandas`, `python-dotenv`, `tenacity`, `pydantic-settings`)
- [ ] Write unit tests for ClusteringManager and AnomalyDetectionManager directly
- [ ] Add tests for NaN/Inf rejection, timeout paths, edge cases

### Medium-term (Next Quarter)

- [ ] **HIGH-2:** Implement concurrent batch processing with bounded executor
- [ ] **MED-3:** Add request ID middleware for request tracing
- [ ] **MED-4:** Optimize `_validate_data_matrix` for large datasets using numpy
- [ ] **MED-5:** Make KMeans `n_init` configurable or adaptive
- [ ] **MED-6:** Add per-operation error handling in batch endpoint
- [ ] Add Prometheus metrics instrumentation
- [ ] Add structured JSON logging
- [ ] Add `/ready` endpoint separate from `/health`
- [ ] Implement feature importance endpoint or remove from docs
- [ ] Lower MAX_DATA_POINTS for NUC deployment target

### Low Priority (Backlog)

- [ ] **LOW-1:** Remove unnecessary `del` statements
- [ ] **LOW-2:** Improve KMeans auto-cluster heuristic (sqrt-based)
- [ ] **LOW-3:** Replace f-strings in logger calls with % formatting
- [ ] **LOW-4:** Restrict CORS `allow_headers` to specific needed headers
- [ ] **LOW-5:** Synchronize README dependency versions with requirements.txt
- [ ] **LOW-6:** Add `__init__.py` to tests directory
- [ ] Add model caching for repeated configurations
- [ ] Configure bounded ThreadPoolExecutor instead of default
- [ ] Add integration test CI pipeline with service startup

---

*Generated by automated deep code review. All line numbers reference the current state of the codebase as of 2026-02-06.*
