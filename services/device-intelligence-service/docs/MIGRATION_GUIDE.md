# ML Model Migration Guide

**Last Updated:** December 2025  
**Purpose:** Guide for migrating from old models to new 2025 improvements

## Overview

This guide helps you migrate from the current RandomForest-based system to the new improved models (LightGBM, TabPFN, Incremental Learning).

## Pre-Migration Checklist

- [ ] Backup current models
- [ ] Review current model performance
- [ ] Test new models in development
- [ ] Plan migration window
- [ ] Prepare rollback plan

## Migration Steps

### Step 1: Backup Current Models

```bash
# Backup model files
cd services/device-intelligence-service
cp -r models models_backup_$(date +%Y%m%d)

# Backup metadata
cp models/model_metadata.json models/model_metadata.json.backup
```

### Step 2: Install New Dependencies

```bash
# Update requirements
pip install -r requirements.txt

# Verify installations
python -c "import lightgbm; print(lightgbm.__version__)"
python -c "import tabpfn; print(tabpfn.__version__)"
python -c "import river; print(river.__version__)"
```

### Step 3: Test New Models

```bash
# Compare models on same dataset
python scripts/compare_models.py --output comparison_results.json

# Review results
cat comparison_results.json
```

### Step 4: Choose Migration Path

#### Option A: Gradual Migration (Recommended)

1. Keep RandomForest as default
2. Test LightGBM/TabPFN in staging
3. Switch one service at a time
4. Monitor performance

#### Option B: Direct Migration

1. Set new model as default
2. Retrain immediately
3. Monitor closely for issues

### Step 5: Update Configuration

#### For LightGBM:

```bash
# .env or docker-compose.yml
ML_FAILURE_MODEL=lightgbm
```

#### For TabPFN:

```bash
ML_FAILURE_MODEL=tabpfn
```

#### For Incremental Learning:

```bash
ML_FAILURE_MODEL=randomforest  # or lightgbm
ML_USE_INCREMENTAL=true
ML_INCREMENTAL_UPDATE_THRESHOLD=100
```

### Step 6: Retrain Models

```bash
# Force retrain with new model
curl -X POST http://localhost:8028/api/predictions/train \
  -H "Content-Type: application/json" \
  -d '{"force_retrain": true, "days_back": 180}'
```

### Step 7: Verify Performance

```bash
# Check model status
curl http://localhost:8028/api/predictions/models/status

# Verify accuracy is acceptable
# Compare with baseline metrics
```

### Step 8: Monitor

- Monitor accuracy for 24-48 hours
- Check training times
- Verify predictions are reasonable
- Watch for errors

## Rollback Procedure

If issues occur:

### Quick Rollback

```bash
# 1. Revert environment variable
ML_FAILURE_MODEL=randomforest

# 2. Restore backup models
cp -r models_backup_YYYYMMDD/* models/

# 3. Restart service
docker compose restart device-intelligence-service
```

### Full Rollback

1. Revert code changes (git)
2. Restore backup models
3. Restart services
4. Investigate issues
5. Fix before retrying

## Migration Scenarios

### Scenario 1: Migrate to LightGBM

**Timeline:** 1-2 hours

1. Set `ML_FAILURE_MODEL=lightgbm`
2. Restart service
3. Retrain models
4. Verify 2-5x speedup
5. Monitor accuracy

**Expected Results:**
- Training time: 1-5s → 0.5-1s
- Accuracy: Similar or better
- No code changes needed

### Scenario 2: Migrate to TabPFN

**Timeline:** 1 hour

1. Set `ML_FAILURE_MODEL=tabpfn`
2. Restart service
3. Retrain models (instant)
4. Verify accuracy improvement

**Expected Results:**
- Training time: 1-5s → <1s
- Accuracy: 85-95% → 90-98%
- Best for ≤10,000 samples

### Scenario 3: Enable Incremental Learning

**Timeline:** 2-3 hours

1. Set `ML_USE_INCREMENTAL=true`
2. Restart service
3. Initial training (uses incremental model)
4. Test incremental updates
5. Set up daily update schedule

**Expected Results:**
- Daily updates: 1-5s → 0.1-0.5s
- Accuracy maintained
- Real-time adaptation

### Scenario 4: Full Migration (All Improvements)

**Timeline:** 1 day

1. Update all dependencies
2. Enable PyTorch compile (automatic)
3. Update TabPFN to v2.5
4. Migrate to LightGBM or TabPFN
5. Enable incremental learning
6. Test thoroughly
7. Deploy to production

## Testing Checklist

After migration, verify:

- [ ] Models train successfully
- [ ] Training time improved
- [ ] Accuracy maintained or improved
- [ ] Predictions work correctly
- [ ] API endpoints respond
- [ ] No errors in logs
- [ ] Memory usage acceptable
- [ ] Incremental updates work (if enabled)

## Common Issues

### Issue: Model Not Loading

**Symptoms:** Service starts but predictions fail

**Solutions:**
1. Check model files exist
2. Verify model version compatibility
3. Retrain models
4. Check logs for errors

### Issue: Accuracy Degraded

**Symptoms:** Predictions less accurate

**Solutions:**
1. Compare with baseline
2. Check data quality
3. Try different model type
4. Retrain with more data

### Issue: Training Slower Than Expected

**Symptoms:** Training time not improved

**Solutions:**
1. Verify model type is correct
2. Check dataset size
3. Verify dependencies installed
4. Check system resources

## Post-Migration

### Week 1: Monitoring

- Daily accuracy checks
- Monitor training times
- Review error logs
- Compare with baseline

### Week 2-4: Optimization

- Fine-tune thresholds
- Adjust update frequency
- Optimize data collection
- Document learnings

### Month 2+: Maintenance

- Regular model retraining
- Performance reviews
- Update documentation
- Plan next improvements

## Support

For issues or questions:
1. Check logs: `docker compose logs device-intelligence-service`
2. Review model status: `GET /api/predictions/models/status`
3. Check metrics: `models/metrics/metrics_history.json`
4. Consult documentation: [ML_IMPROVEMENTS_GUIDE.md](ML_IMPROVEMENTS_GUIDE.md)

---

**Last Updated:** December 2025  
**Version:** 1.0

