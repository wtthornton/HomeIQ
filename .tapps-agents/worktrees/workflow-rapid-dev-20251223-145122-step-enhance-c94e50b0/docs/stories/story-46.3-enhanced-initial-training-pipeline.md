# Story 46.3: Enhanced Initial Training Pipeline

**Story ID:** 46.3  
**Epic:** 46 (Enhanced ML Training Data and Nightly Training Automation)  
**Status:** 📋 Ready for Development  
**Priority:** P0 (Critical for Alpha)  
**Story Points:** 3  
**Complexity:** Low-Medium  
**Estimated Effort:** 3-4 hours

---

## Story Description

Enhance `prepare_for_production.py` to use **template-based synthetic device data** for initial Device Intelligence model training (pre-release only), validate model quality, and ensure pre-trained models are included in Docker image. This ensures alpha users receive high-quality working models immediately. **NUC-optimized**: Fast training (<1 minute), CPU-only, lightweight models.

## User Story

**As a** system administrator preparing for alpha release  
**I want** high-quality pre-trained models included in the Docker image  
**So that** alpha users have working models immediately without waiting for data collection

## Acceptance Criteria

### AC1: Template-Based Synthetic Data Integration
- [ ] Integrate template-based synthetic device data generator into `prepare_for_production.py`
- [ ] Generate synthetic device data before Device Intelligence training (pre-release only)
- [ ] Use synthetic data for initial Device Intelligence model training
- [ ] Fallback to database data if synthetic generation fails
- [ ] Configurable synthetic data generation (count, time range)
- [ ] **Fast generation**: <30 seconds for 1000 samples (NUC-optimized)

### AC2: Model Quality Validation
- [ ] Validate Device Intelligence models meet quality thresholds:
  - Accuracy: ≥85%
  - Precision: ≥80%
  - Recall: ≥80%
  - F1 Score: ≥80%
- [ ] Fail training if thresholds not met (unless `--allow-low-quality`)
- [ ] Clear error messages with quality metrics
- [ ] Quality metrics included in production readiness report

### AC3: Pre-trained Model Inclusion
- [ ] Save trained models to `services/device-intelligence-service/models/`
- [ ] Models included in Docker image build
- [ ] Models load automatically on service startup
- [ ] Models work immediately (no training required on first run)
- [ ] Model metadata saved and included

### AC4: Training Pipeline Updates
- [ ] Update `train_device_intelligence()` function in `prepare_for_production.py`
- [ ] Use synthetic data generator for initial training
- [ ] Validate model quality after training
- [ ] Save models to correct location
- [ ] Update model manifest with Device Intelligence models

### AC5: Documentation Updates
- [ ] Update `prepare_for_production.py` documentation
- [ ] Document synthetic data generation process
- [ ] Document model quality validation
- [ ] Update production readiness guide
- [ ] Include examples and usage instructions

### AC6: Backward Compatibility
- [ ] Existing training methods still work
- [ ] Database data still used if available
- [ ] Fallback to sample data if synthetic generation fails
- [ ] No breaking changes to existing APIs

## Technical Requirements

### Modified Files

**1. `scripts/prepare_for_production.py`**

**Add synthetic data generation:**
```python
async def generate_synthetic_device_data(
    count: int = 1000,
    days: int = 180
) -> list[dict]:
    """Generate synthetic device data for initial training."""
    from services.device_intelligence_service.src.training.synthetic_device_generator import (
        SyntheticDeviceGenerator
    )
    
    generator = SyntheticDeviceGenerator()
    return generator.generate_training_data(count=count, days=days)

async def train_device_intelligence(allow_low_quality: bool = False) -> tuple[bool, dict]:
    """Train device intelligence models with synthetic data."""
    logger.info("Training Device Intelligence Models...")
    
    # Generate synthetic data for initial training
    logger.info("Generating synthetic device data...")
    synthetic_data = await generate_synthetic_device_data(count=1000, days=180)
    logger.info(f"Generated {len(synthetic_data)} synthetic device samples")
    
    # Train with synthetic data
    cmd = [
        sys.executable,
        str(device_intelligence_dir / "scripts" / "train_models.py"),
        "--force",
        "--verbose",
        "--synthetic-data"  # New flag to use synthetic data
    ]
    
    # ... rest of training logic ...
```

