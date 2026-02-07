# Model-Prep Service - Deep Code Review

**Service:** model-prep (Tier 7, Rank #41)
**Type:** Utility / Init container - ML model pre-download and caching
**Port:** None (batch job, not a long-running service)
**Files Reviewed:** `download_all_models.py`, `Dockerfile`, `requirements.txt`, `.dockerignore`, `README.md`
**Review Date:** 2026-02-06

---

## Service Overview

The model-prep service is a utility container that pre-downloads HuggingFace ML models (all-MiniLM-L6-v2, bge-reranker-base, flan-t5-small) into a shared Docker volume. This ensures deterministic caching, faster startup for downstream AI services, and offline capability after initial download.

The service is a **batch job** (run-once), not a long-running daemon. It downloads models and exits.

---

## Findings Summary

| Severity | Count | Categories |
|----------|-------|------------|
| Critical | 1 | Dockerfile build context mismatch |
| High     | 4 | No health check endpoint, no retry logic, no download verification, unpinned dependency upper bounds |
| Medium   | 6 | Memory concerns with large models, no progress reporting, missing PYTHONDONTWRITEBYTECODE, no HuggingFace token support, misleading service config, no integrity verification |
| Low      | 4 | Unused variables, print-based logging, no timeout configuration, cosmetic issues |

---

## Critical Findings

### C1: Dockerfile COPY Path vs Build Context Mismatch

**File:** `Dockerfile:26,45`
**Severity:** Critical

The Dockerfile uses `COPY services/model-prep/requirements.txt .` and `COPY services/model-prep/download_all_models.py .`, which assumes the build context is the repository root (`c:/cursor/HomeIQ/`). However, the README instructs building with the service directory as context:

```dockerfile
# Dockerfile line 26
COPY services/model-prep/requirements.txt .

# Dockerfile line 45
COPY services/model-prep/download_all_models.py .
```

**README (line 31-32) says:**
```bash
docker build -t homeiq-model-prep -f services/model-prep/Dockerfile services/model-prep
```

This `docker build` command sets the context to `services/model-prep/`, but the Dockerfile expects `services/model-prep/` prefix in COPY paths -- which means the Dockerfile expects the **repo root** as context.

The README command will **fail** because inside `services/model-prep/` context there is no `services/model-prep/` subdirectory.

**Fix:** Either the Dockerfile or the README must be corrected. The most common pattern is to use repo root as build context (matching docker-compose conventions):

**Option A - Fix the README to use repo root as context:**
```bash
docker build -t homeiq-model-prep -f services/model-prep/Dockerfile .
```

**Option B - Fix the Dockerfile to use service-local paths:**
```dockerfile
COPY requirements.txt .
# ...
COPY download_all_models.py .
```

Option A is recommended since the Dockerfile already uses the `services/model-prep/` prefix and docker-compose typically uses repo root as context.

---

## High Severity Findings

### H1: No Health Check Endpoint Despite Config Expectation

**File:** `download_all_models.py` (entire file), `scripts/phase1-service-config.yaml:259`
**Severity:** High

The service config at `scripts/phase1-service-config.yaml` defines a health check at `/health` on port 8026 for model-prep. However, model-prep is a **batch job** -- it has no HTTP server and no `/health` endpoint. This config entry is misleading and will cause infrastructure health checks to fail if any orchestration tries to check port 8026.

```yaml
# phase1-service-config.yaml line 256-260
- name: model-prep
  port: 8026
  type: python
  health_check: "/health"
  critical: false
```

**Fix:** Either remove model-prep from the service config or mark it explicitly as a batch/init container with no health check:

```yaml
- name: model-prep
  type: python
  kind: init-container  # or batch-job
  health_check: null
  critical: false
```

### H2: No Retry Logic for Model Downloads

**File:** `download_all_models.py:76-129`
**Severity:** High

Model downloads from HuggingFace Hub can fail due to transient network errors, rate limits, or CDN issues. The `download_model` function has a single try/except with no retry logic. A temporary network glitch causes the entire model download to fail.

```python
# download_all_models.py:76-129
try:
    # ... download logic ...
    return True
except Exception as e:
    print(f"  ✗ Error downloading model: {e}")
    return False
```

**Fix:** Add retry logic with exponential backoff:

```python
import time

MAX_RETRIES = 3
RETRY_DELAY_BASE = 10  # seconds

def download_model(model_key: str, model_info: dict, cache_dir: Path, use_openvino: bool) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # ... existing download logic ...
            return True
        except Exception as e:
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                print(f"  ✗ Attempt {attempt}/{MAX_RETRIES} failed: {e}")
                print(f"    Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  ✗ All {MAX_RETRIES} attempts failed: {e}")
                return False
```

### H3: No Download Verification / Integrity Check

**File:** `download_all_models.py:76-129`
**Severity:** High

After downloading a model, the script does not verify that the downloaded files are complete or valid. A partial download (e.g., from network interruption) would be reported as successful since the `from_pretrained()` call might partially succeed or cache incomplete files.

**Fix:** Add post-download verification:

```python
def verify_model(model_key: str, cache_dir: Path) -> bool:
    """Verify a model was downloaded correctly by checking cache directory."""
    model_info = MODELS[model_key]
    # Check that model directory exists and has files
    model_dirs = list(cache_dir.glob(f"models--{model_info['name'].replace('/', '--')}*"))
    if not model_dirs:
        print(f"  ✗ No cache directory found for {model_key}")
        return False
    # Check snapshot directory has files
    for model_dir in model_dirs:
        snapshots = list(model_dir.glob("snapshots/*/"))
        if snapshots and any(list(s.iterdir()) for s in snapshots):
            return True
    print(f"  ✗ No model files found in cache for {model_key}")
    return False
```

### H4: Unpinned Dependency Upper Bounds

**File:** `requirements.txt:5-14`
**Severity:** High

All dependencies use `>=` without upper bounds. A new major version of `transformers`, `torch`, or `openvino` could introduce breaking API changes that silently break the download script.

```
transformers>=4.46.0
sentence-transformers>=3.3.0
torch>=2.5.0
openvino>=2024.5.0
optimum-intel>=1.20.0
huggingface-hub>=0.24.0
tqdm>=4.66.0
```

**Fix:** Pin to compatible ranges:

```
transformers>=4.46.0,<5.0.0
sentence-transformers>=3.3.0,<4.0.0
torch>=2.5.0,<3.0.0
openvino>=2024.5.0,<2026.0.0
optimum-intel>=1.20.0,<2.0.0
huggingface-hub>=0.24.0,<1.0.0
tqdm>=4.66.0,<5.0.0
```

---

## Medium Severity Findings

### M1: Large Model Loading May Exhaust Memory in Alpine Container

**File:** `download_all_models.py:76-129`, `Dockerfile:30`
**Severity:** Medium

The Dockerfile uses `python:3.12-alpine` which has limited default memory. Loading PyTorch + transformers + OpenVINO models in an Alpine container can be memory-intensive. The `bge-reranker-base` at 280MB (INT8) or ~1.1GB (FP32) plus PyTorch overhead could exceed default container memory limits.

Additionally, models are loaded into Python objects (`model = ...from_pretrained(...)`) but never explicitly deleted, keeping them in memory until the function returns.

**Fix:** Add explicit memory cleanup after each download:

```python
import gc

def download_model(...):
    try:
        # ... download logic ...
        del model  # Free model from memory
        if 'tokenizer' in dir():
            del tokenizer
        gc.collect()
        return True
    except Exception as e:
        ...
```

Also consider documenting minimum memory requirements in the README (e.g., `--memory=4g`).

### M2: No Progress Reporting for Large Downloads

**File:** `download_all_models.py:76-129`
**Severity:** Medium

For models that can be hundreds of MB, there is no progress indication during the actual download. The `tqdm` library is listed in requirements but never imported or used. Long-running downloads appear silent.

```
# requirements.txt line 14
tqdm>=4.66.0
```

**Fix:** The HuggingFace Hub library uses `tqdm` internally for progress bars when available. Having it in requirements is sufficient for console output, but the script should ensure `HF_HUB_DISABLE_PROGRESS_BARS` is not set. Add a note or explicit check:

```python
# Ensure progress bars are shown
os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)
```

### M3: Missing PYTHONDONTWRITEBYTECODE in Dockerfile

**File:** `Dockerfile:50-54`
**Severity:** Medium

The Dockerfile does not set `PYTHONDONTWRITEBYTECODE=1` or `PYTHONUNBUFFERED=1`. Without `PYTHONUNBUFFERED`, print output may be buffered and not visible in Docker logs in real-time.

```dockerfile
# Current env vars (Dockerfile:51-54)
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models
```

**Fix:**
```dockerfile
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models
```

### M4: No HuggingFace Token Support for Private/Gated Models

**File:** `download_all_models.py:62-129`
**Severity:** Medium

The script does not support HuggingFace authentication tokens. While the current three models are public, some HuggingFace models require authentication (e.g., gated models). If the model list is extended, this will silently fail with a confusing error.

**Fix:** Add optional token support:

```python
def download_model(model_key, model_info, cache_dir, use_openvino):
    hf_token = os.getenv("HF_TOKEN")
    # Pass token= parameter to from_pretrained() calls
    model = OVModelForFeatureExtraction.from_pretrained(
        model_name, export=True, cache_dir=str(cache_dir),
        token=hf_token,
    )
```

### M5: Misleading Size Display Logic

**File:** `download_all_models.py:73`
**Severity:** Medium

The size display logic multiplies by 4 when OpenVINO is not used, assuming FP32 is always 4x the INT8 size. This is a rough approximation that may be misleading -- the actual size depends on the model architecture and quantization specifics.

```python
# Line 73
print(f"  Size: ~{size_mb}MB (INT8)" if supports_openvino and use_openvino else f"  Size: ~{size_mb * 4}MB (FP32)")
```

For `flan-t5-small` (which has `openvino: False`), this always shows `~320MB (FP32)` even though the actual FP32 size is ~300MB. The 4x multiplier is not universally accurate.

**Fix:** Add a separate `size_fp32_mb` field to the MODELS dict:

```python
MODELS = {
    "all-MiniLM-L6-v2": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "type": "embedding",
        "size_int8_mb": 20,
        "size_fp32_mb": 90,
        "openvino": True,
    },
    # ...
}
```

### M6: No Checksum/Hash Verification for Downloaded Models

**File:** `download_all_models.py`
**Severity:** Medium

There is no mechanism to verify the integrity of downloaded model files against known checksums. While HuggingFace Hub does some internal verification, adding explicit expected checksums would catch cache corruption and supply-chain attacks.

**Fix:** Store expected model revision hashes in the MODELS dict and verify after download:

```python
MODELS = {
    "all-MiniLM-L6-v2": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "type": "embedding",
        "size_mb": 20,
        "openvino": True,
        "revision": "e4ce9877abf3edfe10b0d82785e83bdcb973e22e",  # pin to known commit
    },
    # ...
}
```

Then pass `revision=model_info.get("revision")` to all `from_pretrained()` calls.

---

## Low Severity Findings

### L1: Unused Variable in seq2seq Download Path

**File:** `download_all_models.py:116`
**Severity:** Low

In the seq2seq download path, the `tokenizer` variable is assigned but never explicitly used beyond being downloaded (cached). While this achieves the goal of caching the tokenizer, the linter would flag it as unused.

```python
# Lines 115-118
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir))
model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=str(cache_dir))
```

**Fix:** Add a comment or use `_` prefix:

```python
_tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir))
```

### L2: Print-Based Logging Instead of Python Logging Module

**File:** `download_all_models.py` (throughout)
**Severity:** Low

The script uses `print()` throughout instead of Python's `logging` module. While acceptable for a simple batch script, using `logging` would allow log level control and structured output.

For a batch utility container, this is acceptable but could be improved if debugging becomes difficult.

### L3: No Configurable Download Timeout

**File:** `download_all_models.py`
**Severity:** Low

The script has no configurable timeout for individual model downloads. A slow or hung download will block indefinitely. The README mentions `HF_HUB_DOWNLOAD_TIMEOUT` as an environment variable, but this is a HuggingFace Hub variable, not something the script explicitly configures or validates.

**Fix:** Add explicit timeout configuration:

```python
# Set download timeout from env (default 5 minutes)
timeout = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(timeout)
print(f"Download timeout: {timeout}s")
```

### L4: .dockerignore Excludes All Markdown Except README.md

**File:** `.dockerignore:44-45`
**Severity:** Low

```
*.md
!README.md
```

This excludes all markdown files except README.md. The README.md is included but never used inside the container -- it is only useful for documentation purposes. This is not harmful but adds ~5KB unnecessarily to the build context.

**Fix:** Simply exclude all `.md` files:

```
*.md
```

---

## Enhancement Suggestions

### E1: Add a `--dry-run` Mode

Add a `--dry-run` flag that lists models to be downloaded without actually downloading them. Useful for CI/CD validation.

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="List models without downloading")
args = parser.parse_args()
```

### E2: Add Disk Space Pre-Check

Before downloading, check available disk space and compare against expected total size:

```python
import shutil

