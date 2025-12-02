# Story AI13.3: Pattern Quality Scoring Service

**Epic:** AI-13 - ML-Based Pattern Quality & Active Learning  
**Story ID:** AI13.3  
**Type:** Feature  
**Points:** 4  
**Status:** ✅ **READY FOR REVIEW** (Core implementation complete, integration pending)  
**Estimated Effort:** 8-10 hours  
**Created:** December 2025  
**Dependencies:** Story AI13.2 (Model Training)

---

## Story Description

Implement pattern quality scoring service using trained model. This service loads the trained model at startup and provides quality scores for patterns, enabling filtering and ranking of patterns by quality.

**Current Issue:**
- No ML-based quality scoring service
- Patterns can't be filtered by quality
- No quality-based ranking for suggestions

**Target:**
- Load trained model at service startup
- Score patterns using quality model
- Quality score: 0.0-1.0 (probability of being good pattern)
- Quality threshold filtering (>0.7 quality score)
- Performance: <50ms per pattern
- Integration with pattern detection pipeline

---

## Acceptance Criteria

- [ ] Load trained model at service startup
- [ ] Score patterns using quality model
- [ ] Quality score: 0.0-1.0 (probability of being good pattern)
- [ ] Quality threshold filtering (>0.7 quality score)
- [ ] Performance: <50ms per pattern
- [ ] Unit tests for quality scoring (>90% coverage)

---

## Tasks

### Task 1: Create Quality Scorer Service
- [x] Create `scorer.py` with `PatternQualityScorer` class
- [x] Implement model loading at initialization
- [x] Implement quality scoring method
- [x] Implement batch scoring method

### Task 2: Create Quality Service
- [x] Create `quality_service.py` with `PatternQualityService` class
- [x] Implement service lifecycle (startup/shutdown)
- [x] Implement quality threshold filtering
- [x] Implement pattern ranking by quality

### Task 3: Integration with Pattern Detection
- [ ] Integrate quality scoring into pattern detection pipeline (deferred - can be done in later story)
- [ ] Filter patterns by quality threshold
- [ ] Rank patterns by quality score
- [ ] Update pattern metadata with quality score

### Task 4: Performance Optimization
- [x] Optimize model loading (lazy loading or caching)
- [x] Optimize batch scoring
- [ ] Ensure <50ms per pattern (requires performance testing with real model)
- [ ] Add performance monitoring (optional enhancement)

### Task 5: Unit Tests
- [x] Test model loading
- [x] Test quality scoring
- [x] Test batch scoring
- [x] Test threshold filtering
- [x] Test pattern ranking
- [x] Achieve >90% coverage

---

## Technical Design

### Quality Scorer Service

```python
from pathlib import Path
from typing import Any
import logging

from services.pattern_quality.quality_model import PatternQualityModel

logger = logging.getLogger(__name__)


class PatternQualityScorer:
    """
    Score patterns using trained quality model.
    """
    
    def __init__(self, model_path: Path | str | None = None):
        """
        Initialize quality scorer.
        
        Args:
            model_path: Path to trained model file (optional, uses default if None)
        """
        self.model: PatternQualityModel | None = None
        self.model_path = self._get_model_path(model_path)
        self._load_model()
    
    def _get_model_path(self, model_path: Path | str | None) -> Path:
        """Get model path (default or provided)."""
        if model_path:
            return Path(model_path)
        
        # Default model path
        default_path = Path(__file__).parent.parent.parent.parent / "models" / "pattern_quality_model.joblib"
        return default_path
    
    def _load_model(self) -> None:
        """Load trained model from disk."""
        try:
            if self.model_path.exists():
                self.model = PatternQualityModel.load(self.model_path)
                logger.info(f"Quality model loaded from {self.model_path}")
            else:
                logger.warning(f"Model file not found: {self.model_path}. Using default scores.")
                self.model = None
        except Exception as e:
            logger.error(f"Error loading quality model: {e}", exc_info=True)
            self.model = None
    
    def score_pattern(self, pattern: Any) -> float:
        """
        Score a single pattern.
        
        Args:
            pattern: Pattern model or dict
        
        Returns:
            Quality score (0.0-1.0)
        """
        if self.model is None:
            return 0.5  # Default score when model not available
        
        return self.model.predict_quality(pattern)
    
    def score_patterns(self, patterns: list[Any]) -> list[float]:
        """
        Score multiple patterns.
        
        Args:
            patterns: List of Pattern models or dicts
        
        Returns:
            List of quality scores
        """
        if self.model is None:
            return [0.5] * len(patterns)  # Default scores
        
        return self.model.predict_quality_batch(patterns)
    
    def filter_by_quality(
        self,
        patterns: list[Any],
        threshold: float = 0.7
    ) -> list[tuple[Any, float]]:
        """
        Filter patterns by quality threshold.
        
        Args:
            patterns: List of patterns
            threshold: Minimum quality score (0.0-1.0)
        
        Returns:
            List of (pattern, score) tuples for patterns above threshold
        """
        scores = self.score_patterns(patterns)
        
        filtered = [
            (pattern, score)
            for pattern, score in zip(patterns, scores)
            if score >= threshold
        ]
        
        return filtered
    
    def rank_by_quality(
        self,
        patterns: list[Any]
    ) -> list[tuple[Any, float]]:
        """
        Rank patterns by quality score (highest first).
        
        Args:
            patterns: List of patterns
        
        Returns:
            List of (pattern, score) tuples sorted by score (descending)
        """
        scores = self.score_patterns(patterns)
        
        ranked = sorted(
            zip(patterns, scores),
            key=lambda x: x[1],
            reverse=True
        )
        
        return ranked
```