**2. `services/device-intelligence-service/scripts/train_models.py`**

**Add synthetic data support:**
```python
parser.add_argument(
    '--synthetic-data',
    action='store_true',
    help='Use synthetic device data for training (for initial training)'
)

async def train_models(
    days_back: int = 180,
    force: bool = False,
    verbose: bool = False,
    use_synthetic: bool = False
):
    """Train models with optional synthetic data."""
    engine = PredictiveAnalyticsEngine(settings)
    
    if use_synthetic:
        # Generate synthetic data
        from src.training.synthetic_device_generator import SyntheticDeviceGenerator
        generator = SyntheticDeviceGenerator()
        historical_data = generator.generate_training_data(count=1000, days=days_back)
    else:
        # Use database data (existing logic)
        historical_data = None
    
    await engine.train_models(historical_data=historical_data, days_back=days_back)
```

**3. `services/device-intelligence-service/src/core/predictive_analytics.py`**

**Enhance `train_models()` to accept synthetic data:**
- Already accepts `historical_data` parameter
- No changes needed (already supports this)

### Docker Image Integration

**Ensure models are included:**
```dockerfile
# In Dockerfile, ensure models directory is copied
COPY models/ /app/models/
```

**Or via docker-compose:**
```yaml
device-intelligence-service:
  volumes:
    - ./services/device-intelligence-service/models:/app/models
```

## Testing Requirements

### Unit Tests
- [ ] Synthetic data generation works
- [ ] Training pipeline accepts synthetic data
- [ ] Model quality validation works
- [ ] Models save correctly

### Integration Tests
- [ ] Full training pipeline with synthetic data
- [ ] Model quality validation
- [ ] Models load on service startup
- [ ] Models work for predictions

### Manual Testing
- [ ] Run `prepare_for_production.py` end-to-end
- [ ] Verify synthetic data generation
- [ ] Verify model training with synthetic data
- [ ] Verify model quality meets thresholds
- [ ] Verify models work on first startup
- [ ] Test with `--allow-low-quality` flag

## Dependencies

**Depends on:**
- Story 46.1 (Synthetic Device Data Generator)
- Existing `prepare_for_production.py` structure
- Existing model quality validation (Epic 43)

**Enables:**
- Alpha release with working models
- High-quality initial models
- User experience (no waiting for data)

## Success Metrics

**Model Quality:**
- Accuracy: ≥85% (target: 90%+)
- Precision: ≥80% (target: 85%+)
- Recall: ≥80% (target: 85%+)
- F1 Score: ≥80% (target: 85%+)

**Training Time (NUC-Optimized):**
- Synthetic data generation: <30 seconds (template-based, no API calls)
- Model training: 1-5 seconds (RandomForest) or <1s (TabPFN)
- Total pipeline: <1 minute
- **CPU-only**: No GPU required, runs on NUC hardware

**User Experience:**
- Models work immediately on first startup
- No training required for initial use
- Models improve with nightly training

## Definition of Done

- [ ] Synthetic data integrated into training pipeline
- [ ] Model quality validation enforced
- [ ] Pre-trained models included in Docker image
- [ ] Models work immediately on first startup
- [ ] Documentation updated
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing complete
- [ ] Code reviewed and approved

## Related Stories

- **Story 46.1**: Synthetic Device Data Generator (provides data)
- **Story 46.2**: Built-in Nightly Training Scheduler (validates scheduler integration)
- **Epic 43**: Model Quality & Documentation (quality validation infrastructure)

---

**Last Updated:** December 2025  
**Status:** 📋 Ready for Development

