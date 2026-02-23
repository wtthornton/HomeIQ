# Energy Forecasting Service - Code Review & Fixes

**Service**: energy-forecasting (Tier 3 AI/ML Core)
**Port**: 8037
**Reviewed**: 2026-02-06
**Reviewer**: Deep Code Review

---

## Service Overview

The energy-forecasting service is a FastAPI-based microservice that provides ML-powered energy consumption forecasting for HomeIQ. It uses the Darts time series library to support multiple forecasting models (N-HiTS, TFT, Prophet, ARIMA, Naive) and exposes REST endpoints for:

- **7-day energy forecasting** (`/api/v1/forecast`)
- **Peak usage prediction** (`/api/v1/peak-prediction`)
- **Optimization recommendations** (`/api/v1/optimization`)
- **Model info** (`/api/v1/model/info`)

### Architecture

```
InfluxDB --> EnergyDataLoader --> Polars DataFrame --> Darts TimeSeries
                                                            |
                                                     EnergyForecaster
                                                            |
                                                     FastAPI Routes --> JSON Response
```

### Files Reviewed

| File | Lines | Purpose |
|------|-------|---------|
| `src/main.py` | 126 | FastAPI app, lifespan, CORS, logging |
| `src/api/routes.py` | 261 | API endpoints, Pydantic models, global model state |
| `src/models/energy_forecaster.py` | 394 | Darts-based forecasting models |
| `src/data/energy_loader.py` | 377 | Data loading from CSV, InfluxDB, synthetic |
| `src/api/__init__.py` | 5 | Package init |
| `src/models/__init__.py` | 5 | Package init |
| `src/data/__init__.py` | 5 | Package init |
| `src/__init__.py` | 3 | Package init |
| `Dockerfile` | 46 | Multi-stage Docker build |
| `requirements.txt` | 32 | Python dependencies |

---

## Code Quality Score: 5.5 / 10

**Justification**: The service has a clean modular structure and good separation of concerns (data loading, models, API). However, it is undermined by critical dependency mismatches (wrong InfluxDB client installed vs. imported), serious security vulnerabilities (unrestricted pickle deserialization), zero test coverage, thread-safety issues with global mutable state, and several functional bugs that would prevent the service from working correctly in production.

---

## Critical Issues (Must Fix)

### C1. InfluxDB Client Dependency Mismatch - Service Will Crash on InfluxDB Queries

**Severity**: CRITICAL - Runtime ImportError guaranteed
**File**: `src/data/energy_loader.py` (line 90) and `requirements.txt` (line 27)

The code imports `influxdb_client_3.InfluxDBClient3` (the new InfluxDB 3 Python client), but `requirements.txt` installs the old `influxdb-client>=1.40.0` (InfluxDB 2.x client). These are completely different packages with incompatible APIs. The rest of the HomeIQ codebase has migrated to `influxdb3-python`.

**Before** (`requirements.txt` line 27):
```
influxdb-client>=1.40.0
```

**After**:
```
influxdb3-python[pandas]>=0.3.0,<1.0.0
```

This mismatch means `load_from_influxdb()` will always fail with `ImportError`, causing the service to silently fall back to synthetic data in production -- a data integrity disaster that would go unnoticed.

---

### C2. Pickle Deserialization Security Vulnerability (Arbitrary Code Execution)

**Severity**: CRITICAL - Remote code execution risk
**File**: `src/models/energy_forecaster.py` (lines 303-325)

The `load()` classmethod uses `pickle.load()` on three separate files (`.config.pkl`, `.pkl`, `.scaler.pkl`) with no validation whatsoever. Pickle deserialization of untrusted data allows arbitrary code execution.

**Before** (`energy_forecaster.py` lines 297-331):
```python
@classmethod
def load(cls, path: Path | str) -> "EnergyForecaster":
    """Load model from disk."""
    path = Path(path)

    # Load config
    with open(path.with_suffix(".config.pkl"), "rb") as f:
        config = pickle.load(f)

    # ...
    # Load model (non-neural)
    with open(path.with_suffix(".pkl"), "rb") as f:
        instance.model = pickle.load(f)

    # Load scaler
    with open(path.with_suffix(".scaler.pkl"), "rb") as f:
        instance.scaler = pickle.load(f)
```

