"""
Test suite for ML-enhanced pattern detectors.

Tests the new sequence and contextual pattern detectors with various
scenarios and edge cases.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from services.ai_automation_service.src.pattern_detection.sequence_detector import SequenceDetector
from services.ai_automation_service.src.pattern_detection.contextual_detector import ContextualDetector


class TestSequenceDetector:
    """Test cases for SequenceDetector."""
    
    @pytest.fixture
    def sample_events_df(self):
        """Create sample events DataFrame for testing."""
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        
        events = []
        # Create a coffee maker -> kitchen light sequence (repeated 5 times)
        for day in range(5):
            day_time = base_time + timedelta(days=day)
            
            # Coffee maker turns on
            events.append({
                'time': day_time,
                'entity_id': 'switch.coffee_maker',
                'state': 'on',
                'area': 'kitchen'
            })
            
            # Kitchen light turns on 2 minutes later
            events.append({
                'time': day_time + timedelta(minutes=2),
                'entity_id': 'light.kitchen',
                'state': 'on',
                'area': 'kitchen'
            })
            
            # Music turns on 5 minutes later
            events.append({
                'time': day_time + timedelta(minutes=5),
                'entity_id': 'media_player.kitchen',
                'state': 'on',
                'area': 'kitchen'
            })
        
        return pd.DataFrame(events)
    
    @pytest.fixture
    def detector(self):
        """Create SequenceDetector instance for testing."""
        return SequenceDetector(
            window_minutes=30,
            min_sequence_length=2,
            min_sequence_occurrences=3,
            min_confidence=0.7
        )
    
    def test_sequence_detection_basic(self, detector, sample_events_df):
        """Test basic sequence detection."""
        patterns = detector.detect_patterns(sample_events_df)
        
        assert len(patterns) > 0
        assert all(p['pattern_type'] == 'sequence' for p in patterns)
        assert all(p['confidence'] >= 0.7 for p in patterns)
        assert all(p['occurrences'] >= 3 for p in patterns)
    
    def test_sequence_detection_with_gaps(self, detector):
        """Test sequence detection with time gaps."""
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        
        events = []
        # Create sequences with varying gaps
        for day in range(3):
            day_time = base_time + timedelta(days=day)
            
            events.append({
                'time': day_time,
                'entity_id': 'switch.coffee_maker',
                'state': 'on',
                'area': 'kitchen'
            })
            
            # 10-minute gap (should break sequence)
            events.append({
                'time': day_time + timedelta(minutes=10),
                'entity_id': 'light.kitchen',
                'state': 'on',
                'area': 'kitchen'
            })
        
        events_df = pd.DataFrame(events)
        patterns = detector.detect_patterns(events_df)
        
        # Should not detect sequences due to large gaps
        assert len(patterns) == 0
    
    def test_sequence_detection_insufficient_occurrences(self, detector):
        """Test sequence detection with insufficient occurrences."""
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        
        events = []
        # Create only 2 occurrences (below minimum of 3)
        for day in range(2):
            day_time = base_time + timedelta(days=day)
            
            events.append({
                'time': day_time,
                'entity_id': 'switch.coffee_maker',
                'state': 'on',
                'area': 'kitchen'
            })
            
            events.append({
                'time': day_time + timedelta(minutes=2),
                'entity_id': 'light.kitchen',
                'state': 'on',
                'area': 'kitchen'
            })
        
        events_df = pd.DataFrame(events)
        patterns = detector.detect_patterns(events_df)
        
        # Should not detect patterns due to insufficient occurrences
        assert len(patterns) == 0
    
    def test_sequence_detection_empty_dataframe(self, detector):
        """Test sequence detection with empty DataFrame."""
        empty_df = pd.DataFrame(columns=['time', 'entity_id', 'state', 'area'])
        patterns = detector.detect_patterns(empty_df)
        
        assert len(patterns) == 0
    
    def test_sequence_detection_invalid_dataframe(self, detector):
        """Test sequence detection with invalid DataFrame."""
        invalid_df = pd.DataFrame({'invalid': [1, 2, 3]})
        patterns = detector.detect_patterns(invalid_df)
        
        assert len(patterns) == 0
    
    def test_sequence_confidence_calculation(self, detector, sample_events_df):
        """Test sequence confidence calculation."""
        patterns = detector.detect_patterns(sample_events_df)
        
        for pattern in patterns:
            assert 0.0 <= pattern['confidence'] <= 1.0
            assert 'occurrences' in pattern
            assert 'devices' in pattern
            assert 'metadata' in pattern
    
    def test_sequence_metadata(self, detector, sample_events_df):
        """Test sequence pattern metadata."""
        patterns = detector.detect_patterns(sample_events_df)
        
        for pattern in patterns:
            metadata = pattern['metadata']
            assert 'sequence_length' in metadata
            assert 'duration_seconds' in metadata
            assert 'avg_gap_seconds' in metadata
            assert 'areas' in metadata
            assert 'sequence_states' in metadata


class TestContextualDetector:
    """Test cases for ContextualDetector."""
    
    @pytest.fixture
    def sample_contextual_events_df(self):
        """Create sample contextual events DataFrame for testing."""
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        
        events = []
        # Create morning routine events with context
        for day in range(10):
            day_time = base_time + timedelta(days=day)
            
            # Morning routine (7 AM, clear weather, home presence)
            events.append({
                'time': day_time,
                'entity_id': 'light.bedroom',
                'state': 'on',
                'area': 'bedroom',
                'temperature': 20.0,
                'humidity': 50.0,
                'weather_state': 'clear',
                'presence_detected': 1
            })
            
            events.append({
                'time': day_time + timedelta(minutes=5),
                'entity_id': 'switch.coffee_maker',
                'state': 'on',
                'area': 'kitchen',
                'temperature': 20.0,
                'humidity': 50.0,
                'weather_state': 'clear',
                'presence_detected': 1
            })
        
        return pd.DataFrame(events)
    
    @pytest.fixture
    def detector(self):
        """Create ContextualDetector instance for testing."""
        return ContextualDetector(
            weather_weight=0.3,
            presence_weight=0.4,
            time_weight=0.3,
            min_confidence=0.7
        )
    
    def test_contextual_detection_basic(self, detector, sample_contextual_events_df):
        """Test basic contextual pattern detection."""
        patterns = detector.detect_patterns(sample_contextual_events_df)
        
        assert len(patterns) > 0
        assert all(p['pattern_type'] in ['contextual', 'contextual_area'] for p in patterns)
        assert all(p['confidence'] >= 0.7 for p in patterns)
        assert all(p['occurrences'] >= 5 for p in patterns)
    
    def test_contextual_detection_without_context_data(self, detector):
        """Test contextual detection without context data."""
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        
        events = []
        for day in range(5):
            day_time = base_time + timedelta(days=day)
            
            events.append({
                'time': day_time,
                'entity_id': 'light.bedroom',
                'state': 'on',
                'area': 'bedroom'
            })
        
        events_df = pd.DataFrame(events)
        patterns = detector.detect_patterns(events_df)
        
        # Should still detect patterns with default context values
        assert len(patterns) > 0
    
    def test_contextual_detection_weather_variations(self, detector):
        """Test contextual detection with weather variations."""
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        
        events = []
        # Create events with different weather conditions
        weather_conditions = ['clear', 'cloudy', 'rainy', 'snowy']
        
        for i, weather in enumerate(weather_conditions):
            day_time = base_time + timedelta(days=i)
            
            events.append({
                'time': day_time,
                'entity_id': 'light.living_room',
                'state': 'on',
                'area': 'living_room',
                'temperature': 15.0 + i * 5,
                'humidity': 40.0 + i * 10,
                'weather_state': weather,
                'presence_detected': 1
            })
        
        events_df = pd.DataFrame(events)
        patterns = detector.detect_patterns(events_df)
        
        # Should detect different contextual patterns
        assert len(patterns) > 0
    
    def test_contextual_detection_time_features(self, detector):
        """Test contextual detection time feature extraction."""
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        
        events = []
        # Create events at different times
        times = [7, 12, 18, 22]  # Morning, noon, evening, night
        
        for i, hour in enumerate(times):
            day_time = base_time.replace(hour=hour) + timedelta(days=i)
            
            events.append({
                'time': day_time,
                'entity_id': 'light.bedroom',
                'state': 'on',
                'area': 'bedroom',
                'temperature': 20.0,
                'humidity': 50.0,
                'weather_state': 'clear',
                'presence_detected': 1
            })
        
        events_df = pd.DataFrame(events)
        patterns = detector.detect_patterns(events_df)
        
        # Should detect time-based contextual patterns
        assert len(patterns) > 0
    
    def test_contextual_detection_empty_dataframe(self, detector):
        """Test contextual detection with empty DataFrame."""
        empty_df = pd.DataFrame(columns=['time', 'entity_id', 'state', 'area'])
        patterns = detector.detect_patterns(empty_df)
        
        assert len(patterns) == 0
    
    def test_contextual_detection_invalid_dataframe(self, detector):
        """Test contextual detection with invalid DataFrame."""
        invalid_df = pd.DataFrame({'invalid': [1, 2, 3]})
        patterns = detector.detect_patterns(invalid_df)
        
        assert len(patterns) == 0
    
    def test_contextual_confidence_calculation(self, detector, sample_contextual_events_df):
        """Test contextual confidence calculation."""
        patterns = detector.detect_patterns(sample_contextual_events_df)
        
        for pattern in patterns:
            assert 0.0 <= pattern['confidence'] <= 1.0
            assert 'occurrences' in pattern
            assert 'devices' in pattern
            assert 'metadata' in pattern
    
    def test_contextual_metadata(self, detector, sample_contextual_events_df):
        """Test contextual pattern metadata."""
        patterns = detector.detect_patterns(sample_contextual_events_df)
        
        for pattern in patterns:
            metadata = pattern['metadata']
            assert 'context_key' in metadata
            assert 'context_parsed' in metadata
            assert 'first_occurrence' in metadata
            assert 'last_occurrence' in metadata


class TestMLPatternDetectorIntegration:
    """Integration tests for ML pattern detectors."""
    
    def test_detector_statistics(self):
        """Test detector statistics tracking."""
        detector = SequenceDetector()
        
        # Create sample data
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        events = []
        
        for day in range(5):
            day_time = base_time + timedelta(days=day)
            
            events.append({
                'time': day_time,
                'entity_id': 'switch.coffee_maker',
                'state': 'on',
                'area': 'kitchen'
            })
            
            events.append({
                'time': day_time + timedelta(minutes=2),
                'entity_id': 'light.kitchen',
                'state': 'on',
                'area': 'kitchen'
            })
        
        events_df = pd.DataFrame(events)
        patterns = detector.detect_patterns(events_df)
        
        # Check statistics
        stats = detector.get_detection_stats()
        assert stats['total_patterns'] > 0
        assert stats['processing_time'] > 0
    
    def test_detector_reset_stats(self):
        """Test detector statistics reset."""
        detector = SequenceDetector()
        
        # Run detection to generate stats
        base_time = datetime(2024, 1, 1, 7, 0, 0)
        events = []
        
        for day in range(3):
            day_time = base_time + timedelta(days=day)
            
            events.append({
                'time': day_time,
                'entity_id': 'switch.coffee_maker',
                'state': 'on',
                'area': 'kitchen'
            })
            
            events.append({
                'time': day_time + timedelta(minutes=2),
                'entity_id': 'light.kitchen',
                'state': 'on',
                'area': 'kitchen'
            })
        
        events_df = pd.DataFrame(events)
        detector.detect_patterns(events_df)
        
        # Reset stats
        detector.reset_stats()
        stats = detector.get_detection_stats()
        
        assert stats['total_patterns'] == 0
        assert stats['processing_time'] == 0.0
    
    def test_detector_validation(self):
        """Test detector input validation."""
        detector = SequenceDetector()
        
        # Test with missing required columns
        invalid_df = pd.DataFrame({'time': [datetime.now()], 'invalid': ['test']})
        patterns = detector.detect_patterns(invalid_df)
        
        assert len(patterns) == 0
        
        # Test with empty DataFrame
        empty_df = pd.DataFrame(columns=['time', 'entity_id', 'state'])
        patterns = detector.detect_patterns(empty_df)
        
        assert len(patterns) == 0


if __name__ == '__main__':
    pytest.main([__file__])
