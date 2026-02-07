# Rule Recommendation ML Service - Deep Code Review

**Service**: rule-recommendation-ml (Tier 7 - Specialized)
**Port**: 8035 (internal) / 8040 (external)
**Date**: 2026-02-06
**Reviewer**: Claude Opus 4.6

---

## Service Overview

The rule-recommendation-ml service provides ML-powered automation rule recommendations for HomeIQ using collaborative filtering (ALS via the `implicit` library). It loads the Wyze Rule Recommendation dataset from Hugging Face (~1M+ rules from 300K+ users), maps Wyze device types to Home Assistant domains, and produces rule suggestions via a FastAPI REST API.

**Architecture**: FastAPI app -> RuleRecommender (implicit ALS) -> Wyze dataset (Hugging Face/Polars)

**Files Reviewed**:
- `src/main.py` (124 lines) - Application entry point, lifespan, CORS
- `src/api/routes.py` (367 lines) - REST API endpoints, Pydantic models
- `src/models/rule_recommender.py` (417 lines) - ALS collaborative filtering model
- `src/data/wyze_loader.py` (377 lines) - Dataset loading & preprocessing
- `Dockerfile` (49 lines) - Multi-stage Docker build
- `requirements.txt` (33 lines) - Python dependencies
- `pyproject.toml` (70 lines) - Project configuration
- `src/__init__.py`, `src/api/__init__.py`, `src/data/__init__.py`, `src/models/__init__.py` - Package init files

---

## Findings Summary

| Severity | Count | Categories |
|----------|-------|------------|
| Critical | 2 | Security (pickle deserialization), Feedback not persisted |
| High     | 6 | No tests, CORS wildcard, logging inconsistency, health check discrepancy, unused deps, no model validation |
| Medium   | 8 | Pattern parsing fragility, no rate limiting, no auth, missing error handling, memory, port mismatch docs, no training endpoint, streaming hardcoded limit |
| Low      | 5 | f-string logging, version duplication, dead code path, __pycache__ in repo, minor docs gaps |

---

## Critical Findings

### C1. Insecure Model Deserialization via Pickle

**File**: `src/models/rule_recommender.py:335-336`
**Severity**: CRITICAL

The model is loaded using `pickle.load()` which is fundamentally insecure. An attacker who can place a malicious `.pkl` file on the model volume can achieve arbitrary code execution.

```python
# CURRENT - Vulnerable to arbitrary code execution
with open(path, "rb") as f:
    model_data = pickle.load(f)
```

**Risk**: If the Docker volume (`rule_recommendation_models`) is compromised or a malicious model file is placed at the `MODEL_PATH`, `pickle.load()` will execute arbitrary Python code during deserialization.

**Recommended Fix**: Use a safer serialization format, or at minimum, validate the file before loading.

```python
# OPTION 1: Use safetensors or joblib with hash verification
import hashlib
import json

def load(cls, path: Path | str) -> "RuleRecommender":
    path = Path(path)

    # Verify model file integrity via checksum
    checksum_path = path.with_suffix(".sha256")
    if checksum_path.exists():
        expected_hash = checksum_path.read_text().strip()
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"Model file integrity check failed: {path}")

    # Load with restricted unpickler
    import io
    import pickle as _pickle

    ALLOWED_MODULES = {"numpy", "scipy.sparse", "implicit.als", "builtins"}

    class RestrictedUnpickler(_pickle.Unpickler):
        def find_class(self, module, name):
            if module.split(".")[0] not in ALLOWED_MODULES:
                raise _pickle.UnpicklingError(
                    f"Disallowed class: {module}.{name}"
                )
            return super().find_class(module, name)

    with open(path, "rb") as f:
        model_data = RestrictedUnpickler(f).load()
```