**After** -- Use JSON for config and add integrity checking:
```python
import hashlib
import json

@classmethod
def load(cls, path: Path | str) -> "EnergyForecaster":
    """Load model from disk."""
    path = Path(path)

    # Load config from JSON instead of pickle
    config_path = path.with_suffix(".config.json")
    if not config_path.exists():
        # Fallback to pickle for backward compatibility, but log warning
        config_path_pkl = path.with_suffix(".config.pkl")
        if not config_path_pkl.exists():
            raise FileNotFoundError(f"No model config found at {path}")
        logger.warning(
            "Loading config from pickle (deprecated). "
            "Re-save model to migrate to JSON config."
        )
        with open(config_path_pkl, "rb") as f:
            config = pickle.load(f)
    else:
        with open(config_path, "r") as f:
            config = json.load(f)

    # Validate config keys
    required_keys = {"model_type", "input_chunk_length", "output_chunk_length"}
    if not required_keys.issubset(config.keys()):
        raise ValueError(f"Invalid model config. Missing keys: {required_keys - config.keys()}")

    if config["model_type"] not in cls.SUPPORTED_MODELS:
        raise ValueError(f"Unknown model_type in config: {config['model_type']}")

    # Create instance (rest of method unchanged)
    ...
```

Also update `save()` to write config as JSON:
```python
def save(self, path: Path | str) -> None:
    """Save model to disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save config as JSON (not pickle)
    config = {
        "model_type": self.model_type,
        "input_chunk_length": self.input_chunk_length,
        "output_chunk_length": self.output_chunk_length,
        "model_kwargs": self.model_kwargs,
    }
    with open(path.with_suffix(".config.json"), "w") as f:
        json.dump(config, f, indent=2)

    # Model and scaler still use pickle (Darts objects are complex),
    # but should only be loaded from trusted sources
    ...
```

Note: The scaler and model pickle files are harder to replace since Darts/scikit-learn objects require pickle. The mitigation is to ensure model files are only loaded from trusted, read-only paths and never from user-supplied paths.

---

### C3. Zero Test Coverage

**Severity**: CRITICAL
**Files**: No `tests/` directory exists

There are no tests of any kind -- no unit tests, no integration tests, no smoke tests. For an ML service that generates financial/operational predictions, this is a serious gap. At minimum, the following should be tested:

1. **Unit tests for `EnergyForecaster`**: init, fit, predict, save/load round-trip, evaluate
2. **Unit tests for `EnergyDataLoader`**: CSV loading, column standardization, synthetic data generation, resampling, feature engineering
3. **API endpoint tests**: health check, forecast (with/without model), peak prediction, optimization, model info, error cases (no model loaded)
4. **Integration tests**: InfluxDB data loading, model training end-to-end
5. **Forecast accuracy tests**: Verify predictions on known synthetic data are within expected bounds

**Recommended test structure**:
```
tests/
  __init__.py
  conftest.py          # Fixtures: sample data, trained model, test client
  test_forecaster.py   # EnergyForecaster unit tests
  test_loader.py       # EnergyDataLoader unit tests
  test_routes.py       # API endpoint tests
  test_integration.py  # End-to-end tests
```

**Minimum conftest.py fixture**:
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def sample_series():
    """Create a sample Darts TimeSeries for testing."""
    import numpy as np
    import pandas as pd
    from darts import TimeSeries

    np.random.seed(42)
    n = 24 * 14  # 2 weeks
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h")
    values = 200 + 100 * np.sin(2 * np.pi * timestamps.hour / 24) + np.random.normal(0, 10, n)

    return TimeSeries.from_dataframe(
        pd.DataFrame({"timestamp": timestamps, "power": values}),
        time_col="timestamp",
        value_cols="power",
    )

@pytest.fixture
def trained_forecaster(sample_series):
    """Create a trained naive forecaster for testing."""
    from src.models.energy_forecaster import EnergyForecaster

    forecaster = EnergyForecaster(model_type="naive", input_chunk_length=24, output_chunk_length=24)
    train, _ = sample_series.split_after(0.8)
    forecaster.fit(train)
    return forecaster

@pytest.fixture
def test_client(trained_forecaster):
    """Create a test client with a loaded model."""
    from src.main import app
    from src.api.routes import _forecaster
    import src.api.routes as routes_module

    routes_module._forecaster = trained_forecaster
    return TestClient(app)
```

---

### C4. Global Mutable State is Not Thread-Safe

**Severity**: CRITICAL
**File**: `src/api/routes.py` (lines 77-89)

The forecasting model is stored as a global variable `_forecaster` and accessed without any locking. FastAPI runs on asyncio with potential thread pool executors. Concurrent requests could cause race conditions during model loading or if model replacement were ever triggered.

**Before** (`routes.py` lines 77-89):
```python
_forecaster = None
_model_path = Path("./models/energy_forecaster")

def get_forecaster():
    """Get the loaded forecaster."""
    global _forecaster
    if _forecaster is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please ensure the model is trained and available."
        )
    return _forecaster
