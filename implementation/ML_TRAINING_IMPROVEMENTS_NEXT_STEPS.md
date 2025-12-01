# ML Training Improvements - Next Steps

**Date:** December 2025  
**Status:** Implementation Complete - Ready for Testing & Deployment

---

## Current Status

✅ **Implementation:** Complete  
✅ **Code Review:** Passed  
✅ **2025 Best Practices Review:** Aligned  
✅ **Documentation:** Complete

---

## Next Steps (Recommended Order)

### Step 1: Local Testing & Validation (1-2 hours)

**Purpose:** Verify all improvements work correctly before deployment

#### 1.1 Test Model Comparison

```bash
cd services/device-intelligence-service
python scripts/compare_models.py
```

**Expected Results:**
- RandomForest: Baseline (1-5s training, 85-95% accuracy)
- LightGBM: 2-5x faster training, similar/better accuracy
- TabPFN: 5-10x faster training, 90-98% accuracy

**What to Check:**
- ✅ All models train successfully
- ✅ Training times match expectations
- ✅ Accuracy metrics are reasonable
- ✅ No errors in logs

#### 1.2 Test Incremental Learning

```bash
cd services/device-intelligence-service
python scripts/test_incremental_learning.py
```

**Expected Results:**
- Full retrain: 1-5 seconds
- Incremental update: 0.1-0.5 seconds (10-50x faster)
- Accuracy maintained within 2% of full retrain

**What to Check:**
- ✅ Incremental updates work
- ✅ Speed improvement is significant
- ✅ Accuracy doesn't degrade
- ✅ Memory buffer prevents forgetting

#### 1.3 Test GNN Compile (if GNN is used)

```bash
# Check if GNN training is faster
# Monitor logs during synergy detection training
```

**Expected Results:**
- 1.5-2x faster GNN training
- No accuracy degradation
- Compilation message in logs

---

### Step 2: Test Environment Deployment (2-4 hours)

**Purpose:** Deploy to test environment and validate end-to-end

#### 2.1 Update Environment Variables

**In `.env` or `docker-compose.yml`:**

```bash
# Start with RandomForest (default, most stable)
ML_FAILURE_MODEL=randomforest
ML_USE_INCREMENTAL=false
GNN_USE_COMPILE=true

# Or test LightGBM
ML_FAILURE_MODEL=lightgbm
ML_USE_INCREMENTAL=false
GNN_USE_COMPILE=true
```

#### 2.2 Deploy Services

```bash
# Rebuild and restart device-intelligence-service
docker compose build device-intelligence-service
docker compose up -d device-intelligence-service

# Rebuild and restart ai-automation-service (for GNN compile)
docker compose build ai-automation-service
docker compose up -d ai-automation-service
```

#### 2.3 Verify Services Start

```bash
# Check health endpoints
curl http://localhost:8028/health
curl http://localhost:8001/health

# Check logs for errors
docker compose logs device-intelligence-service | tail -50
docker compose logs ai-automation-service | tail -50
```

#### 2.4 Train Models

```bash
# Trigger model training
curl -X POST http://localhost:8028/api/predictions/train \
  -H "Content-Type: application/json" \
  -d '{"force_retrain": true, "days_back": 180}'
```

**What to Check:**
- ✅ Training completes successfully
- ✅ Models are saved
- ✅ Training time is reasonable
- ✅ Model status endpoint shows trained models

#### 2.5 Test Predictions

```bash
# Get model status
curl http://localhost:8028/api/predictions/models/status

# Test prediction endpoint
curl -X POST http://localhost:8028/api/predictions/failure \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test_device",
    "metrics": {
      "response_time": 500,
      "error_rate": 0.05,
      "battery_level": 75
    }
  }'
```

---

### Step 3: Performance Benchmarking (1-2 hours)

**Purpose:** Establish baseline metrics and verify improvements

#### 3.1 Benchmark Training Times

**Test with different model types:**

```bash
# Test RandomForest
ML_FAILURE_MODEL=randomforest python scripts/compare_models.py --output rf_results.json

# Test LightGBM
ML_FAILURE_MODEL=lightgbm python scripts/compare_models.py --output lgbm_results.json

# Test TabPFN
ML_FAILURE_MODEL=tabpfn python scripts/compare_models.py --output tabpfn_results.json
```

**Record:**
- Training time
- Accuracy, precision, recall, F1
- Memory usage
- CPU usage

#### 3.2 Compare Results

**Create comparison table:**

| Model | Training Time | Accuracy | Precision | Recall | F1 | Memory |
|-------|---------------|----------|-----------|--------|-----|--------|
| RandomForest | | | | | | |
| LightGBM | | | | | | |
| TabPFN | | | | | | |

