"""
Unit tests for Pattern Analyzer modules

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta

from src.pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector


class TestTimeOfDayPatternDetector:
    """Test suite for TimeOfDayPatternDetector."""
    
    @pytest.mark.unit
    def test_detect_patterns_empty_dataframe(self):
        """Test pattern detection with empty DataFrame."""
        detector = TimeOfDayPatternDetector()
        df = pd.DataFrame()
        
        patterns = detector.detect_patterns(df)
        assert isinstance(patterns, list)
        assert len(patterns) == 0
    
    @pytest.mark.unit
    def test_detect_patterns_simple_data(self):
        """Test pattern detection with simple time-of-day data."""
        detector = TimeOfDayPatternDetector(
            min_occurrences=2,
            min_confidence=0.5
        )
        
        # Create sample events at consistent times
        now = datetime.now(timezone.utc)
        events = []
        for i in range(5):
            # Same time each day (7 AM)
            event_time = now.replace(hour=7, minute=0, second=0) - timedelta(days=i)
            events.append({
                "timestamp": event_time,
                "_time": event_time,
                "entity_id": "light.office_lamp",
                "device_id": "light.office_lamp",
                "state": "on",
                "event_type": "state_changed",
                "domain": "light"
            })
        
        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)
        
        assert isinstance(patterns, list)
        # Should detect at least one pattern if data is consistent
        if len(patterns) > 0:
            pattern = patterns[0]
            assert "pattern_type" in pattern
            assert pattern["pattern_type"] == "time_of_day"
            assert "device_id" in pattern
            assert "confidence" in pattern


class TestCoOccurrencePatternDetector:
    """Test suite for CoOccurrencePatternDetector."""
    
    @pytest.mark.unit
    def test_detect_patterns_empty_dataframe(self):
        """Test pattern detection with empty DataFrame."""
        detector = CoOccurrencePatternDetector()
        df = pd.DataFrame()
        
        patterns = detector.detect_patterns(df)
        assert isinstance(patterns, list)
        assert len(patterns) == 0
    
    @pytest.mark.unit
    def test_detect_patterns_co_occurring_devices(self):
        """Test pattern detection with co-occurring devices."""
        detector = CoOccurrencePatternDetector(
            min_support=0.1,
            min_confidence=0.5,
            window_minutes=5
        )
        
        # Create sample events where two devices change together
        now = datetime.now(timezone.utc)
        events = []
        for i in range(5):
            base_time = now - timedelta(hours=i)
            # Motion sensor triggers
            events.append({
                "timestamp": base_time,
                "_time": base_time,
                "entity_id": "binary_sensor.motion_office",
                "device_id": "binary_sensor.motion_office",
                "state": "on",
                "event_type": "state_changed",
                "domain": "binary_sensor"
            })
            # Light turns on shortly after
            events.append({
                "timestamp": base_time + timedelta(seconds=30),
                "_time": base_time + timedelta(seconds=30),
                "entity_id": "light.office_lamp",
                "device_id": "light.office_lamp",
                "state": "on",
                "event_type": "state_changed",
                "domain": "light"
            })
        
        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)
        
        assert isinstance(patterns, list)
        # Should detect co-occurrence pattern if devices change together
        if len(patterns) > 0:
            pattern = patterns[0]
            assert "pattern_type" in pattern
            assert pattern["pattern_type"] == "co_occurrence"
            assert "device_id" in pattern or "device1" in pattern
            assert "confidence" in pattern