```

**After** -- Use a proper dependency with thread safety:
```python
import threading
from dataclasses import dataclass, field

@dataclass
class ModelRegistry:
    """Thread-safe model registry."""
    _forecaster: Any = None
    _model_path: Path = field(default_factory=lambda: Path("./models/energy_forecaster"))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get_forecaster(self):
        with self._lock:
            if self._forecaster is None:
                raise HTTPException(
                    status_code=503,
                    detail="Model not loaded. Please ensure the model is trained and available."
                )
            return self._forecaster

    def set_forecaster(self, forecaster):
        with self._lock:
            self._forecaster = forecaster

    @property
    def is_loaded(self) -> bool:
        with self._lock:
            return self._forecaster is not None

model_registry = ModelRegistry()
```

---

## High Priority Issues (Should Fix)

### H1. Forecast Endpoint Leaks Internal Exceptions to Client

**Severity**: HIGH
**File**: `src/api/routes.py` (lines 164-166, 200-202, 242-244)

All three forecast endpoints catch generic `Exception` and return the raw exception message as the HTTP response detail. This leaks internal implementation details (stack traces, model internals, file paths) to API consumers.

**Before** (`routes.py` line 166):
```python
except Exception as e:
    logger.error(f"Forecast error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

**After**:
```python
except Exception as e:
    logger.error("Forecast error", exc_info=True, error=str(e))
    raise HTTPException(
        status_code=500,
        detail="An internal error occurred while generating the forecast. Check service logs for details."
    )
```

Apply the same pattern to `/peak-prediction` (line 202) and `/optimization` (line 244).

---

### H2. Health Endpoint Always Returns "healthy" Even When Service Cannot Forecast

**Severity**: HIGH
**File**: `src/api/routes.py` (lines 119-127)

The health check always returns `status: "healthy"` regardless of whether the model is loaded. Orchestration tools (Docker healthcheck, Kubernetes probes) rely on health endpoints to determine service readiness.

**Before** (`routes.py` lines 119-127):
```python
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="energy-forecasting",
        version="1.0.0",
        model_loaded=_forecaster is not None,
    )
```

**After** -- Distinguish liveness from readiness:
```python
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (liveness)."""
    return HealthResponse(
        status="healthy",
        service="energy-forecasting",
        version="1.0.0",
        model_loaded=_forecaster is not None,
    )

@router.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check - returns 503 if model is not loaded."""
    is_ready = _forecaster is not None
    status_code = 200 if is_ready else 503
    response = HealthResponse(
        status="ready" if is_ready else "not_ready",
        service="energy-forecasting",
        version="1.0.0",
        model_loaded=is_ready,
    )
    if not is_ready:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return response
```

Update Dockerfile healthcheck to use `/api/v1/ready` instead of `/api/v1/health`.

---

### H3. `daily_total_kwh` Calculation Is Wrong

**Severity**: HIGH - Produces incorrect data
**File**: `src/api/routes.py` (line 191)

The calculation `float(values.sum()) / 1000` treats each hourly power value (watts) as if dividing by 1000 gives kWh. But watts-to-kWh for hourly data is: `sum(watts) * 1_hour / 1000`. Since each data point already represents a 1-hour interval, the sum of watts over 24 hours needs to be divided by 1000 to get kWh. Numerically the formula is coincidentally correct only if each step is exactly 1 hour, but this assumption is not validated anywhere and the comment/naming is misleading.

**Before** (`routes.py` line 191):
```python
# Calculate daily total (kWh)
daily_total_kwh = float(values.sum()) / 1000
```

**After** -- Make the conversion explicit and correct:
```python
# Convert watts to kWh: each forecast point = 1 hour interval
# kWh = sum(watts) * interval_hours / 1000
interval_hours = 1  # Forecast points are hourly
daily_total_kwh = float(values.sum()) * interval_hours / 1000
```

---

### H4. Blocking ML Operations in Async Endpoints

**Severity**: HIGH
**File**: `src/api/routes.py` (lines 130-166, 169-202, 205-244)

`forecaster.predict()` is a CPU-intensive, synchronous operation (neural network inference or statistical computation). It is called directly inside `async def` endpoints. This blocks the asyncio event loop and prevents all other requests from being served during prediction.

**Before** (`routes.py` lines 130-166):
```python
@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    hours: int = Query(48, ge=1, le=168, description="Forecast horizon in hours"),
):
    forecaster = get_forecaster()
    try:
        forecast_series = forecaster.predict(n=hours)
        ...
```

**After** -- Offload to thread pool:
```python
import asyncio
from functools import partial

@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    hours: int = Query(48, ge=1, le=168, description="Forecast horizon in hours"),
):
    forecaster = get_forecaster()
    try:
        # Run CPU-intensive prediction in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        forecast_series = await loop.run_in_executor(
            None, partial(forecaster.predict, n=hours)
        )
        ...
```

Apply the same pattern to `/peak-prediction` and `/optimization`.

---

### H5. `_load_forecasting_model` Checks Wrong File Extension

**Severity**: HIGH - Model may not load on startup
**File**: `src/main.py` (lines 51-66)

The startup function checks for `.config.pkl` to determine if a model exists. But if the model was saved with the JSON config fix (C2), or if only the `.pt` file exists for neural models, the check will fail. Furthermore, the `load_model` function in `routes.py` also checks for `.config.pkl` (line 101). These checks should be consistent and resilient.

**Before** (`main.py` lines 51-66):
```python
def _load_forecasting_model() -> None:
    model_path = Path(os.getenv("MODEL_PATH", "./models/energy_forecaster"))
    config_path = model_path.with_suffix(".config.pkl")

    if config_path.exists():
        success = load_model(model_path)
        ...
```

**After**:
```python
def _load_forecasting_model() -> None:
    model_path = Path(os.getenv("MODEL_PATH", "./models/energy_forecaster"))

    # Check for config in either format
    config_pkl = model_path.with_suffix(".config.pkl")
    config_json = model_path.with_suffix(".config.json")

    if config_pkl.exists() or config_json.exists():
        success = load_model(model_path)
        if success:
            logger.info("Model loaded successfully", path=str(model_path))
        else:
            logger.warning("Failed to load model", path=str(model_path))
    else:
        logger.info(
            "No model found. Train a model and save to the configured path.",
            path=str(model_path)
        )
```

---

## Medium Priority Issues (Nice to Fix)

### M1. Inconsistent Logging -- stdlib `logging` vs. `structlog`

**Severity**: MEDIUM
**Files**: `src/main.py` uses `structlog`; all other files use `logging.getLogger(__name__)`

The main module configures `structlog` with JSON rendering, but every other module (`routes.py`, `energy_forecaster.py`, `energy_loader.py`) uses the stdlib `logging` module directly. This means structured log context, JSON formatting, and correlation IDs are not applied to the majority of log output.

**Fix**: Replace `logging.getLogger(__name__)` with `structlog.get_logger(__name__)` in all modules:

```python
# Before (in routes.py, energy_forecaster.py, energy_loader.py):
import logging
logger = logging.getLogger(__name__)

# After:
import structlog
logger = structlog.get_logger(__name__)
```

---

### M2. CORS Wildcard in Production

**Severity**: MEDIUM - Security
**File**: `src/main.py` (lines 95-101)

The default `CORS_ORIGINS` is `"*"`, which permits any origin. Combined with `allow_credentials=True`, this is a security antipattern. Browsers will reject `credentials: true` with `origin: *` in modern specs, but older browsers may not.

**Before** (`main.py` lines 95-101):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**After**:
```python
cors_origins = os.getenv("CORS_ORIGINS", "")
if cors_origins:
    origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
else:
    origins = ["http://localhost:3000", "http://localhost:8037"]
    logger.warning("CORS_ORIGINS not set, using restrictive defaults")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],  # This service only serves GET requests
    allow_headers=["*"],
)
```

---

### M3. Synthetic Data Fallback Silently Masks Production Failures

**Severity**: MEDIUM
**File**: `src/data/energy_loader.py` (lines 89-142)

When InfluxDB is unreachable, the token is missing, or the query returns no data, the loader silently returns synthetic data with `_create_synthetic_data()`. In production, this means the forecasting service would serve predictions based on fake data without any indication to the consumer.

**Before** (`energy_loader.py` lines 93-94, 101-102, 129-131, 141-142):
```python
logger.warning("influxdb_client_3 not installed")
return self._create_synthetic_data()
# ...
logger.warning("INFLUXDB_TOKEN not set, using synthetic data")
return self._create_synthetic_data()
# ...
logger.warning("No data returned from InfluxDB")
return self._create_synthetic_data()
# ...
logger.error(f"Error querying InfluxDB: {e}")
return self._create_synthetic_data()
```

**After** -- Raise exceptions in production, only use synthetic data when explicitly requested:
```python
def load_from_influxdb(
    self,
    bucket: str = "home_assistant_events",
    measurement: str = "sensor",
    field: str = "power",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    allow_synthetic_fallback: bool = False,
) -> pl.DataFrame:
    try:
        from influxdb_client_3 import InfluxDBClient3
        import os
    except ImportError:
        if allow_synthetic_fallback:
            logger.warning("influxdb_client_3 not installed, using synthetic data")
            return self._create_synthetic_data()
        raise ImportError(
            "influxdb3-python is required for InfluxDB queries. "
            "Install with: pip install influxdb3-python"
        )

    # ... similar pattern for other fallback points
```

---

### M4. Fixed Random Seed in Synthetic Data Produces Identical Data Every Time

**Severity**: MEDIUM
**File**: `src/data/energy_loader.py` (line 186)

`np.random.seed(42)` is hardcoded. If synthetic data is used for testing, this is fine. But if it is used as a fallback in production (see M3), every restart produces the exact same "predictions," which would be misleading.

**Before** (`energy_loader.py` line 186):
```python
np.random.seed(42)
```

**After**:
```python
# Use fixed seed only when explicitly requested (for reproducible tests)
# In production fallback, use random seed
if seed is not None:
    np.random.seed(seed)
```

(Add `seed: int | None = 42` parameter to `_create_synthetic_data`.)

---

### M5. Optimization Recommendation Text Can Be Misleading

**Severity**: MEDIUM
**File**: `src/api/routes.py` (lines 234-235)

The recommendation message uses `best_hours[0]` and `best_hours[-1]` as a range, but these hours are the 4 lowest-consumption hours sorted by value, not necessarily contiguous. For example, if the best hours are [2, 4, 14, 23], the message would say "Shift activities to 2:00-23:00" which is nearly the entire day.

**Before** (`routes.py` line 235):
```python
recommendation=f"Shift high-power activities to {best_hours[0]}:00-{best_hours[-1]}:00 to reduce peak load",
```

**After**:
```python
best_hours_str = ", ".join(f"{h}:00" for h in sorted(best_hours))
avoid_hours_str = ", ".join(f"{h}:00" for h in sorted(avoid_hours))
recommendation=(
    f"Best times for high-power activities: {best_hours_str}. "
    f"Avoid: {avoid_hours_str}."
),
```

---

### M6. No Request Timeout or Rate Limiting on Forecast Endpoints

**Severity**: MEDIUM
**File**: `src/api/routes.py`

A single request for 168-hour forecast with a complex model could take minutes. There is no timeout or rate limiting to prevent resource exhaustion from concurrent forecast requests.

**Fix**: Add request timeout and simple rate limiting:
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: float = 30.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out"}
            )
