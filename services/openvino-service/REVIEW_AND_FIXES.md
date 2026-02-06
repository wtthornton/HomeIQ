# OpenVINO Service - Deep Code Review & Fixes

**Review Date:** 2026-02-06
**Service:** openvino-service (Tier 3 AI/ML Core, Port 8026 external / 8019 internal)
**Reviewer:** Deep Code Review (automated)
**Files Reviewed:** 17 source files (2 src, 8 test, 2 config, 2 Docker, 2 fixture, 1 README)

---

## Service Overview

### What It Does
The OpenVINO Service provides transformer-based model inference for the HomeIQ platform:

1. **Text Embeddings** - BAAI/bge-large-en-v1.5 (1024-dim) via sentence-transformers for semantic similarity and entity matching
2. **Candidate Re-ranking** - bge-reranker-base for search result relevance scoring
3. **Pattern Classification** - flan-t5-small for categorizing home automation patterns (energy/comfort/security/convenience) and assigning priorities (high/medium/low)

### Architecture
```
FastAPI (main.py)
  |-- /health          GET   - Health check with model status
  |-- /models/status   GET   - Detailed model readiness
  |-- /embeddings      POST  - Text -> 1024-dim vectors
  |-- /rerank          POST  - Query + candidates -> ranked list
  |-- /classify        POST  - Pattern description -> category + priority
  |
  +-- OpenVINOManager (openvino_manager.py)
        |-- Lazy model loading with asyncio locks
        |-- OpenVINO path (disabled: use_openvino=False)
        |-- Standard fallback (sentence-transformers, transformers)
        |-- Thread pool for blocking inference
        |-- Cleanup with gc.collect() and cache purge
```

### Key Consumers
- `rag-service` (port 8027) - depends on openvino-service for embeddings
- `ai-automation-service` (port 8018) - depends on openvino-service

### Resource Allocation
- Docker memory limit: 1.5 GB, reservation: 1 GB
- CPU limit: 2.0 cores, reservation: 1.5 cores
- Health check start_period: 300s (5 min for model loading)

---

## Code Quality Score: 5.5 / 10

### Justification
**Strengths:**
- Clean separation between API layer (main.py) and model management (openvino_manager.py)
- Async-safe model loading with double-checked locking pattern
- Good input validation functions with specific error messages
- Deterministic test framework with fake models (no real model downloads in CI)
- Proper tensor cleanup with gc.collect() in inference paths
- Thread pool execution for blocking model operations
- Configurable timeouts for both model loading and inference

**Weaknesses:**
- **Duplicate variable declarations** override earlier values silently (critical)
- **Duplicate validation calls** in endpoint handlers (bugs)
- **Redundant model_status fetch** in health endpoint (bug)
- **Test assertions reference wrong model names** (test correctness issue)
- **Port mismatch** in `__main__` block (8019 in Dockerfile vs 8019 in code -- but README says port 8026 and `__main__` says 8019 -- confusing)
- **CORS wildcard** in a service that should only receive internal traffic
- **No request concurrency limiting** (no semaphore guarding inference thread pool)
- **No structured metrics** (no Prometheus/OpenTelemetry integration)
- **Stale OpenVINO code paths** that can never execute (`use_openvino=False` hardcoded)
- **Testing dependencies in production requirements.txt** (pytest, hypothesis, pytest-cov)

---

## Critical Issues (Must Fix)

### CRIT-1: Duplicate Variable Declarations Override Limits Silently

**File:** `src/main.py` lines 24-31 vs lines 37-42

The same configuration variables are declared twice with DIFFERENT default values. The second declaration silently overrides the first, causing the documented limits (from env vars or line 24-29) to be lost.

```python
# Lines 24-29 (FIRST declaration)
MAX_TEXTS = int(os.getenv("OPENVINO_MAX_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "10000"))
MAX_RERANK_CANDIDATES = int(os.getenv("OPENVINO_MAX_RERANK_CANDIDATES", "200"))
MAX_TOP_K = int(os.getenv("OPENVINO_MAX_TOP_K", "50"))
MAX_QUERY_LENGTH = int(os.getenv("OPENVINO_MAX_QUERY_LENGTH", "2000"))
MAX_PATTERN_LENGTH = int(os.getenv("OPENVINO_MAX_PATTERN_LENGTH", "8000"))
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}

# Lines 37-42 (SECOND declaration -- OVERRIDES the above!)
MAX_EMBEDDING_TEXTS = int(os.getenv("OPENVINO_MAX_EMBEDDING_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "4000"))       # WAS 10000!
MAX_RERANK_CANDIDATES = int(os.getenv("OPENVINO_MAX_RERANK_CANDIDATES", "200"))
MAX_RERANK_TOP_K = int(os.getenv("OPENVINO_MAX_RERANK_TOP_K", "50"))
MAX_PATTERN_LENGTH = int(os.getenv("OPENVINO_MAX_PATTERN_LENGTH", "4000"))  # WAS 8000!
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}
```

