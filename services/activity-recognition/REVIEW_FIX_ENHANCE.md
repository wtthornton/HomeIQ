# Activity Recognition - Deep Review: Fix & Enhance Plan

**Service:** activity-recognition (Tier 6: Device Management)
**Port:** 8036
**Review Date:** February 6, 2026
**Findings:** 3 CRITICAL, 8 HIGH, 12 MEDIUM, 10 LOW

---

## Executive Summary

The activity-recognition service is the **most mature** of the Tier 6 services - it has a proper LSTM model, ONNX export pipeline, data loading from real datasets (Smart*, REFIT), structured API with versioned routes, and Pydantic models. However, it has a **guaranteed crash bug** in the prediction endpoint (`probs[0]` returns a scalar instead of the probability array), a **security vulnerability** (`torch.load` without `weights_only=True` enables pickle RCE), and the ONNX export **freezes sequence length** preventing variable-length inference. The Dockerfile runs as root and includes ~2GB of PyTorch that's only needed for training.

---

## CRITICAL Fixes (Must Fix)

### FIX-1: Fix Softmax Return Value - probs[0] Truncation Bug
**Finding:** `predict_activity()` returns `probs[0]` (scalar probability of class 0) instead of full probability array
**File:** `src/api/routes.py` line 193
**Action:**
```python
# Change line 193 from:
return predicted_class, probs[0]
# To:
return predicted_class, probs
```
This fix is required for **both** the 1D and 2D branches. After line 191, `probs` is already a 1D array of shape `(num_classes,)`. The extra `[0]` index truncates it to a scalar.

### FIX-2: Add Dynamic Sequence Length to ONNX Export
**Finding:** `dynamic_axes` only marks batch dimension as dynamic; sequence length is frozen
**File:** `src/models/activity_classifier.py` lines 385-388
**Action:**
```python
dynamic_axes={
    "sensor_sequence": {0: "batch_size", 1: "sequence_length"},
    "activity_logits": {0: "batch_size"},
},
```

### FIX-3: Fix torch.load Security Vulnerability
**Finding:** `torch.load` without `weights_only=True` allows arbitrary code execution via pickle
**File:** `src/models/activity_classifier.py` line 345
**Action:**
```python
checkpoint = torch.load(path, map_location=self.device, weights_only=True)
```
Note: This requires that all checkpoint data is pure tensors/primitives. If the checkpoint contains custom objects, refactor to save/load with `safetensors` format instead.

---

## HIGH Fixes

### FIX-4: Add Thread Synchronization for Global _onnx_session
**Finding:** Global mutable state without locks; race condition possible
**File:** `src/api/routes.py` lines 82, 113, 129
**Action:** Use `threading.Lock` around session assignment and access

### FIX-5: Fix CORS Configuration
**Finding:** `allow_origins=["*"]` + `allow_credentials=True` is spec-prohibited
**File:** `src/main.py` lines 82-88
**Action:** Either remove CORS middleware (internal service) or set specific origins

### FIX-6: Return HTTP 503 When Model Not Loaded
**Finding:** Health check returns 200 "healthy" even without model
**File:** `src/api/routes.py` lines 200-208
**Action:**
```python
if _onnx_session is None:
    return HealthResponse(status="degraded", service="activity-recognition", version="1.0.0", model_loaded=False)
```
Return HTTP 503 for degraded state.

### FIX-7: Fix input_size Default Mismatch (10 vs 5 Features)
**Finding:** ActivityLSTM defaults to input_size=10 but API sends 5 features
**File:** `src/models/activity_classifier.py` line 53
**Action:** Change default to `input_size: int = 5`

### FIX-8: Add Range Validation on Sensor Readings
**Finding:** No bounds on sensor values; NaN/Inf accepted, corrupts inference
**File:** `src/api/routes.py` lines 27-34
**Action:**
```python
class SensorReading(BaseModel):
    motion: float = Field(0.0, ge=0.0, le=1.0)
    door: float = Field(0.0, ge=0.0, le=1.0)
    temperature: float = Field(20.0, ge=-50.0, le=80.0)
    humidity: float = Field(50.0, ge=0.0, le=100.0)
    power: float = Field(0.0, ge=0.0, le=100000.0)
```
Add custom validator to reject NaN/Inf values.

### FIX-9: Deduplicate Softmax Implementation
**Finding:** Identical softmax code in routes.py and activity_classifier.py
**Files:** `src/api/routes.py` lines 158-193, `src/models/activity_classifier.py` lines 416-452
**Action:** Delete inline implementation in routes.py; call `predict_with_onnx()` from activity_classifier.py