```

---

### M7. `evaluate()` Does Not Handle Forecast Length Mismatch

**Severity**: MEDIUM
**File**: `src/models/energy_forecaster.py` (lines 236-267)

The `evaluate` method calls `self.predict(n=len(test_series))`, but many models (e.g., N-HiTS, TFT) can only predict up to `output_chunk_length` steps at once. If `len(test_series)` exceeds `output_chunk_length`, Darts will auto-regress, which may not be the intended behavior and can cause significant accuracy degradation without warning.

**Before** (`energy_forecaster.py` lines 252-254):
```python
n = len(test_series)
forecast = self.predict(n=n)
```

**After**:
```python
n = len(test_series)
if n > self.output_chunk_length:
    logger.warning(
        f"Test series length ({n}) exceeds output_chunk_length "
        f"({self.output_chunk_length}). Model will auto-regress, "
        f"which may reduce accuracy."
    )
forecast = self.predict(n=n)
```

---

## Low Priority Issues (Improvements)

### L1. Dockerfile Uses `COPY models/ ... 2>/dev/null || true` Which Is a Docker Build Anti-pattern

**Severity**: LOW
**File**: `Dockerfile` (line 27)

`COPY ... 2>/dev/null || true` does not work in Docker. Docker COPY is not a shell command -- it will fail the build if the source does not exist. This line only works because Docker treats the `|| true` as a shell directive when using `RUN`, not `COPY`.

**Before** (`Dockerfile` line 27):
```dockerfile
COPY models/ ./models/ 2>/dev/null || true
```

**After** -- Use a `.dockerignore` guard or conditional copy:
```dockerfile
# Create models directory (models are mounted at runtime via volume)
RUN mkdir -p /app/models
# Remove the COPY models/ line entirely; models should be mounted via Docker volume
```

---

### L2. Hardcoded Version Strings in Multiple Places

**Severity**: LOW
**Files**: `src/main.py` (line 88), `src/api/routes.py` (lines 125, 248), `src/__init__.py`

The version "1.0.0" is hardcoded in four places. Any version bump requires updating all of them.

**Fix**: Import from `src/__init__.py`:
```python
# In routes.py and main.py:
from .. import __version__
# Then use __version__ wherever version is referenced
```

---

### L3. f-string Logging Without structlog Context

**Severity**: LOW
**Files**: `src/api/routes.py`, `src/models/energy_forecaster.py`, `src/data/energy_loader.py`

All log statements use f-strings: `logger.info(f"Loaded model from {path}")`. With structlog, context should be passed as keyword arguments for structured parsing.

**Before**:
```python
logger.info(f"Loaded model from {path}")
logger.error(f"Failed to load model: {e}")
```

**After**:
```python
logger.info("Loaded model", path=str(path))
logger.error("Failed to load model", error=str(e), exc_info=True)
```

---

### L4. Missing `__all__` in `src/__init__.py`

**Severity**: LOW
**File**: `src/__init__.py`

The root `__init__.py` only defines `__version__`. It does not export key classes, making imports less discoverable.

---

### L5. `main()` Functions in `energy_forecaster.py` and `energy_loader.py` Are Demo Code

**Severity**: LOW
**Files**: `src/models/energy_forecaster.py` (lines 343-393), `src/data/energy_loader.py` (lines 351-376)

These `main()` functions are essentially example/demo scripts bundled in production code. They should be moved to an `examples/` directory or removed.

---

## Security Review

| Issue | Severity | Status |
|-------|----------|--------|
| Pickle deserialization (arbitrary code execution) | CRITICAL | C2 above |
| CORS wildcard with credentials | MEDIUM | M2 above |
| Internal exception details leaked to clients | HIGH | H1 above |
| No authentication on any endpoint | MEDIUM | See below |
| No rate limiting | MEDIUM | M6 above |
| InfluxDB token in environment variable (acceptable) | LOW | OK |
| No input sanitization on SQL-interpolated InfluxDB query | HIGH | See S1 below |

### S1. SQL Injection in InfluxDB Query

**Severity**: HIGH
**File**: `src/data/energy_loader.py` (lines 111-117)

The `field` and `measurement` parameters are directly interpolated into a SQL string without any sanitization.

**Before** (`energy_loader.py` lines 111-117):
```python
query = f'''
SELECT time, {field}
FROM {measurement}
WHERE time >= '{start_time.isoformat()}'
  AND time <= '{end_time.isoformat()}'
ORDER BY time
'''
```

**After** -- Validate inputs:
```python
import re

