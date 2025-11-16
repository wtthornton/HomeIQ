# ML Model Update Plan
## Device Intelligence Service

**Created:** 2025-01-XX  
**Status:** Planning  
**Owner:** Development Team

---

## Executive Summary

This plan outlines the process for updating the Machine Learning models used by the Device Intelligence Service for predictive analytics (failure prediction and anomaly detection). The current models were trained with scikit-learn 1.7.2, but the service uses scikit-learn 1.4.2, causing version compatibility warnings.

---

## Current State Analysis

### Current Model Configuration
- **Models:** 
  - Failure Prediction Model (RandomForestClassifier)
  - Anomaly Detection Model (IsolationForest)
  - Feature Scalers (StandardScaler) for both models
- **Model Location:** `services/device-intelligence-service/models/`
- **Model Files:**
  - `failure_prediction_model.pkl`
  - `anomaly_detection_model.pkl`
  - `failure_prediction_scaler.pkl`
  - `anomaly_detection_scaler.pkl`

### Current Dependencies
- **scikit-learn:** 1.4.2 (in requirements.txt)
- **pandas:** 2.3.3
- **numpy:** 2.3.4
- **joblib:** 1.4.2

### Issues Identified
1. **Version Mismatch:** Models trained with scikit-learn 1.7.2, but service uses 1.4.2
2. **Training Data:** Currently uses synthetic sample data instead of real historical metrics
3. **No Model Versioning:** No tracking of model versions or training metadata
4. **Limited Training Data Collection:** `_collect_training_data()` generates sample data instead of querying database

### Available Training Infrastructure
- **API Endpoint:** `POST /api/predictions/train` (exists in `predictions_router.py`)
- **Database Tables:** `DeviceHealthMetric` table stores historical metrics
- **Training Method:** `train_models()` in `predictive_analytics.py`

---

## Objectives

1. **Resolve Version Compatibility:** Update scikit-learn to match model training version or retrain with current version
2. **Use Real Training Data:** Collect historical metrics from `DeviceHealthMetric` table
3. **Implement Model Versioning:** Track model versions, training dates, and performance metrics
4. **Improve Training Process:** Create robust training pipeline with validation and testing
5. **Documentation:** Document the training and update process for future maintenance

---

## Implementation Plan

### Phase 1: Dependency Update and Compatibility Check

#### Task 1.1: Update scikit-learn Version
- **Action:** Update `requirements.txt` to use scikit-learn 1.7.2 (or latest stable)
- **Files:** `services/device-intelligence-service/requirements.txt`
- **Risk:** Low - scikit-learn maintains backward compatibility for model loading
- **Validation:** Verify existing models can be loaded with new version

#### Task 1.2: Update Related Dependencies
- **Action:** Ensure pandas, numpy, and joblib versions are compatible
- **Files:** `services/device-intelligence-service/requirements.txt`
- **Validation:** Test model loading and prediction with updated versions

#### Task 1.3: Test Existing Models
- **Action:** Load existing models with new scikit-learn version
- **Validation:** Verify no errors and predictions work correctly

**Deliverable:** Updated requirements.txt with compatible versions

---

### Phase 2: Real Training Data Collection

#### Task 2.1: Update `_collect_training_data()` Method
- **Action:** Query `DeviceHealthMetric` table for historical data
- **Files:** `services/device-intelligence-service/src/core/predictive_analytics.py`
- **Requirements:**
  - Query metrics from last 90-180 days
  - Aggregate metrics by device and time window
  - Extract features matching `feature_columns`:
    - `response_time`, `error_rate`, `battery_level`, `signal_strength`
    - `usage_frequency`, `temperature`, `humidity`, `uptime_hours`
    - `restart_count`, `connection_drops`, `data_transfer_rate`
  - Handle missing data gracefully
  - Return minimum 100 samples for training

#### Task 2.2: Create Database Query Helper
- **Action:** Create helper function to query and aggregate device metrics
- **Files:** `services/device-intelligence-service/src/core/predictive_analytics.py`
- **Functionality:**
  - Query `DeviceHealthMetric` table
  - Group by device_id and time windows
  - Calculate aggregated features (mean, max, min, std)
  - Join with `Device` table for device metadata
  - Filter for relevant time periods