**Impact:** `MAX_TEXT_LENGTH` defaults to 4000 (not 10000 as the first block says), `MAX_PATTERN_LENGTH` defaults to 4000 (not 8000). The README documents both sets of values in different places. Additionally, `MAX_TEXTS` (from line 24) is used in `_validate_text_batch()` but `MAX_EMBEDDING_TEXTS` (line 37) is never referenced anywhere.

**Fix:**
```python
# Remove lines 24-31 entirely, keep only the second block (lines 37-43).
# Consolidate to a single, authoritative set of constants:

# Service guards & configuration
MAX_EMBEDDING_TEXTS = int(os.getenv("OPENVINO_MAX_EMBEDDING_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "4000"))
MAX_RERANK_CANDIDATES = int(os.getenv("OPENVINO_MAX_RERANK_CANDIDATES", "200"))
MAX_RERANK_TOP_K = int(os.getenv("OPENVINO_MAX_RERANK_TOP_K", "50"))
MAX_QUERY_LENGTH = int(os.getenv("OPENVINO_MAX_QUERY_LENGTH", "2000"))
MAX_PATTERN_LENGTH = int(os.getenv("OPENVINO_MAX_PATTERN_LENGTH", "4000"))
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")
```

Then update `_validate_text_batch()` to use `MAX_EMBEDDING_TEXTS` instead of `MAX_TEXTS`, and `_validate_rerank_payload()` to use `MAX_RERANK_TOP_K` instead of `MAX_TOP_K`.

---

### CRIT-2: Duplicate Validation Calls in Endpoint Handlers

**File:** `src/main.py`

Both `/embeddings` and `/classify` endpoints call their validation functions TWICE per request:

```python
# /embeddings endpoint (lines 209-211)
@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    manager = _require_manager()
    _validate_text_batch(request.texts)     # FIRST call
    _validate_text_batch(request.texts)     # DUPLICATE call (line 211)
    ...

# /classify endpoint (lines 279-281)
@app.post("/classify", response_model=ClassifyResponse)
async def classify_pattern(request: ClassifyRequest):
    manager = _require_manager()
    _validate_pattern_description(request.pattern_description)    # FIRST call
    _validate_pattern_description(request.pattern_description)    # DUPLICATE call (line 281)
    ...
```

**Impact:** Wastes CPU cycles on redundant validation. While not functionally broken, it doubles the validation overhead and suggests copy-paste errors that could mask more serious issues.

**Fix:** Remove the duplicate calls on lines 211 and 281.

---

### CRIT-3: Redundant `model_status` Fetch in Health Endpoint

**File:** `src/main.py` lines 186-189

```python
@app.get("/health")
async def health_check():
    manager = _require_manager()
    readiness = manager.is_ready()

    model_status = manager.get_model_status()       # Line 188 - called on manager (via _require_manager)

    model_status = openvino_manager.get_model_status()  # Line 189 - OVERRIDES using global directly!
    ready_state = "ready" if model_status.get("all_models_loaded") else "warming"
    ...
```

**Impact:** Two issues:
1. `model_status` is computed twice (line 188 result is discarded)
2. Line 189 uses the global `openvino_manager` directly instead of the `manager` local variable, bypassing the `_require_manager()` guard. If some future refactor changes the guard behavior, this inconsistency will cause bugs.
3. `model_status.get("all_models_loaded")` always returns `None` because `get_model_status()` never returns a key called `"all_models_loaded"`. This means `ready_state` is always `"warming"`, but `ready_state` is never used in the return dict anyway.

**Fix:**
```python
@app.get("/health")
async def health_check():
    manager = _require_manager()
    readiness = manager.is_ready()
    model_status = manager.get_model_status()

    return {
        "status": "healthy" if readiness else "initializing",
        "service": "openvino-service",
        "ready": readiness,
        "models_loaded": model_status
    }
```

---

## High Priority Issues (Should Fix)

### HIGH-1: CORS Wildcard on Internal-Only Service

**File:** `src/main.py` lines 82-88

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Risk:** This service is only consumed by other backend services (`rag-service`, `ai-automation-service`) over the Docker network. A wildcard CORS policy with `allow_credentials=True` is a security anti-pattern - it allows any browser-based origin to make credentialed requests if the service is accidentally exposed.

Note: `allow_origins=["*"]` with `allow_credentials=True` is actually rejected by browsers (they refuse to send credentials with wildcard origins), but it still represents sloppy security posture.

