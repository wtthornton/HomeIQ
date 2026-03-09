# Epic 40: Pattern Detection ML Upgrade

**Priority:** P2 Medium
**Estimated Duration:** 3-4 weeks
**Status:** Complete
**Created:** 2026-03-09
**Completed:** 2026-03-09
**Source:** Sprint 8 review — only 1/10 detectors uses real ML (KMeans)

## Overview

Upgrade the pattern detection pipeline from purely statistical heuristics to hybrid ML approaches. Currently, 9 of 10 detectors use statistical methods (z-scores, linear regression, coefficient of variation). This epic adds learned models for sequence prediction, anomaly detection, and pattern clustering while keeping statistical methods as fast baselines.

## Background

Epic 37 delivered 10 pattern detectors. While statistically sound and interpretable, they have limitations:
- **Sequence detector** uses fixed-window counting — can't predict *next* device in a chain
- **Anomaly detector** uses z-score thresholds — can't adapt to non-Gaussian distributions
- **No cross-detector learning** — detectors run independently, missing compound patterns
- **No user feedback loop** — pattern confidence doesn't improve from user acceptance/rejection

The ML upgrade adds learned models that train on accumulated pattern data, while keeping statistical baselines as fallbacks when training data is insufficient.

## Current Detector Architecture

| Detector | Current Algorithm | ML Opportunity |
|----------|------------------|----------------|
| TimeOfDay | KMeans clustering | Already ML — enhance with DBSCAN |
| CoOccurrence | Sliding window + support | Association rule mining (FP-Growth) |
| Sequence | Timing variance + counting | LSTM / Transformer sequence prediction |
| Duration | Coefficient of variation | Gaussian Mixture Models |
| Anomaly | Z-score thresholds | Isolation Forest / Autoencoder |
| DayType | Distribution overlap | Learned day-type classifier |
| Frequency | Linear regression | Prophet / time-series decomposition |
| RoomBased | Area co-occurrence | Graph Neural Network clustering |
| Seasonal | Profile comparison | Seasonal decomposition (STL) |
| Contextual | Sun correlation | Multi-variate regression |

## Stories

### Story 40.1: ML Training Data Pipeline
**Priority:** P0 (Prerequisite)
**Estimate:** 3 days

Build infrastructure to collect, store, and serve training data from pattern detection history.

**Acceptance Criteria:**
- [ ] Create `pattern_training_data` table in PostgreSQL (automation schema)
- [ ] Store raw events + detected patterns + user feedback per detection run
- [ ] Alembic migration for new table
- [ ] Data export utility for offline model training
- [ ] Minimum 7 days of accumulated data before ML models activate
- [ ] Data retention policy (90 days rolling window)

### Story 40.2: Sequence Prediction Model (LSTM)
**Priority:** P1 High
**Estimate:** 5 days

Replace counting-based sequence detection with an LSTM model that predicts the next device activation.

**Acceptance Criteria:**
- [ ] LSTM model trained on historical device activation sequences
- [ ] Input: last N device activations with timestamps
- [ ] Output: predicted next device + confidence + expected delay
- [ ] Fallback to statistical detector when < 7 days training data
- [ ] Model stored as ONNX for portable inference
- [ ] Inference latency < 50ms per prediction
- [ ] A/B comparison: ML predictions vs statistical baseline accuracy
- [ ] 20+ unit tests

### Story 40.3: Isolation Forest Anomaly Detection
**Priority:** P1 High
**Estimate:** 3 days

Add Isolation Forest as a secondary anomaly detection method alongside z-score.

**Acceptance Criteria:**
- [ ] scikit-learn `IsolationForest` trained on device behavioral features
- [ ] Features: hour_of_day, day_of_week, activation_count, duration, interval
- [ ] Ensemble scoring: combine z-score and IF scores (configurable weights)
- [ ] Contamination parameter auto-tuned from historical anomaly rate
- [ ] Fallback to z-score only when IF model unavailable
- [ ] Anomaly type classification maintained (timing, frequency, duration, absence)
- [ ] 15+ unit tests

### Story 40.4: FP-Growth Association Rules
**Priority:** P2 Medium
**Estimate:** 3 days