VALID_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _validate_identifier(name: str, label: str) -> str:
    """Validate SQL identifier to prevent injection."""
    if not VALID_IDENTIFIER.match(name):
        raise ValueError(f"Invalid {label}: {name!r}")
    return name

# In load_from_influxdb:
field = self._validate_identifier(field, "field")
measurement = self._validate_identifier(measurement, "measurement")

query = f'''
SELECT time, {field}
FROM {measurement}
WHERE time >= '{start_time.isoformat()}'
  AND time <= '{end_time.isoformat()}'
ORDER BY time
'''
```

### S2. No Authentication on Endpoints

The service exposes forecast data without any authentication. While this may be acceptable for internal-only services behind a reverse proxy, if the service is exposed externally, API key or JWT authentication should be added.

---

## Performance Review

### P1. Forecast Computation Blocks the Event Loop

**Impact**: HIGH
**Details**: See H4. Neural model inference (N-HiTS, TFT) and even statistical models (AutoARIMA) are CPU-bound. Running them in async handlers blocks the entire server.

### P2. No Forecast Caching

**Impact**: MEDIUM
**File**: `src/api/routes.py`

Every request triggers a full model prediction, even if the same forecast was requested seconds ago. Energy forecasts change slowly (hourly at most), so caching is very effective.

**Fix**: Add simple TTL cache:
```python
from functools import lru_cache
from datetime import datetime