**Fix:**
```python
# Option A: Remove CORS entirely (preferred for internal services)
# No CORSMiddleware needed

# Option B: Restrict to known consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # health-dashboard
        "http://localhost:3001",   # dev dashboard
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

---

### HIGH-2: No Concurrency Limiter for Model Inference

**File:** `src/models/openvino_manager.py`

The `_run_blocking` method uses `loop.run_in_executor(None, bound)` which submits work to the default thread pool executor. There is no semaphore or concurrency limit, so N concurrent requests will all run inference simultaneously, potentially exhausting the 1.5GB memory limit.

```python
async def _run_blocking(self, func, *args, timeout=None, **kwargs):
    loop = asyncio.get_running_loop()
    bound = functools.partial(func, *args, **kwargs)
    return await asyncio.wait_for(loop.run_in_executor(None, bound), timeout or self.inference_timeout)
```

**Impact:** Under load, multiple concurrent embedding requests can each allocate tensors simultaneously, causing OOM kills.

**Fix:**
```python
# In __init__:
self._inference_semaphore: asyncio.Semaphore | None = None
MAX_CONCURRENT_INFERENCES = int(os.getenv("OPENVINO_MAX_CONCURRENT", "3"))

def _get_semaphore(self) -> asyncio.Semaphore:
    if self._inference_semaphore is None:
        self._inference_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_INFERENCES)
    return self._inference_semaphore

async def _run_blocking(self, func, *args, timeout=None, **kwargs):
    semaphore = self._get_semaphore()
    async with semaphore:
        loop = asyncio.get_running_loop()
        bound = functools.partial(func, *args, **kwargs)
        return await asyncio.wait_for(
            loop.run_in_executor(None, bound),
            timeout or self.inference_timeout
        )
```

---

### HIGH-3: Testing Dependencies in Production Requirements

**File:** `requirements.txt` lines 34-38

```
# Testing
pytest==8.3.3
pytest-asyncio==0.23.0
hypothesis==6.112.0
pytest-cov==5.0.0
```

**Impact:** These packages (and their transitive dependencies) are installed in the production Docker image, bloating it unnecessarily and increasing the attack surface.

**Fix:** Split into two files:

`requirements.txt` (production):
```
# Web Framework
fastapi>=0.123.0,<0.124.0
uvicorn[standard]>=0.32.0,<0.33.0
pydantic==2.12.4
pydantic-settings==2.12.0
httpx>=0.28.1,<0.29.0
pandas>=2.2.0,<3.0.0
numpy>=1.26.0,<1.27.0
--extra-index-url https://download.pytorch.org/whl/cpu
sentence-transformers==3.3.1
transformers==4.46.1
torch>=2.4.0,<3.0.0
sentencepiece
python-dotenv==1.2.1
tenacity==8.2.3
```

`requirements-dev.txt` (testing):
```
-r requirements.txt
pytest==8.3.3
pytest-asyncio==0.23.0
hypothesis==6.112.0
pytest-cov==5.0.0
```

---

### HIGH-4: Dead OpenVINO Code Paths

**File:** `src/models/openvino_manager.py`

The constructor hardcodes `self.use_openvino = False` (line 71), meaning all three `_load_*_model()` methods will always hit the `raise ImportError("OpenVINO not available")` branch in the `if self.use_openvino:` block, then fall through to the standard model path.

This means ~80 lines of OpenVINO-specific loading code (lines 139-188, 226-245, 290-310) are unreachable dead code.

**Impact:** Code maintenance burden, confusion for developers, and wasted review effort. The docstrings and comments still reference "INT8 quantization" and "OpenVINO optimization" which is misleading.

**Fix:** Either:
1. Remove the dead OpenVINO paths entirely and simplify each `_load_*_model()` method, OR
2. Make `use_openvino` configurable via environment variable: `self.use_openvino = os.getenv("OPENVINO_USE_OPENVINO", "false").lower() in {"1", "true", "yes"}`

---

### HIGH-5: Reranker Processes Candidates One at a Time (No Batching)

**File:** `src/models/openvino_manager.py` lines 408-428

```python
def _rerank() -> list[dict]:
    scores = []
    for candidate in candidates:
        text = candidate.get('description', str(candidate))
        pair = f"{query} [SEP] {text}"
        inputs = self._reranker_tokenizer(pair, return_tensors='pt', truncation=True, max_length=512)
        outputs = None
        try:
            outputs = self._reranker_model(**inputs)
            score = float(outputs.logits[0][0].item())
            scores.append((candidate, score))
        finally:
            del inputs
            if outputs is not None:
                del outputs
            gc.collect()  # <-- gc.collect() per SINGLE candidate!
