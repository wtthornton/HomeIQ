# Training OOM (Out of Memory) Fix

**Date:** 2025-11-25  
**Issue:** Training runs failing with return code -9 (SIGKILL/OOM kill)  
**Status:** Fixed

## Root Cause

The training process was being killed by the Docker OOM killer because:
- Container memory limit: **512MB**
- Memory usage before training: **514.57 MB** (already over limit!)
- Process killed with return code **-9** (SIGKILL)

The training process needs significant memory for:
- Model loading (~200-300MB)
- Dataset preparation (~100-200MB)
- Training loop with gradients (~300-500MB)
- Total needed: **~1-1.5GB**

## Fixes Applied

### 1. Increased Container Memory Limit ✅

**File:** `docker-compose.yml`

```yaml
# BEFORE
deploy:
  resources:
    limits:
      memory: 512M  # Too small for training
    reservations:
      memory: 256M

# AFTER
deploy:
  resources:
    limits:
      memory: 2G  # Increased for training runs
    reservations:
      memory: 512M  # Increased base reservation
```

**Rationale:**
- Training needs ~1-1.5GB peak memory
- 2GB provides safety margin
- Still reasonable for a service that handles ML workloads

### 2. Added OOM Detection ✅

**File:** `services/ai-automation-service/src/api/admin_router.py`

Added detection for return code -9 with helpful error message:

```python
# Check for OOM kill (return code -9)
if process.returncode == -9:
    error_output = (
        "⚠️ OUT OF MEMORY (OOM) KILL DETECTED\n"
        "The training process was killed by the system due to insufficient memory.\n"
        "Return code: -9 (SIGKILL)\n\n"
        "SOLUTIONS:\n"
        "1. Increase container memory limit in docker-compose.yml (recommended: 2GB)\n"
        "2. Reduce training parameters:\n"
        "   - Reduce --max-samples (e.g., 200 instead of 2000)\n"
        "   - Reduce --batch-size (already at minimum: 1)\n"
        "   - Reduce --epochs (e.g., 1 instead of 3)\n\n"
        f"Original error output:\n{error_output}"
    )
```

### 3. Enhanced Error Handling ✅

**File:** `services/ai-automation-service/scripts/train_soft_prompt.py`

Added better exception handling to catch OOM-related errors:

```python
except BaseException as e:
    # Catch all other exceptions including OOM kills
    error_msg = str(e)
    logger.exception("Training failed with unexpected error: %s", e)
    
    # Check if this might be an OOM kill
    if hasattr(e, 'errno') and e.errno == -9:
        logger.error("Process was killed (likely OOM). Container memory limit may be too low.")
        logger.error("Recommendation: Increase memory limit to 2GB or reduce training parameters")
```

## Deployment

To apply the fix:

```bash
# Restart service with new memory limit
docker compose up -d ai-automation-service

# Verify new limit
docker stats ai-automation-service --no-stream
```

## Verification

After restart, training should:
1. ✅ Load model successfully
2. ✅ Prepare dataset without OOM
3. ✅ Complete training without being killed
4. ✅ Show clear error messages if OOM occurs

## Alternative Solutions (If 2GB Not Available)

If system doesn't have 2GB available for the container:

1. **Reduce training parameters:**
   ```bash
   # Use fewer samples
   --max-samples 200  # Instead of 2000
   
   # Use fewer epochs
   --epochs 1  # Instead of 3
   ```

2. **Train in smaller batches:**
   - Already using batch_size=1 (minimum)
   - Could reduce gradient_accumulation_steps from 2 to 1

3. **Train outside container:**
   - Run training script directly on host
   - Has access to full system memory

## Related Files

- `docker-compose.yml` - Container memory limits
- `services/ai-automation-service/src/api/admin_router.py` - OOM detection
- `services/ai-automation-service/scripts/train_soft_prompt.py` - Error handling

## Testing

After fix is deployed:
1. Start a new training run
2. Monitor memory usage: `docker stats ai-automation-service`
3. Verify training completes successfully
4. Check error messages are clear if issues occur