_forecast_cache = {}
_cache_ttl_seconds = 300  # 5 minutes

def _get_cached_forecast(hours: int):
    key = f"forecast_{hours}"
    if key in _forecast_cache:
        cached_at, result = _forecast_cache[key]
        if (datetime.now() - cached_at).total_seconds() < _cache_ttl_seconds:
            return result
    return None

def _set_cached_forecast(hours: int, result):
    _forecast_cache[f"forecast_{hours}"] = (datetime.now(), result)
```

### P3. EnergyDataLoader Converts Polars to Pandas Unnecessarily

**Impact**: LOW
**File**: `src/data/energy_loader.py` (line 314)

The `to_darts_timeseries` method converts a Polars DataFrame to Pandas. This is currently necessary because Darts requires Pandas, but it means data is loaded in Polars, then converted to Pandas, doubling memory usage for large datasets.

### P4. Docker Image Size

**Impact**: LOW
**File**: `Dockerfile`

The image pulls PyTorch (`torch>=2.5.0`) which is ~2GB. For CPU-only inference, `torch` should be replaced with `torch-cpu` or installed with `--index-url https://download.pytorch.org/whl/cpu`:
```dockerfile
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --user -r requirements.txt
```

---

## Test Coverage Assessment

| Component | Test Coverage | Assessment |
|-----------|--------------|------------|
| `src/api/routes.py` | 0% | No tests |
| `src/models/energy_forecaster.py` | 0% | No tests |
| `src/data/energy_loader.py` | 0% | No tests |
| `src/main.py` | 0% | No tests |
| **Overall** | **0%** | **CRITICAL: No test directory or test files exist** |

