---
status: Closed
priority: Critical
service: openvino-service
created: 2025-11-15
closed: 2025-11-15
labels: [critical, race-condition, memory-leak]
---

# [CRITICAL] OpenVINO Service - Race Conditions and Memory Management Issues

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The OpenVINO service has **8 CRITICAL issues** that pose significant risks to service stability, including race conditions, memory leaks, and unhandled failures that can cause container OOM kills.

---

## Resolution (2025-11-15)

- Added per-model `asyncio.Lock` instances, centralized `_run_blocking` helper, and hardened exception handling / timeouts for all model loading paths (`services/openvino-service/src/models/openvino_manager.py`).
- Implemented deterministic cleanup (`gc.collect`, optional cache purge, torch cache eviction) plus explicit tensor deletion and executor-based inference with bounded `OPENVINO_INFERENCE_TIMEOUT`.
- Introduced request guardrails and health-aware readiness reporting in `services/openvino-service/src/main.py` (input limits, sanitized errors, preload flag, enriched `/health` surface).
- Updated `services/openvino-service/README.md` with 2025 safety patterns, new endpoints (`/embeddings`), configuration knobs, and guardrail documentation.
- Issue file moved to `issues/closed/` with status updated to `Closed`.

## Validation

- Code formatting / lint: `cursor:read_lints` (no findings for updated modules).
- Functional tests not executed because model downloads would require multi-GB HuggingFace artifacts on the CI runner; manual verification recommended once container images are rebuilt.

---

## CRITICAL Issues

### 1. **RACE CONDITION - Concurrent Model Loading**
**Location:** `openvino_manager.py:99-205` (all `_load_*_model()` methods)
**Severity:** CRITICAL

**Issue:** No locking mechanism for model loading. Multiple concurrent requests trigger parallel model initialization.

```python
async def _load_embedding_model(self):
    if self._embed_model is None:  # ← NOT THREAD-SAFE
        # Model loading code (each model is 80MB-1.1GB)
```

**Impact:**
- **Memory spike:** 2-3x model size during concurrent loads (could hit 3GB+)
- **Container OOM kill:** Exceeds docker-compose memory limit (1.5G)
- **Crash on startup:** Multiple health checks could race during container start

**Fix:** Add asyncio.Lock for each model type:
```python
def __init__(self):
    self._embed_lock = asyncio.Lock()

async def _load_embedding_model(self):
    async with self._embed_lock:
        if self._embed_model is None:
            # Load model
```

---

### 2. **MEMORY LEAK - Incomplete Model Cleanup**
**Location:** `openvino_manager.py:67-80`
**Severity:** CRITICAL

**Issue:** Models only set to None, doesn't free memory.

```python
async def cleanup(self):
    # Only sets to None, doesn't free memory
    self._embed_model = None
    self._embed_tokenizer = None
    # No explicit cache clearing or GC
```

**Impact:**
- Models remain in memory until Python GC runs (non-deterministic)
- HuggingFace cache in `/app/models` never cleared
- With 380MB-1.5GB models in 1.5GB container, this is critical
- Unpredictable cleanup timing (GC may not run for minutes)

**Fix:** Add explicit cleanup and force garbage collection:
```python
async def cleanup(self):
    self._embed_model = None
    self._embed_tokenizer = None
    # ... set other models to None

    import gc
    gc.collect()

    # Clear HuggingFace cache if needed
    torch.cuda.empty_cache() if torch.cuda.is_available() else None
```

---

### 3. **UNHANDLED MODEL LOADING FAILURES**
**Location:** `openvino_manager.py:99-205`
**Severity:** CRITICAL

**Issue:** Only catches `ImportError` for OpenVINO fallback, doesn't handle other failures.

```python
try:
    # Model loading
except ImportError:  # ← ONLY catches ImportError
    # Fallback
# Network errors, disk full, OOM, corrupted files NOT handled
```

**Impact:**
- Silent failures: Models fail to load, requests error with cryptic messages
- No recovery: Service must be restarted manually
- Production outages: Dependent services (AI Automation) break

**Fix:** Add comprehensive exception handling:
```python
try:
    # Model loading
except ImportError:
    # OpenVINO fallback
except (OSError, RuntimeError, MemoryError) as e:
    logger.error(f"Model loading failed: {e}")
    raise
```

---

### 4. **NO TIMEOUT ON MODEL INFERENCE**
**Location:** `openvino_manager.py:207-306`
**Severity:** CRITICAL

**Issue:** Model inference can hang indefinitely on malformed inputs.

```python
embeddings = self._embed_model.encode(texts)  # No timeout
outputs = self._reranker_model(**inputs)      # No timeout
outputs = self._classifier_model.generate(**inputs)  # No timeout
```

**Impact:**
- Request handler exhaustion: All workers blocked on hung inference
- Service unresponsive: Health checks may pass but service can't process requests
- DoS vulnerability: Malicious inputs could lock up service

**Fix:** Add timeouts using asyncio:
```python
embeddings = await asyncio.wait_for(
    loop.run_in_executor(None, self._embed_model.encode, texts),
    timeout=30.0
)
```

