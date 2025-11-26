# Next Steps - Synthetic Home Generation

**Date:** November 24, 2025  
**Status:** ✅ Code Ready | ⏳ Waiting for API Access

---

## Current Status

### ✅ Completed
1. ✅ Scripts updated (90-day default, import fixes)
2. ✅ Container rebuilt with updated code
3. ✅ OpenAI API client updated for 2025 best practices
4. ✅ Rate limiting and error handling improved
5. ✅ Quota vs rate limit detection implemented
6. ✅ Delays added between API calls

### ⏳ Current Blocker
- OpenAI API quota/rate limit issues
- Need to verify API access is working

---

## Immediate Next Steps

### Step 1: Test Generation with Updated Code ⏳

**Purpose:** Verify the updated error handling works correctly

**Command:**
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 2 --output tests/datasets/synthetic_homes --days 90"
```

**Expected Results:**
- ✅ If quota issue: Clear error message with billing link (no retries)
- ✅ If rate limit: Automatic retry with exponential backoff
- ✅ If successful: 2 homes generated with 90 days of events each

**What to Check:**
- Error messages are clear and actionable
- Rate limits are handled with retries
- Quota errors don't waste retries

---

### Step 2: Verify API Access ✅/❌

**If Step 1 shows quota error:**
1. Check OpenAI account: https://platform.openai.com/account/billing
2. Verify API key has sufficient quota
3. Add credits if needed
4. Retry Step 1

**If Step 1 shows rate limit:**
- Code will automatically retry
- Monitor logs for successful retries
- May need to wait or reduce request rate

**If Step 1 succeeds:**
- Proceed to Step 3

---

### Step 3: Run Test Generation (5 homes) ⏳

**Purpose:** Verify full pipeline works end-to-end

**Command:**
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 5 --output tests/datasets/synthetic_homes --days 90"
```

**Expected Time:** 10-20 minutes (with delays)

**What to Verify:**
- ✅ 5 homes generated successfully
- ✅ Each home has areas, devices, events
- ✅ Events span 90 days
- ✅ Files saved to `tests/datasets/synthetic_homes/`

**Check Output:**
```bash
docker-compose exec ai-automation-service ls -lh tests/datasets/synthetic_homes/
docker-compose exec ai-automation-service python -c "import json; f=open('tests/datasets/synthetic_homes/home_001.json'); d=json.load(f); print(f\"Devices: {len(d.get('devices', []))}, Events: {len(d.get('events', []))}\")"
```

---

### Step 4: Full Generation (100 homes) ⏳

**Purpose:** Generate complete training dataset

**Command:**
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 100 --output tests/datasets/synthetic_homes --days 90"
```

**Expected Time:** 26-52 hours (with delays and retries)

**What to Monitor:**
- Progress logs (homes generated)
- Rate limit retries (should be automatic)
- Quota errors (should stop with clear message)
- Disk space (100 homes × 90 days ≈ 13MB)

**Progress Check:**
```bash
# Count generated homes
docker-compose exec ai-automation-service ls -1 tests/datasets/synthetic_homes/home_*.json | wc -l

# Check total events
docker-compose exec ai-automation-service bash -c "grep -h '\"events\"' tests/datasets/synthetic_homes/home_*.json | wc -l"
```

---

### Step 5: Train Model ⏳

**Purpose:** Train home type classifier on synthetic data

**Command:**
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/train_home_type_classifier.py --synthetic-homes tests/datasets/synthetic_homes --output models/home_type_classifier.pkl --test-size 0.2"
```

**Expected Time:** 5-10 minutes

**Expected Output:**
- Model: `models/home_type_classifier.pkl`
- Results: `models/home_type_classifier_results.json`
- Metrics: Accuracy, F1, Precision, Recall

**Target Metrics:**
- Accuracy: >85%
- F1 Score: >0.80
- Per-class precision: >0.75

---

### Step 6: Verify Model ⏳

**Purpose:** Test model inference and verify it works

**Commands:**
```bash
# Check model file exists
docker-compose exec ai-automation-service ls -lh models/home_type_classifier.pkl

# Check results
docker-compose exec ai-automation-service cat models/home_type_classifier_results.json

# Test model loading
docker-compose exec ai-automation-service python -c "from src.home_type.home_type_classifier import FineTunedHomeTypeClassifier; c = FineTunedHomeTypeClassifier('models/home_type_classifier.pkl'); print('✅ Model loaded successfully')"
```

---

### Step 7: Deploy Model ⏳

**Purpose:** Include model in Docker image for production

**Steps:**
1. Copy model to host:
   ```bash
   docker cp ai-automation-service:/app/models/home_type_classifier.pkl services/ai-automation-service/models/
   ```

2. Rebuild container (model will be included):
   ```bash
   docker-compose build ai-automation-service
   docker-compose up -d ai-automation-service
   ```

3. Verify model is accessible:
   ```bash
   curl http://localhost:8018/api/home-type/classify?home_id=default
   ```

---

## Summary Checklist

- [ ] **Step 1:** Test generation with updated code (2 homes)
- [ ] **Step 2:** Verify API access/quota resolved
- [ ] **Step 3:** Run test generation (5 homes)
- [ ] **Step 4:** Full generation (100 homes, 90 days each)
- [ ] **Step 5:** Train model on synthetic data
- [ ] **Step 6:** Verify model performance
- [ ] **Step 7:** Deploy model to production

---

## Estimated Timeline

- **Step 1-2:** 5-10 minutes (testing)
- **Step 3:** 10-20 minutes (5 homes)
- **Step 4:** 26-52 hours (100 homes)
- **Step 5:** 5-10 minutes (training)
- **Step 6:** 5 minutes (verification)
- **Step 7:** 10 minutes (deployment)

**Total:** ~1.5-2.5 days (mostly waiting for generation)

---

## Current Blocker Resolution

**If quota error persists:**
1. Visit: https://platform.openai.com/account/billing
2. Check current usage and limits
3. Add payment method if needed
4. Add credits ($10-50 for 100 homes)
5. Retry Step 1

**If rate limit persists:**
- Code will automatically retry
- May need to reduce request rate further
- Consider running generation in smaller batches

---

## Files Ready

All code is ready and updated:
- ✅ `generate_synthetic_homes.py` - 90-day default, error handling
- ✅ `train_home_type_classifier.py` - Ready for training
- ✅ `openai_client.py` - 2025 best practices
- ✅ All generators - Rate limiting and delays

---

**Next Action:** Run Step 1 to test the updated code