### FIX-10: Replace np.random.seed with np.random.default_rng
**Finding:** Global random state is thread-unsafe and affects entire process
**File:** `src/data/sensor_loader.py` line 332
**Action:** `rng = np.random.default_rng(42)` and use `rng` for all random operations

### FIX-11: Fail Fast on Missing Data (Don't Silently Use Synthetic)
**Finding:** Missing data directories silently produce random synthetic data for training
**File:** `src/data/sensor_loader.py` lines 101-103, 117-119, 179-181, 197-199
**Action:** Raise `FileNotFoundError` by default; add explicit `allow_synthetic=True` parameter for testing

---

## MEDIUM Fixes

### FIX-12: Fix SensorSequence min_length Mismatch
**Finding:** Pydantic allows min_length=1 but endpoint rejects < 10
**File:** `src/api/routes.py` lines 40-44
**Action:** Change to `min_length=10`

### FIX-13: Fix Dockerfile COPY Shell Redirect
**File:** `Dockerfile` line 28
**Action:** Replace `COPY models/ ./models/ 2>/dev/null || true` with proper multi-stage or just `RUN mkdir -p /app/models`

### FIX-14: Fix Docker HEALTHCHECK
**File:** `Dockerfile` lines 43-44
**Action:** Use curl instead of Python; check HTTP status code; or use simple wget

### FIX-15: Add Non-Root USER to Dockerfile
**Finding:** Container runs as root
**File:** `Dockerfile`
**Action:** Add `RUN adduser --disabled-password appuser` and `USER appuser`

### FIX-16: Fix Lifespan Return Type Annotation
**File:** `src/main.py` line 46
**Action:** Change `-> None` to `-> AsyncGenerator[None, None]` or remove annotation

### FIX-17: Handle Zero-Variance Columns in Normalization
**File:** `src/data/sensor_loader.py` lines 487-496
**Action:** Log warning for zero-variance columns; add to params with (min, min) to indicate constant

### FIX-18: Replace map_elements with Vectorized replace()
**File:** `src/data/sensor_loader.py` lines 547-552
**Action:** `pl.col("activity_label").replace(ACTIVITY_LABELS, default="unknown")`

### FIX-19: Add Rate Limiting on /predict Endpoint
### FIX-20: Fix Bare except:pass in _standardize_columns
**File:** `src/data/sensor_loader.py` lines 276-282
### FIX-21: Vectorize _generate_activity_labels with np.select
**File:** `src/data/sensor_loader.py` lines 286-323
### FIX-22: Make _map_column_name Mapping a Class Constant
**File:** `src/data/sensor_loader.py` lines 232-256
### FIX-23: Use Consistent Logging (structlog keywords vs f-strings)

---

## LOW Fixes

### FIX-24: Deduplicate ACTIVITIES Dictionary (3 copies)
**Action:** Define once in `src/models/activity_classifier.py`, import everywhere else

### FIX-25: Remove Unused httpx Dependency
**File:** `requirements.txt` line 15

### FIX-26: Split Requirements into Inference vs Training
**Action:** Create `requirements.txt` (fastapi, onnxruntime, numpy, polars) and `requirements-train.txt` (add torch)

### FIX-27: Remove Unused python-dotenv Dependency
**File:** `requirements.txt` line 19

### FIX-28: Run ONNX Inference in Thread Pool
**File:** `src/api/routes.py` line 228
**Action:** Change `async def predict` to `def predict` or use `run_in_executor()`

### FIX-29: Deduplicate Version String (4 copies)
**Action:** Use `__version__` from `src/__init__.py` everywhere

### FIX-30: Use Native Polars sin/cos Instead of np.sin
**File:** `src/data/sensor_loader.py` lines 467-470

### FIX-31: Use Polars .slice() Instead of Python Slicing
**File:** `src/data/sensor_loader.py` lines 524-526

### FIX-32: Add Unit Tests (Currently Zero)
### FIX-33: Add /model/info Pydantic Response Model

---

## Enhancement Opportunities

### ENHANCE-1: Real-Time Sensor Stream Integration
Connect to websocket-ingestion to receive live sensor data for continuous activity prediction.

### ENHANCE-2: Activity History Storage
Write predictions to InfluxDB for historical activity tracking and pattern analysis.

### ENHANCE-3: Model Versioning and Hot-Reload
Support loading new models without container restart via API endpoint.

### ENHANCE-4: Confidence Threshold Alerts
Emit alerts when prediction confidence drops below threshold (model drift detection).

### ENHANCE-5: Implement CurrentActivityResponse Endpoint
The Pydantic model exists (routes.py lines 59-66) but no endpoint uses it. Create a stateful endpoint that maintains current activity state.