```python
# OPTION 2: Replace pickle with numpy/JSON-based serialization
def save(self, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save config as JSON (safe)
    config_path = path.with_suffix(".json")
    config_data = {
        "config": {
            "factors": self.factors,
            "iterations": self.iterations,
            "regularization": self.regularization,
            "random_state": self.random_state,
        },
        "mappings": {
            "idx_to_user": {str(k): v for k, v in self.idx_to_user.items()},
            "idx_to_pattern": {str(k): v for k, v in self.idx_to_pattern.items()},
        },
    }
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    # Save model factors as numpy arrays (safe)
    np.savez(
        path.with_suffix(".npz"),
        user_factors=self.model.user_factors,
        item_factors=self.model.item_factors,
    )

    # Save sparse matrix separately
    if self._user_items is not None:
        from scipy.sparse import save_npz
        save_npz(path.with_name(path.stem + "_matrix.npz"), self._user_items)
```

---

### C2. Feedback Endpoint Does Not Persist Data

**File**: `src/api/routes.py:315-344`
**Severity**: CRITICAL

The feedback endpoint (`POST /api/v1/rule-recommendations/feedback`) accepts user feedback but only logs it -- it does not persist to any database or file. All feedback is lost on service restart. The endpoint returns `success: True` which is misleading.

```python
# CURRENT - Feedback is logged but never stored
feedback_id = str(uuid.uuid4())

logger.info(
    f"Received feedback: {feedback.feedback_type} for pattern '{feedback.rule_pattern}' "
    f"from user {feedback.user_id or 'anonymous'} (feedback_id={feedback_id})"
)

# TODO: Store feedback in database
# TODO: Trigger incremental model update if enough feedback accumulated

return FeedbackResponse(
    success=True,  # Lies - data is not actually stored
    message=f"Feedback recorded successfully",
    feedback_id=feedback_id,
)
```

**Recommended Fix**: At minimum, persist feedback to a JSON file or SQLite database. Ideally, write to InfluxDB following the HomeIQ pattern.

```python
import json
from datetime import datetime, timezone

FEEDBACK_FILE = Path(os.getenv("FEEDBACK_PATH", "./data/feedback.jsonl"))

@router.post("/rule-recommendations/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: RecommendationFeedback):
    feedback_id = str(uuid.uuid4())

    record = {
        "feedback_id": feedback_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule_pattern": feedback.rule_pattern,
        "user_id": feedback.user_id,
        "feedback_type": feedback.feedback_type,
        "automation_id": feedback.automation_id,
        "rating": feedback.rating,
        "comment": feedback.comment,
    }

    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    logger.info("Feedback stored", feedback_id=feedback_id, feedback_type=feedback.feedback_type)

    return FeedbackResponse(
        success=True,
        message="Feedback recorded and persisted",
        feedback_id=feedback_id,
    )
```

---

## High Severity Findings

### H1. No Tests Exist

**Severity**: HIGH

There is no `tests/` directory and zero test files despite `pyproject.toml` configuring `testpaths = ["tests"]` and listing test dependencies (`pytest`, `pytest-asyncio`, `pytest-cov`). For an ML service, testing is essential to catch regressions in recommendation quality.

**Recommended Fix**: Create at minimum:

```
tests/
  __init__.py
  test_routes.py          # API endpoint tests
  test_rule_recommender.py # Model unit tests
  test_wyze_loader.py     # Data loading tests
  conftest.py             # Shared fixtures
```

