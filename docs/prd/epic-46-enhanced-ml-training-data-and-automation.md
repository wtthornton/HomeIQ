# Epic 46: Enhanced ML Training Data and Nightly Training Automation

**Status:** 📋 **PLANNING**  
**Type:** ML Training & Production Readiness  
**Priority:** High (Alpha Release Blocker)  
**Effort:** 3 Stories (12-16 hours estimated)  
**Created:** December 2025  
**Target Completion:** December 2025  
**Based On:** Alpha Release Requirements - Initial Training Data Quality & Nightly Training Automation

---

## Epic Goal

Enhance ML training infrastructure to support high-quality initial model training for alpha release and automated nightly training for users. This epic addresses critical gaps in the training pipeline to ensure alpha users receive working models immediately and can continuously improve them with their own data.

**Business Value:**
- **Alpha-Ready Models**: High-quality pre-trained models shipped with alpha release
- **User Autonomy**: Automated nightly training without manual setup
- **Better Accuracy**: Realistic synthetic data improves initial model quality
- **Production Ready**: Built-in training automation reduces support burden
- **Continuous Improvement**: Models improve automatically with user data

---

## Existing System Context

### Current Training Infrastructure

**Location:** `services/device-intelligence-service/`, `scripts/prepare_for_production.py`

**Current State:**
1. **Initial Training Data**: 
   - Device Intelligence models use basic random sample data (200 samples, simple distributions)
   - No realistic device behavior patterns
   - No failure scenarios
   - May not meet quality thresholds (85% accuracy, 80% precision/recall)

2. **Home Type Classifier**:
   - ✅ Excellent synthetic data generation (100-120 homes, 90 days events)
   - ✅ Pre-trained models included in Docker image
   - ✅ Template-based generation (no API costs)

3. **Nightly Training**:
   - ⚠️ Scripts exist but require manual cron/Task Scheduler setup
   - ⚠️ No built-in scheduler in service
   - ⚠️ Users must configure external scheduling

4. **Training Pipeline**:
   - ✅ `prepare_for_production.py` can train all models
   - ✅ API endpoint for training exists
   - ✅ Incremental learning support (10-50x faster)
   - ⚠️ No high-quality synthetic data for Device Intelligence

### Technology Stack
- **ML Libraries**: scikit-learn, LightGBM, TabPFN, River (2025 improvements - Epic 36)
- **Scheduling**: APScheduler (used in ai-automation-service, not in device-intelligence-service)
- **Data Generation**: Template-based (synthetic homes), random distributions (device intelligence)
- **Deployment**: Docker Compose (single-home NUC, 8-16GB RAM)
- **Language**: Python 3.11+
- **Architecture Pattern**: Single-home edge deployment (NUC-optimized, CPU-only, no GPU)

### Deployment Constraints (2025 Best Practices)

**Single-Home NUC Deployment:**
- **Hardware**: Intel NUC i3/i5, 8-16GB RAM (recommended)
- **Resource Constraints**: CPU-only, no GPU required
- **Memory**: <2GB per service, lightweight models
- **Processing**: Batch processing (nightly), non-blocking
- **Cost**: Template-based generation (no API costs)
- **Philosophy**: Practical first, incremental improvements, avoid over-engineering

---

## Enhancement Details

### What's Being Added/Changed

1. **Synthetic Device Data Generator** (Template-Based, No API Costs)
   - **Template-based generation** following `synthetic_home_generator.py` pattern
   - **No LLM/API calls** - uses predefined distributions and templates
   - Realistic device behavior patterns (usage cycles, degradation over time)
   - Failure scenarios and edge cases (progressive degradation, sudden failures)
   - Device type diversity (sensors, switches, lights, climate, security, etc.)
   - Temporal patterns (daily cycles, weekly patterns, seasonal variations)
   - 1000+ high-quality training samples
   - **Pre-release training only** - used before alpha release, not ongoing

2. **Built-in Nightly Training Scheduler**
   - APScheduler integration in device-intelligence-service
   - Automatic nightly training (configurable, default: 2 AM)
   - Incremental update option (10-50x faster)
   - Health monitoring and error handling
   - Configurable schedule via environment variables

3. **Enhanced Initial Training Pipeline**
   - Use synthetic device data for initial training
   - Validate model quality before shipping
   - Include in `prepare_for_production.py`
   - Pre-trained models in Docker image
   - Quality thresholds enforced

---

## Stories

### Story 46.1: Synthetic Device Data Generator
**Priority:** P0 (Critical for Alpha)  
**Story Points:** 5  
**Effort:** 4-5 hours

Create a synthetic device data generator that produces realistic device metrics with behavior patterns, failure scenarios, and temporal patterns. Similar to synthetic home generation but focused on device health metrics.