```

**Impact:** For 200 candidates (the max), this calls `gc.collect()` 200 times and does 200 separate tokenizer + forward passes. `gc.collect()` is expensive (~1-5ms per call), so this alone adds 200-1000ms of overhead.

**Fix:**
```python
def _rerank() -> list[dict]:
    texts = [candidate.get('description', str(candidate)) for candidate in candidates]
    pairs = [f"{query} [SEP] {text}" for text in texts]

    # Batch tokenize all pairs at once
    inputs = self._reranker_tokenizer(
        pairs, return_tensors='pt', truncation=True,
        max_length=512, padding=True
    )
    try:
        outputs = self._reranker_model(**inputs)
        scores_tensor = outputs.logits[:, 0]
        scores = scores_tensor.detach().cpu().tolist()
    finally:
        del inputs, outputs
        gc.collect()

    scored = list(zip(candidates, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [candidate for candidate, _ in scored[:top_k]]
```

---

## Medium Priority Issues (Nice to Fix)

### MED-1: Test Assertions Use Wrong Model Names

**File:** `tests/test_openvino_service.py` lines 53-65

```python
async def test_model_status_endpoint(wired_manager):
    status = await get_model_status()
    assert status["embedding_model"] == "BAAI/bge-m3-base"  # WRONG - actual is "BAAI/bge-large-en-v1.5"

async def test_embeddings_endpoint(wired_manager):
    request = EmbeddingRequest(texts=["Turn on the hallway lights"], normalize=True)
    response = await generate_embeddings(request)
    assert response.model_name == "BAAI/bge-m3-base"  # WRONG - actual returned is "BAAI/bge-large-en-v1.5"
```

**Impact:** These tests currently fail (or are skipped) because the assertions reference `"BAAI/bge-m3-base"` but `get_model_status()` returns `"BAAI/bge-large-en-v1.5"` (the value of `EMBEDDING_MODEL_NAME` in `openvino_manager.py`). The endpoint in `main.py` hardcodes `model_name="BAAI/bge-large-en-v1.5"` in the response.

Wait -- actually the endpoint hardcodes `model_name="BAAI/bge-large-en-v1.5"` at line 225 of main.py. So the test at line 65 asserting `"BAAI/bge-m3-base"` would fail.

**Fix:**
```python
assert status["embedding_model"] == "BAAI/bge-large-en-v1.5"
# ...
assert response.model_name == "BAAI/bge-large-en-v1.5"
```

---

### MED-2: `_get_lock()` Has a Race Condition

**File:** `src/models/openvino_manager.py` lines 495-501

```python
def _get_lock(self, attr_name: str) -> asyncio.Lock:
    lock = getattr(self, attr_name)
    if lock is None:
        lock = asyncio.Lock()
        setattr(self, attr_name, lock)
    return lock
```

This is called from async context. Although Python's GIL prevents true race conditions in CPython, the pattern is fragile: if two coroutines both call `_get_lock("_embed_lock")` before either has set the attribute, they could create two different Lock objects. The double-checked locking inside `_load_embedding_model()` would then fail because each coroutine holds a different lock.

**In practice:** This is unlikely in single-threaded asyncio because the `if lock is None` check and `setattr` happen synchronously without an `await` between them. But it is a code smell.

**Fix:** Create locks eagerly in `__init__`:
```python
def __init__(self, models_dir: str = "/app/models"):
    ...
    self._embed_lock = asyncio.Lock()
    self._reranker_lock = asyncio.Lock()
    self._classifier_lock = asyncio.Lock()
```

Note: This requires the event loop to exist at construction time. If that is an issue, use a factory pattern or create locks in the lifespan handler.

Actually, `asyncio.Lock()` does NOT require a running event loop in Python 3.10+. It is safe to construct in `__init__`. The current lazy pattern is unnecessarily complex.

---

### MED-3: `_initialized` Flag is Set Before Models Actually Load

**File:** `src/models/openvino_manager.py` line 72

```python
self._initialized = True  # Ready for lazy loading immediately
```

This is set to `True` in `__init__`, making `is_ready()` return `True` even when no models are loaded. The `/health` endpoint reports `"status": "healthy"` before any model is available.

**Impact:** Upstream services like `rag-service` that wait for `service_healthy` may start sending requests before models are loaded, causing the first requests to block for seconds during lazy loading.

**Fix:**
```python
# In __init__:
self._initialized = True  # Service is ready to accept requests (models lazy-load)

# The current behavior IS intentional for lazy-loading mode.
# However, the health endpoint should distinguish:
@app.get("/health")
async def health_check():
    manager = _require_manager()
    model_status = manager.get_model_status()
    any_model_loaded = any([
        model_status["embedding_loaded"],
        model_status["reranker_loaded"],
        model_status["classifier_loaded"],
    ])

    return {
        "status": "healthy",
        "service": "openvino-service",
        "ready": manager.is_ready(),
        "models_ready": any_model_loaded,
        "models_loaded": model_status
    }
```

---

### MED-4: No Request Logging / Metrics

**File:** `src/main.py`

There is no middleware or per-request logging to track:
- Request count per endpoint
- Latency percentiles (p50, p95, p99)
- Error rates per endpoint
- Active request count
- Model load count

The README mentions "Structured Logging" with latency, batch sizes, and error rates, but none of this is implemented.

**Fix:** Add a simple timing middleware:
```python
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": round(duration, 4),
            }
        )
        return response

