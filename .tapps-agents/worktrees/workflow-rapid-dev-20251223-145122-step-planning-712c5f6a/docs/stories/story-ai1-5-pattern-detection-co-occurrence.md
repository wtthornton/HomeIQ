# Story AI1.5: Pattern Detection - Device Co-Occurrence

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.5  
**Priority:** High  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI1.4 (Time-of-day patterns)

---

## User Story

**As a** pattern analyzer  
**I want** to detect device co-occurrence patterns  
**so that** I can identify devices frequently used together

---

## Business Value

- Discovers device relationships ("when motion detected, lights turn on")
- Enables multi-device automation suggestions
- Identifies implicit user workflows
- Simple sliding window algorithm (fast, efficient)

---

## Acceptance Criteria

1. ✅ Detects devices used within 5-minute window
2. ✅ Minimum support threshold: 5 occurrences
3. ✅ Minimum confidence threshold: 70%
4. ✅ Patterns stored with device pairs and timing statistics
5. ✅ Processing time <3 minutes for 100 devices
6. ✅ Memory efficient (handles 10k+ event combinations)
7. ✅ Unit tests validate association rules
8. ✅ False positive rate <10% (manual validation)

---

## Technical Implementation Notes

### Co-Occurrence Detector

**Create: src/pattern_analyzer/co_occurrence.py**

**Reference: PRD Section 7.1 Example 2**

```python
import pandas as pd
from collections import defaultdict
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CoOccurrencePatternDetector:
    """
    Detects device co-occurrence patterns.
    Finds devices frequently used together within time window.
    """
    
    def __init__(
        self, 
        window_minutes: int = 5,
        min_support: int = 5,
        min_confidence: float = 0.7
    ):
        self.window_minutes = window_minutes
        self.min_support = min_support
        self.min_confidence = min_confidence
    
    def detect_patterns(self, events: pd.DataFrame) -> List[Dict]:
        """
        Find devices used together within time window.
        Simple approach: sliding window + counting.
        
        Args:
            events: DataFrame with columns [device_id, timestamp, state]
        
        Returns:
            List of co-occurrence patterns
        """
        
        # 1. Sort by time
        events = events.sort_values('timestamp').copy()
        
        # 2. Find co-occurrences
        co_occurrences = defaultdict(int)
        
        for i, event in events.iterrows():
            # Look ahead within window
            window_end = event['timestamp'] + pd.Timedelta(minutes=self.window_minutes)
            nearby = events[
                (events['timestamp'] > event['timestamp']) &
                (events['timestamp'] <= window_end)
            ]
            
            # Count co-occurrences
            for _, nearby_event in nearby.iterrows():
                if nearby_event['device_id'] != event['device_id']:
                    # Create sorted pair (avoid duplicates)
                    pair = tuple(sorted([event['device_id'], nearby_event['device_id']]))
                    co_occurrences[pair] += 1
        
        # 3. Filter for significant patterns
        patterns = []
        total_events = len(events)
        
        for (device1, device2), count in co_occurrences.items():
            support = count / total_events
            
            if count >= self.min_support and support >= self.min_confidence:
                patterns.append({
                    'pattern_type': 'co_occurrence',
                    'device1': device1,
                    'device2': device2,
                    'occurrences': int(count),
                    'total_events': int(total_events),
                    'confidence': float(support),
                    'metadata': {
                        'window_minutes': self.window_minutes,
                        'support': float(support)
                    }
                })
                
                logger.info(
                    f"Co-occurrence: {device1} + {device2} "
                    f"({count} times, {support:.0%} confidence)"
                )
        
        logger.info(f"Detected {len(patterns)} co-occurrence patterns")
        return patterns

# ~60 lines. Simple and effective.
```

### Performance Optimization

**For large datasets, use sampling:**

```python
def detect_patterns_optimized(self, events: pd.DataFrame) -> List[Dict]:
    """Optimized version for large event counts"""
    
    # If too many events, sample intelligently
    if len(events) > 50000:
        # Keep all recent events, sample older ones
        recent = events[events['timestamp'] > events['timestamp'].max() - pd.Timedelta(days=7)]
        older = events[events['timestamp'] <= events['timestamp'].max() - pd.Timedelta(days=7)]
        older_sampled = older.sample(n=min(20000, len(older)), random_state=42)
        events = pd.concat([recent, older_sampled]).sort_values('timestamp')
        logger.info(f"Sampled events for performance: {len(events)} events")
    
    return self.detect_patterns(events)
```

