# Production Readiness Report

**Generated:** 2025-12-02T21:36:44.608753

---

## Overall Status

❌ **NOT PRODUCTION READY** (Critical components failed)

---

## 1. Build Status

- **Status:** ✅ PASSED

---

## 2. Deployment Status

- **Status:** ✅ PASSED

---

## 3. Smoke Test Results

- **Status:** Not run

---

## 4. Test Data Generation

- **Status:** ✅ PASSED

---

## 5. Model Training Results

### Critical Models (Required for Production)

#### Home Type

- **Status:** ✅ PASSED
- **Type:** 🔴 CRITICAL
- **Quality:** ✅ All thresholds met
- **Metrics:**
  - accuracy: 0.9532710280373832
  - precision: 0.9535383335973389
  - recall: 0.9532710280373832
  - f1_score: 0.9533206297767509
  - cv_accuracy_mean: 0.9788235294117648
  - cv_accuracy_std: 0.026201244060376567
  - accuracy: 0.9532710280373832
  - training_samples: 425
  - test_samples: 107

#### Device Intelligence

- **Status:** ✅ PASSED
- **Type:** 🔴 CRITICAL
- **Quality:** ✅ All thresholds met
- **Metrics:**
  - accuracy: 1.0
  - precision: 1.0
  - recall: 1.0
  - f1_score: 1.0
  - training_duration_seconds: 0.220304

### Optional Models (Enhancements)

#### Gnn Synergy

- **Status:** ⚠️ NOT CONFIGURED
- **Type:** 🟡 OPTIONAL
- **Note:** Optional enhancement - not required for production deployment

#### Soft Prompt

- **Status:** ⚠️ NOT CONFIGURED
- **Type:** 🟡 OPTIONAL
- **Note:** Optional enhancement - not required for production deployment

---

## 6. Model Manifest

- **Generated:** 2025-12-02T21:36:44.605780

### Models Saved

#### Home Type Classifier

- **model:** C:\cursor\HomeIQ\services\ai-automation-service\models\home_type_classifier.pkl
- **metadata:** C:\cursor\HomeIQ\services\ai-automation-service\models\home_type_classifier_metadata.json
- **results:** C:\cursor\HomeIQ\services\ai-automation-service\models\home_type_classifier_results.json
- **size_bytes:** 501686

#### Device Intelligence

- **failure_model:** C:\cursor\HomeIQ\services\device-intelligence-service\models\failure_prediction_model.pkl
- **anomaly_model:** C:\cursor\HomeIQ\services\device-intelligence-service\models\anomaly_detection_model.pkl
- **metadata:** C:\cursor\HomeIQ\services\device-intelligence-service\models\model_metadata.json
- **failure_size_bytes:** 339353
- **anomaly_size_bytes:** 1164136

---

## 7. Production Readiness Checklist

- ✅ Build completed successfully
- ✅ Services deployed and running
- ❌ All critical smoke tests passed
- ✅ Test data generated
- ✅ Home type classifier trained
- ✅ Device intelligence models trained
- ✅ Models saved and verified

---

## Next Steps

1. Review failed steps above
2. Fix critical issues
3. Re-run this script
