# Story AI1.6: Pattern Detection - Anomaly Detection

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.6  
**Priority:** High  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI1.5 (Co-occurrence patterns)

---

## User Story

**As a** pattern analyzer  
**I want** to detect anomalies indicating automation opportunities  
**so that** I can suggest automations for repeated manual interventions

---

## Business Value

- Discovers unmet automation needs (repeated manual actions)
- Identifies user pain points (things they do manually but could automate)
- Uses Isolation Forest to find "too regular" manual interventions
- High-value patterns (user already doing this manually)

---

## Acceptance Criteria

1. ✅ Detects repeated manual interventions (same device, similar time)
2. ✅ Minimum 3 occurrences to qualify as pattern
3. ✅ Differentiates anomalies from random actions
4. ✅ Confidence score based on repetition consistency
5. ✅ Processing time <2 minutes for 30 days of data
6. ✅ Memory usage <300MB
7. ✅ Unit tests validate anomaly vs noise distinction
8. ✅ Precision >60% (manual validation on test data)

---

## Technical Implementation Notes

### Anomaly Detector

**Create: src/pattern_analyzer/anomaly_detector.py**

**Reference: PRD Section 7.1 Example 3**

```python
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class AnomalyPatternDetector:
    """
    Detects automation opportunities from anomalies.
    
    Key Insight: Regular manual interventions = automation opportunities.
    We use Isolation Forest INVERTED - find regular patterns, not anomalies.
    """
    
    def __init__(self, min_occurrences: int = 3, min_confidence: float = 0.6):
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence
    
    def detect_patterns(self, events: pd.DataFrame) -> List[Dict]:
        """
        Find repeated manual interventions = automation opportunities.
        Use Isolation Forest to find "too regular" patterns.
        
        Args:
            events: DataFrame with columns [device_id, timestamp, state]
        
        Returns:
            List of automation opportunity patterns
        """
        
        # 1. Feature engineering
        events['hour'] = events['timestamp'].dt.hour
        events['day_of_week'] = events['timestamp'].dt.dayofweek
        events['is_weekend'] = events['day_of_week'] >= 5
        
        patterns = []
        
        # 2. Analyze each device
        for device_id in events['device_id'].unique():
            device_events = events[events['device_id'] == device_id]
            
            if len(device_events) < 10:
                continue
            
            # 3. Create features for Isolation Forest
            features = device_events[['hour', 'day_of_week']].values
            
            # 4. Isolation Forest (contamination = expected anomaly rate)
            iso_forest = IsolationForest(
                contamination=0.1,  # Expect 10% to be regular patterns
                random_state=42
            )
            scores = iso_forest.fit_predict(features)
            
            # 5. Regular patterns (inliers, NOT anomalies) = automation candidates
            # Inliers have score = 1, outliers have score = -1
            regular = device_events[scores == 1]
            
            # 6. Group by hour to find repeated times
            for hour in regular['hour'].unique():
                hour_events = regular[regular['hour'] == hour]
                
                if len(hour_events) >= self.min_occurrences:
                    confidence = len(hour_events) / len(device_events)
                    
                    if confidence >= self.min_confidence:
                        # Check if weekday pattern
                        weekday_ratio = (hour_events['day_of_week'] < 5).sum() / len(hour_events)
                        
                        patterns.append({
                            'device_id': device_id,
                            'pattern_type': 'anomaly_opportunity',
                            'hour': int(hour),
                            'occurrences': int(len(hour_events)),
                            'total_events': int(len(device_events)),
                            'confidence': float(confidence),
                            'metadata': {
                                'weekday_ratio': float(weekday_ratio),
                                'is_weekday_only': weekday_ratio > 0.8,
                                'avg_day_of_week': float(hour_events['day_of_week'].mean())
                            }
                        })
                        
                        logger.info(
                            f"Automation opportunity: {device_id} at {hour}:00 "
                            f"({len(hour_events)} times, {confidence:.0%} confidence)"
                        )
        
        logger.info(f"Detected {len(patterns)} automation opportunities")
        return patterns

# ~70 lines. Isolation Forest as pattern detector.
```

### Integration with Other Detectors