#### Task 2.3: Add Training Data Validation
- **Action:** Validate training data quality before training
- **Requirements:**
  - Minimum sample count check (100+ samples)
  - Feature completeness check
  - Data quality checks (no NaN, reasonable ranges)
  - Log data statistics (sample count, date range, device count)

**Deliverable:** Updated training data collection using real database metrics

---

### Phase 3: Model Versioning and Metadata

#### Task 3.1: Create Model Metadata Structure
- **Action:** Add model metadata tracking
- **Files:** `services/device-intelligence-service/src/core/predictive_analytics.py`
- **Metadata Fields:**
  - Model version (semantic versioning: MAJOR.MINOR.PATCH)
  - Training date/time
  - Training data statistics (sample count, date range, device count)
  - Model performance metrics (accuracy, precision, recall, F1)
  - scikit-learn version used
  - Feature columns used
  - Training parameters (n_estimators, max_depth, contamination, etc.)

#### Task 3.2: Save Model Metadata
- **Action:** Save metadata JSON file alongside models
- **Files:** `services/device-intelligence-service/src/core/predictive_analytics.py`
- **File:** `models/model_metadata.json`
- **Format:** JSON with all metadata fields

#### Task 3.3: Load and Display Model Metadata
- **Action:** Load metadata on model initialization
- **Files:** `services/device-intelligence-service/src/core/predictive_analytics.py`
- **API:** Update `get_model_status()` to include metadata

**Deliverable:** Model versioning and metadata tracking system

---

### Phase 4: Enhanced Training Pipeline

#### Task 4.1: Improve Training Process
- **Action:** Enhance `train_models()` method
- **Files:** `services/device-intelligence-service/src/core/predictive_analytics.py`
- **Improvements:**
  - Better error handling and logging
  - Training progress logging
  - Model validation before saving
  - Backup existing models before overwriting
  - Training time tracking

#### Task 4.2: Add Model Validation
- **Action:** Add validation checks after training
- **Requirements:**
  - Minimum performance thresholds (e.g., accuracy > 0.7)
  - Model file integrity checks
  - Prediction test on sample data
  - Comparison with previous model performance

#### Task 4.3: Create Training Script
- **Action:** Create standalone training script
- **Files:** `services/device-intelligence-service/scripts/train_models.py`
- **Functionality:**
  - Can be run independently or via API
  - Command-line arguments for configuration
  - Logging to file
  - Progress reporting
  - Error handling and rollback

**Deliverable:** Enhanced training pipeline with validation

---

### Phase 5: API Enhancements

#### Task 5.1: Enhance Training API Endpoint
- **Action:** Update `POST /api/predictions/train` endpoint
- **Files:** `services/device-intelligence-service/src/api/predictions_router.py`
- **Enhancements:**
  - Return training status and progress
  - Support training parameters (date range, sample count)
  - Return model metadata after training
  - Better error messages

#### Task 5.2: Add Model Status Endpoint
- **Action:** Enhance model status endpoint
- **Files:** `services/device-intelligence-service/src/api/predictions_router.py`
- **Response:** Include model metadata, version, performance metrics

#### Task 5.3: Add Model Comparison Endpoint
- **Action:** Compare current model with previous version
- **Files:** `services/device-intelligence-service/src/api/predictions_router.py`
- **Functionality:** Show performance differences, training data differences

**Deliverable:** Enhanced API endpoints for model management

---

### Phase 6: Testing and Validation

#### Task 6.1: Unit Tests
- **Action:** Create unit tests for training functions
- **Files:** `services/device-intelligence-service/tests/test_training.py`
- **Coverage:**
  - Training data collection
  - Model training
  - Model saving/loading
  - Model prediction
  - Metadata handling

#### Task 6.2: Integration Tests
- **Action:** Test full training pipeline
- **Files:** `services/device-intelligence-service/tests/test_integration.py`
- **Coverage:**
  - End-to-end training from database
  - Model deployment
  - Prediction accuracy
  - API endpoints

#### Task 6.3: Performance Tests
- **Action:** Test model performance on real data
- **Requirements:**
  - Accuracy benchmarks
  - Prediction latency
  - Memory usage
  - Training time

