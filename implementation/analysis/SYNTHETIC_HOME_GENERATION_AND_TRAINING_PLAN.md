# Synthetic Home Generation and Model Training Plan

**Date:** November 2025  
**Status:** Ready for Execution  
**Purpose:** Generate 100-120 synthetic homes and train the home type classifier model

---

## Overview

This plan executes the synthetic home generation and model training phase of the Home Type Categorization System.

**Pipeline:**
1. Generate 100-120 synthetic homes (template-based, no LLM required)
2. Generate areas, devices, and events for each home
3. Extract features from synthetic homes
4. Train RandomForest classifier
5. Evaluate and save model

---

## Phase 1: Synthetic Home Generation

### 1.1 Prerequisites

- ✅ Output directory: `services/ai-automation-service/tests/datasets/synthetic_homes`
- ✅ Model directory: `services/ai-automation-service/models`
- ✅ No external API keys required (template-based generation)

### 1.2 Generation Strategy

**Home Distribution (100 homes):**
- Single-family house: 30 homes (30%)
- Apartment: 20 homes (20%)
- Condo: 15 homes (15%)
- Townhouse: 10 homes (10%)
- Cottage: 10 homes (10%)
- Studio: 5 homes (5%)
- Multi-story: 5 homes (5%)
- Ranch house: 5 homes (5%)

**Size Distribution:**
- Small (10-20 devices): 30 homes (30%)
- Medium (20-40 devices): 40 homes (40%)
- Large (40-60 devices): 20 homes (20%)
- Extra-large (60+ devices): 10 homes (10%)

### 1.3 Generation Command

```bash
cd services/ai-automation-service
python scripts/generate_synthetic_homes.py \
    --count 100 \
    --output tests/datasets/synthetic_homes \
    --days 90
```

**Expected Output:**
- 100 JSON files: `home_001.json` through `home_100.json`
- Each file contains: home metadata, areas, devices, events (90 days)

**Estimated Time:** 10-30 minutes (template-based, no API calls)  
**Note:** With 90 days of events per home, event generation adds ~5-15 minutes total  
**Estimated Cost:** $0 (no API calls required) - Template-based generation is free

### 1.4 Validation

After generation, verify:
- ✅ All 100 homes generated
- ✅ Each home has areas, devices, events
- ✅ Home types match distribution
- ✅ Device counts match size distribution

---

## Phase 2: Model Training

### 2.1 Training Process

**Training Command:**
```bash
cd services/ai-automation-service
python scripts/train_home_type_classifier.py \
    --synthetic-homes tests/datasets/synthetic_homes \
    --output models/home_type_classifier.pkl \
    --test-size 0.2
```

**Training Steps:**
1. Load all synthetic homes
2. Extract features using `HomeTypeFeatureExtractor`
3. Generate labels from home types
4. Split train/test (80/20)
5. Train RandomForest classifier
6. Evaluate with cross-validation
7. Save model and results

**Expected Output:**
- Model: `models/home_type_classifier.pkl`
- Results: `models/home_type_classifier_results.json`
- Metrics: Accuracy, F1, Precision, Recall

**Estimated Time:** 5-10 minutes
**Model Size:** <5MB

### 2.2 Model Evaluation

**Target Metrics:**
- Accuracy: >85%
- F1 Score: >0.80
- Per-class precision: >0.75

**Evaluation Output:**
- Classification report
- Confusion matrix
- Feature importance
- Cross-validation scores

---

## Phase 3: Verification

### 3.1 Model Loading Test

```python
from src.home_type.home_type_classifier import FineTunedHomeTypeClassifier

classifier = FineTunedHomeTypeClassifier(
    model_path='models/home_type_classifier.pkl'
)
```

### 3.2 Inference Test

Test on sample synthetic homes:
- Load 5-10 sample homes
- Extract features
- Run inference
- Verify predictions match expected home types

---

## Execution Checklist

- [ ] Create output directories
- [ ] Run synthetic home generation (100 homes)
- [ ] Verify all homes generated successfully
- [ ] Run model training
- [ ] Verify model saved successfully
- [ ] Check training metrics (accuracy, F1)
- [ ] Test model loading
- [ ] Test inference on sample homes
- [ ] Document results

---

## Expected Results

**Synthetic Homes:**
- 100 complete homes with areas, devices, events
- JSON files in `tests/datasets/synthetic_homes/`
- Total size: ~1MB

**Trained Model:**
- Model file: `models/home_type_classifier.pkl`
- Accuracy: >85%
- Ready for Docker deployment

**Training Results:**
- Results file: `models/home_type_classifier_results.json`
- Metrics and feature importance documented

---

## Next Steps After Training

1. **Docker Build:** Model will be included in Docker image
2. **API Endpoint:** `/api/home-type/classify` will be active
3. **Integration:** All home type features will be fully operational

---

**Status:** Ready for execution  
**Estimated Total Time:** 10-30 minutes (generation) + 10 minutes (training)  
**Estimated Total Cost:** $0 (template-based generation, no API calls)