### Minimum Test Coverage Targets

| Component | Target | Rationale |
|-----------|--------|-----------|
| API routes | 90% | Core product functionality, all paths |
| EnergyForecaster | 85% | ML model lifecycle, save/load integrity |
| EnergyDataLoader | 80% | Data pipeline correctness |
| main.py | 70% | Startup, config |

---

## Specific Code Fixes (Additional)

### Fix 1: `to_darts_timeseries` Does Not Handle Missing `timestamp` Column

**File**: `src/data/energy_loader.py` (lines 297-325)

**Before**:
```python
def to_darts_timeseries(self, df: pl.DataFrame, value_col: str = "power"):
    try:
        from darts import TimeSeries
    except ImportError:
        raise ImportError("Please install darts: pip install darts>=0.30.0")

    pdf = df.to_pandas()
    ts = TimeSeries.from_dataframe(
        pdf, time_col="timestamp", value_cols=value_col,
        fill_missing_dates=True, freq=self.frequency,
    )
    return ts
```

**After**:
```python
def to_darts_timeseries(self, df: pl.DataFrame, value_col: str = "power"):
    try:
        from darts import TimeSeries
    except ImportError:
        raise ImportError("Please install darts: pip install darts>=0.30.0")

    if "timestamp" not in df.columns:
        raise ValueError(
            f"DataFrame must have a 'timestamp' column. Found: {df.columns}"
        )
    if value_col not in df.columns:
        raise ValueError(
            f"DataFrame must have a '{value_col}' column. Found: {df.columns}"
        )

    pdf = df.select(["timestamp", value_col]).to_pandas()
    ts = TimeSeries.from_dataframe(
        pdf, time_col="timestamp", value_cols=value_col,
        fill_missing_dates=True, freq=self.frequency,
    )
    return ts
```

### Fix 2: `_standardize_columns` Silently Swallows Timestamp Parse Errors

**File**: `src/data/energy_loader.py` (lines 163-169)

**Before**:
```python
if "timestamp" in df.columns:
    try:
        df = df.with_columns([
            pl.col("timestamp").str.to_datetime().alias("timestamp")
        ])
    except Exception:
        pass  # Silent failure
```

**After**:
```python
if "timestamp" in df.columns:
    try:
        df = df.with_columns([
            pl.col("timestamp").str.to_datetime().alias("timestamp")
        ])
    except Exception as e:
        logger.warning(
            "Could not parse timestamp column as datetime. "
            "Ensure timestamps are in a standard format.",
            error=str(e),
        )
```

### Fix 3: Docker Healthcheck Uses `httpx` Which May Not Be Installed at Top Level

**File**: `Dockerfile` (line 41)

**Before**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8037/api/v1/health')" || exit 1
```

**After** -- Use `curl` or a simpler approach:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8037/api/v1/health || exit 1
```

Note: `start-period` increased to 60s because ML model loading can be slow.

---

## Enhancement Recommendations

### E1. Add Prometheus Metrics

Expose prediction latency, request count, model accuracy, and cache hit rates:
```python
from prometheus_client import Histogram, Counter, Gauge

FORECAST_LATENCY = Histogram("forecast_latency_seconds", "Time to generate forecast", ["model_type", "hours"])
FORECAST_REQUESTS = Counter("forecast_requests_total", "Total forecast requests", ["endpoint", "status"])
MODEL_LOADED = Gauge("model_loaded", "Whether a model is currently loaded")
```

### E2. Add Model Retraining Endpoint

Currently there is no way to retrain the model via the API. A `POST /api/v1/model/retrain` endpoint would allow automated retraining pipelines.

### E3. Add Confidence Intervals to Forecasts

The `ForecastPoint` model has `lower_bound` and `upper_bound` fields, but they are never populated. Darts supports probabilistic forecasting via `predict(n, num_samples=100)`:
```python
forecast = forecaster.model.predict(n=hours, num_samples=100)
quantile_lo = forecast.quantile_timeseries(0.05)
quantile_hi = forecast.quantile_timeseries(0.95)
```

### E4. Add Model Versioning