Example test file `tests/test_rule_recommender.py`:
```python
import numpy as np
import pytest
from scipy.sparse import csr_matrix
from src.models.rule_recommender import RuleRecommender


@pytest.fixture
def trained_recommender():
    n_users, n_patterns = 50, 20
    data = np.random.default_rng(42).random((n_users, n_patterns))
    data[data > 0.9] = 1.0
    data[data <= 0.9] = 0.0
    matrix = csr_matrix(data)

    idx_to_user = {i: f"user_{i}" for i in range(n_users)}
    idx_to_pattern = {i: f"binary_sensor_to_light" if i == 0 else f"pattern_{i}" for i in range(n_patterns)}

    recommender = RuleRecommender(factors=8, iterations=5)
    recommender.fit(matrix, idx_to_user, idx_to_pattern)
    return recommender


def test_recommend_returns_results(trained_recommender):
    results = trained_recommender.recommend(user_id="user_0", n=5)
    assert len(results) <= 5
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


def test_recommend_unknown_user_returns_popular(trained_recommender):
    results = trained_recommender.recommend(user_id="nonexistent_user", n=5)
    assert len(results) > 0  # Falls back to popular


def test_get_popular_rules(trained_recommender):
    results = trained_recommender.get_popular_rules(n=5)
    assert len(results) <= 5
    # Should be sorted by popularity (descending)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_unfitted_model_raises():
    recommender = RuleRecommender()
    with pytest.raises(RuntimeError, match="Model must be fitted"):
        recommender.recommend(user_id="test")
```

---

### H2. CORS Wildcard in Production

**File**: `src/main.py:94-100`
**Severity**: HIGH

CORS is configured with `allow_origins="*"` by default, `allow_credentials=True`, and `allow_methods=["*"]` plus `allow_headers=["*"]`. This is overly permissive for a production service.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),  # Default: allow ALL origins
    allow_credentials=True,   # With credentials!
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Note**: `allow_credentials=True` with `allow_origins=["*"]` is actually rejected by browsers (CORS spec disallows it), but this indicates a configuration misunderstanding.

**Recommended Fix**:
```python
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

### H3. Inconsistent Logging: stdlib vs structlog

**Files**: `src/main.py` uses `structlog`, but `src/api/routes.py:18`, `src/models/rule_recommender.py:13`, and `src/data/wyze_loader.py:14` all use `logging.getLogger(__name__)` (stdlib).

**Severity**: HIGH

The `main.py` configures structlog, but all other modules use the stdlib `logging` module directly. This means:
- Structured JSON logging only works for `main.py`
- All other modules emit unstructured text logs
- Log output format is inconsistent across the service

```python
# main.py - uses structlog
import structlog
logger = structlog.get_logger(__name__)

# routes.py, rule_recommender.py, wyze_loader.py - use stdlib
import logging
logger = logging.getLogger(__name__)
```

**Recommended Fix**: Use structlog consistently across all modules:
```python
# In all modules:
import structlog
logger = structlog.get_logger(__name__)
```

---

### H4. Health Check Discrepancy Between Dockerfile and docker-compose.yml

**File**: `Dockerfile:43-44` vs `docker-compose.yml:1774`
**Severity**: HIGH

The Dockerfile health check uses `httpx` (which may not be installed in the runtime image correctly), while `docker-compose.yml` uses `urllib.request` (stdlib). They also differ in behavior.

```dockerfile
# Dockerfile - uses httpx (third-party, may fail if not installed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8035/api/v1/health')" || exit 1
```

```yaml
# docker-compose.yml - uses urllib.request (stdlib, always available)
test: ["CMD", "python", "-c", "import urllib.request; import sys; response = urllib.request.urlopen('http://localhost:8035/api/v1/health', timeout=5); sys.exit(0 if response.getcode() == 200 else 1)"]
```

The docker-compose version is better (uses stdlib, checks status code). The Dockerfile version doesn't check the response status code and relies on `httpx` which is an async library being used synchronously.

**Recommended Fix** for Dockerfile:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; import sys; r = urllib.request.urlopen('http://localhost:8035/api/v1/health', timeout=5); sys.exit(0 if r.getcode() == 200 else 1)" || exit 1
```

---

### H5. Unnecessary Dependencies Inflate Image Size

**File**: `requirements.txt`
**Severity**: HIGH

Several dependencies are included but never used in the codebase:

| Dependency | Used? | Notes |
|-----------|-------|-------|
| `duckdb>=1.0.0` | **NO** | Never imported anywhere |
| `onnxruntime>=1.19.0` | **NO** | Never imported; no ONNX model export code |
| `scikit-learn>=1.4.0` | **NO** | Never imported anywhere |
| `joblib>=1.3.0` | **NO** | Never imported anywhere |
| `python-dotenv>=1.0.0` | **NO** | Never imported; no `.env` loading code |

These inflate the Docker image size significantly (onnxruntime alone is ~200MB, duckdb ~80MB).

**Recommended Fix**: Remove unused dependencies:
```txt
# Data Processing
polars>=1.0.0
pyarrow>=14.0.0

# Hugging Face
datasets>=3.0.0

# ML - Recommendation
implicit>=0.7.0
scipy>=1.12.0
numpy>=1.26.0

# API
fastapi>=0.115.0
uvicorn>=0.30.0
httpx>=0.27.0
pydantic>=2.5.0

# Utilities
structlog>=24.1.0
```

---

### H6. No Model Integrity Validation on Load

**File**: `src/models/rule_recommender.py:319-366`
**Severity**: HIGH

When loading a model, there is no validation that the loaded data has the expected structure. Missing keys, wrong types, or corrupted data will produce confusing errors deep in the recommendation logic rather than clear load-time failures.

```python
# CURRENT - No validation
model_data = pickle.load(f)
config = model_data["config"]  # KeyError if missing
instance.model.user_factors = model_data["model_state"]["user_factors"]  # Could be wrong type
```

**Recommended Fix**:
```python
@classmethod
def load(cls, path: Path | str) -> "RuleRecommender":
    path = Path(path)

    with open(path, "rb") as f:
        model_data = pickle.load(f)

    # Validate structure
    required_keys = {"model_state", "mappings", "config"}
    missing = required_keys - set(model_data.keys())
    if missing:
        raise ValueError(f"Invalid model file: missing keys {missing}")

    required_config = {"factors", "iterations", "regularization", "random_state"}
    missing_config = required_config - set(model_data["config"].keys())
    if missing_config:
        raise ValueError(f"Invalid model config: missing keys {missing_config}")

    if "user_factors" not in model_data["model_state"]:
        raise ValueError("Model state missing user_factors")
    if "item_factors" not in model_data["model_state"]:
        raise ValueError("Model state missing item_factors")

    # ... proceed with loading
```

---

## Medium Severity Findings

### M1. Pattern Parsing is Fragile

**File**: `src/api/routes.py:141-147`
**Severity**: MEDIUM

The `pattern_to_recommendation` function splits on `"_to_"` which can fail for multi-word domains like `binary_sensor_to_alarm_control_panel` since `binary_sensor` itself does not contain `_to_` but `alarm_control_panel` also doesn't. The real issue is patterns like `"alarm_control_panel_to_light"` which would incorrectly split as `["alarm_control_panel", "light"]` -- actually this works. But `"binary_sensor_to_alarm_control_panel"` splits to `["binary_sensor", "alarm_control_panel"]` -- this also works because `split("_to_", 1)` isn't used, so `split("_to_")` on `"a_to_b_to_c"` returns 3 parts and falls to the `else` branch returning "unknown".

```python
parts = pattern.split("_to_")
if len(parts) == 2:
    trigger_domain, action_domain = parts
else:
    trigger_domain = "unknown"
    action_domain = "unknown"
```

A pattern like `"time_to_binary_sensor_to_light"` (if it existed) would silently produce `unknown/unknown`.

**Recommended Fix**: Use `split("_to_", maxsplit=1)`:
```python
parts = pattern.split("_to_", 1)
```

---

### M2. No Rate Limiting on API Endpoints

**Severity**: MEDIUM

No rate limiting is configured on any endpoint. The `/api/v1/rule-recommendations` endpoint calls `model.recommend()` which involves matrix operations that are CPU-intensive. A burst of requests could saturate the NUC.