**Deliverable:** Comprehensive test suite

---

### Phase 7: Documentation

#### Task 7.1: Update README
- **Action:** Document model training process
- **Files:** `services/device-intelligence-service/README.md`
- **Sections:**
  - Model Training section
  - Training data requirements
  - How to retrain models
  - Model versioning

#### Task 7.2: Create Training Guide
- **Action:** Create detailed training guide
- **Files:** `services/device-intelligence-service/docs/MODEL_TRAINING_GUIDE.md`
- **Content:**
  - Step-by-step training instructions
  - Training data preparation
  - Model evaluation
  - Troubleshooting

#### Task 7.3: Update API Documentation
- **Action:** Document new/updated API endpoints
- **Files:** `services/device-intelligence-service/README.md`
- **Content:** API endpoint documentation with examples

**Deliverable:** Complete documentation

---

### Phase 8: Deployment

#### Task 8.1: Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Models trained and validated
- [ ] Documentation updated
- [ ] Version compatibility verified
- [ ] Backup of existing models

#### Task 8.2: Deployment Steps
1. Update requirements.txt
2. Build new Docker image
3. Test in development environment
4. Backup existing models
5. Deploy to production
6. Monitor model performance
7. Verify predictions are working

#### Task 8.3: Rollback Plan
- **Action:** Document rollback procedure
- **Requirements:**
  - Keep backup of previous models
  - Quick rollback to previous Docker image
  - Database rollback if needed

**Deliverable:** Successful deployment with monitoring

---

## Implementation Timeline

| Phase | Tasks | Estimated Time | Priority |
|-------|-------|----------------|----------|
| Phase 1 | Dependency Update | 2-4 hours | High |
| Phase 2 | Real Training Data | 8-12 hours | High |
| Phase 3 | Model Versioning | 4-6 hours | Medium |
| Phase 4 | Enhanced Training | 6-8 hours | High |
| Phase 5 | API Enhancements | 4-6 hours | Medium |
| Phase 6 | Testing | 8-12 hours | High |
| Phase 7 | Documentation | 4-6 hours | Medium |
| Phase 8 | Deployment | 4-6 hours | High |
| **Total** | | **40-60 hours** | |

---

## Risk Assessment

### High Risk
- **Model Performance Degradation:** New models may perform worse than existing
  - **Mitigation:** Validate performance before deployment, keep backups
- **Training Data Quality:** Insufficient or poor quality training data
  - **Mitigation:** Data validation, minimum sample requirements

### Medium Risk
- **Version Compatibility Issues:** scikit-learn version updates may cause issues
  - **Mitigation:** Test thoroughly, maintain backward compatibility
- **Database Query Performance:** Large training data queries may be slow
  - **Mitigation:** Optimize queries, add indexes, use pagination

### Low Risk
- **Deployment Issues:** Docker build or deployment problems
  - **Mitigation:** Test in development first, have rollback plan

---

## Success Criteria

1. ✅ Models trained with scikit-learn 1.7.2 (or latest stable)
2. ✅ Training uses real historical data from database
3. ✅ Model versioning and metadata tracking implemented
4. ✅ All tests passing
5. ✅ Model performance meets or exceeds current models
6. ✅ Documentation complete
7. ✅ Successfully deployed to production
8. ✅ No version compatibility warnings

---

## Next Steps

1. **Review and Approve Plan:** Get stakeholder approval
2. **Start Phase 1:** Update dependencies and test compatibility
3. **Set Up Development Environment:** Ensure database has sufficient training data
4. **Begin Implementation:** Follow phases sequentially

---

## References

- **Current Code:**
  - `services/device-intelligence-service/src/core/predictive_analytics.py`
  - `services/device-intelligence-service/src/api/predictions_router.py`
  - `services/device-intelligence-service/src/models/database.py`
- **Documentation:**
  - `services/device-intelligence-service/README.md`
- **Dependencies:**
  - scikit-learn: https://scikit-learn.org/
  - pandas: https://pandas.pydata.org/
  - joblib: https://joblib.readthedocs.io/

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Next Review:** After Phase 1 completion

