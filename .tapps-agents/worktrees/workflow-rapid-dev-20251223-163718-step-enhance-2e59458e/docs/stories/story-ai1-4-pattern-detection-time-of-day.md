# Story AI1.4: Pattern Detection - Time-of-Day Clustering

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.4  
**Priority:** High  
**Estimated Effort:** 10-12 hours  
**Dependencies:** Story AI1.3 (Data API integration)

---

## User Story

**As a** pattern analyzer  
**I want** to detect time-of-day patterns using KMeans clustering  
**so that** I can identify when devices are consistently used

---

## Business Value

- Detects most common automation opportunity (devices used at consistent times)
- Foundation for automation suggestions ("turn on lights at 7 AM")
- Simple, proven algorithm (KMeans) with low resource usage
- High user value (time-based automations very common)

---

## Acceptance Criteria

1. ✅ Detects patterns for devices used at consistent times
2. ✅ Minimum 3 occurrences required for pattern (avoid noise)
3. ✅ Confidence score calculated as (occurrences / opportunities)
4. ✅ Only patterns >70% confidence stored
5. ✅ Processes 30 days of data in <5 minutes
6. ✅ Memory usage stays <500MB during analysis
7. ✅ Patterns stored in SQLite with timestamps
8. ✅ Unit tests cover edge cases (no data, sparse data, single occurrence)

---

## Technical Implementation Notes

### Pattern Detector Implementation

**Create: src/pattern_analyzer/time_of_day.py**

**Reference: PRD Section 7.1 Example 1**

```python
import pandas as pd
from sklearn.cluster import KMeans
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class TimeOfDayPatternDetector:
    """
    Detects time-of-day patterns using simple KMeans clustering.
    Finds when devices are consistently used at the same time.
    """
    
    def __init__(self, min_occurrences: int = 3, min_confidence: float = 0.7):
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence
    
    def detect_patterns(self, events: pd.DataFrame) -> List[Dict]:
        """
        Simple KMeans clustering to find consistent usage times.
        
        Args:
            events: DataFrame with columns [device_id, timestamp, state]
        
        Returns:
            List of patterns with confidence scores
        """
        
        # 1. Feature engineering (keep simple!)
        events['hour'] = events['timestamp'].dt.hour
        events['minute'] = events['timestamp'].dt.minute
        events['time_decimal'] = events['hour'] + events['minute'] / 60
        
        patterns = []
        
        # 2. Analyze each device separately
        for device_id in events['device_id'].unique():
            device_events = events[events['device_id'] == device_id]
            
            # Need minimum data
            if len(device_events) < 5:
                logger.debug(f"Skipping {device_id}: insufficient data ({len(device_events)} events)")
                continue
            
            # 3. Cluster time patterns (simple KMeans)
            times = device_events[['time_decimal']].values
            n_clusters = min(3, len(times))  # Max 3 clusters per device
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(times)
            
            # 4. Find consistent clusters (confidence = size / total)
            for cluster_id in range(n_clusters):
                cluster_times = times[labels == cluster_id]
                
                if len(cluster_times) >= self.min_occurrences:
                    avg_time = cluster_times.mean()
                    confidence = len(cluster_times) / len(times)
                    
                    if confidence >= self.min_confidence:
                        hour = int(avg_time)
                        minute = int((avg_time % 1) * 60)
                        
                        patterns.append({
                            'device_id': device_id,
                            'pattern_type': 'time_of_day',
                            'hour': hour,
                            'minute': minute,
                            'occurrences': int(len(cluster_times)),
                            'total_events': int(len(times)),
                            'confidence': float(confidence),
                            'metadata': {
                                'avg_time_decimal': float(avg_time),
                                'cluster_id': int(cluster_id),
                                'std_minutes': float(cluster_times.std() * 60)
                            }
                        })
                        
                        logger.info(
                            f"Pattern detected: {device_id} at {hour:02d}:{minute:02d} "
                            f"({len(cluster_times)}/{len(times)} = {confidence:.0%})"
                        )
        
        logger.info(f"Detected {len(patterns)} time-of-day patterns across {events['device_id'].nunique()} devices")
        return patterns

# That's it! ~60 lines, no complexity.
```

### Pattern Storage

**Reference database schema from PRD Section 7.3**

```python
# src/database/crud.py
async def store_patterns(db: AsyncSession, patterns: List[Dict]):
    """Store detected patterns in database"""
    from .models import Pattern
    from datetime import datetime
    
    for pattern_data in patterns:
        pattern = Pattern(
            pattern_type=pattern_data['pattern_type'],
            device_id=pattern_data['device_id'],
            metadata=pattern_data.get('metadata', {}),
            confidence=pattern_data['confidence'],
            occurrences=pattern_data['occurrences'],
            created_at=datetime.utcnow()
        )
        db.add(pattern)
    
    await db.commit()
    logger.info(f"Stored {len(patterns)} patterns in database")
```

