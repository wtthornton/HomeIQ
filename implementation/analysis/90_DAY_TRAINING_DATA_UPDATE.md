# 90-Day Training Data Update

**Date:** November 2025  
**Status:** ✅ Updated  
**Change:** Training data generation increased from 7 days to 90 days per home

---

## Change Summary

**Previous:** 7 days of events per synthetic home  
**New:** 90 days of events per synthetic home  
**Impact:** ~13x more training data per home

---

## Benefits of 90-Day Data

### 1. **Seasonal Patterns**
- Capture seasonal behavior changes
- Temperature/climate variations
- Daylight hour changes affecting lighting patterns

### 2. **Weekly Cycles**
- Multiple full weeks (12-13 weeks)
- Weekend vs weekday patterns
- Long-term habit formation

### 3. **Behavioral Patterns**
- Long-term device usage trends
- Gradual changes in automation patterns
- More realistic event distributions

### 4. **Model Training Quality**
- More robust feature extraction
- Better generalization
- Reduced overfitting risk

---

## Impact Analysis

### Generation Time

**Previous (7 days):**
- 2-4 hours for 100 homes
- ~1.2-2.4 minutes per home

**New (90 days):**
- 26-52 hours for 100 homes (estimated)
- ~15.6-31.2 minutes per home
- **13x increase** in generation time

### Storage

**Previous (7 days):**
- ~1MB total for 100 homes
- ~10KB per home

**New (90 days):**
- ~13MB total for 100 homes (estimated)
- ~130KB per home
- **13x increase** in storage

### Cost

**OpenAI API Cost:**
- **Unchanged** - Home generation (LLM calls) cost is the same
- Only event generation increases (local computation, no API calls)

### Training Quality

**Improvements:**
- ✅ More robust feature extraction
- ✅ Better temporal pattern recognition
- ✅ Improved model generalization
- ✅ Reduced overfitting

---

## Updated Commands

### Test Generation (5 homes, 90 days)
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 5 --output tests/datasets/synthetic_homes --days 90"
```

### Full Generation (100 homes, 90 days)
```bash
docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 100 --output tests/datasets/synthetic_homes --days 90"
```

**Note:** Default is now 90 days, so `--days 90` is optional.

---

## Event Generation Details

### Event Frequency (per device type, per day)
- Lights: ~11 events/day
- Binary sensors: ~36 events/day
- Sensors: ~26 events/day
- Switches: ~5 events/day
- Climate: ~8 events/day

### Total Events per Home (90 days)
**Small home (15 devices):**
- ~15 devices × 20 events/day × 90 days = **27,000 events**

**Medium home (30 devices):**
- ~30 devices × 20 events/day × 90 days = **54,000 events**

**Large home (50 devices):**
- ~50 devices × 20 events/day × 90 days = **90,000 events**

**Average per home:** ~57,000 events (90 days)

---

## Training Data Statistics

### With 100 Homes, 90 Days Each:

**Total Events:**
- ~5.7 million events
- Rich temporal patterns
- Seasonal variations
- Weekly cycles

**Feature Extraction:**
- Daily patterns (24 hours × 90 days = 2,160 hourly bins)
- Weekly patterns (7 days × 12-13 weeks)
- Seasonal trends (90 days = ~3 months)

**Model Training:**
- More robust feature vectors
- Better temporal understanding
- Improved classification accuracy

---

## Recommendations

### 1. **Batch Processing**
Run generation in batches to avoid timeouts:
```bash
# Generate 20 homes at a time
for i in {1..5}; do
  docker-compose exec ai-automation-service bash -c "cd /app && PYTHONPATH=/app python scripts/generate_synthetic_homes.py --count 20 --output tests/datasets/synthetic_homes --days 90 --start-index $((($i-1)*20+1))"
done
```

### 2. **Progress Monitoring**
Monitor generation progress:
```bash
# Check number of homes generated
docker-compose exec ai-automation-service ls -1 tests/datasets/synthetic_homes/home_*.json | wc -l

# Check total events generated
docker-compose exec ai-automation-service bash -c "grep -h '\"events\"' tests/datasets/synthetic_homes/home_*.json | wc -l"
```

### 3. **Storage Management**
Ensure sufficient disk space:
- 100 homes × 90 days ≈ 13MB
- Plus model files: ~5MB
- Total: ~20MB (manageable)

---

## Updated Timeline

### Phase 1: Test Generation (5 homes)
- **Time:** 1.5-3 hours
- **Purpose:** Verify generation pipeline

### Phase 2: Full Generation (100 homes)
- **Time:** 26-52 hours (1-2 days)
- **Purpose:** Complete training dataset

### Phase 3: Model Training
- **Time:** 5-10 minutes
- **Purpose:** Train classifier on 90-day data

### Phase 4: Evaluation
- **Time:** 5 minutes
- **Purpose:** Verify model performance

**Total Time:** ~1.5-2.5 days

---

## Status

✅ **Scripts Updated:**
- `generate_synthetic_homes.py` - Default changed to 90 days
- All documentation updated

✅ **Ready for Execution:**
- Rebuild container
- Run test generation
- Run full generation
- Train model

---

**Status:** ✅ Updated and Ready  
**Next Step:** Rebuild container and begin generation