---

## Integration Verification

**IV1: Runs alongside time-of-day clustering without conflicts**
- Both detectors can run in same batch job
- No shared state between detectors
- SQLite handles concurrent pattern storage

**IV2: Doesn't duplicate patterns from Story 1.4**
- Co-occurrence distinct from time-of-day patterns
- Different pattern_type in database
- No overlap in suggestions generated

**IV3: SQLite transactions don't lock database**
- Use WAL mode for concurrent access
- Batch inserts for performance
- No long-running transactions

**IV4: Memory usage cumulative with Story 1.4 stays <1GB**
- Measure total memory during both detectors
- Garbage collect between detectors
- Log peak memory usage

---

## Tasks Breakdown

1. **Create CoOccurrencePatternDetector class** (2 hours)
2. **Implement sliding window logic** (2 hours)
3. **Calculate support and confidence** (1 hour)
4. **Add sampling for large datasets** (1.5 hours)
5. **Implement pattern storage** (1 hour)
6. **Unit tests** (1.5 hours)
7. **Integration test with real data** (1 hour)
8. **Performance testing and optimization** (1 hour)

**Total:** 8-10 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_co_occurrence_detector.py
import pytest
import pandas as pd
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector

def test_detects_motion_light_pattern():
    """Test detection of motion sensor + light pattern"""
    events = pd.DataFrame({
        'device_id': [
            'motion.hallway', 'light.hallway',  # Pair 1
            'motion.hallway', 'light.hallway',  # Pair 2
            'motion.hallway', 'light.hallway',  # Pair 3
            'motion.hallway', 'light.hallway',  # Pair 4
            'motion.hallway', 'light.hallway',  # Pair 5
        ],
        'timestamp': pd.to_datetime([
            '2025-10-01 18:00:00', '2025-10-01 18:00:30',
            '2025-10-02 18:01:00', '2025-10-02 18:01:25',
            '2025-10-03 18:02:00', '2025-10-03 18:02:20',
            '2025-10-04 18:00:00', '2025-10-04 18:00:15',
            '2025-10-05 18:01:00', '2025-10-05 18:01:40',
        ]),
        'state': ['on'] * 10
    })
    
    detector = CoOccurrencePatternDetector(window_minutes=5, min_support=3)
    patterns = detector.detect_patterns(events)
    
    assert len(patterns) >= 1
    pattern = patterns[0]
    assert set([pattern['device1'], pattern['device2']]) == {'motion.hallway', 'light.hallway'}
    assert pattern['occurrences'] >= 5

def test_respects_time_window():
    """Test only detects co-occurrences within window"""
    events = pd.DataFrame({
        'device_id': ['device_a', 'device_b', 'device_a', 'device_b'],
        'timestamp': pd.to_datetime([
            '2025-10-01 10:00:00',
            '2025-10-01 10:00:30',  # Within window (30 sec)
            '2025-10-02 10:00:00',
            '2025-10-02 10:10:00',  # Outside window (10 min)
        ]),
        'state': ['on'] * 4
    })
    
    detector = CoOccurrencePatternDetector(window_minutes=5, min_support=1)
    patterns = detector.detect_patterns(events)
    
    # Should detect only 1 co-occurrence (first pair within window)
    if len(patterns) > 0:
        assert patterns[0]['occurrences'] == 1
```

---

## Definition of Done

- [ ] CoOccurrencePatternDetector implemented
- [ ] Sliding window algorithm working
- [ ] Support and confidence calculated correctly
- [ ] Pattern storage to SQLite
- [ ] Performance optimized (<3 min for 100 devices)
- [ ] Memory efficient (handles 10k+ combinations)
- [ ] Unit tests pass (80%+ coverage)
- [ ] Integration test with real data
- [ ] False positive rate validated (<10%)
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- PRD Section 7.1 Example 2
- Story AI1.4 for pattern storage patterns

**Documentation:**
- Association Rule Mining: https://en.wikipedia.org/wiki/Association_rule_learning
- pandas sliding window: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html

---

## Notes

- 5-minute window is reasonable default (tune based on user feedback)
- Sorted pairs avoid duplicates (A,B) vs (B,A)
- Sampling strategy critical for large homes (>10k events)
- Consider directionality in Phase 2 (A before B vs A after B)

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15


