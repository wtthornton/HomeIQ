# Story AI13.4: Active Learning Infrastructure

**Epic:** AI-13 - ML-Based Pattern Quality & Active Learning  
**Story ID:** AI13.4  
**Type:** Foundation  
**Points:** 4  
**Status:** ✅ **COMPLETE**  
**Estimated Effort:** 8-10 hours  
**Created:** December 2025  
**Dependencies:** Story AI13.1 (Feature Engineering)

---

## Story Description

Build infrastructure for active learning from user feedback. This enables the system to learn from user approvals, rejections, and entity selections to continuously improve pattern quality predictions.

**Current State:**
- UserFeedback model exists for suggestions (approved/rejected/modified)
- No pattern-level feedback tracking
- No feedback aggregation for patterns
- No infrastructure for active learning

**Target:**
- Track pattern-level feedback (approvals, rejections, entity selections)
- Aggregate feedback by pattern
- Store feedback in database
- Provide feedback analysis and statistics
- Enable incremental model updates from feedback
- Unit tests >90% coverage

---

## Acceptance Criteria

- [ ] Track user approvals for patterns (positive examples)
- [ ] Track user rejections for patterns (negative examples)
- [ ] Track entity selections (preference signals)
- [ ] Store feedback in database
- [ ] Feedback aggregation and analysis
- [ ] Unit tests for active learning infrastructure (>90% coverage)

---

## Tasks

### Task 1: Create Pattern Feedback Tracker
- [x] Create `pattern_feedback_tracker.py` with `PatternFeedbackTracker` class
- [x] Implement approval tracking
- [x] Implement rejection tracking
- [x] Implement entity selection tracking
- [x] Implement feedback storage

### Task 2: Create Feedback Aggregator
- [x] Create feedback aggregation methods
- [x] Calculate approval rate per pattern
- [x] Calculate rejection rate per pattern
- [x] Track entity preference patterns
- [x] Generate feedback statistics

### Task 3: Database Integration
- [x] Use existing UserFeedback model (via suggestion.pattern_id)
- [x] Link feedback to patterns via suggestions
- [x] Store feedback metadata in pattern.pattern_metadata

### Task 4: Feedback Analysis
- [x] Analyze feedback trends
- [x] Identify high-quality patterns (high approval rate)
- [x] Identify low-quality patterns (high rejection rate)
- [x] Generate feedback statistics

### Task 5: Unit Tests
- [x] Test approval tracking
- [x] Test rejection tracking
- [x] Test entity selection tracking
- [x] Test feedback aggregation
- [x] Test feedback analysis
- [x] Achieve >90% coverage

---

## Technical Design

### Pattern Feedback Tracker

```python
from typing import Any
from datetime import datetime, timezone
import logging

from database.models import Pattern, UserFeedback, Suggestion
from database.crud import get_db_session

logger = logging.getLogger(__name__)


class PatternFeedbackTracker:
    """
    Track user feedback for patterns to enable active learning.
    """
    
    async def track_approval(
        self,
        pattern_id: int,
        suggestion_id: int | None = None,
        feedback_text: str | None = None
    ) -> UserFeedback:
        """
        Track user approval of a pattern.
        
        Args:
            pattern_id: ID of the pattern
            suggestion_id: ID of the suggestion (if from suggestion)
            feedback_text: Optional feedback text
        
        Returns:
            Stored UserFeedback
        """
        pass
    
    async def track_rejection(
        self,
        pattern_id: int,
        suggestion_id: int | None = None,
        feedback_text: str | None = None
    ) -> UserFeedback:
        """
        Track user rejection of a pattern.
        
        Args:
            pattern_id: ID of the pattern
            suggestion_id: ID of the suggestion (if from suggestion)
            feedback_text: Optional feedback text
        
        Returns:
            Stored UserFeedback
        """
        pass
    
    async def track_entity_selection(
        self,
        pattern_id: int,
        selected_entities: list[str],
        suggestion_id: int | None = None
    ) -> dict:
        """
        Track entity selections (preference signals).
        
        Args:
            pattern_id: ID of the pattern
            selected_entities: List of selected entity IDs
            suggestion_id: ID of the suggestion (if from suggestion)
        
        Returns:
            Tracking metadata
        """
        pass
    
    async def get_pattern_feedback(
        self,
        pattern_id: int
    ) -> dict[str, Any]:
        """
        Get aggregated feedback for a pattern.
        
        Args:
            pattern_id: ID of the pattern
        
        Returns:
            Feedback statistics (approvals, rejections, approval_rate, etc.)
        """
        pass
    
    async def get_feedback_statistics(
        self,
        pattern_ids: list[int] | None = None
    ) -> dict[str, Any]:
        """
        Get feedback statistics for patterns.
        
        Args:
            pattern_ids: Optional list of pattern IDs to filter
        
        Returns:
            Overall feedback statistics
        """
        pass
```

