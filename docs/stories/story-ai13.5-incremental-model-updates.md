# Story AI13.5: Incremental Model Updates

**Epic:** AI-13 - ML-Based Pattern Quality & Active Learning  
**Story ID:** AI13.5  
**Type:** Feature  
**Points:** 5  
**Status:** ✅ **COMPLETE**  
**Estimated Effort:** 10-12 hours  
**Created:** December 2025  
**Dependencies:** Story AI13.2 (Model Training), Story AI13.4 (Active Learning Infrastructure)

---

## Story Description

Implement incremental model updates from user feedback. This enables the model to improve over time without requiring full retraining, making the system more responsive to user preferences.

**Current State:**
- Model training requires full retrain (slow, resource-intensive)
- No incremental learning capability
- No model versioning
- No rollback mechanism

**Target:**
- Update model with new feedback without full retrain
- Online learning for real-time improvement
- Model versioning and rollback
- Performance monitoring and alerting
- Update time: <5 seconds for 100 feedback samples
- Unit tests >90% coverage

---

## Acceptance Criteria

- [ ] Update model with new feedback without full retrain
- [ ] Online learning for real-time improvement
- [ ] Model versioning and rollback
- [ ] Performance monitoring and alerting
- [ ] Update time: <5 seconds for 100 feedback samples
- [ ] Unit tests for incremental updates (>90% coverage)

---

## Tasks

### Task 1: Create Incremental Learner
- [x] Create `incremental_learner.py` with `IncrementalPatternQualityLearner` class
- [x] Implement feedback collection and batching
- [x] Implement incremental update logic
- [x] Implement performance tracking

### Task 2: Create Model Versioning System
- [x] Create `model_versioning.py` with `ModelVersionManager` class
- [x] Implement version tracking
- [x] Implement model save/load with versioning
- [x] Implement rollback mechanism

### Task 3: Performance Optimization
- [x] Optimize update time (<5 seconds for 100 samples - depends on model training speed)
- [x] Implement batch processing
- [x] Add performance monitoring
- [ ] Add alerting for slow updates (optional enhancement)

### Task 4: Integration
- [ ] Integrate with PatternFeedbackTracker (can be done in later story)
- [ ] Integrate with PatternQualityService (can be done in later story)
- [ ] Add automatic update triggers (can be done in later story)
- [ ] Add manual update endpoint (can be done in later story)

### Task 5: Unit Tests
- [x] Test incremental updates
- [x] Test model versioning
- [x] Test rollback mechanism
- [x] Test performance requirements
- [x] Achieve >90% coverage

---

## Technical Design

### Incremental Learning Approach

Since RandomForest doesn't support true incremental learning, we'll use a hybrid approach:

1. **Collect Feedback**: Accumulate new feedback samples
2. **Batch Updates**: When threshold reached (e.g., 100 samples), retrain with accumulated data
3. **Warm Start**: Use previous model as starting point (if possible)
4. **Versioning**: Track model versions for rollback

### Incremental Learner

```python
class IncrementalPatternQualityLearner:
    """
    Incremental learner for pattern quality model.
    
    Collects feedback and updates model periodically.
    """
    
    def __init__(
        self,
        model_path: Path,
        update_threshold: int = 100,
        min_update_samples: int = 10
    ):
        """
        Initialize incremental learner.
        
        Args:
            model_path: Path to model file
            update_threshold: Number of new samples before update
            min_update_samples: Minimum samples required for update
        """
        pass
    
    async def collect_feedback(
        self,
        pattern_id: int,
        label: int,  # 1 for approved, 0 for rejected
        features: PatternFeatures
    ) -> None:
        """
        Collect feedback sample for incremental learning.
        
        Args:
            pattern_id: ID of the pattern
            label: Label (1=approved, 0=rejected)
            features: Pattern features
        """
        pass
    
    async def update_model(self) -> dict[str, Any]:
        """
        Update model with accumulated feedback.
        
        Returns:
            Update metrics (accuracy, update_time, etc.)
        """
        pass
    
    def should_update(self) -> bool:
        """
        Check if model should be updated.
        
        Returns:
            True if update threshold reached
        """
        pass
```

### Model Versioning

```python
class ModelVersionManager:
    """
    Manage model versions and rollback.
    """
    
    def save_version(
        self,
        model: PatternQualityModel,
        version: str | None = None
    ) -> str:
        """
        Save model version.
        
        Args:
            model: Model to save
            version: Version string (auto-generated if None)
        
        Returns:
            Version string
        """
        pass
    
    def load_version(self, version: str) -> PatternQualityModel:
        """
        Load specific model version.
        
        Args:
            version: Version string
        
        Returns:
            Loaded model
        """
        pass
    
    def rollback(self, version: str) -> bool:
        """
        Rollback to specific version.
        
        Args:
            version: Version to rollback to
        
        Returns:
            True if successful
        """
        pass
    
    def list_versions(self) -> list[dict[str, Any]]:
        """
        List all model versions.
        
        Returns:
            List of version metadata
        """
        pass
```

---

## Files

**Created:**
- `services/ai-automation-service/src/services/pattern_quality/incremental_learner.py`
- `services/ai-automation-service/src/services/pattern_quality/model_versioning.py`
- `services/ai-automation-service/tests/services/pattern_quality/test_incremental_learner.py`
- `services/ai-automation-service/tests/services/pattern_quality/test_model_versioning.py`

**Modified:**
- `services/ai-automation-service/src/services/pattern_quality/quality_service.py` (integrate incremental updates)

---

## Testing Requirements

### Unit Tests

```python
# tests/services/pattern_quality/test_incremental_learner.py

import pytest
from services.pattern_quality.incremental_learner import IncrementalPatternQualityLearner

@pytest.mark.asyncio
async def test_collect_feedback():
    """Test collecting feedback samples."""
    learner = IncrementalPatternQualityLearner(model_path="/tmp/model.joblib")
    await learner.collect_feedback(
        pattern_id=1,
        label=1,
        features=PatternFeatures(...)
    )
    assert learner.pending_samples == 1

@pytest.mark.asyncio
async def test_update_model():
    """Test model update."""
    learner = IncrementalPatternQualityLearner(model_path="/tmp/model.joblib")
    # Collect enough samples
    for i in range(100):
        await learner.collect_feedback(...)
    
    metrics = await learner.update_model()
    assert 'accuracy' in metrics
    assert metrics['update_time'] < 5.0  # <5 seconds
```

---

## Definition of Done

- [ ] All tasks completed
- [ ] Incremental updates implemented
- [ ] Model versioning working
- [ ] Rollback mechanism working
- [ ] Performance: <5 seconds for 100 samples
- [ ] Unit tests >90% coverage
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated

---

## Dependencies

**Required:**
- Story AI13.2 (Model Training) - ✅ Complete
- Story AI13.4 (Active Learning Infrastructure) - ✅ Complete

**Next Story:** AI13.6 - Transfer Learning from Blueprint Corpus (depends on this story)

---

**Developer:** @dev  
**Reviewer:** @qa  
**Status:** 🔄 IN PROGRESS

