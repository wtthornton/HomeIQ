# Synthetic Home Generation - Execution Plan

**Date:** November 2025  
**Status:** Ready for Execution  
**Action Required:** Rebuild Docker container to include updated scripts

---

## Issue Identified

The synthetic home generation scripts have been updated with correct imports (`from src.config` instead of `from config`), but the Docker container still contains the old version.

## Solution

**Option 1: Rebuild Container (Recommended)**
```bash
docker-compose build ai-automation-service
docker-compose up -d ai-automation-service
```

**Option 2: Copy Files to Running Container**
```bash
docker cp services/ai-automation-service/scripts/generate_synthetic_homes.py ai-automation-service:/app/scripts/
docker cp services/ai-automation-service/scripts/train_home_type_classifier.py ai-automation-service:/app/scripts/
```

---

## Execution Steps

### Step 1: Rebuild Container
```bash
docker-compose build ai-automation-service
docker-compose up -d ai-automation-service
```

### Step 2: Test Generation (5 homes)
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 5 --output tests/datasets/synthetic_homes --days 90"
```

**Note:** 90 days of events per home for better training data quality

### Step 3: Verify Test Results
- Check that 5 homes were generated
- Verify each home has areas, devices, and events
- Check file sizes and structure

### Step 4: Full Generation (100 homes)
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 100 --output tests/datasets/synthetic_homes --days 90"
```

**Expected Time:** 26-52 hours (90 days of events per home)  
**Expected Cost:** $10-50 (OpenAI API) - Home generation cost unchanged  
**Note:** 90 days provides much richer training data with seasonal patterns, weekly cycles, and long-term behavior

### Step 5: Train Model
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/train_home_type_classifier.py --synthetic-homes tests/datasets/synthetic_homes --output models/home_type_classifier.pkl --test-size 0.2"
```

**Expected Time:** 5-10 minutes

### Step 6: Verify Model
- Check model file exists: `models/home_type_classifier.pkl`
- Check results file: `models/home_type_classifier_results.json`
- Verify accuracy >85%

---

## Files Updated

1. ✅ `services/ai-automation-service/scripts/generate_synthetic_homes.py`
   - Fixed imports: `from src.config`, `from src.llm.openai_client`, etc.

2. ✅ `services/ai-automation-service/scripts/train_home_type_classifier.py`
   - Fixed imports: `from src.home_type.home_type_classifier`

---

## Next Steps

1. Rebuild Docker container
2. Run test generation (5 homes)
3. Verify test results
4. Run full generation (100 homes)
5. Train model
6. Verify model performance

---

**Status:** Scripts updated, ready for container rebuild and execution