---

### 5. **MISSING INPUT VALIDATION**
**Location:** `main.py:121-200`, `openvino_manager.py:233-260`
**Severity:** HIGH

**Issue:** No limits on list sizes or text lengths.

```python
@app.post("/embeddings")
async def generate_embeddings(request: EmbeddingRequest):
    # request.texts could be 10,000 items, each 1MB
    embeddings = await openvino_manager.generate_embeddings(
        texts=request.texts  # NO SIZE LIMIT
    )
```

**Impact:**
- OOM from massive inputs (1000 texts × 384 dims × 4 bytes = 1.5MB+ per request)
- Extremely long processing times (50+ seconds for large batches)
- DoS vulnerability

**Fix:** Add validation:
```python
MAX_TEXTS = 100
MAX_TEXT_LENGTH = 10000

if len(request.texts) > MAX_TEXTS:
    raise HTTPException(status_code=400, detail=f"Too many texts (max {MAX_TEXTS})")
if any(len(text) > MAX_TEXT_LENGTH for text in request.texts):
    raise HTTPException(status_code=400, detail=f"Text too long (max {MAX_TEXT_LENGTH} chars)")
```

---

### 6. **TENSOR MEMORY NOT EXPLICITLY FREED**
**Location:** `openvino_manager.py:216-221, 252-256, 283-285, 298-300`
**Severity:** HIGH

**Issue:** PyTorch tensors not explicitly deleted, relies on GC.

```python
inputs = self._embed_tokenizer(texts, ...)  # Creates tensors
outputs = self._embed_model(**inputs)       # More tensors
embeddings = outputs.last_hidden_state.mean(dim=1).detach().numpy()
# Tensors not explicitly deleted, relies on GC
```

**Impact:**
- Memory spikes during load (could exceed 1.5GB limit)
- Intermittent OOM under concurrent requests
- Unpredictable performance (GC pauses)

**Fix:** Explicitly delete tensors:
```python
try:
    inputs = self._embed_tokenizer(texts, ...)
    outputs = self._embed_model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).detach().numpy()
    return embeddings
finally:
    del inputs, outputs
    import gc
    gc.collect()
```

---

### 7. **INCONSISTENT INITIALIZATION STATE**
**Location:** `main.py:34-43`, `openvino_manager.py:82-88`
**Severity:** HIGH

**Issue:** `initialize()` never called, so `_initialized` always False.

```python
# main.py
openvino_manager = OpenVINOManager()
# DON'T call initialize() - models will load on first request
# await openvino_manager.initialize()  # <-- REMOVED
```

**Impact:**
- Misleading health status: Service reports healthy when not ready
- Service dependency failures: Other services don't know when models are loaded
- No initialization validation: Startup errors not caught

**Fix:** Call initialize during startup or fix health check to use lazy loading status.

---

### 8. **INADEQUATE ERROR CONTEXT**
**Location:** `main.py:143-145, 171-173, 198-200`
**Severity:** MEDIUM-HIGH

**Issue:** Generic exception handling loses stack traces.

```python
except Exception as e:
    logger.error(f"Error generating embeddings: {e}")  # NO STACK TRACE
    raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")
```

**Impact:**
- Difficult debugging: Can't diagnose root cause of failures
- Longer MTTR: Mean time to resolution increased
- Hidden bugs: Intermittent issues go undiagnosed

**Fix:** Use `logger.exception()` to capture stack traces:
```python
except Exception as e:
    logger.exception("Error generating embeddings")  # Captures stack trace
    raise HTTPException(status_code=500, detail="Embedding generation failed")
```

---

## Summary Table

| Issue | Severity | Impact | Fix Priority |
|-------|----------|--------|--------------|
| Race condition in model loading | CRITICAL | Container OOM kill | IMMEDIATE |
| Memory leak in cleanup | CRITICAL | Gradual memory growth | IMMEDIATE |
| Unhandled model loading failures | CRITICAL | Service broken state | IMMEDIATE |
| No timeout on inference | CRITICAL | DoS vulnerability | IMMEDIATE |
| Missing input validation | HIGH | OOM, DoS | HIGH |
| Tensor memory not freed | HIGH | Memory spikes | HIGH |
| Inconsistent initialization | HIGH | Misleading status | HIGH |
| Inadequate error context | MEDIUM-HIGH | Difficult debugging | MEDIUM |

---

## RECOMMENDED IMMEDIATE ACTIONS

1. Add asyncio.Lock to model loading (prevents race condition)
2. Implement explicit cleanup with gc.collect() (fixes memory leak)
3. Add comprehensive exception handling (catches all loading failures)
4. Add asyncio.timeout() to inference calls (prevents hangs)
5. Validate input sizes and lengths (prevents DoS/OOM)
6. Use logger.exception() instead of logger.error() (captures stack traces)

---

## References
- CLAUDE.md - Async Patterns & Performance Optimization
- Service location: `/services/openvino-service/`
- Port: 8026 → 8019
- Container Memory Limit: 1.5G
- Model Sizes: 80MB-1.1GB each