app.add_middleware(MetricsMiddleware)
```

---

### MED-5: Classifier Makes Two Sequential Model Calls

**File:** `src/models/openvino_manager.py` lines 454-487

```python
def _classify() -> dict[str, str]:
    category_raw = _generate(category_prompt)
    category = self._parse_category(category_raw)
    # ... builds priority_prompt using category ...
    priority_raw = _generate(priority_prompt)
    priority = self._parse_priority(priority_raw)
```

The classification endpoint calls `_generate()` twice sequentially (once for category, once for priority). Each call tokenizes, runs a forward pass, and calls `gc.collect()`.

**Impact:** Classification latency is 2x what it needs to be. The priority prompt includes the category result, creating a serial dependency.

**Fix (option A):** Combine into a single prompt:
```python
combined_prompt = f"""Classify this smart home pattern.

Pattern: {pattern_description}

1. Category (one of: energy, comfort, security, convenience):
2. Priority (one of: high, medium, low):

Answer:"""
```
Then parse both values from a single model output.

**Fix (option B):** If the serial dependency is important, accept the latency but remove the redundant `gc.collect()` from the inner `_generate()` function and do it once at the end.

---

### MED-6: `pandas` Dependency is Unused

**File:** `requirements.txt` line 16

```
pandas>=2.2.0,<3.0.0  # Stable pandas 2.x (2025)
```

Neither `main.py` nor `openvino_manager.py` imports or uses pandas. This adds ~30MB to the Docker image for no reason.

**Fix:** Remove the pandas line from `requirements.txt`.

---

### MED-7: `httpx` and `tenacity` Dependencies are Unused

**File:** `requirements.txt` lines 13, 31

```
httpx>=0.28.1,<0.29.0
tenacity==8.2.3
```

Neither is imported anywhere in the source code.

**Fix:** Remove both from `requirements.txt` unless they are planned for future use.

---

## Low Priority Issues (Improvements)

### LOW-1: Port Inconsistency in `__main__` Block

**File:** `src/main.py` line 311

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)
```

This is correct (matches the Dockerfile `CMD` port 8019), but the README mentions port 8026 (the Docker-exposed port). The `__main__` block does not read from an environment variable.

**Fix:**
```python
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8019"))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

### LOW-2: f-strings Used in Logging

**File:** `src/models/openvino_manager.py` lines 76, 136, 157, 169, 188, 208

```python
logger.info(f"OpenVINOManager initialized (BGE-M3-base, {self.embedding_model_dim}-dim, ...)")
logger.info(f"Loading embedding model: BGE-M3-base...")
```

f-strings in logging calls evaluate the string even if the log level is too high to emit the message. This is a minor performance waste and prevents structured logging systems from deduplicating messages.

**Fix:** Use %-style formatting:
```python
logger.info("OpenVINOManager initialized (BGE-M3-base, %d-dim, models will load on first use)", self.embedding_model_dim)
logger.info("Loading embedding model: %s...", "BGE-M3-base")
```

---

### LOW-3: `pydantic-settings` is Listed But Never Used

**File:** `requirements.txt` line 10

```
pydantic-settings==2.12.0
```

The service uses `os.getenv()` for all configuration, not Pydantic Settings classes.

**Fix:** Remove or convert configuration to a `BaseSettings` class (recommended):
```python
from pydantic_settings import BaseSettings

class ServiceSettings(BaseSettings):
    max_embedding_texts: int = 100
    max_text_length: int = 4000
    max_rerank_candidates: int = 200
    max_rerank_top_k: int = 50
    max_query_length: int = 2000
    max_pattern_length: int = 4000
    preload_models: bool = False
    model_cache_dir: str = "/app/models"
    inference_timeout: float = 30.0
    model_load_timeout: float = 180.0

    class Config:
        env_prefix = "OPENVINO_"
```

---

### LOW-4: NER Benchmark Fixture Contains Entity Data That Is Never Tested

**File:** `tests/fixtures/ner_benchmark.json`

Each entry has an `"entities"` field with NER annotations, but the test in `test_ner.py` only tests `expected_category` and `expected_priority`. The entity data is unused.

**Impact:** The fixture name and structure suggest NER testing, but the actual NER capability was apparently removed. The test file is also named `test_ner.py` despite testing classification.

**Fix:** Rename `test_ner.py` to `test_classification.py`, rename the fixture to `classification_benchmark.json`, and remove unused `entities` fields from the fixture data.

---

### LOW-5: `_embed_tokenizer` Set to `None` in Standard Path But Never Cleaned Up Symmetrically

**File:** `src/models/openvino_manager.py` line 207

When the standard sentence-transformers path is used, `_embed_tokenizer` is explicitly set to `None`. But in `generate_embeddings()`, the check `if self.use_openvino and self._embed_tokenizer is not None` handles this correctly. This is fine but could be clearer.

---

### LOW-6: Emoji in Logging

**File:** `src/main.py` and `src/models/openvino_manager.py`

Extensive use of emoji in log messages (rocket, checkmark, cross, broom, arrows). While visually helpful in development, these can cause encoding issues in some log aggregation systems and make grep/search harder.

**Fix:** Replace emoji with text prefixes: `[START]`, `[OK]`, `[FAIL]`, `[CLEANUP]`.

---

## Security Review

### SEC-1: CORS Wildcard (HIGH - see HIGH-1)
Covered above. Internal services should not have permissive CORS.

### SEC-2: No Authentication or API Key
The service has no authentication mechanism. Anyone with network access to port 8019/8026 can invoke model inference.

**Risk:** Low in Docker network (services communicate internally). Medium if the port is accidentally exposed to the host network.

**Recommendation:** Add a simple API key check via middleware or dependency injection:
```python
API_KEY = os.getenv("OPENVINO_API_KEY")