Replace sliding-window co-occurrence with FP-Growth frequent itemset mining for richer device associations.

**Acceptance Criteria:**
- [ ] Implement FP-Growth using mlxtend or custom implementation
- [ ] Mine frequent itemsets with configurable min_support (default: 0.1)
- [ ] Generate association rules with min_confidence (default: 0.5)
- [ ] Support lift metric for rule quality assessment
- [ ] Handle temporal ordering (A before B vs A with B)
- [ ] Fallback to sliding-window when < 100 events
- [ ] 15+ unit tests

### Story 40.5: User Feedback Loop
**Priority:** P1 High
**Estimate:** 3 days

Close the feedback loop: user acceptance/rejection of automation suggestions improves future pattern confidence.

**Acceptance Criteria:**
- [ ] API endpoint: `POST /patterns/{id}/feedback` (accept/reject/ignore)
- [ ] Feedback stored in pattern_training_data with user_action column
- [ ] Pattern confidence adjusted: +0.1 on accept, -0.2 on reject (capped 0.1–0.95)
- [ ] Rejected patterns suppressed for 30 days (configurable)
- [ ] Accepted patterns boost related detector confidence
- [ ] Integration with Memory Brain (save feedback as OUTCOME memories)
- [ ] Dashboard shows acceptance rate per pattern type
- [ ] 10+ unit tests

### Story 40.6: Prophet Time-Series for Frequency Detection
**Priority:** P3 Low
**Estimate:** 3 days

Replace linear regression trend detection with Facebook Prophet for richer time-series decomposition.

**Acceptance Criteria:**
- [ ] Prophet model fitted per device's daily activation counts
- [ ] Decompose into trend, weekly seasonality, yearly seasonality
- [ ] Detect changepoints in activation frequency
- [ ] Forecast next 7 days of expected activations
- [ ] Anomaly detection via prediction interval violations
- [ ] Fallback to linear regression when Prophet unavailable or data < 14 days
- [ ] 10+ unit tests

### Story 40.7: Model Registry & Versioning
**Priority:** P2 Medium
**Estimate:** 2 days

Create a simple model registry for managing trained ML models.

**Acceptance Criteria:**
- [ ] Model metadata table: model_name, version, trained_at, metrics, file_path
- [ ] Model storage in `/app/data/models/` with versioned directories
- [ ] API endpoint: `GET /models` — list registered models with metrics
- [ ] Automatic model retraining on schedule (weekly, configurable)
- [ ] Model rollback: revert to previous version via API
- [ ] Health check reports model versions and last training time

### Story 40.8: Cross-Detector Pattern Fusion
**Priority:** P3 Low
**Estimate:** 3 days

Combine outputs from multiple detectors to identify compound patterns that no single detector can find.

**Acceptance Criteria:**
- [ ] Post-detection fusion step in PatternAnalysisScheduler
- [ ] Merge overlapping patterns (e.g., sequence + room_based → room routine sequence)
- [ ] Deduplicate patterns with >85% entity overlap
- [ ] Compound pattern confidence = weighted average of constituent patterns
- [ ] New pattern_type: "compound" with references to source patterns
- [ ] 10+ unit tests

## Dependencies

- Epic 37 (Pattern Detection Expansion) — complete
- Epic 38 (ML Dependencies) — complete (scikit-learn, sentence-transformers upgraded)
- Story 40.1 (Training Data Pipeline) must complete before Stories 40.2–40.4
- Story 40.5 (Feedback Loop) integrates with Memory Brain (Epics 29–35)

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Insufficient training data | High (new system) | High | Statistical baselines as fallback |
| LSTM overfitting on small dataset | Medium | Medium | Early stopping, dropout, cross-validation |
| Prophet dependency bloat (~150MB) | Low | Low | Optional dependency, lazy import |
| Model drift over time | Medium | Medium | Weekly retraining + drift detection |

## Success Metrics

- Pattern acceptance rate increases by 15%+ after feedback loop
- Sequence prediction accuracy > 70% (vs ~50% statistical baseline)
- Anomaly false positive rate drops by 30%+ with Isolation Forest
- No performance regression in scheduler runtime (< 2x baseline)
