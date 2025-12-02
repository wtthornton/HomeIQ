# Epic AI-13: ML-Based Pattern Quality & Active Learning

**Epic ID:** AI-13  
**Title:** ML-Based Pattern Quality & Active Learning  
**Status:** 📋 **PLANNING**  
**Type:** Brownfield Enhancement (AI/ML Infrastructure)  
**Priority:** High (Critical Quality Blocker)  
**Effort:** 11 Stories (44 story points, 4-6 weeks estimated)  
**Created:** January 2025  
**Based On:** Pattern Detection Quality Analysis, False Positive Rate Analysis, Active Learning Requirements

---

## Epic Goal

Train supervised ML models to predict pattern quality and learn from user feedback (approve/reject suggestions). Addresses the critical 98.2% false positive rate by learning what makes a "good" pattern from user approvals/rejections, enabling the system to filter low-quality patterns before suggestion generation and continuously improve through active learning.

**Business Value:**
- **-4,456% False Positive Rate** (98.2% → <20%)
- **+4,344% Pattern Precision** (1.8% → 80%+)
- **+100% User Trust** (Only high-quality suggestions shown)
- **+50% Approval Rate** (Better suggestions = more approvals)
- **+100% Continuous Improvement** (Learns from every user action)

---

## Existing System Context

### Current Pattern Detection Quality

**Location:** `services/ai-automation-service/src/pattern_detection/`, `src/pattern_analyzer/`

**Current State:**
1. **Pattern Detection:**
   - ✅ Multiple detectors (time-of-day, co-occurrence, anomaly, seasonal, etc.)
   - ✅ Pattern confidence scoring
   - ✅ Pattern validation and deduplication
   - ⚠️ **CRITICAL ISSUE**: 98.2% false positive rate (only 3 of 170 patterns correct)
   - ⚠️ **CRITICAL ISSUE**: 1.8% precision (overwhelming noise)
   - ⚠️ **GAP**: No ML-based quality prediction
   - ⚠️ **GAP**: No learning from user feedback

2. **Pattern Quality:**
   - ✅ Basic confidence scoring
   - ✅ Pattern validation (deduplication, cross-validation)
   - ⚠️ **GAP**: No supervised learning for quality prediction
   - ⚠️ **GAP**: No ground truth validation framework
   - ⚠️ **GAP**: No active learning from approvals/rejections

3. **User Feedback:**
   - ✅ Suggestion approval/rejection tracking
   - ✅ Entity selection tracking
   - ⚠️ **GAP**: Feedback not used for model training
   - ⚠️ **GAP**: No active learning pipeline

### Technology Stack

- **Language:** Python 3.12+ (async/await, type hints, Pydantic 2.x)
- **Frameworks:** FastAPI, Pydantic Settings, scikit-learn, PyTorch
- **ML Models:**
  - RandomForest Classifier (pattern quality prediction)
  - IsolationForest (anomaly detection - existing)
  - PyTorch GNN (synergy detection - existing)
  - Sentence Transformers (embeddings - existing)
- **Location:** `services/ai-automation-service/src/services/pattern_quality/` (new)
- **2025 Patterns:** Type hints, structured logging, async generators, ML model versioning
- **Context7 KB:** scikit-learn patterns, PyTorch best practices, active learning frameworks

### Integration Points

- `TimeOfDayPatternDetector` - Time-of-day pattern detection
- `CoOccurrencePatternDetector` - Co-occurrence pattern detection
- `AnomalyDetector` - Anomaly detection
- `DailyAnalysisScheduler` - 3 AM workflow (pattern filtering)
- `SuggestionGenerator` - Suggestion generation (quality filtering)
- `UnifiedPromptBuilder` - Prompt building (quality-aware)

---

## Enhancement Details

### What's Being Added

1. **Supervised ML Model for Pattern Quality** (NEW)
   - Train RandomForest classifier to predict pattern quality
   - Features: pattern type, confidence, device count, occurrence count, time span, etc.
   - Target: user approval/rejection labels
   - Quality score: 0.0-1.0 (probability of being a good pattern)
   - Filter patterns before suggestion generation

2. **Active Learning from User Feedback** (NEW)
   - Learn from user approvals (positive examples)
   - Learn from user rejections (negative examples)
   - Learn from entity selections (preference signals)
   - Update model incrementally (no full retrain)
   - Improve quality prediction over time

3. **Transfer Learning from Blueprint Corpus** (NEW)
   - Use blueprint corpus (1000+ examples) as pre-training data
   - Fine-tune on user feedback
   - Leverage community knowledge for initial quality model
   - Improve cold-start performance