async def verify_api_key(request: Request):
    if API_KEY and request.headers.get("X-API-Key") != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

### SEC-3: HuggingFace Token Handling
**File:** `src/models/openvino_manager.py` lines 148-152

```python
hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
if hf_token:
    os.environ["HF_TOKEN"] = hf_token
    os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token
```

This code is in the dead OpenVINO path (never executes), but if it were enabled, it writes secrets back into `os.environ` which could leak via `/proc/self/environ` or debugging endpoints.

**Recommendation:** Pass tokens directly to function calls rather than writing to `os.environ`.

### SEC-4: No Input Sanitization for Log Injection
User-supplied text is logged in error messages. Malicious input could inject fake log entries.

**Risk:** Low (structured logging would mitigate this).

### SEC-5: Model Download from External Sources
Models are downloaded from HuggingFace Hub at runtime. A compromised HuggingFace account or man-in-the-middle attack could serve a malicious model.

**Recommendation:** Pin model revisions with commit hashes or use model integrity verification.

---

## Performance Review

### Inference Latency

| Operation | Current Architecture | Potential Issue |
|-----------|---------------------|----------------|
| Embeddings | sentence-transformers encode (batched) | Good - native batching |
| Reranking | Per-candidate tokenize + forward pass | **Bad** - O(n) forward passes |
| Classification | Two sequential generate calls | **Moderate** - 2x latency |

### Memory Management

**Good:**
- `gc.collect()` after inference operations
- `del inputs` / `del outputs` in finally blocks
- `torch.cuda.empty_cache()` in cleanup (though CUDA is not used)
- Cache purge on shutdown

**Bad:**
- `gc.collect()` called per candidate in reranking (200 calls for max batch)
- No memory monitoring or reporting
- No max tensor size guard

### Batching

**Good:**
- Embedding endpoint accepts batch of texts
- sentence-transformers handles internal batching

**Bad:**
- Reranker does not batch candidates (see HIGH-5)
- No adaptive batching based on available memory

### Cold Start

- First request per model: 2-5s (download + compile)
- Docker health check allows 5-minute start period
- Lazy loading is the default, which is appropriate for the 1.5GB memory limit

---

## Test Coverage Assessment

### Test Files and Coverage

| Test File | What It Tests | Quality |
|-----------|---------------|---------|
| `test_embeddings.py` | Dimensions, normalization, similarity, dissimilarity, properties | Good |
| `test_model_loading.py` | Fallback to standard models, cleanup | Good |
| `test_ner.py` | Classification benchmark, parser edge cases | Good (misnamed) |
| `test_openvino_service.py` | All endpoints, validation errors | Good but has wrong assertions |
| `test_performance.py` | Single and batch latency | Adequate |
| `test_reranking.py` | Ordering, top_k limits | Adequate |
| `conftest.py` | Path setup | Functional |
| `utils.py` | Deterministic test framework | Excellent |

### Coverage Gaps

1. **No tests for concurrent requests** - Multiple simultaneous embedding requests
2. **No tests for model loading timeout** - What happens when `_run_blocking` times out
3. **No tests for OOM handling** - Memory exhaustion scenarios
4. **No tests for the lifespan handler** - FastAPI startup/shutdown
5. **No tests for malformed input** - Unicode, null bytes, extremely long strings at the boundary
6. **No tests for the health endpoint when manager is partially initialized** - e.g., embedding loaded but reranker not
7. **No integration tests with real models** - All tests use fake models (acceptable for CI, but real model tests should exist for release validation)
8. **Wrong model name assertions in test_openvino_service.py** (see MED-1)

### Test Framework Quality

The `TestOpenVINOManager` class in `utils.py` is well-designed:
- Subclasses the real manager to override model loading
- Uses deterministic hash-based embeddings (reproducible across runs)
- Bypasses thread pool for speed
- Fake reranker uses actual cosine similarity for meaningful ordering tests

---

## Specific Code Fixes

### Fix 1: Consolidated main.py Configuration (CRIT-1 + CRIT-2 + CRIT-3)

