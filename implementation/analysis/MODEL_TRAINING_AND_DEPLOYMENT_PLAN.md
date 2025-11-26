# Model Training and Deployment Plan - Test Environment

**Date:** November 25, 2025  
**Environment:** Test  
**Goal:** Train home type classifier model and deploy it

---

## Current Status

### ✅ Completed
- ✅ Code updated for 90-day event generation
- ✅ OpenAI API client updated for 2025 best practices
- ✅ Rate limiting and error handling improved
- ✅ Home type integration code deployed

### ⏳ In Progress
- ⏳ Service restarting (fixing indentation error)
- ⏳ Need to generate synthetic homes
- ⏳ Need to train model
- ⏳ Need to deploy model

---

## Step-by-Step Plan

### Phase 1: Fix Service and Verify Environment ✅/⏳

**1.1 Fix Service Startup**
- ✅ Fix indentation error in `home_type_client.py`
- ⏳ Verify service starts successfully
- ⏳ Check health endpoint

**1.2 Verify Test Environment**
- Check OpenAI API access
- Verify directories exist:
  - `tests/datasets/synthetic_homes/`
  - `models/`

---

### Phase 2: Generate Synthetic Homes ⏳

**2.1 Test Generation (2-5 homes)**
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 5 --output tests/datasets/synthetic_homes --days 90"
```

**Purpose:**
- Verify generation pipeline works
- Check OpenAI API access
- Verify output format

**Expected Time:** 10-20 minutes

**2.2 Full Generation (100 homes)**
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 100 --output tests/datasets/synthetic_homes --days 90"
```

**Purpose:**
- Generate complete training dataset
- 100 homes × 90 days = ~5.7M events

**Expected Time:** 26-52 hours

---

### Phase 3: Train Model ⏳

**3.1 Train Classifier**
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/train_home_type_classifier.py --synthetic-homes tests/datasets/synthetic_homes --output models/home_type_classifier.pkl --test-size 0.2"
```

**Expected Output:**
- Model: `models/home_type_classifier.pkl`
- Results: `models/home_type_classifier_results.json`
- Metrics: Accuracy, F1, Precision, Recall

**Expected Time:** 5-10 minutes

**3.2 Verify Model**
```bash
# Check model file
docker-compose exec ai-automation-service ls -lh models/home_type_classifier.pkl

# Check results
docker-compose exec ai-automation-service cat models/home_type_classifier_results.json

# Test model loading
docker-compose exec ai-automation-service python -c "from src.home_type.home_type_classifier import FineTunedHomeTypeClassifier; c = FineTunedHomeTypeClassifier('models/home_type_classifier.pkl'); print('✅ Model loaded')"
```

---

### Phase 4: Deploy Model ⏳

**4.1 Copy Model to Host**
```bash
# Copy model from container to host
docker cp ai-automation-service:/app/models/home_type_classifier.pkl services/ai-automation-service/models/
```

**4.2 Rebuild Container with Model**
```bash
# Rebuild to include model
docker-compose build ai-automation-service

# Restart service
docker-compose up -d ai-automation-service
```

**4.3 Verify Deployment**
```bash
# Check model is in container
docker-compose exec ai-automation-service ls -lh /app/models/home_type_classifier.pkl

# Test endpoint
curl -H "X-HomeIQ-API-Key: <api_key>" http://localhost:8024/api/home-type/classify?home_id=default
```

---

## Quick Start (If Service is Fixed)

### Option 1: Start with Test Generation
```bash
# 1. Generate 5 homes (test)
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 5 --output tests/datasets/synthetic_homes --days 90"

# 2. Train model
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/train_home_type_classifier.py --synthetic-homes tests/datasets/synthetic_homes --output models/home_type_classifier.pkl"

# 3. Deploy model
docker cp ai-automation-service:/app/models/home_type_classifier.pkl services/ai-automation-service/models/
docker-compose build ai-automation-service
docker-compose up -d ai-automation-service
```

### Option 2: Full Generation (If API Access Works)
```bash
# 1. Generate 100 homes (full dataset)
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 100 --output tests/datasets/synthetic_homes --days 90"

# 2. Train model (same as above)
# 3. Deploy model (same as above)
```

---

## Expected Results

### After Training
- ✅ Model file: `models/home_type_classifier.pkl` (~5MB)
- ✅ Results file: `models/home_type_classifier_results.json`
- ✅ Accuracy: >85%
- ✅ F1 Score: >0.80

### After Deployment
- ✅ Model accessible via `/api/home-type/classify`
- ✅ Home type classification working
- ✅ All integration features active

---

## Troubleshooting

### If OpenAI API Quota Error
- Check billing: https://platform.openai.com/account/billing
- Add credits if needed
- Or use template-based generation (no LLM)

### If Service Won't Start
- Check logs: `docker-compose logs ai-automation-service`
- Fix syntax errors
- Restart: `docker-compose restart ai-automation-service`

### If Model Training Fails
- Check synthetic homes exist: `ls tests/datasets/synthetic_homes/`
- Verify homes have events: Check JSON files
- Check training script: `python scripts/train_home_type_classifier.py --help`

---

**Status:** ⏳ **Ready to Proceed Once Service is Fixed**