**Recommended Fix**: Add slowapi or simple in-memory rate limiting:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/rule-recommendations")
@limiter.limit("30/minute")
async def get_recommendations(request: Request, ...):
    ...
```

---

### M3. No Authentication or Authorization

**Severity**: MEDIUM

All endpoints are completely open. While this may be acceptable for an internal service on the HomeIQ Docker network, the CORS wildcard (H2) combined with no auth means any origin can access the API.

**Recommended Fix**: At minimum, add API key authentication for external access:
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    expected = os.getenv("API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

---

### M4. Missing Error Handling in recommend_for_devices

**File**: `src/models/rule_recommender.py:212`
**Severity**: MEDIUM

The `recommend_for_devices` method accesses `self._user_items[:, idx].sum()` without checking if `_user_items` is None. While `_is_fitted` is checked at the top, `_user_items` could theoretically be None if a model was loaded without the `.npz` file.

```python
if not self._is_fitted:
    raise RuntimeError("Model must be fitted before making recommendations")

# ... later:
pattern_popularity = self._user_items[:, idx].sum()  # _user_items could be None
```

**Recommended Fix**: Add an explicit check:
```python
if self._user_items is None:
    raise RuntimeError("User-items matrix not available. Model may be incompletely loaded.")
```

---

### M5. Streaming Data Loader Has Hardcoded 1M Record Limit

**File**: `src/data/wyze_loader.py:173`
**Severity**: MEDIUM

The streaming loader has a hardcoded limit of 1,000,000 records with a comment saying "remove in production" but no env var or config to control it.

```python
# Limit for initial testing - remove in production
if i >= 1000000:  # 1M records max
    break
```

**Recommended Fix**: Make configurable:
```python
def __init__(self, cache_dir=None, streaming=True, max_records=None):
    self.max_records = max_records or int(os.getenv("MAX_TRAINING_RECORDS", "0"))  # 0 = unlimited

# In load():
if self.max_records and i >= self.max_records:
    break
```

---

### M6. Memory: Collecting All Streaming Records into a List

**File**: `src/data/wyze_loader.py:167-175`
**Severity**: MEDIUM

The streaming loader collects all records into a Python list before converting to a Polars DataFrame. For 1M records, this creates two copies of the data in memory (list + DataFrame).

```python
records = []
for i, record in enumerate(dataset["train"]):
    records.append(record)  # Growing list in memory
    ...
df = pl.DataFrame(records)  # Second copy
```

**Recommended Fix**: Write records to a temporary Parquet file in batches, then read with Polars:
```python
import tempfile

batch = []
batch_size = 50000
temp_files = []

for i, record in enumerate(dataset["train"]):
    batch.append(record)
    if len(batch) >= batch_size:
        tmp = Path(tempfile.mktemp(suffix=".parquet"))
        pl.DataFrame(batch).write_parquet(tmp)
        temp_files.append(tmp)
        batch = []

if batch:
    tmp = Path(tempfile.mktemp(suffix=".parquet"))
    pl.DataFrame(batch).write_parquet(tmp)
    temp_files.append(tmp)

df = pl.concat([pl.read_parquet(f) for f in temp_files])
for f in temp_files:
    f.unlink()
```

---

### M7. Port Documentation Mismatch

**File**: `README.md:22-23`
**Severity**: MEDIUM

The README says external port is 8035, but `docker-compose.yml` maps it to 8040:

```markdown
## Port
- **Internal**: 8035
- **External**: 8035   # <-- Wrong, should be 8040
```

```yaml
# docker-compose.yml
ports:
  - "8040:8035"  # External:Internal - using 8040 as 803x range is in use