**Before** (lines 24-42, abbreviated):
```python
MAX_TEXTS = int(os.getenv("OPENVINO_MAX_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "10000"))
# ... 5 more lines ...
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}

# ... later ...
MAX_EMBEDDING_TEXTS = int(os.getenv("OPENVINO_MAX_EMBEDDING_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "4000"))
# ... 4 more lines ...
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")
```

**After:**
```python
# Service guards & configuration (single authoritative block)
MAX_EMBEDDING_TEXTS = int(os.getenv("OPENVINO_MAX_EMBEDDING_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "4000"))
MAX_RERANK_CANDIDATES = int(os.getenv("OPENVINO_MAX_RERANK_CANDIDATES", "200"))
MAX_RERANK_TOP_K = int(os.getenv("OPENVINO_MAX_RERANK_TOP_K", "50"))
MAX_QUERY_LENGTH = int(os.getenv("OPENVINO_MAX_QUERY_LENGTH", "2000"))
MAX_PATTERN_LENGTH = int(os.getenv("OPENVINO_MAX_PATTERN_LENGTH", "4000"))
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")
```

Then update references:
- `_validate_text_batch`: `MAX_TEXTS` -> `MAX_EMBEDDING_TEXTS`
- `_validate_rerank_payload`: `MAX_TOP_K` -> `MAX_RERANK_TOP_K`

### Fix 2: Clean health endpoint (CRIT-3)

**Before:**
```python
@app.get("/health")
async def health_check():
    manager = _require_manager()
    readiness = manager.is_ready()
    model_status = manager.get_model_status()
    model_status = openvino_manager.get_model_status()
    ready_state = "ready" if model_status.get("all_models_loaded") else "warming"
    return {
        "status": "healthy" if readiness else "initializing",
        "service": "openvino-service",
        "ready": readiness,
        "models_loaded": model_status
    }
```

**After:**
```python
@app.get("/health")
async def health_check():
    manager = _require_manager()
    readiness = manager.is_ready()
    model_status = manager.get_model_status()
    return {
        "status": "healthy" if readiness else "initializing",
        "service": "openvino-service",
        "ready": readiness,
        "models_loaded": model_status
    }
```

### Fix 3: Remove duplicate validation calls (CRIT-2)

**Before (`/embeddings`):**
```python
async def generate_embeddings(request: EmbeddingRequest):
    manager = _require_manager()
    _validate_text_batch(request.texts)
    _validate_text_batch(request.texts)  # <-- remove this line
```

**Before (`/classify`):**
```python
async def classify_pattern(request: ClassifyRequest):
    manager = _require_manager()
    _validate_pattern_description(request.pattern_description)
    _validate_pattern_description(request.pattern_description)  # <-- remove this line
```

### Fix 4: Eager lock creation (MED-2)

**Before:**
```python
def __init__(self, models_dir: str = "/app/models"):
    ...
    self._embed_lock: asyncio.Lock | None = None
    self._reranker_lock: asyncio.Lock | None = None
    self._classifier_lock: asyncio.Lock | None = None

def _get_lock(self, attr_name: str) -> asyncio.Lock:
    lock = getattr(self, attr_name)
    if lock is None:
        lock = asyncio.Lock()
        setattr(self, attr_name, lock)
    return lock
```

**After:**
```python
def __init__(self, models_dir: str = "/app/models"):
    ...
    self._embed_lock = asyncio.Lock()
    self._reranker_lock = asyncio.Lock()
    self._classifier_lock = asyncio.Lock()

# _get_lock() can be removed; use self._embed_lock directly in _load_embedding_model(), etc.
```

---

## Enhancement Recommendations

### ENH-1: Add Prometheus Metrics
Integrate `prometheus-fastapi-instrumentator` or `starlette-prometheus` for:
- `openvino_request_duration_seconds` histogram (by endpoint)
- `openvino_model_loaded` gauge (per model)
- `openvino_inference_errors_total` counter
- `openvino_active_requests` gauge

### ENH-2: Add Model Warm-up Endpoint
```python
@app.post("/models/warmup")
async def warmup_models():
    """Pre-load all models (useful for orchestrators)."""
    manager = _require_manager()
    await manager.initialize()
    return {"status": "all_models_loaded", "models": manager.get_model_status()}
```

### ENH-3: Add Embedding Caching
For frequently embedded texts (entity names), add an LRU cache:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _cached_embedding(text: str) -> tuple:
    # Return as tuple for hashability
    return tuple(embedding.tolist())
```

### ENH-4: Add Structured JSON Logging
Replace `logging.basicConfig()` with structured JSON logging for better log aggregation:
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
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)
```

### ENH-5: Add Graceful Degradation
If one model fails to load, the service should still serve endpoints for the other models instead of crashing entirely. Currently, `initialize()` raises on any failure, blocking startup.