### Feedback Aggregation

```python
class PatternFeedbackAggregator:
    """
    Aggregate and analyze pattern feedback.
    """
    
    async def aggregate_feedback(
        self,
        pattern_id: int
    ) -> dict[str, Any]:
        """
        Aggregate feedback for a pattern.
        
        Returns:
            {
                'pattern_id': int,
                'approvals': int,
                'rejections': int,
                'approval_rate': float,
                'total_feedback': int,
                'last_feedback': datetime,
                'entity_selections': dict
            }
        """
        pass
    
    async def identify_high_quality_patterns(
        self,
        min_approval_rate: float = 0.8,
        min_feedback_count: int = 5
    ) -> list[int]:
        """
        Identify patterns with high approval rates.
        
        Args:
            min_approval_rate: Minimum approval rate (0.0-1.0)
            min_feedback_count: Minimum number of feedback samples
        
        Returns:
            List of pattern IDs
        """
        pass
    
    async def identify_low_quality_patterns(
        self,
        max_approval_rate: float = 0.3,
        min_feedback_count: int = 5
    ) -> list[int]:
        """
        Identify patterns with low approval rates.
        
        Args:
            max_approval_rate: Maximum approval rate (0.0-1.0)
            min_feedback_count: Minimum number of feedback samples
        
        Returns:
            List of pattern IDs
        """
        pass
```

---

## Files

**Created:**
- `services/ai-automation-service/src/services/learning/pattern_feedback_tracker.py`
- `services/ai-automation-service/src/services/learning/feedback_aggregator.py`
- `services/ai-automation-service/tests/services/learning/test_pattern_feedback_tracker.py`
- `services/ai-automation-service/tests/services/learning/test_feedback_aggregator.py`

**Modified:**
- `services/ai-automation-service/src/database/models.py` (may need PatternFeedback model or enhance UserFeedback)
- `services/ai-automation-service/src/database/crud.py` (add pattern feedback CRUD)

---

## Testing Requirements

### Unit Tests

```python
# tests/services/learning/test_pattern_feedback_tracker.py

import pytest
from unittest.mock import AsyncMock, Mock
from services.learning.pattern_feedback_tracker import PatternFeedbackTracker

@pytest.mark.asyncio
async def test_track_approval():
    """Test tracking pattern approval."""
    tracker = PatternFeedbackTracker()
    feedback = await tracker.track_approval(
        pattern_id=1,
        suggestion_id=10,
        feedback_text="Great pattern!"
    )
    assert feedback.action == 'approved'
    assert feedback.suggestion_id == 10

@pytest.mark.asyncio
async def test_track_rejection():
    """Test tracking pattern rejection."""
    tracker = PatternFeedbackTracker()
    feedback = await tracker.track_rejection(
        pattern_id=1,
        suggestion_id=10,
        feedback_text="Not useful"
    )
    assert feedback.action == 'rejected'

@pytest.mark.asyncio
async def test_get_pattern_feedback():
    """Test getting aggregated feedback."""
    tracker = PatternFeedbackTracker()
    stats = await tracker.get_pattern_feedback(pattern_id=1)
    assert 'approvals' in stats
    assert 'rejections' in stats
    assert 'approval_rate' in stats
```

---

## Definition of Done

- [ ] All tasks completed
- [ ] Pattern feedback tracking implemented
- [ ] Feedback aggregation implemented
- [ ] Database integration complete
- [ ] Feedback analysis working
- [ ] Unit tests >90% coverage
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated

---

## Dependencies

**Required:**
- Story AI13.1 (Feature Engineering) - ✅ Complete

**Next Story:** AI13.5 - Incremental Model Updates (depends on this story)

---

**Developer:** @dev  
**Reviewer:** @qa  
**Status:** 🔄 IN PROGRESS