#### 3.3 Document Findings

**Update `ML_IMPROVEMENTS_GUIDE.md` with actual results:**
- Real training times from your environment
- Actual accuracy metrics
- Resource usage patterns

---

### Step 4: Gradual Migration (1-2 weeks)

**Purpose:** Migrate from RandomForest to improved models gradually

#### 4.1 Week 1: LightGBM Testing

**Day 1-2:**
- Enable LightGBM in test environment
- Monitor for 48 hours
- Compare predictions with RandomForest

**Day 3-4:**
- If stable, enable in production
- Keep RandomForest as fallback
- Monitor closely

**Day 5-7:**
- Full week of production monitoring
- Document any issues
- Verify performance improvements

#### 4.2 Week 2: TabPFN or Incremental Learning

**Option A: TabPFN (if dataset is small)**
- Enable TabPFN for specific use cases
- Monitor accuracy improvements
- Expand gradually

**Option B: Incremental Learning (if frequent updates needed)**
- Enable incremental learning
- Test daily updates
- Monitor for catastrophic forgetting
- Verify speed improvements

---

### Step 5: Production Monitoring (Ongoing)

**Purpose:** Ensure improvements maintain quality over time

#### 5.1 Monitor Metrics

**Track weekly:**
- Model accuracy trends
- Training times
- Prediction latency
- Error rates
- Resource usage

#### 5.2 Set Up Alerts

**Configure alerts for:**
- Accuracy degradation (>5% drop)
- Training failures
- Prediction errors
- Resource spikes

#### 5.3 Regular Reviews

**Monthly review:**
- Compare model performance
- Review training times
- Assess resource usage
- Plan optimizations

---

## Quick Start (Fast Track)

**If you want to test quickly:**

```bash
# 1. Test model comparison (5-10 minutes)
cd services/device-intelligence-service
python scripts/compare_models.py

# 2. Test incremental learning (2-3 minutes)
python scripts/test_incremental_learning.py

# 3. Deploy with LightGBM (10-15 minutes)
# Update docker-compose.yml:
#   ML_FAILURE_MODEL=lightgbm
docker compose build device-intelligence-service
docker compose up -d device-intelligence-service

# 4. Train and verify (5-10 minutes)
curl -X POST http://localhost:8028/api/predictions/train \
  -H "Content-Type: application/json" \
  -d '{"force_retrain": true}'
curl http://localhost:8028/api/predictions/models/status
```

**Total time: ~30-40 minutes**

---

## Rollback Plan

**If issues occur:**

1. **Revert to RandomForest:**
   ```bash
   ML_FAILURE_MODEL=randomforest
   docker compose restart device-intelligence-service
   ```

2. **Disable Incremental Learning:**
   ```bash
   ML_USE_INCREMENTAL=false
   docker compose restart device-intelligence-service
   ```

3. **Disable GNN Compile:**
   ```bash
   GNN_USE_COMPILE=false
   docker compose restart ai-automation-service
   ```

4. **Load Previous Models:**
   ```bash
   # Models are backed up automatically
   # Check models/ directory for backups
   ls -la services/device-intelligence-service/models/*.backup_*
   ```

---

## Success Criteria

**Phase 1 (Testing):**
- ✅ All models train successfully
- ✅ Training times match expectations
- ✅ Accuracy metrics are reasonable
- ✅ No errors in production logs

**Phase 2 (Deployment):**
- ✅ Services start without errors
- ✅ Models train in production
- ✅ Predictions work correctly
- ✅ Performance improvements verified

**Phase 3 (Monitoring):**
- ✅ Accuracy maintained over time
- ✅ Training times remain fast
- ✅ No catastrophic forgetting (if incremental)
- ✅ Resource usage acceptable

---

## Timeline Estimate

| Phase | Duration | Priority |
|-------|----------|----------|
| Local Testing | 1-2 hours | 🔴 High |
| Test Deployment | 2-4 hours | 🔴 High |
| Performance Benchmarking | 1-2 hours | 🟡 Medium |
| Gradual Migration | 1-2 weeks | 🟡 Medium |
| Production Monitoring | Ongoing | 🟢 Low |

**Total initial time:** 4-8 hours  
**Full migration:** 1-2 weeks

---

## Questions or Issues?

**If you encounter problems:**

1. Check logs: `docker compose logs device-intelligence-service`
2. Review documentation: `services/device-intelligence-service/docs/ML_IMPROVEMENTS_GUIDE.md`
3. Check troubleshooting section in guide
4. Review error messages (they include "What/Why/How to Fix")

---

**Last Updated:** December 2025  
**Status:** Ready for Testing