```python
# src/pattern_analyzer/coordinator.py
from .time_of_day import TimeOfDayPatternDetector
from .co_occurrence import CoOccurrencePatternDetector
from .anomaly_detector import AnomalyPatternDetector

class PatternAnalysisCoordinator:
    """Runs all pattern detectors and combines results"""
    
    def __init__(self):
        self.time_detector = TimeOfDayPatternDetector()
        self.cooccur_detector = CoOccurrencePatternDetector()
        self.anomaly_detector = AnomalyPatternDetector()
    
    async def analyze_all_patterns(self, events: pd.DataFrame) -> Dict:
        """Run all 3 pattern detectors"""
        
        logger.info("Starting pattern analysis on {len(events)} events")
        
        # Run detectors (can be parallelized in Phase 2)
        time_patterns = self.time_detector.detect_patterns(events)
        cooccur_patterns = self.cooccur_detector.detect_patterns(events)
        anomaly_patterns = self.anomaly_detector.detect_patterns(events)
        
        results = {
            'time_of_day': time_patterns,
            'co_occurrence': cooccur_patterns,
            'anomaly_opportunities': anomaly_patterns,
            'total_patterns': len(time_patterns) + len(cooccur_patterns) + len(anomaly_patterns)
        }
        
        logger.info(f"Analysis complete: {results['total_patterns']} patterns detected")
        return results
```

---

## Integration Verification

**IV1: Runs alongside other pattern detectors**
- All 3 detectors run in same batch job
- No conflicts in pattern storage
- Total time: sum of individual detectors

**IV2: Anomaly patterns don't duplicate time-of-day patterns**
- Different pattern_type in database
- May detect same device/time but different rationale
- Deduplication in LLM generation (Story 1.8)

**IV3: Total pattern detection time <10 minutes**
- Time-of-day: ~5 min
- Co-occurrence: ~3 min
- Anomaly: ~2 min
- Total: ~10 min (acceptable)

**IV4: Combined memory usage <1GB peak**
- Each detector: 300-500MB
- Run sequentially (not parallel) to control memory
- Garbage collect between detectors

---

## Tasks Breakdown

1. **Create AnomalyPatternDetector class** (2 hours)
2. **Implement Isolation Forest logic** (2 hours)
3. **Define automation opportunity criteria** (1.5 hours)
4. **Calculate confidence scoring** (1 hour)
5. **Implement pattern storage** (1 hour)
6. **Create pattern coordinator** (1.5 hours)
7. **Unit tests** (1.5 hours)
8. **Manual validation of detected patterns** (1 hour)

**Total:** 8-10 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_anomaly_detector.py
import pytest
import pandas as pd
from src.pattern_analyzer.anomaly_detector import AnomalyPatternDetector

def test_detects_repeated_manual_intervention():
    """Test detection of manual thermostat adjustment every morning"""
    # User manually adjusts thermostat at 6 AM daily
    events = pd.DataFrame({
        'device_id': ['climate.bedroom'] * 20,
        'timestamp': pd.date_range('2025-10-01 06:00', periods=20, freq='D'),
        'state': [72] * 20  # Set to 72°F every day
    })
    
    detector = AnomalyPatternDetector(min_occurrences=3)
    patterns = detector.detect_patterns(events)
    
    assert len(patterns) >= 1
    pattern = patterns[0]
    assert pattern['device_id'] == 'climate.bedroom'
    assert pattern['hour'] == 6
    assert pattern['occurrences'] >= 15  # Most days

def test_filters_random_actions():
    """Test ignores truly random actions"""
    # Random device usage at various times
    events = pd.DataFrame({
        'device_id': ['light.bedroom'] * 20,
        'timestamp': pd.to_datetime([
            '2025-10-01 06:00', '2025-10-02 14:00', '2025-10-03 22:00',
            '2025-10-04 09:00', '2025-10-05 16:00', '2025-10-06 19:00',
            # ... random times
        ] * 3 + ['2025-10-20 11:00', '2025-10-21 23:00']),
        'state': ['on'] * 20
    })
    
    detector = AnomalyPatternDetector(min_confidence=0.6)
    patterns = detector.detect_patterns(events)
    
    # Should not detect patterns in random data
    assert len(patterns) == 0 or all(p['confidence'] < 0.3 for p in patterns)
```

---

## Definition of Done

- [ ] AnomalyPatternDetector class implemented
- [ ] Isolation Forest configured correctly
- [ ] Automation opportunity criteria defined
- [ ] Confidence scoring implemented
- [ ] Pattern storage to SQLite
- [ ] Pattern coordinator created
- [ ] Processes 30 days in <2 minutes
- [ ] Memory usage <300MB verified
- [ ] Unit tests pass (80%+ coverage)
- [ ] Manual validation on real data >60% precision
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- PRD Section 7.1 Example 3 (complete working code)
- scikit-learn Isolation Forest docs
- Story AI1.4 for pattern storage patterns

**Documentation:**
- Isolation Forest: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- Anomaly Detection: https://scikit-learn.org/stable/modules/outlier_detection.html

---

## Notes

- **Key insight:** We're using Isolation Forest INVERTED
- Inliers (regular patterns) = automation opportunities
- Outliers (actual anomalies) = ignore
- This is counterintuitive but correct for our use case
- Contamination=0.1 means expect 10% regular patterns
- Tune contamination based on real data in testing

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

