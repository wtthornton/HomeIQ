# TAPPS Code Quality Review: ml-service

**Service Tier**: 3 (AI/ML Core)
**Review Date**: 2026-02-22
**Preset**: standard
**Final Status**: ALL PASS (5/5 files, 3 at 100.0, gate threshold 70.0)

## Files Reviewed

| File | Initial Score | Final Score | Gate | Lint Issues | Security Issues |
|------|--------------|-------------|------|-------------|-----------------|
| `src/main.py` | 65.0 | 100.0 | PASS | 7 -> 0 | 1 (advisory) |
| `src/algorithms/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/algorithms/anomaly_detection.py` | 70.0 | 100.0 | PASS | 1 -> 0 | 0 |
| `src/algorithms/clustering.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/algorithms/utils.py` | 100.0 | 100.0 | PASS | 0 | 0 |

## Issues Found and Fixed

### main.py (7 lint issues fixed, score 65.0 -> 100.0)

#### I001: Import block un-sorted or un-formatted (line 11)
- Removed unused `Union` import from `typing` (replaced by `X | Y` syntax)
- Removed extra blank line after import block (ruff/isort formatting)

#### ARG001: Unused function argument `app` (line 212)
```python
# Before
async def lifespan(app: FastAPI):
# After
async def lifespan(_app: FastAPI):
```
The `app` parameter is required by FastAPI's lifespan protocol but unused in the body. Prefixed with `_` to indicate intentional non-use.

#### UP007: Use `X | Y` for type annotations (lines 331, 511)

**Line 331**: `BatchOperation` type alias
```python
# Before
BatchOperation = Annotated[
    Union[BatchClusterOperation, BatchAnomalyOperation],
    Field(discriminator="type"),
]
# After
BatchOperation = Annotated[
    BatchClusterOperation | BatchAnomalyOperation,
    Field(discriminator="type"),
]
```

**Line 511**: `_process_single_operation` parameter
```python
# Before
async def _process_single_operation(
    operation: Union[BatchClusterOperation, BatchAnomalyOperation],
) -> BatchOperationResult:
# After
async def _process_single_operation(
    operation: BatchClusterOperation | BatchAnomalyOperation,
) -> BatchOperationResult:
```

#### B904: Missing exception chaining in `except` clauses (lines 460, 500)

**Line 460**: `cluster_data` endpoint
```python
# Before
except Exception:
    logger.exception("Error clustering data")
    raise HTTPException(status_code=500, detail="Clustering failed due to an internal error.")
# After
except Exception as exc:
    logger.exception("Error clustering data")
    raise HTTPException(status_code=500, detail="Clustering failed due to an internal error.") from exc
```

**Line 500**: `detect_anomalies` endpoint
```python
# Before
except Exception:
    logger.exception("Error detecting anomalies")
    raise HTTPException(status_code=500, detail="Anomaly detection failed due to an internal error.")
# After
except Exception as exc:
    logger.exception("Error detecting anomalies")
    raise HTTPException(status_code=500, detail="Anomaly detection failed due to an internal error.") from exc
```

#### SIM102: Nested `if` statements collapsed (line 528)
```python
# Before
if req.n_clusters is not None:
    if req.n_clusters < 2 or req.n_clusters > MAX_CLUSTERS or req.n_clusters > num_points:
        return BatchOperationResult(...)
# After
if req.n_clusters is not None and (
    req.n_clusters < 2 or req.n_clusters > MAX_CLUSTERS or req.n_clusters > num_points
):
    return BatchOperationResult(...)
```

### anomaly_detection.py (1 lint issue fixed, score 70.0 -> 100.0)

#### F401: Unused import `numpy` (line 8)
```python
# Before
import numpy as np
from sklearn.ensemble import IsolationForest
# After
from sklearn.ensemble import IsolationForest
```
The `numpy` import was unused since all array operations go through `sklearn` and the `scale_features` utility.

### main.py (1 advisory, no fix needed)

**B104**: `Possible binding to all interfaces` at line 655
- `uvicorn.run(app, host="0.0.0.0", port=8020)` in `if __name__ == "__main__":` block
- Standard practice for Docker containers; only used in local dev
- tapps correctly reports `security_passed: true` (advisory only)

## Complexity Notes

- `main.py` max cyclomatic complexity CC~20 (high level)
- tapps suggestion: "Consider splitting complex functions" -- the `_process_single_operation` and `cluster_data` functions handle multiple algorithm branches which drives complexity, but the structure is clear and well-organized
- Collapsing nested `if` in the batch processing path slightly reduces nesting depth

## Architecture Observations

- Clean separation: `main.py` (FastAPI app, endpoints, models) / `algorithms/` (ML logic)
- Strong input validation: data matrix shape/type/size checks, NaN/Inf detection, resource guardrails
- CPU-bound ML operations properly offloaded to thread executor with timeout
- Rate limiting middleware with sliding window per client IP
- Batch processing with per-operation error isolation (one failure does not abort the batch)
- Structured JSON logging with request ID tracing
- CORS restricted to explicit allowed origins