**Acceptance Criteria:**
- Generate 1000+ realistic device training samples
- Include diverse device types (sensors, switches, lights, climate, etc.)
- Realistic behavior patterns (usage cycles, degradation)
- Failure scenarios (high error rates, low battery, connection issues)
- Temporal patterns (device aging, seasonal variations)
- Configurable generation parameters
- Output format compatible with existing training pipeline

---

### Story 46.2: Built-in Nightly Training Scheduler
**Priority:** P1 (High for Alpha)  
**Story Points:** 5  
**Effort:** 4-5 hours

Integrate APScheduler into device-intelligence-service to enable automatic nightly model training without requiring users to set up external cron/Task Scheduler.

**Acceptance Criteria:**
- APScheduler integration in device-intelligence-service
- Configurable training schedule (default: 2 AM daily)
- Support for full retrain and incremental update modes
- Health monitoring and error handling
- Logging and status tracking
- Environment variable configuration
- Graceful shutdown handling
- Manual trigger capability via API

---

### Story 46.3: Enhanced Initial Training Pipeline
**Priority:** P0 (Critical for Alpha)  
**Story Points:** 3  
**Effort:** 3-4 hours

Enhance `prepare_for_production.py` to use synthetic device data for initial Device Intelligence model training, validate model quality, and ensure pre-trained models are included in Docker image.

**Acceptance Criteria:**
- Integrate synthetic device data generator into training pipeline
- Use synthetic data for initial Device Intelligence training
- Validate model quality against thresholds (85% accuracy, 80% precision/recall)
- Include pre-trained models in Docker image
- Update documentation with new training process
- Ensure models work immediately on first startup

---

## Technical Approach

### Story 46.1: Synthetic Device Data Generator

**New File:** `services/device-intelligence-service/src/training/synthetic_device_generator.py`

**Pattern Reference:** Follows `services/ai-automation-service/src/training/synthetic_home_generator.py` pattern

**Key Features:**
- **Template-based generation** (no LLM/API calls, zero cost)
- Device type templates (sensor, switch, light, climate, security, etc.)
- Realistic metric distributions (not just random numbers)
- Failure scenarios (progressive degradation, sudden failures, intermittent issues)
- Temporal patterns (daily cycles, weekly patterns, seasonal variations)
- Device aging simulation (gradual degradation over time)
- Configurable parameters (device count, time range, failure rate)
- **NUC-optimized**: Fast generation (<30 seconds for 1000 samples)

**Integration:**
- Used by `prepare_for_production.py` for **pre-release initial training only**
- Can be called standalone for testing
- Output format matches `_collect_training_data()` return format
- **Not used in production** - only for initial model training before alpha release

---

### Story 46.2: Built-in Nightly Training Scheduler

**Modified Files:**
- `services/device-intelligence-service/src/main.py` - Add scheduler startup/shutdown
- `services/device-intelligence-service/src/config.py` - Add scheduler configuration
- `services/device-intelligence-service/src/api/predictions_router.py` - Add manual trigger endpoint

**New File:** `services/device-intelligence-service/src/scheduler/training_scheduler.py`

**Pattern Reference:** Follows APScheduler pattern from `ai-automation-service` (already proven)

**Key Features:**
- APScheduler with cron trigger (configurable, default: 2 AM daily)
- Support for full retrain and incremental update (10-50x faster)
- Error handling and retry logic (graceful failure handling)
- Status tracking and logging (health monitoring integration)
- **NUC-optimized**: Non-blocking background processing, resource-efficient
- Concurrent run prevention (skip if already running)

**Configuration:**
```python
# config.py
ML_TRAINING_SCHEDULE: str = "0 2 * * *"  # 2 AM daily
ML_TRAINING_ENABLED: bool = True
ML_TRAINING_MODE: str = "incremental"  # or "full"
```

---

### Story 46.3: Enhanced Initial Training Pipeline

**Modified Files:**
- `scripts/prepare_for_production.py` - Integrate synthetic device data
- `services/device-intelligence-service/src/core/predictive_analytics.py` - Support synthetic data input

**Key Features:**
- Generate synthetic device data before training
- Use synthetic data for initial Device Intelligence training
- Validate model quality
- Save pre-trained models to Docker image
- Update documentation

---

## Dependencies

**Depends on:**
- Existing ML training infrastructure (Epic DI-3.3)
- `prepare_for_production.py` script (Epic 42, 43)
- APScheduler library (already used in ai-automation-service)

**Enables:**
- Alpha release with working models
- User autonomy (no manual training setup)
- Continuous model improvement

---

## Success Criteria

### Story 46.1: Synthetic Device Data Generator
- ✅ Generate 1000+ realistic device samples
- ✅ Include diverse device types and failure scenarios
- ✅ Realistic behavior patterns and temporal variations
- ✅ Compatible with existing training pipeline