def check_disk_space(cache_dir: Path, required_mb: int) -> bool:
    usage = shutil.disk_usage(cache_dir)
    available_mb = usage.free // (1024 * 1024)
    if available_mb < required_mb:
        print(f"WARNING: Only {available_mb}MB available, need ~{required_mb}MB")
        return False
    return True
```

### E3: Add Skip-If-Exists Logic

Check if a model is already cached before downloading, to avoid re-downloading on repeated runs:

```python
def is_model_cached(model_key: str, model_info: dict, cache_dir: Path) -> bool:
    """Check if a model is already cached."""
    model_dirs = list(cache_dir.glob(f"models--{model_info['name'].replace('/', '--')}*"))
    return bool(model_dirs)
```

### E4: Add JSON Summary Output

Write a JSON summary file after completion for programmatic consumption by CI/CD:

```python
import json

summary = {
    "timestamp": datetime.utcnow().isoformat(),
    "cache_dir": str(cache_dir),
    "openvino": use_openvino,
    "models": {k: {"success": v, "size_mb": MODELS[k]["size_mb"]} for k, v in results.items()},
}
with open(cache_dir / "model-prep-summary.json", "w") as f:
    json.dump(summary, f, indent=2)
```

### E5: Support for Model Pruning/Cleanup

Add a `--cleanup` mode to remove old or unused model versions from the cache.

---

## Prioritized Action Plan

### Immediate (before next deployment)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | **C1**: Fix Dockerfile/README build context mismatch | 5 min | Prevents build failure |
| 2 | **H1**: Fix misleading service config (health check on batch job) | 5 min | Prevents false health check failures |
| 3 | **M3**: Add PYTHONDONTWRITEBYTECODE and PYTHONUNBUFFERED to Dockerfile | 2 min | Ensures real-time log output |

### Short-term (next sprint)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 4 | **H2**: Add retry logic with exponential backoff | 30 min | Prevents transient download failures |
| 5 | **H4**: Pin dependency upper bounds | 10 min | Prevents surprise breakage from major upgrades |
| 6 | **H3**: Add post-download verification | 30 min | Catches partial/corrupt downloads |
| 7 | **M1**: Add explicit memory cleanup (gc.collect) | 10 min | Prevents OOM in constrained environments |
| 8 | **M6**: Pin model revisions for reproducibility | 15 min | Supply chain security + reproducibility |

### Medium-term (next month)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 9 | **M4**: Add HuggingFace token support | 15 min | Future-proofs for gated models |
| 10 | **M5**: Fix size display with separate FP32 sizes | 10 min | Accurate user-facing information |
| 11 | **E3**: Add skip-if-exists logic | 30 min | Faster repeated runs |
| 12 | **E2**: Add disk space pre-check | 15 min | Better error messages for space issues |
| 13 | **E4**: Add JSON summary output | 20 min | CI/CD integration |

### Low priority

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 14 | **L1**: Fix unused tokenizer variable | 2 min | Code clarity |
| 15 | **L2**: Switch to logging module | 15 min | Better debugging |
| 16 | **L3**: Add configurable download timeout | 10 min | Operational control |
| 17 | **L4**: Clean up .dockerignore README inclusion | 2 min | Minor cleanup |
| 18 | **E1**: Add --dry-run mode | 20 min | CI/CD convenience |
| 19 | **E5**: Add model pruning/cleanup mode | 1 hr | Disk management |

---

## Overall Assessment

The model-prep service is a well-conceived utility that solves a real problem (deterministic ML model caching). The code is clean, readable, and well-documented with an excellent README.

**Strengths:**
- Clear purpose and good documentation
- Proper Docker multi-stage build with non-root user
- Supports both OpenVINO (INT8) and standard (FP32) models
- Selective model download via MODELS_TO_DOWNLOAD env var
- Good exit code handling (0 for success, 1 for failure)

**Key Weaknesses:**
- The Dockerfile/README build context mismatch is a **critical** bug that prevents the documented build command from working
- Lack of retry logic makes the service fragile in real-world network conditions
- No download verification means partial downloads could go undetected
- Unpinned dependency bounds risk breaking changes
- Service config incorrectly defines a health check endpoint on a batch job

The service is small and focused, which is appropriate for its role. The recommended fixes are straightforward and the highest-priority items can be addressed in under an hour.