Track model version, training date, training data range, and performance metrics alongside the saved model. This enables model comparison and rollback.

### E5. Support Batch Forecasting for Multiple Entities

The current API forecasts a single aggregate energy value. Supporting per-device or per-zone forecasts would add significant value.

### E6. Add OpenAPI Response Examples

Add example responses to the Pydantic models for better API documentation:
```python
class ForecastResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "forecast": [{"timestamp": "2026-02-06T00:00:00", "power_watts": 450.5}],
            "model_type": "nhits",
            "forecast_horizon_hours": 48,
            "generated_at": "2026-02-06T12:00:00",
        }
    })
```

---

## Dependency Audit

| Package | Required Version | Latest (Feb 2026) | Issue |
|---------|-----------------|-------------------|-------|
| `polars` | `>=1.0.0` | ~1.20.x | OK, but very wide range |
| `pandas` | `>=2.2.0` | ~2.3.x | OK |
| `numpy` | `>=1.26.0` | ~2.2.x | OK |
| `darts` | `>=0.30.0` | ~0.32.x | OK |
| `statsforecast` | `>=1.7.0` | ~2.0.x | OK |
| `torch` | `>=2.5.0` | ~2.6.x | **Bloated for CPU-only inference** |
| `pytorch-lightning` | `>=2.2.0` | ~2.5.x | OK |
| `fastapi` | `>=0.115.0` | ~0.115.x | OK |
| `uvicorn` | `>=0.30.0` | ~0.34.x | OK |
| `httpx` | `>=0.27.0` | ~0.28.x | OK |
| `pydantic` | `>=2.5.0` | ~2.12.x | OK |
| **`influxdb-client`** | `>=1.40.0` | N/A | **WRONG PACKAGE -- should be `influxdb3-python`** |
| `python-dotenv` | `>=1.0.0` | ~1.1.x | OK |
| `structlog` | `>=24.1.0` | ~25.x | OK |

### Missing Dependencies

- `pytest` (dev dependency for testing)
- `pytest-asyncio` (dev dependency for async test support)
- `pytest-cov` (dev dependency for coverage)

### Unnecessary Dependencies

- `statsforecast>=1.7.0` is listed but never imported anywhere in the codebase. Remove unless planned for future use.

---

## Action Items (Prioritized Checklist)

### Immediate (Sprint 1)

- [ ] **C1**: Fix InfluxDB dependency -- replace `influxdb-client` with `influxdb3-python[pandas]` in `requirements.txt`
- [ ] **C2**: Replace pickle config with JSON serialization, add validation to model loading
- [ ] **C3**: Create `tests/` directory with unit tests for all modules (target: 80%+ coverage)
- [ ] **C4**: Replace global mutable state with thread-safe ModelRegistry
- [ ] **S1**: Add SQL identifier validation in `energy_loader.py` to prevent injection
- [ ] **H1**: Stop leaking internal exceptions to API consumers

### High Priority (Sprint 2)

- [ ] **H2**: Add readiness endpoint separate from liveness health check
- [ ] **H3**: Fix `daily_total_kwh` calculation with explicit unit conversion
- [ ] **H4**: Offload `predict()` calls to thread pool with `run_in_executor`
- [ ] **H5**: Support both `.config.pkl` and `.config.json` in model loading
- [ ] **M1**: Migrate all modules to structlog

### Medium Priority (Sprint 3)

- [ ] **M2**: Restrict CORS origins and methods in production
- [ ] **M3**: Make synthetic data fallback opt-in, raise exceptions by default
- [ ] **M5**: Fix misleading optimization recommendation text
- [ ] **M6**: Add request timeout middleware
- [ ] **P2**: Implement forecast caching with configurable TTL

### Low Priority (Backlog)

- [ ] **L1**: Fix Dockerfile COPY anti-pattern, use volume mounts for models
- [ ] **L2**: Centralize version string
- [ ] **L3**: Convert f-string logging to structlog keyword arguments
- [ ] **L5**: Move demo `main()` functions to `examples/` directory
- [ ] **P4**: Use CPU-only PyTorch to reduce Docker image by ~1.5GB
- [ ] **E1**: Add Prometheus metrics
- [ ] **E3**: Populate confidence interval bounds in forecast responses
- [ ] **E4**: Add model versioning metadata

### Dependency Fixes

- [ ] Replace `influxdb-client>=1.40.0` with `influxdb3-python[pandas]>=0.3.0,<1.0.0`
- [ ] Remove unused `statsforecast>=1.7.0` or add code that uses it
- [ ] Add `requirements-dev.txt` with pytest, pytest-asyncio, pytest-cov
- [ ] Pin CPU-only PyTorch variant to reduce image size
