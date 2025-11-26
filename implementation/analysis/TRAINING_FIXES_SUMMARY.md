# Training Script Fixes Summary

**Date:** 2025-11-25  
**Run ID:** `run_20251125_211350`  
**Status:** Fixed multiple issues identified from failed training run

## Issues Identified

### 1. TRANSFORMERS_CACHE FutureWarning
- **Problem:** Code was setting both `HF_HOME` and `TRANSFORMERS_CACHE`, causing deprecation warnings
- **Impact:** Warning messages cluttering logs
- **Fix:** Prioritize `HF_HOME`, only use `TRANSFORMERS_CACHE` as fallback

### 2. Missing Device Configuration
- **Problem:** Model and trainer not explicitly configured for CPU, causing potential device mismatches
- **Impact:** Training failures due to device placement issues
- **Fix:** Explicitly set device to CPU and move model to CPU device

### 3. Insufficient Error Handling During Training
- **Problem:** Generic exception handling didn't distinguish between memory errors and other runtime errors
- **Impact:** Difficult to diagnose OOM vs other training failures
- **Fix:** Added specific error handling for OOM errors with helpful suggestions

### 4. Missing Memory Monitoring
- **Problem:** No visibility into memory usage before/during training
- **Impact:** Cannot diagnose memory-related failures
- **Fix:** Added memory usage logging (if psutil available)

## Fixes Implemented

### File: `services/ai-automation-service/scripts/train_soft_prompt.py`

#### 1. Fixed Environment Variable Handling
```python
# Before: Used both HF_HOME and TRANSFORMERS_CACHE
cache_dir = os.environ.get('HF_HOME') or os.environ.get('TRANSFORMERS_CACHE') or None

# After: Prioritize HF_HOME, use TRANSFORMERS_CACHE only as fallback
cache_dir = os.environ.get('HF_HOME') or None
if cache_dir is None:
    cache_dir = os.environ.get('TRANSFORMERS_CACHE')
```

#### 2. Added Explicit CPU Device Configuration
```python
# Added explicit device configuration
import torch
device = torch.device("cpu")
logger.info(f"Using device: {device}")

# Load model with explicit dtype and move to CPU
model = AutoModelForSeq2SeqLM.from_pretrained(
    args.base_model,
    cache_dir=cache_dir,
    local_files_only=True,
    torch_dtype=torch.float32,  # Explicitly use float32 for CPU
)
model = model.to(device)  # Ensure on CPU
```

#### 3. Enhanced Training Error Handling
```python
try:
    # ... training setup ...
    train_result = trainer.train()
except torch.cuda.OutOfMemoryError as e:
    logger.exception("CUDA out of memory error (unexpected on CPU): %s", e)
    sys.exit(1)
except RuntimeError as e:
    error_msg = str(e)
    if "out of memory" in error_msg.lower() or "OOM" in error_msg:
        logger.exception("Out of memory error during training: %s", e)
        logger.error("Try reducing batch_size (--batch-size) or max_samples (--max-samples)")
    else:
        logger.exception("Runtime error during training: %s", e)
    sys.exit(1)
except Exception as e:
    logger.exception("Training failed with unexpected error: %s", e)
    logger.error("Error type: %s", type(e).__name__)
    sys.exit(1)
```

#### 4. Added Memory Usage Logging
```python
# Log memory usage before training (if psutil available)
process = None
try:
    import psutil
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logger.info(f"Memory usage before training: {memory_info.rss / 1024 / 1024:.2f} MB")
    logger.info(f"Available memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
except ImportError:
    logger.info("Memory logging unavailable (psutil not installed)")

# ... training ...

# Log memory usage after training
if process is not None:
    try:
        memory_info_after = process.memory_info()
        logger.info(f"Memory usage after training: {memory_info_after.rss / 1024 / 1024:.2f} MB")
    except Exception:
        pass
```

#### 5. Ensure Trainer Uses CPU
```python
# Ensure trainer uses CPU before training
trainer.model = trainer.model.to(torch.device("cpu"))
train_result = trainer.train()
```

### File: `services/ai-automation-service/src/api/admin_router.py`

#### Fixed Environment Variable Setup
```python
# Before: Always set both
env['HF_HOME'] = str(Path(settings.gnn_model_path).parent)
env['TRANSFORMERS_CACHE'] = str(Path(settings.gnn_model_path).parent)

# After: Prioritize HF_HOME, only set TRANSFORMERS_CACHE if not already set
models_dir = str(Path(settings.gnn_model_path).parent)
env['HF_HOME'] = models_dir
if 'TRANSFORMERS_CACHE' not in env:
    env['TRANSFORMERS_CACHE'] = models_dir
```

## Expected Improvements

1. **No More FutureWarnings:** TRANSFORMERS_CACHE deprecation warning eliminated
2. **Better Device Handling:** Explicit CPU configuration prevents device mismatch errors
3. **Clearer Error Messages:** Specific error handling provides actionable feedback
4. **Memory Visibility:** Memory logging helps diagnose OOM issues
5. **More Reliable Training:** Explicit device placement ensures consistent behavior

## Testing Recommendations

1. **Run Training with Small Dataset:**
   ```bash
   python scripts/train_soft_prompt.py \
     --db-path data/ai_automation.db \
     --max-samples 10 \
     --batch-size 1 \
     --epochs 1
   ```

2. **Monitor Logs for:**
   - Memory usage before/after training
   - Device configuration messages
   - Any error messages with specific error types

3. **Check for:**
   - No FutureWarning about TRANSFORMERS_CACHE
   - Explicit "Using device: cpu" message
   - Memory usage logs (if psutil available)
   - Clear error messages if training fails

## Related Files

- `services/ai-automation-service/scripts/train_soft_prompt.py` - Main training script
- `services/ai-automation-service/src/api/admin_router.py` - Training execution handler
- `implementation/analysis/TRAINING_RUN_FAILURE_ANALYSIS.md` - Original failure analysis

## Next Steps

1. Test training with the fixes applied
2. Monitor memory usage during training
3. Verify error messages are clear and actionable
4. Document any additional issues discovered