---

## Integration Verification

**IV1: Data fetching doesn't impact other services**
- Monitor Data API CPU/memory before and during analysis
- Verify Health Dashboard still responsive
- Check no query timeouts

**IV2: Pattern analysis runs without blocking**
- Runs as async background job
- Doesn't block FastAPI server
- Can be cancelled gracefully

**IV3: SQLite database doesn't conflict with existing databases**
- Uses separate database file: `ai_automation.db`
- No connection to `metadata.db` or `webhooks.db`
- WAL mode for concurrent access

**IV4: Memory usage stays within NUC constraints**
- Peak memory <500MB (measured)
- Garbage collection after each device
- No memory leaks over 7-day run

---

## Tasks Breakdown

1. **Create TimeOfDayPatternDetector class** (2 hours)
2. **Implement feature engineering** (1 hour)
3. **Implement KMeans clustering** (2 hours)
4. **Add confidence scoring** (1 hour)
5. **Implement pattern persistence** (1.5 hours)
6. **Add logging and metrics** (1 hour)
7. **Unit tests with synthetic data** (1.5 hours)
8. **Integration test with real HA data** (1 hour)
9. **Performance optimization** (1 hour)

**Total:** 10-12 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_time_of_day_detector.py
import pytest
import pandas as pd
from src.pattern_analyzer.time_of_day import TimeOfDayPatternDetector

def create_test_events(device_id: str, times: List[str]) -> pd.DataFrame:
    """Helper to create test event data"""
    return pd.DataFrame({
        'device_id': [device_id] * len(times),
        'timestamp': pd.to_datetime(times),
        'state': ['on'] * len(times)
    })

def test_detects_consistent_morning_pattern():
    """Test detection of morning routine (lights on at 7 AM)"""
    events = create_test_events('light.bedroom', [
        '2025-10-01 07:00:00',
        '2025-10-02 07:01:00',
        '2025-10-03 06:59:00',
        '2025-10-04 07:00:00',
        '2025-10-05 07:02:00',
    ])
    
    detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.7)
    patterns = detector.detect_patterns(events)
    
    assert len(patterns) == 1
    assert patterns[0]['hour'] == 7
    assert patterns[0]['minute'] in [0, 1]  # Average around 7:00
    assert patterns[0]['confidence'] == 1.0  # All 5 events in one cluster

def test_skips_insufficient_data():
    """Test skips devices with <5 events"""
    events = create_test_events('light.bedroom', [
        '2025-10-01 07:00:00',
        '2025-10-02 08:00:00',
    ])
    
    detector = TimeOfDayPatternDetector()
    patterns = detector.detect_patterns(events)
    
    assert len(patterns) == 0  # Skipped due to insufficient data

def test_filters_low_confidence_patterns():
    """Test only keeps high-confidence patterns"""
    # Mix of times - no clear pattern
    events = create_test_events('light.bedroom', [
        '2025-10-01 07:00:00',
        '2025-10-02 08:00:00',
        '2025-10-03 14:00:00',
        '2025-10-04 19:00:00',
        '2025-10-05 22:00:00',
    ])
    
    detector = TimeOfDayPatternDetector(min_confidence=0.7)
    patterns = detector.detect_patterns(events)
    
    # No cluster should have >70% of events
    assert len(patterns) == 0 or all(p['confidence'] < 0.7 for p in patterns)
```

---

## Definition of Done

- [ ] TimeOfDayPatternDetector class implemented
- [ ] KMeans clustering working correctly
- [ ] Confidence scoring implemented
- [ ] Pattern persistence to SQLite
- [ ] Processes 30 days in <5 minutes
- [ ] Memory usage <500MB verified
- [ ] Unit tests pass (80%+ coverage)
- [ ] Integration test with real data passes
- [ ] Performance benchmarked and logged
- [ ] Code reviewed and approved

---

## Performance Benchmarks

**Target Performance:**
- 100 devices, 30 days (30k events): 3-5 minutes
- Memory peak: 300-500MB
- CPU usage: 60-80% during analysis

**Measure and Log:**
```python
logger.info("Pattern detection metrics", extra={
    'devices_analyzed': device_count,
    'events_processed': event_count,
    'patterns_detected': pattern_count,
    'duration_seconds': duration,
    'memory_peak_mb': memory_peak
})
```

---

## Reference Files

**Copy patterns from:**
- PRD Section 7.1 Example 1 (complete working code)
- scikit-learn KMeans documentation
- pandas DataFrame operations

---

## Notes

- **Keep it simple** - This is the MVP, don't optimize prematurely
- Use KMeans defaults (no hyperparameter tuning in Phase 1)
- Max 3 clusters per device (morning, evening, night)
- Log everything for debugging
- Measure performance to validate <5 minute target

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15