```

**Recommended Fix**: Update README.md:
```markdown
## Port
- **Internal**: 8035
- **External**: 8040
```

---

### M8. No Training/Retrain Endpoint

**Severity**: MEDIUM

The service can only load pre-trained models from disk. There is no endpoint to trigger training or retraining. The `WyzeDataLoader` and training code exist but are only usable via CLI scripts. For a production ML service, a retrain endpoint (even if async/background) is important.

**Recommended Fix**: Add a training endpoint:
```python
@router.post("/model/train", response_model=dict)
async def train_model(background_tasks: BackgroundTasks):
    """Trigger model retraining (runs in background)."""
    background_tasks.add_task(_train_model_background)
    return {"status": "training_started", "message": "Model training initiated in background"}
```

---

## Low Severity Findings

### L1. F-string Logging (Security/Performance)

**Files**: `src/api/routes.py:123,128,131,239,333`, `src/models/rule_recommender.py:104,150,317,364`
**Severity**: LOW

Using f-strings in log messages bypasses structlog's lazy formatting and performs string formatting even when the log level would suppress the message.

```python
# CURRENT
logger.warning(f"Model file not found at {_model_path}")
logger.error(f"Failed to load model: {e}")
logger.warning(f"Collaborative filtering failed for {user_id}: {e}")

# RECOMMENDED
logger.warning("Model file not found", path=str(_model_path))
logger.error("Failed to load model", error=str(e))
logger.warning("Collaborative filtering failed", user_id=user_id, error=str(e))
```

---

### L2. Version String Duplicated in 3 Places

**Severity**: LOW

The version "1.0.0" appears in:
1. `src/__init__.py:3` - `__version__ = "1.0.0"`
2. `src/main.py:87` - `version="1.0.0"` (FastAPI app)
3. `pyproject.toml:7` - `version = "1.0.0"`
4. `src/api/routes.py:91` - `version: str` in health response (set to "1.0.0" at line 91)

**Recommended Fix**: Import from `__init__.py`:
```python
from src import __version__

app = FastAPI(
    title="Rule Recommendation ML Service",
    version=__version__,
    ...
)
```

---

### L3. Unreachable Code Path in `get_popular_rules`

**File**: `src/models/rule_recommender.py:267-268`
**Severity**: LOW

The `get_popular_rules` method checks `if self._user_items is None: return []` but the `recommend` method that calls it (as a fallback for unknown users) has already checked `_is_fitted`. If `_is_fitted` is True but `_user_items` is None, this creates a silent empty-result scenario rather than an error.

This is a defensive check that's fine to keep, but the inconsistent behavior (sometimes raise, sometimes return empty) could mask bugs.

---

### L4. `__pycache__` Directory Committed

**File**: `src/__pycache__/main.cpython-313.pyc`
**Severity**: LOW

A compiled Python bytecode file exists in the repository. This should be in `.gitignore`.

**Recommended Fix**: Add to `.gitignore` and remove:
```
__pycache__/
*.pyc
```

---

### L5. Docker Image Runs as Root

**File**: `Dockerfile`
**Severity**: LOW

The Dockerfile does not create or switch to a non-root user. While this is common for internal services, it's a security best practice to run as non-root.

**Recommended Fix**:
```dockerfile
# Add before CMD
RUN useradd --create-home appuser
USER appuser
```

---

## ML-Specific Findings

### ML1. No Model Evaluation Metrics

**Severity**: MEDIUM

There are no evaluation metrics tracked during training -- no precision@k, recall@k, NDCG, MAP, or AUC. Without these, there's no way to know if the model is performing well or if retraining improves quality.

**Recommended Fix**: Add evaluation during training:
```python
from implicit.evaluation import precision_at_k, mean_average_precision_at_k

def evaluate(self, test_matrix: csr_matrix, k: int = 10) -> dict:
    p_at_k = precision_at_k(self.model, self._user_items, test_matrix, K=k)
    map_at_k = mean_average_precision_at_k(self.model, self._user_items, test_matrix, K=k)
    return {
        "precision_at_k": float(p_at_k),
        "map_at_k": float(map_at_k),
        "k": k,
    }