### Story 46.2: Built-in Nightly Training Scheduler
- ✅ Automatic nightly training without external setup
- ✅ Configurable schedule and training mode
- ✅ Health monitoring and error handling
- ✅ Manual trigger capability

### Story 46.3: Enhanced Initial Training Pipeline
- ✅ High-quality initial models in Docker image
- ✅ Model quality validation (meets thresholds)
- ✅ Models work immediately on first startup
- ✅ Documentation updated

---

## Testing Strategy

### Unit Tests
- Synthetic data generator produces valid samples
- Scheduler triggers training at correct times
- Training pipeline uses synthetic data correctly

### Integration Tests
- Full training pipeline with synthetic data
- Scheduler integration with training API
- Model quality validation

### Manual Testing
- Generate synthetic data and verify quality
- Test scheduler with different schedules
- Verify pre-trained models work on first startup

---

## Risk Mitigation

### Risk 1: Synthetic Data Quality
- **Mitigation**: Use realistic patterns from real device data analysis, follow template-based pattern (proven in home generator)
- **Validation**: Compare synthetic data distributions with real data, ensure realistic correlations
- **2025 Best Practice**: Template-based generation (no API costs, deterministic, fast)

### Risk 2: Scheduler Reliability
- **Mitigation**: Use proven APScheduler (already used in ai-automation-service), follow existing patterns
- **Validation**: Test scheduler with various schedules and error scenarios, graceful shutdown handling
- **2025 Best Practice**: Incremental learning by default (10-50x faster, less resource-intensive)

### Risk 3: Model Quality Degradation
- **Mitigation**: Enforce quality thresholds (85% accuracy, 80% precision/recall), validate before shipping
- **Validation**: Test models on real data before alpha release, use quality validation framework (Epic 43)
- **2025 Best Practice**: Start simple (RandomForest default), add complexity only when proven necessary

### Risk 4: Resource Constraints (NUC Deployment)
- **Mitigation**: Use incremental learning (default), lightweight models, batch processing
- **Validation**: Test on NUC hardware, monitor memory/CPU usage during training
- **2025 Best Practice**: CPU-only optimization, avoid GPU dependencies, practical first approach

---

## Timeline

**Total Effort:** 12-16 hours (3 stories)

**Week 1:**
- Day 1-2: Story 46.1 (Synthetic Device Data Generator)
- Day 3-4: Story 46.2 (Built-in Nightly Training Scheduler)
- Day 5: Story 46.3 (Enhanced Initial Training Pipeline)

**Alpha Release:** After Epic 46 completion

---

## 2025 Best Practices Alignment

### ✅ Practical First
- **Template-based generation** (no API costs, fast, deterministic)
- **Incremental learning by default** (10-50x faster updates)
- **Pre-release training only** (synthetic data used before alpha, not ongoing)
- **NUC-optimized** (CPU-only, lightweight, resource-efficient)

### ✅ Avoid Over-Engineering
- **No deep learning** - Uses proven scikit-learn, LightGBM, TabPFN, River
- **No federated learning** - Single-home deployment doesn't need it
- **Simple ML pipelines** - Template-based generation, straightforward training
- **Production-focused** - All improvements use battle-tested libraries

### ✅ Single-Home NUC Deployment
- **Hardware**: Intel NUC i3/i5, 8-16GB RAM (recommended)
- **CPU-only**: No GPU required, all models CPU-optimized
- **Memory**: <2GB per service, lightweight models
- **Processing**: Batch processing (nightly), non-blocking
- **Cost**: Template-based generation (zero API costs)

### ✅ Follow Existing Patterns
- **Synthetic data generation**: Follows `synthetic_home_generator.py` template-based pattern
- **Scheduler integration**: Follows APScheduler pattern from `ai-automation-service`
- **Training pipeline**: Integrates with existing `prepare_for_production.py` structure
- **Model quality**: Uses existing quality validation framework (Epic 43)

---

## Related Documentation

- `services/device-intelligence-service/docs/MODEL_TRAINING_GUIDE.md`
- `services/device-intelligence-service/docs/ML_IMPROVEMENTS_GUIDE.md`
- `scripts/prepare_for_production.py`
- `implementation/ML_TRAINING_IMPROVEMENTS_NEXT_STEPS.md`
- `services/ai-automation-service/src/training/synthetic_home_generator.py` (pattern reference)
- `implementation/analysis/2025_BEST_PRACTICES_REVIEW_AND_VALIDATION.md`

---

**Last Updated:** December 2025  
**Status:** 📋 **PLANNING** - Ready for Development  
**2025 Best Practices:** ✅ Aligned - Template-based, NUC-optimized, practical first