4. **Incremental Model Updates** (NEW)
   - Update model with new feedback without full retrain
   - Online learning for real-time improvement
   - Model versioning and rollback
   - Performance monitoring and alerting

5. **Pattern Quality Scoring** (ENHANCEMENT)
   - ML-based quality score for all patterns
   - Quality threshold filtering (>0.7 quality score)
   - Quality-aware suggestion ranking
   - Quality metrics reporting

### Success Criteria

1. **Functional:**
   - Pattern quality model trained and deployed
   - Active learning pipeline operational
   - Pattern precision: 1.8% → 80%+
   - False positive rate: 98.2% → <20%
   - Quality filtering reduces low-quality patterns by 90%+

2. **Technical:**
   - Pattern precision: 1.8% → 80%+
   - False positive rate: 98.2% → <20%
   - Model accuracy: >85% (quality prediction)
   - Incremental update time: <5 seconds
   - All code uses 2025 patterns (Python 3.12+, async/await, type hints)

3. **Quality:**
   - Unit tests >90% coverage for all changes
   - Integration tests validate end-to-end pipeline
   - Performance: <50ms per pattern (quality scoring)
   - Memory: <100MB for model (RandomForest)

---

## Stories

### Phase 1: ML Model Foundation (Weeks 1-2)

#### Story AI13.1: Pattern Quality Feature Engineering
**Type:** Foundation  
**Points:** 4  
**Effort:** 8-10 hours

Extract features from patterns for quality prediction.

