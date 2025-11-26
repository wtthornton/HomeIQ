# Training Run Failure Analysis

**Date:** 2025-11-25  
**Run ID:** `run_20251125_204934`  
**Status:** Failed  
**Duration:** ~10 seconds (8:49:34 PM - 8:49:44 PM)

## Summary

The training run failed shortly after successfully loading the model and tokenizer from cache. The failure occurred within 10 seconds of starting, indicating an early-stage failure in the training pipeline.

## Observed Logs

From the UI Notes field (truncated):
```
FO Attempting to load model from cache: /app/models
INFO Tokenizer loaded from cache
INFO Loadi from cache...
INFO Model loaded from cache successfully
```

**Note:** The "FO" prefix appears to be a truncated log level indicator (likely "INFO").

## Failure Analysis

### Successful Steps
1. ✅ Model cache directory located (`/app/models`)
2. ✅ Tokenizer loaded from cache successfully
3. ✅ Model loaded from cache successfully

### Likely Failure Points

Based on the training script flow (`services/ai-automation-service/scripts/train_soft_prompt.py`), after model loading, the next steps are:

#### 1. Dataset Preparation (Line 261-266)
```python
dataset = prepare_dataset(
    tokenizer,
    examples,
    max_source_tokens=args.source_max_tokens,
    max_target_tokens=args.target_max_tokens,
)
```

**Potential Issues:**
- Empty or malformed training examples
- Tokenization errors
- Memory issues during dataset creation

#### 2. LoRA Configuration (Line 284-292)
```python
lora_config = LoraConfig(...)
model = get_peft_model(model, lora_config)
```

**Potential Issues:**
- PEFT library incompatibility
- Model architecture mismatch
- Memory allocation failure

#### 3. Trainer Initialization (Line 326-331)
```python
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    processing_class=tokenizer,
)
```

**Potential Issues:**
- Dataset format incompatibility
- Missing required columns
- Memory constraints

#### 4. Training Start (Line 333)
```python
train_result = trainer.train()
```

**Potential Issues:**
- Out of memory during first batch
- CUDA/device errors (if GPU expected but not available)
- Dataset iteration errors

## Root Cause Hypothesis

Given the timing (10 seconds) and successful model loading, the most likely failure points are:

1. **Dataset Preparation Failure** (Most Likely)
   - The `prepare_dataset()` function creates a `PromptDataset` class
   - If `examples` is empty or malformed, this could fail silently or raise an exception
   - The script checks for empty examples at line 231-233, but only logs and returns (exit code 0, not failure)

2. **PEFT Model Wrapping Failure**
   - `get_peft_model()` might fail if the model architecture is incompatible
   - Could raise an exception that's not properly caught

3. **Memory Exhaustion**
   - Loading the model + creating dataset + LoRA adapters might exceed available memory
   - Would cause an immediate crash

## Code Issues Identified

### Issue 1: Silent Failure on No Training Data

```230:233:services/ai-automation-service/scripts/train_soft_prompt.py
examples = load_training_examples(args.db_path, args.max_samples)
if not examples:
    logger.error("No Ask AI labelled data available. Nothing to train.")
    return
```

**Problem:** The script returns with exit code 0 (success) when there's no training data, but the backend expects a non-zero exit code for failures.

**Fix:** Should use `sys.exit(1)` instead of `return` to indicate failure.

### Issue 2: Missing Exception Handling

The script doesn't have comprehensive exception handling around critical sections:
- Dataset preparation
- PEFT model wrapping
- Trainer initialization

**Fix:** Add try/except blocks with proper error logging and exit codes.

### Issue 3: Error Message Truncation

The UI only shows the last 160 characters of the error message:

```413:414:services/ai-automation-ui/src/pages/Admin.tsx
<td className="px-4 py-2 text-xs">
  {run.errorMessage ? run.errorMessage.slice(-160) : run.baseModel ?? '—'}
</td>
```

**Problem:** Important error details at the beginning of the log are truncated.

**Fix:** Show full error message in a modal or expandable section.

## Recommendations

### Immediate Actions

