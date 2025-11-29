# Training PARTIAL Status - Analysis and Solutions

**Date:** November 28, 2025  
**Issue:** Training shows "PARTIAL" status instead of "PASSED"  
**Impact:** System is still production-ready (critical models passed), but status reporting could be improved

---

## Current Status

### ✅ Successful Training (2/4 models)

1. **Home Type Classifier** ✅
   - **Status:** PASSED
   - **Metrics:** 
     - Accuracy: 96.2% (excellent!)
     - Precision: 96.3%
     - Recall: 96.3%
     - F1 Score: 96.3%
     - Cross-validation: 97.9% ± 2.6%
   - **Model:** `services/ai-automation-service/models/home_type_classifier.pkl`
   - **Size:** 504,086 bytes

2. **Device Intelligence** ✅
   - **Status:** PASSED
   - **Training Duration:** 0.17 seconds
   - **Models:**
     - Failure Prediction: 181,913 bytes
     - Anomaly Detection: 1,102,184 bytes

### ❌ Failed Training (2/4 models - Non-Critical)

3. **GNN Synergy Detector** ❌
   - **Status:** FAILED
   - **Reason:** Missing required environment variables
   - **Required Variables:**
     - `HA_HTTP_URL` - Home Assistant HTTP URL
     - `HA_TOKEN` - Home Assistant authentication token
     - `MQTT_BROKER` - MQTT broker address
     - `OPENAI_API_KEY` - OpenAI API key for enhancements
   - **Impact:** Non-critical (marked as optional in code)

4. **Soft Prompt** ❌
   - **Status:** FAILED
   - **Reason:** Missing optional dependencies
   - **Missing Dependencies:**
     - `transformers[torch]` - HuggingFace transformers with PyTorch
     - `torch` (CPU wheel) - PyTorch CPU-only version
     - `peft` - Parameter-Efficient Fine-Tuning library
   - **Impact:** Non-critical (enhanced AI capabilities, not required for core functionality)

---

## Why Status Shows "PARTIAL"

The script determines training status using this logic (line 711):

```python
logger.info(f"Training: {'✅ PASSED' if all(r.get('success') for r in results['training'].values()) else '⚠️  PARTIAL'}")
```

**Current Behavior:**
- Checks if **ALL** 4 models succeeded
- Since 2 models failed → Shows "PARTIAL"
- **Problem:** Doesn't distinguish between critical and non-critical models

**Production Readiness:**
- The script correctly determines production readiness using only **critical** models:
  - Home Type Classifier ✅
  - Device Intelligence ✅
- System is marked as **✅ PRODUCTION READY** (line 700)

---

## Solutions

### Option 1: Fix the Environment Variables (Recommended for GNN)

**For GNN Synergy Training:**

Add to `.env` file:
```bash
# Home Assistant Configuration
HA_HTTP_URL=http://192.168.1.86:8123
HA_TOKEN=your_long_lived_access_token_here

# MQTT Configuration
MQTT_BROKER=192.168.1.86:1883

# OpenAI Configuration (optional but recommended)
OPENAI_API_KEY=your_openai_api_key_here
```

**Steps:**
1. Ensure Home Assistant is accessible at the configured URL
2. Generate a long-lived access token in Home Assistant
3. Configure MQTT broker connection
4. Optionally add OpenAI API key for enhanced training

### Option 2: Install Missing Dependencies (For Soft Prompt)

**For Soft Prompt Training:**

Install dependencies in the AI Automation Service:
```bash
cd services/ai-automation-service
pip install transformers[torch] torch peft
```

Or add to `requirements.txt`:
```
transformers[torch]>=4.46.1,<5.0.0
torch>=2.4.0,<3.0.0  # CPU-only from PyTorch index
peft>=0.12.0,<1.0.0
```

**Note:** These are already in `requirements.txt` but may need to be installed:
- Check if dependencies are installed: `pip list | grep -E "transformers|torch|peft"`
- Reinstall if needed: `pip install -r requirements.txt --upgrade`

### Option 3: Improve Status Reporting (Code Fix)

**Problem:** Status shows "PARTIAL" even when all critical models pass.

**Solution:** Update the script to distinguish critical vs. non-critical models:

```python
# Current (line 711):
logger.info(f"Training: {'✅ PASSED' if all(r.get('success') for r in results['training'].values()) else '⚠️  PARTIAL'}")

# Improved:
critical_models = ['home_type', 'device_intelligence']
non_critical_models = ['gnn_synergy', 'soft_prompt']

critical_passed = all(results['training'][model].get('success') for model in critical_models)
all_passed = all(results['training'][model].get('success') for model in critical_models + non_critical_models)

if all_passed:
    logger.info(f"Training: ✅ PASSED (all models)")
elif critical_passed:
    non_critical_failed = [m for m in non_critical_models if not results['training'][m].get('success')]
    logger.info(f"Training: ✅ PASSED (critical) | ⚠️ Optional failed: {', '.join(non_critical_failed)}")
else:
    logger.info(f"Training: ⚠️ PARTIAL (some critical models failed)")
```

---

## Recommended Approach

### For Production Deployment (Now)

**Status:** ✅ **READY TO DEPLOY**

All critical models are trained with excellent results:
- Home Type Classifier: 96.2% accuracy
- Device Intelligence: Trained successfully

**Action:** Deploy now. GNN and Soft Prompt are enhancements that can be added later.

### For Complete Training (Optional)

**If you want all models trained:**

1. **Fix GNN Synergy:**
   ```bash
   # Add to .env file:
   HA_HTTP_URL=http://your-ha-url:8123
   HA_TOKEN=your_token
   MQTT_BROKER=your-mqtt-broker:1883
   OPENAI_API_KEY=your_key  # Optional
   ```

2. **Fix Soft Prompt:**
   ```bash
   # Verify dependencies are installed:
   cd services/ai-automation-service
   pip install -r requirements.txt
   
   # Or install specifically:
   pip install transformers[torch] torch peft
   ```

3. **Re-run training:**
   ```bash
   python scripts/prepare_for_production.py --skip-build --skip-deploy --skip-smoke --skip-generation
   ```

---

## Model Importance Assessment

### Critical Models (Required for Production)

1. **Home Type Classifier** ✅
   - **Purpose:** Classify homes into types (single-family, apartment, etc.)
   - **Status:** ✅ Trained with 96.2% accuracy
   - **Required:** Yes

2. **Device Intelligence** ✅
   - **Purpose:** Predict device failures and detect anomalies
   - **Status:** ✅ Trained successfully
   - **Required:** Yes

### Optional Models (Enhancements)

3. **GNN Synergy Detector** ⚠️
   - **Purpose:** Advanced device relationship detection using Graph Neural Networks
   - **Status:** ❌ Failed (missing env vars)
   - **Required:** No (enhancement, can improve recommendations by 25-35%)
   - **When to fix:** When you want advanced synergy detection features

4. **Soft Prompt** ⚠️
   - **Purpose:** Fine-tuned prompts for AI responses
   - **Status:** ❌ Failed (missing dependencies)
   - **Required:** No (enhancement, improves AI response quality)
   - **When to fix:** When you want optimized AI responses

---

## Current Production Readiness

**✅ SYSTEM IS PRODUCTION READY**

The production readiness check correctly evaluates:

```python
critical_passed = (
    results['build'] and
    results['deploy'] and
    results['smoke_tests']['success'] and
    results['data_generation'] and
    results['training'].get('home_type', {}).get('success', False) and
    results['training'].get('device_intelligence', {}).get('success', False)
)
```

**Result:** ✅ All critical checks passed → **PRODUCTION READY**

The "PARTIAL" status is only for informational purposes and doesn't affect production readiness determination.

---

## Summary

### Why PARTIAL?
- 2 out of 4 models failed (GNN and Soft Prompt)
- Script checks if ALL models pass → Shows "PARTIAL"
- But critical models (Home Type + Device Intelligence) both passed ✅

### Current Status
- ✅ **Production Ready** (critical models trained)
- ⚠️ **PARTIAL training** (optional models not trained)
- ✅ **96.2% accuracy** on home type classification (excellent!)

### To Fix PARTIAL Status

**Quick Fix (Improve Reporting):**
- Update script to show "PASSED (critical)" when critical models succeed
- Optional models can fail without affecting status

**Complete Fix (Train All Models):**
1. Add environment variables for GNN training
2. Install/verify dependencies for Soft Prompt training
3. Re-run training step

**Recommendation:** Deploy now with current excellent results. Add optional models later if needed.

---

**Status Analysis Complete** ✅