**Acceptance Criteria:**
- Feature extraction from patterns (type, confidence, device count, occurrence count, time span, etc.)
- Feature normalization and scaling
- Feature importance analysis
- Feature validation and testing
- Unit tests for feature engineering (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/feature_extractor.py` (new)
- `services/ai-automation-service/src/services/pattern_quality/features.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_feature_extractor.py` (new)

**Dependencies:** None

---

#### Story AI13.2: Pattern Quality Model Training
**Type:** Foundation  
**Points:** 5  
**Effort:** 10-12 hours

Train RandomForest classifier for pattern quality prediction.

**Acceptance Criteria:**
- Train model on user feedback data (approvals/rejections)
- Use blueprint corpus for pre-training (transfer learning)
- Model evaluation (accuracy, precision, recall, F1)
- Model validation (cross-validation, holdout test)
- Model persistence and versioning
- Model performance: >85% accuracy
- Unit tests for model training (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/model_trainer.py` (new)
- `services/ai-automation-service/src/services/pattern_quality/quality_model.py` (new)
- `services/ai-automation-service/scripts/train_pattern_quality_model.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_model_trainer.py` (new)

**Dependencies:** Story AI13.1, Epic AI-4 (blueprint corpus)

---

#### Story AI13.3: Pattern Quality Scoring Service
**Type:** Feature  
**Points:** 4  
**Effort:** 8-10 hours

Implement pattern quality scoring service using trained model.

**Acceptance Criteria:**
- Load trained model at service startup
- Score patterns using quality model
- Quality score: 0.0-1.0 (probability of being good pattern)
- Quality threshold filtering (>0.7 quality score)
- Performance: <50ms per pattern
- Unit tests for quality scoring (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/scorer.py` (new)
- `services/ai-automation-service/src/services/pattern_quality/quality_service.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_scorer.py` (new)

**Dependencies:** Story AI13.2

---

### Phase 2: Active Learning (Weeks 2-3)

#### Story AI13.4: Active Learning Infrastructure
**Type:** Foundation  
**Points:** 4  
**Effort:** 8-10 hours

Build infrastructure for active learning from user feedback.

**Acceptance Criteria:**
- Track user approvals (positive examples)
- Track user rejections (negative examples)
- Track entity selections (preference signals)
- Store feedback in database
- Feedback aggregation and analysis
- Unit tests for active learning infrastructure (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/learning/pattern_feedback_tracker.py` (new)
- `services/ai-automation-service/src/database/models.py` (enhanced - feedback tables)
- `services/ai-automation-service/tests/services/learning/test_pattern_feedback.py` (new)

**Dependencies:** Story AI13.1

---

#### Story AI13.5: Incremental Model Updates
**Type:** Feature  
**Points:** 5  
**Effort:** 10-12 hours

Implement incremental model updates from user feedback.

**Acceptance Criteria:**
- Update model with new feedback without full retrain
- Online learning for real-time improvement
- Model versioning and rollback
- Performance monitoring and alerting
- Update time: <5 seconds for 100 feedback samples
- Unit tests for incremental updates (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/incremental_learner.py` (new)
- `services/ai-automation-service/src/services/pattern_quality/model_versioning.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_incremental_learner.py` (new)

**Dependencies:** Story AI13.2, Story AI13.4

---

#### Story AI13.6: Transfer Learning from Blueprint Corpus
**Type:** Feature  
**Points:** 4  
**Effort:** 8-10 hours

Implement transfer learning from blueprint corpus.

**Acceptance Criteria:**
- Load blueprint corpus (1000+ examples from Epic AI-4)
- Pre-train quality model on blueprint patterns
- Fine-tune on user feedback
- Improve cold-start performance
- Compare pre-trained vs non-pre-trained models
- Unit tests for transfer learning (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/transfer_learner.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_transfer_learning.py` (new)

**Dependencies:** Story AI13.2, Epic AI-4 (blueprint corpus)

---

### Phase 3: Integration & Filtering (Weeks 3-4)

#### Story AI13.7: Pattern Quality Filtering in 3 AM Workflow
**Type:** Integration  
**Points:** 4  
**Effort:** 8-10 hours

Integrate pattern quality filtering into 3 AM workflow.

**Acceptance Criteria:**
- Filter patterns by quality score before suggestion generation
- Quality threshold: >0.7 (configurable)
- Quality-aware suggestion ranking
- Maintain backward compatibility
- Performance: <100ms overhead per workflow
- Integration tests for 3 AM workflow

**Files:**
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (enhanced)
- `services/ai-automation-service/src/services/pattern_quality/filter.py` (new)
- `services/ai-automation-service/tests/integration/test_3am_quality_filtering.py` (new)

**Dependencies:** Story AI13.3, Story AI13.5

---

#### Story AI13.8: Pattern Quality Filtering in Ask AI Flow
**Type:** Integration  
**Points:** 4  
**Effort:** 8-10 hours

Integrate pattern quality filtering into Ask AI flow.

**Acceptance Criteria:**
- Filter patterns by quality score in Ask AI
- Quality-aware suggestion ranking
- Learn from Ask AI feedback
- Maintain backward compatibility
- Integration tests for Ask AI flow

**Files:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (enhanced)
- `services/ai-automation-service/src/services/pattern_quality/filter.py` (enhanced)
- `services/ai-automation-service/tests/integration/test_ask_ai_quality_filtering.py` (new)

**Dependencies:** Story AI13.3, Story AI13.5

---

### Phase 4: Metrics & Optimization (Weeks 4-5)

#### Story AI13.9: Quality Metrics & Reporting
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Implement comprehensive quality metrics and reporting.

**Acceptance Criteria:**
- Pattern precision/recall metrics
- False positive rate tracking
- Quality score distribution
- Model performance metrics
- User feedback statistics
- Quality improvement over time
- Unit tests for metrics (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/metrics.py` (new)
- `services/ai-automation-service/src/services/pattern_quality/reporting.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_metrics.py` (new)

**Dependencies:** Story AI13.7, Story AI13.8

---

#### Story AI13.10: Model Performance Monitoring
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Implement model performance monitoring and alerting.

**Acceptance Criteria:**
- Model accuracy monitoring
- Quality score distribution monitoring
- False positive rate monitoring
- Alerting on performance degradation
- Model version comparison
- Rollback capability
- Unit tests for monitoring (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/monitoring.py` (new)
- `services/ai-automation-service/src/services/pattern_quality/alerts.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_monitoring.py` (new)

**Dependencies:** Story AI13.5, Story AI13.9

---

#### Story AI13.11: Continuous Learning Pipeline
**Type:** Integration  
**Points:** 4  
**Effort:** 8-10 hours

Implement continuous learning pipeline for automated model improvement.

**Acceptance Criteria:**
- Automated feedback collection
- Scheduled model updates (daily/weekly)
- Automated model evaluation
- Automated model deployment
- Rollback on performance degradation
- Integration with CI/CD pipeline
- Unit tests for continuous learning (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/pattern_quality/continuous_learner.py` (new)
- `services/ai-automation-service/src/scheduler/quality_learning_scheduler.py` (new)
- `services/ai-automation-service/tests/services/pattern_quality/test_continuous_learning.py` (new)

**Dependencies:** Story AI13.5, Story AI13.10

---

## Technical Architecture

### Pattern Quality Prediction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Pattern Quality Prediction System                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Pattern Detection (Existing)                          │  │
│  │    - Time-of-day patterns                                │  │
│  │    - Co-occurrence patterns                              │  │
│  │    - Anomaly patterns                                    │  │
│  │    - Other pattern types                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 2. Feature Extraction                                    │  │
│  │    - Pattern type, confidence, device count             │  │
│  │    - Occurrence count, time span                        │  │
│  │    - Device types, area distribution                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3. Quality Prediction (ML Model)                        │  │
│  │    - RandomForest classifier                            │  │
│  │    - Quality score: 0.0-1.0                             │  │
│  │    - Threshold filtering (>0.7)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4. Quality Filtering                                    │  │
│  │    - Filter low-quality patterns                        │  │
│  │    - Quality-aware ranking                              │  │
│  │    - Pass to suggestion generation                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 5. Active Learning (Feedback Loop)                      │  │
│  │    - User approvals (positive examples)                 │  │
│  │    - User rejections (negative examples)                │  │
│  │    - Incremental model updates                          │  │
│  │    - Continuous improvement                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

1. **Pattern Detection:**
   - All pattern detectors (time-of-day, co-occurrence, anomaly, etc.)
   - Pattern quality scoring after detection
   - Quality filtering before suggestion generation

2. **Suggestion Generation:**
   - Quality-aware suggestion ranking
   - Quality score in suggestion metadata
   - Quality filtering in suggestion selection

3. **User Feedback:**
   - Track approvals/rejections from 3 AM suggestions
   - Track approvals/rejections from Ask AI
   - Use feedback for active learning

4. **Model Training:**
   - Initial training on user feedback
   - Transfer learning from blueprint corpus
   - Incremental updates from new feedback

---

## Dependencies

### Prerequisites
- **Epic AI-11**: Realistic Training Data Enhancement (ground truth validation)
- **Epic AI-12**: Personalized Entity Resolution (entity context for quality)
- **Epic AI-4**: Community Knowledge Augmentation (blueprint corpus for transfer learning)
- **Existing**: Pattern detection infrastructure
- **Existing**: User feedback tracking

### Can Run In Parallel
- **Epic AI-16**: Simulation Framework (can integrate after AI13.2)

---

## Risk Assessment

### Technical Risks
1. **Model Accuracy**: Quality model may not improve precision enough
   - **Mitigation**: Transfer learning, feature engineering, active learning
   - **Target**: >85% model accuracy, 80%+ pattern precision

2. **Cold Start**: No feedback data for initial training
   - **Mitigation**: Transfer learning from blueprint corpus, synthetic data
   - **Approach**: Pre-train on blueprints, fine-tune on feedback

3. **Performance**: Quality scoring may slow down workflow
   - **Mitigation**: Caching, optimization, async processing
   - **Target**: <50ms per pattern (quality scoring)

### Integration Risks
1. **Backward Compatibility**: Quality filtering may break existing workflows
   - **Mitigation**: Feature flag, gradual rollout, quality threshold tuning
   - **Approach**: Support both filtered and unfiltered modes

2. **Feedback Quality**: User feedback may be noisy
   - **Mitigation**: Feedback validation, outlier detection, confidence weighting
   - **Approach**: Weight feedback by user engagement level

---

## Success Metrics

### Quality Metrics
- **Pattern Precision**: 1.8% → 80%+
- **False Positive Rate**: 98.2% → <20%
- **Model Accuracy**: >85% (quality prediction)
- **Approval Rate**: +50% (better suggestions)

### Performance Metrics
- **Quality Scoring Time**: <50ms per pattern
- **Incremental Update Time**: <5 seconds for 100 feedback samples
- **Memory Usage**: <100MB for model

### Learning Metrics
- **Feedback Collection Rate**: >10 samples per user per week
- **Model Improvement Rate**: +5% accuracy per month
- **Active Learning Effectiveness**: +20% accuracy with feedback

---

## Future Enhancements

1. **Deep Learning Models**: Replace RandomForest with neural networks for better accuracy
2. **Multi-Task Learning**: Learn pattern quality and suggestion quality together
3. **Ensemble Methods**: Combine multiple models for better predictions
4. **Explainability**: Explain why patterns are high/low quality
5. **User-Specific Models**: Personalized quality models per user

---

## References

- [Epic AI-11: Realistic Training Data Enhancement](epic-ai11-realistic-training-data-enhancement.md)
- [Epic AI-12: Personalized Entity Resolution](epic-ai12-personalized-entity-resolution.md)
- [Epic AI-4: Community Knowledge Augmentation](epic-ai4-community-knowledge-augmentation.md)
- [Dataset Test Analysis](../../implementation/analysis/DATASET_TEST_ANALYSIS_AND_NEXT_STEPS.md)
- [BMAD Methodology](../../.bmad-core/user-guide.md)

---

**Last Updated:** January 2025  
**Next Review:** After Story AI13.1 completion

