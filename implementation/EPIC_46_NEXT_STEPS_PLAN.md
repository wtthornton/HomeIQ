# Epic 46 Next Steps Implementation Plan

**Date:** December 1, 2025  
**Status:** Planning Complete - Ready for Implementation

## Overview

Implementing all 4 next steps with 2025 patterns and versions:
1. Test home-type-specific models
2. Scale up to 10,000+ samples
3. Add temporal patterns
4. Deploy to production

## Technology Stack Verification (2025)

### ✅ Current Versions (All 2025-Compliant)
- **Python:** 3.11+ (2025 standard)
- **scikit-learn:** 1.5.0+ (stable 2025)
- **pandas:** 2.2.0+ (stable 2025)
- **numpy:** 1.26.0+ (CPU-only compatible, 2025)
- **FastAPI:** 0.115.0+ (stable 2025)
- **Pydantic:** 2.12.4 (stable 2025)
- **LightGBM:** 4.0.0+ (2025 improvement - 2-5x faster)
- **TabPFN:** 2.5.0+ (2025 improvement - 5-10x faster)
- **River:** 0.21.0+ (2025 incremental learning)
- **APScheduler:** 3.10.0+ (2025 stable)

## Implementation Plan

### Step 1: Test Home-Type-Specific Models

**Goal:** Train separate models per home type and compare performance

**Approach:**
- Load home-type-specific datasets (500 samples each)
- Train 8 separate models (one per home type)
- Compare performance metrics across home types
- Identify home-type-specific failure patterns
- Generate comparison report

**2025 Patterns:**
- Use scikit-learn 1.5.0+ RandomForestClassifier
- Use joblib for model persistence
- Use pandas 2.2.0+ for data manipulation
- Type hints throughout (PEP 484/526)

**Files to Create:**
- `scripts/train_home_type_models.py` - Batch training script
- `scripts/compare_home_type_models.py` - Comparison analysis
- `data/models/home_type_models/` - Directory for home-type models

### Step 2: Scale Up to 10,000+ Samples

**Goal:** Generate 10,000+ samples for advanced training

**Approach:**
- Generate 10,000 samples with diverse home types
- Mix home types proportionally (realistic distribution)
- Train production model on larger dataset
- Compare performance vs 5,000 sample model

**2025 Patterns:**
- Use numpy 1.26.0+ for efficient array operations
- Use pandas 2.2.0+ for data manipulation
- Memory-efficient generation (batch processing)
- Progress tracking with logging

**Files to Create:**
- `scripts/generate_large_dataset.py` - Large-scale generation
- `data/synthetic_datasets/large_training_data.json` - 10,000+ samples

### Step 3: Add Temporal Patterns

**Goal:** Add seasonal, weekly, and daily variations to synthetic data

**Approach:**
- Enhance `_generate_realistic_value()` with temporal patterns
- Add seasonal variation (winter/summer patterns)
- Add weekly patterns (weekday vs weekend)
- Add daily patterns (morning/evening peaks)
- Update generator to support temporal context

**2025 Patterns:**
- Use datetime.timezone for timezone-aware dates (2025 standard)
- Use numpy for efficient temporal calculations
- Type hints for all temporal parameters
- Configurable temporal patterns

**Files to Modify:**
- `src/training/synthetic_device_generator.py` - Add temporal patterns
- `scripts/generate_synthetic_devices.py` - Add temporal options

### Step 4: Deploy to Production

**Goal:** Integrate trained model into device intelligence service

**Approach:**
- Verify model loading in service startup
- Add health check endpoint for model status
- Add model version endpoint
- Update Docker image to include pre-trained models
- Add model refresh capability via API

**2025 Patterns:**
- FastAPI 0.115.0+ async endpoints
- Pydantic 2.12.4 for request/response validation
- Type hints throughout
- Proper error handling
- Logging with structured format

**Files to Modify:**
- `src/main.py` - Add model health check
- `src/api/predictions_router.py` - Add model status endpoints
- `Dockerfile` - Include models in image
- `docker-compose.yml` - Verify model volume mounts

## Implementation Order

1. **Step 3: Temporal Patterns** (Foundation)
   - Enhances data generation quality
   - Needed for better training data

2. **Step 2: Scale Up** (Data Generation)
   - Uses enhanced temporal patterns
   - Generates large dataset

3. **Step 1: Home-Type Models** (Analysis)
   - Uses scaled-up data
   - Trains specialized models

4. **Step 4: Production Deployment** (Integration)
   - Uses all trained models
   - Final integration step

## Success Criteria

- ✅ All 4 steps implemented
- ✅ 2025 patterns and versions used throughout
- ✅ Type hints and documentation complete
- ✅ All tests passing
- ✅ Production-ready deployment

## Timeline

- **Step 3:** ~30 minutes (temporal patterns)
- **Step 2:** ~15 minutes (large dataset generation)
- **Step 1:** ~45 minutes (home-type model training)
- **Step 4:** ~30 minutes (production integration)
- **Total:** ~2 hours