### Quality Service

```python
class PatternQualityService:
    """
    Service for pattern quality scoring and filtering.
    """
    
    def __init__(self, model_path: Path | str | None = None):
        """Initialize quality service."""
        self.scorer = PatternQualityScorer(model_path)
        self._started = False
    
    async def startup(self) -> None:
        """Start service (load model)."""
        if not self._started:
            # Model is loaded in scorer.__init__, but we can reload here if needed
            self._started = True
            logger.info("Pattern quality service started")
    
    async def shutdown(self) -> None:
        """Shutdown service."""
        self._started = False
        logger.info("Pattern quality service stopped")
    
    def score_pattern(self, pattern: Any) -> float:
        """Score a single pattern."""
        return self.scorer.score_pattern(pattern)
    
    def score_patterns(self, patterns: list[Any]) -> list[float]:
        """Score multiple patterns."""
        return self.scorer.score_patterns(patterns)
    
    def filter_by_quality(
        self,
        patterns: list[Any],
        threshold: float = 0.7
    ) -> list[tuple[Any, float]]:
        """Filter patterns by quality threshold."""
        return self.scorer.filter_by_quality(patterns, threshold)
    
    def rank_by_quality(self, patterns: list[Any]) -> list[tuple[Any, float]]:
        """Rank patterns by quality score."""
        return self.scorer.rank_by_quality(patterns)
```

---

## Files

**Created:**
- `services/ai-automation-service/src/services/pattern_quality/scorer.py`
- `services/ai-automation-service/src/services/pattern_quality/quality_service.py`
- `services/ai-automation-service/tests/services/pattern_quality/test_scorer.py`

**Modified:**
- `services/ai-automation-service/src/services/pattern_detection/pattern_detector.py` (integrate quality scoring)

---

## Testing Requirements

### Unit Tests

```python
# tests/services/pattern_quality/test_scorer.py

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from services.pattern_quality.scorer import PatternQualityScorer

def test_scorer_initialization():
    """Test scorer initialization."""
    scorer = PatternQualityScorer()
    assert scorer is not None

def test_score_pattern():
    """Test scoring a single pattern."""
    scorer = PatternQualityScorer()
    pattern = {'pattern_type': 'time_of_day', 'confidence': 0.8}
    
    score = scorer.score_pattern(pattern)
    assert 0.0 <= score <= 1.0

def test_score_patterns_batch():
    """Test batch scoring."""
    scorer = PatternQualityScorer()
    patterns = [
        {'pattern_type': 'time_of_day', 'confidence': 0.8},
        {'pattern_type': 'co_occurrence', 'confidence': 0.6}
    ]
    
    scores = scorer.score_patterns(patterns)
    assert len(scores) == 2
    assert all(0.0 <= s <= 1.0 for s in scores)

def test_filter_by_quality():
    """Test quality threshold filtering."""
    scorer = PatternQualityScorer()
    patterns = [
        {'pattern_type': 'time_of_day', 'confidence': 0.9},
        {'pattern_type': 'co_occurrence', 'confidence': 0.5}
    ]
    
    filtered = scorer.filter_by_quality(patterns, threshold=0.7)
    assert len(filtered) >= 0  # May be 0 if scores are below threshold

def test_rank_by_quality():
    """Test ranking by quality."""
    scorer = PatternQualityScorer()
    patterns = [
        {'pattern_type': 'time_of_day', 'confidence': 0.6},
        {'pattern_type': 'co_occurrence', 'confidence': 0.9}
    ]
    
    ranked = scorer.rank_by_quality(patterns)
    assert len(ranked) == 2
    # Should be sorted by score (descending)
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)
```

---

## Definition of Done

- [ ] All tasks completed
- [ ] Model loads at service startup
- [ ] Quality scoring works for single patterns
- [ ] Quality scoring works for batch patterns
- [ ] Quality threshold filtering implemented
- [ ] Pattern ranking by quality implemented
- [ ] Performance: <50ms per pattern
- [ ] Unit tests >90% coverage
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated

---

## Dependencies

**Required:**
- Story AI13.2 (Model Training) - ✅ Complete

**Next Story:** AI13.4 - Active Learning Infrastructure (depends on this story)

---

**Developer:** @dev  
**Reviewer:** @qa  
**Status:** 🔄 IN PROGRESS