### ENH-6: Add OpenTelemetry Tracing
The `rag-service` already has OTLP configuration. Add tracing spans for model loading and inference:
```python
from opentelemetry import trace
tracer = trace.get_tracer("openvino-service")

async def generate_embeddings(self, texts, normalize=True):
    with tracer.start_as_current_span("generate_embeddings") as span:
        span.set_attribute("batch_size", len(texts))
        ...
```

---

## Dependency Audit

| Dependency | Version | Used? | Notes |
|------------|---------|-------|-------|
| fastapi | >=0.123.0,<0.124.0 | Yes | Core framework |
| uvicorn[standard] | >=0.32.0,<0.33.0 | Yes | ASGI server |
| pydantic | ==2.12.4 | Yes | Request/response models |
| pydantic-settings | ==2.12.0 | **No** | Not imported anywhere |
| httpx | >=0.28.1,<0.29.0 | **No** | Not imported anywhere |
| pandas | >=2.2.0,<3.0.0 | **No** | Not imported anywhere |
| numpy | >=1.26.0,<1.27.0 | Yes | Embedding arrays |
| sentence-transformers | ==3.3.1 | Yes | Embedding model |
| transformers | ==4.46.1 | Yes | Reranker and classifier |
| torch | >=2.4.0,<3.0.0 | Yes (transitive) | Required by sentence-transformers |
| sentencepiece | (any) | Yes | T5 tokenizer |
| python-dotenv | ==1.2.1 | **No** | Not imported anywhere |
| tenacity | ==8.2.3 | **No** | Not imported anywhere |
| pytest | ==8.3.3 | Testing only | Should be in dev requirements |
| pytest-asyncio | ==0.23.0 | Testing only | Should be in dev requirements |
| hypothesis | ==6.112.0 | Testing only | Should be in dev requirements |
| pytest-cov | ==5.0.0 | Testing only | Should be in dev requirements |

**Unused production dependencies:** pydantic-settings, httpx, pandas, python-dotenv, tenacity (5 packages)
**Misplaced test dependencies:** pytest, pytest-asyncio, hypothesis, pytest-cov (4 packages)

### Version Concerns
- `numpy>=1.26.0,<1.27.0` -- This constrains numpy to 1.26.x which may conflict with newer sentence-transformers or torch releases.
- README lists different versions than requirements.txt (e.g., README says `fastapi==0.121.2` but requirements says `>=0.123.0,<0.124.0`).

---

## Action Items (Prioritized Checklist)

### Immediate (before next deploy)
- [ ] **CRIT-1:** Remove duplicate configuration block in main.py (lines 24-31)
- [ ] **CRIT-2:** Remove duplicate `_validate_text_batch` call (line 211) and `_validate_pattern_description` call (line 281)
- [ ] **CRIT-3:** Fix health endpoint: remove duplicate `model_status` fetch and dead `ready_state` variable

### This Sprint
- [ ] **HIGH-1:** Remove or restrict CORS middleware (internal service)
- [ ] **HIGH-2:** Add inference concurrency semaphore to prevent OOM under load
- [ ] **HIGH-3:** Split requirements.txt into prod and dev files; remove test deps from Docker image
- [ ] **HIGH-4:** Remove dead OpenVINO code paths (or make configurable)
- [ ] **HIGH-5:** Batch reranker tokenization and forward passes

### Next Sprint
- [ ] **MED-1:** Fix wrong model name assertions in test_openvino_service.py
- [ ] **MED-2:** Create locks eagerly in `__init__` instead of lazy `_get_lock()`
- [ ] **MED-3:** Improve health endpoint to report per-model readiness
- [ ] **MED-4:** Add request logging middleware with timing
- [ ] **MED-5:** Optimize classifier to use single prompt or remove redundant gc.collect
- [ ] **MED-6:** Remove unused pandas dependency
- [ ] **MED-7:** Remove unused httpx and tenacity dependencies

### Backlog
- [ ] **LOW-1:** Make port configurable in `__main__` block
- [ ] **LOW-2:** Replace f-strings in logging with %-style
- [ ] **LOW-3:** Remove or use pydantic-settings (convert to BaseSettings class)
- [ ] **LOW-4:** Rename test_ner.py to test_classification.py
- [ ] **LOW-5:** Clean up _embed_tokenizer handling
- [ ] **LOW-6:** Replace emoji in log messages with text prefixes
- [ ] **ENH-1:** Add Prometheus metrics
- [ ] **ENH-2:** Add model warm-up endpoint
- [ ] **ENH-3:** Add embedding LRU cache for frequently embedded texts
- [ ] **ENH-4:** Add structured JSON logging
- [ ] **ENH-5:** Add graceful degradation per model
- [ ] **ENH-6:** Add OpenTelemetry tracing

### Testing Improvements
- [ ] Add concurrent request tests
- [ ] Add timeout handling tests
- [ ] Add lifespan handler tests
- [ ] Add boundary input tests (max length, unicode, etc.)
- [ ] Fix wrong model name assertions
- [ ] Add partial initialization health tests

---

**End of Review**