```

### ML2. No Train/Test Split in Data Loader

**Severity**: MEDIUM

The `WyzeDataLoader` provides no mechanism for train/test splitting. All data is used for training, making it impossible to evaluate model quality without manual data handling.

### ML3. Recommendation Scores Not Normalized

**Severity**: LOW

The ALS scores returned by `recommend()` are raw model scores, not probabilities or normalized values. This makes it hard for downstream consumers to interpret confidence levels.

### ML4. No Cold-Start Strategy Beyond Popular

**Severity**: LOW

For new users (not in training data), the only fallback is popular rules. A content-based approach using device inventory metadata could provide better cold-start recommendations.

---

## Prioritized Action Plan

### Phase 1: Critical Fixes (Immediate)

| # | Finding | Action | Effort |
|---|---------|--------|--------|
| 1 | C1 | Replace pickle with restricted unpickler or safer serialization | 2-3 hours |
| 2 | C2 | Implement feedback persistence (JSONL file or SQLite) | 1-2 hours |
| 3 | H4 | Fix Dockerfile health check to use urllib (stdlib) | 15 min |
| 4 | H5 | Remove unused dependencies (duckdb, onnxruntime, scikit-learn, joblib, python-dotenv) | 15 min |
| 5 | L4 | Remove `__pycache__` and add `.gitignore` | 5 min |

### Phase 2: High Priority (This Sprint)

| # | Finding | Action | Effort |
|---|---------|--------|--------|
| 6 | H1 | Create test suite with pytest (routes, model, loader) | 4-6 hours |
| 7 | H2 | Restrict CORS origins to health-dashboard and internal services | 15 min |
| 8 | H3 | Use structlog consistently across all modules | 30 min |
| 9 | H6 | Add model validation on load | 30 min |
| 10 | M7 | Fix port documentation in README.md (8035 -> 8040 external) | 5 min |
| 11 | L2 | Centralize version string | 15 min |

### Phase 3: Medium Priority (Next Sprint)

| # | Finding | Action | Effort |
|---|---------|--------|--------|
| 12 | M1 | Fix pattern parsing to use maxsplit=1 | 5 min |
| 13 | M3 | Add API key authentication | 1 hour |
| 14 | M4 | Add _user_items None check in recommend_for_devices | 5 min |
| 15 | M5 | Make streaming record limit configurable via env var | 15 min |
| 16 | M8 | Add background training endpoint | 2-3 hours |
| 17 | ML1 | Add model evaluation metrics | 2-3 hours |
| 18 | ML2 | Add train/test split to data loader | 1 hour |
| 19 | L1 | Replace f-string logging with structured kwargs | 30 min |

### Phase 4: Enhancements (Backlog)

| # | Finding | Action | Effort |
|---|---------|--------|--------|
| 20 | M2 | Add rate limiting (slowapi) | 1 hour |
| 21 | M6 | Optimize streaming loader memory usage | 2 hours |
| 22 | L5 | Run Docker container as non-root user | 15 min |
| 23 | ML3 | Normalize recommendation scores to 0-1 range | 1 hour |
| 24 | ML4 | Implement content-based cold-start strategy | 4-6 hours |

---

## Summary

The rule-recommendation-ml service is well-structured with clean separation of concerns (data loading, model, API). The code is readable, uses modern Python features (type hints, Pydantic v2, async context managers), and the ML approach (ALS collaborative filtering) is appropriate for the use case.

**Key strengths**:
- Clean FastAPI architecture with proper Pydantic models
- Good use of Polars for data processing
- Graceful degradation (unknown users fall back to popular rules)
- Multi-stage Docker build
- Structured logging configuration (though inconsistently applied)

**Key concerns**:
- **Security**: Pickle deserialization vulnerability is the most critical issue
- **Reliability**: No tests and no feedback persistence undermine production readiness
- **Observability**: Mixed logging frameworks reduce debugging capability
- **Bloat**: ~300MB+ of unused dependencies in the Docker image
- **ML Quality**: No evaluation metrics means model quality is unknown
