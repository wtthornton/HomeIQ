# TAPPS Code Quality Review: energy-forecasting

**Service Tier**: 3 (AI/ML Core)
**Review Date**: 2026-02-22
**Preset**: standard
**Final Status**: ALL PASS (8/8 files at 100.0)

## Files Reviewed

| File | Initial Score | Final Score | Gate | Lint Issues | Security Issues |
|------|--------------|-------------|------|-------------|-----------------|
| `src/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/api/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/api/routes.py` | 75.0 | 100.0 | PASS | 5 -> 0 | 0 |
| `src/data/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/data/energy_loader.py` | 85.0 | 100.0 | PASS | 3 -> 0 | 1 (advisory) |
| `src/main.py` | 90.0 | 100.0 | PASS | 2 -> 0 | 1 (advisory) |
| `src/models/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/models/energy_forecaster.py` | 20.0 | 100.0 | PASS (was FAIL) | 11 -> 0 | 4 (advisory) |

## Issues Found and Fixed

### energy_forecaster.py (11 lint issues fixed, FAIL -> PASS)

#### F401: Unused import removed
```python
# Before
import numpy as np
# After (removed - numpy was not used in this module)
```

#### B904: Exception chaining added
**Line 70**: `_init_model()` darts import
```python
# Before
except ImportError:
    raise ImportError("Please install darts: pip install darts>=0.30.0")
# After
except ImportError as err:
    raise ImportError("Please install darts: pip install darts>=0.30.0") from err
```

#### I001: Import block sorted
**Line 248**: `evaluate()` method darts imports
```python
# Before
from darts.metrics import mape, rmse, mae
# After
from darts.metrics import mae, mape, rmse
```

#### PTH123: `open()` replaced with `Path.open()` (7 occurrences)
Lines 289, 298, 302, 317, 325, 354, 358 all changed from `open(path, mode)` to `path.open(mode)`.

#### UP015: Unnecessary mode argument removed
**Line 317**: JSON config read
```python
# Before
with open(config_path_json, "r") as f:
# After
with config_path_json.open() as f:
```

#### Security advisories (B403/B301 - pickle usage)
- `pickle` import and `pickle.load()` calls are inherent to Darts ML model serialization
- Models are only loaded from trusted internal storage, not user input
- Added `noqa: S403` comment on import and `noqa: S301` on `pickle.load()` calls
- tapps correctly reports `security_passed: true` (advisory only)

### routes.py (5 lint issues fixed)

#### B905: `zip()` without `strict=` parameter (2 occurrences)
**Line 244**: Forecast point construction
```python
# Before
for ts, val in zip(timestamps, values)
# After
for ts, val in zip(timestamps, values, strict=False)
```

**Line 331**: Hour-value pair construction
```python
# Before
hour_values = [(ts.hour, val) for ts, val in zip(timestamps, values)]
# After
hour_values = [(ts.hour, val) for ts, val in zip(timestamps, values, strict=False)]
```

#### B904: Exception chaining added (3 occurrences)
Lines 261, 305, 359 - all `raise HTTPException(...)` in except clauses now use `from e`.

### energy_loader.py (3 lint issues fixed)

#### I001: Import block sorted
**Line 102**: InfluxDB import block reordered (stdlib `os` before third-party `influxdb_client_3`).

#### B904: Exception chaining added (2 occurrences)
**Line 108**: InfluxDB import fallback
```python
# Before
except ImportError:
    raise ImportError(...)
# After
except ImportError as err:
    raise ImportError(...) from err
```

**Line 353**: Darts import fallback (same pattern).

#### Security advisory (B608 - SQL injection)
- SQL query uses f-string interpolation for `field` and `measurement` identifiers
- Both are validated via `_validate_identifier()` regex before interpolation
- Added `noqa: S608` comment documenting the mitigation
- tapps correctly reports `security_passed: true` (advisory only)

### main.py (2 lint issues fixed)

#### I001: Import block sorted
**Line 21**: Local imports reordered alphabetically.
```python
# Before
from .api.routes import router, load_model
# After
from .api.routes import load_model, router
```

#### ARG001: Unused function argument
**Line 96**: FastAPI lifespan handler `app` parameter renamed to `_app` (required by protocol but unused).

#### Security advisory (B104 - binding to all interfaces)
- `uvicorn.run(host="0.0.0.0")` is standard practice for Docker containers
- Only used in `if __name__ == "__main__":` block for local dev
- tapps correctly reports `security_passed: true` (advisory only)

## Complexity Notes

- `energy_loader.py` max cyclomatic complexity ~12 (moderate level, acceptable for data loading logic)
- tapps suggestion: "Consider splitting complex functions" -- the `load_from_influxdb` method handles multiple fallback paths which is appropriate for its purpose

## Architecture Observations

- Clean separation of concerns: `main.py` (app setup), `routes.py` (API endpoints), `energy_loader.py` (data ingestion), `energy_forecaster.py` (ML model)
- Thread-safe model registry with lock-based access for concurrent requests
- Forecast caching with configurable TTL to reduce redundant predictions
- CPU-intensive predictions properly offloaded to thread pool via `run_in_executor`
- Supports multiple Darts model backends (N-HiTS, TFT, Prophet, ARIMA, Naive)
- SQL injection mitigated via regex-validated identifiers for InfluxDB queries
- Good fallback handling: synthetic data generation when InfluxDB is unavailable
- Model config stored as JSON (not pickle) for security; pickle only used for complex Darts model objects from trusted sources