1. **Check Training Data Availability**
   ```python
   # Verify training examples exist
   python -c "from pathlib import Path; import sqlite3; conn = sqlite3.connect('data/ai_automation.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM ask_ai_queries WHERE suggestions IS NOT NULL'); print(f'Training examples: {cursor.fetchone()[0]}'); conn.close()"
   ```

2. **Review Full Error Logs**
   - Check backend service logs for the full error output
   - The error message should be stored in `training_runs.error_message` (up to 5000 chars)

3. **Test Training Script Manually**
   ```bash
   cd services/ai-automation-service
   python scripts/train_soft_prompt.py \
     --db-path data/ai_automation.db \
     --output-dir data/ask_ai_soft_prompt \
     --run-directory data/ask_ai_soft_prompt/test_run \
     --run-id test_run \
     --max-samples 10
   ```

### Code Improvements

1. **Fix Silent Failure**
   ```python
   if not examples:
       logger.error("No Ask AI labelled data available. Nothing to train.")
       sys.exit(1)  # Indicate failure
   ```

2. **Add Comprehensive Error Handling**
   ```python
   try:
       dataset = prepare_dataset(...)
   except Exception as e:
       logger.exception("Failed to prepare dataset")
       sys.exit(1)
   
   try:
       model = get_peft_model(model, lora_config)
   except Exception as e:
       logger.exception("Failed to wrap model with PEFT")
       sys.exit(1)
   ```

3. **Improve UI Error Display**
   - Add a "View Full Logs" button/modal
   - Show error messages in a scrollable, expandable section
   - Display both `error_message` and any available logs

### Diagnostic Steps

1. **Verify Database Connection**
   - Ensure the training script can access the database
   - Check file permissions

2. **Check Dependencies**
   - Verify all required packages are installed: `torch`, `transformers`, `peft`
   - Check versions for compatibility

3. **Memory Check**
   - Monitor memory usage during training
   - Consider reducing batch size or max samples if memory is constrained

4. **Review Environment Variables**
   - Verify `HF_HOME` and `TRANSFORMERS_CACHE` are set correctly
   - Check that model cache directory is accessible

## Next Steps

1. ✅ **COMPLETED:** Added improved error handling and logging to the training script
2. ✅ **COMPLETED:** Enhanced the UI to display full error messages (expandable + modal)
3. Query the database/API to retrieve the full error message from `training_runs.error_message` (when service is running)
4. Run the training script manually to reproduce the error

## Implemented Fixes

### 1. Training Script Improvements ✅

**File:** `services/ai-automation-service/scripts/train_soft_prompt.py`

- ✅ Added `sys` import
- ✅ Changed `return` to `sys.exit(1)` when no training data (line 233)
- ✅ Added comprehensive exception handling around:
  - Dataset preparation (lines 261-266)
  - Model loading (lines 268-282)
  - LoRA adapter configuration (lines 284-292)
  - Trainer initialization (lines 360-371)
  - Training execution (lines 373-379)
  - Model/tokenizer saving (lines 381-387)
  - Metadata saving (lines 389-401)
- ✅ Added detailed logging at each step for better debugging

### 2. UI Improvements ✅

**File:** `services/ai-automation-ui/src/pages/Admin.tsx`

- ✅ Added state management for expanded error messages
- ✅ Added expandable error message display (shows first 160 chars, expandable to full)
- ✅ Added "Show full error" button for long error messages
- ✅ Added modal dialog to view complete error details with:
  - Full run information (ID, status, timestamps, model, samples, loss)
  - Complete error message in scrollable, formatted display
  - Copy to clipboard functionality
- ✅ Improved error message styling (monospace font, proper colors)

### 3. Error Retrieval Script ✅

**File:** `get_training_error.py`

- Created utility script to retrieve full error messages via API
- Can be run when the service is available: `python get_training_error.py`

## Related Files

- `services/ai-automation-service/scripts/train_soft_prompt.py` - Training script
- `services/ai-automation-service/src/api/admin_router.py` - Training execution handler
- `services/ai-automation-ui/src/pages/Admin.tsx` - UI display
- `implementation/analysis/TRAINING_CALL_TREE.md` - Complete call tree documentation

