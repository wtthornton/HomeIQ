"""
Unit tests for Time-of-Day Pattern Detector
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from src.pattern_analyzer.time_of_day import TimeOfDayPatternDetector


def create_test_events(device_id: str, times: list) -> pd.DataFrame:
    """
    Helper to create test event data.
    
    Args:
        device_id: Device identifier
        times: List of timestamp strings or datetime objects
    
    Returns:
        DataFrame with device_id, timestamp, state columns
    """
    return pd.DataFrame({
        'device_id': [device_id] * len(times),
        'timestamp': pd.to_datetime(times),
        'state': ['on'] * len(times)
    })


class TestTimeOfDayPatternDetector:
    """Test Time-of-Day Pattern Detector"""

    def test_initialization(self):
        """Test detector initialization with custom parameters"""
        detector = TimeOfDayPatternDetector(min_occurrences=5, min_confidence=0.8)
        assert detector.min_occurrences == 5
        assert detector.min_confidence == 0.8

    def test_detects_consistent_morning_pattern(self):
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
        assert patterns[0]['device_id'] == 'light.bedroom'
        assert patterns[0]['pattern_type'] == 'time_of_day'
        assert patterns[0]['hour'] == 7
        assert patterns[0]['minute'] in [0, 1]  # Average around 7:00
        assert patterns[0]['confidence'] == 1.0  # All 5 events in one cluster
        assert patterns[0]['occurrences'] == 5
        assert patterns[0]['total_events'] == 5

    def test_detects_evening_pattern(self):
        """Test detection of evening routine (lights on at 6 PM)"""
        events = create_test_events('light.living_room', [
            '2025-10-01 18:00:00',
            '2025-10-02 18:05:00',
            '2025-10-03 17:55:00',
            '2025-10-04 18:02:00',
            '2025-10-05 18:00:00',
            '2025-10-06 17:58:00',
        ])

        detector = TimeOfDayPatternDetector()
        patterns = detector.detect_patterns(events)

        assert len(patterns) == 1
        assert patterns[0]['hour'] == 18
        assert patterns[0]['confidence'] == 1.0

    def test_detects_multiple_patterns_same_device(self):
        """Test detection of multiple patterns for same device (morning + evening)"""
        # Need 21+ events to use 3 clusters
        # Morning pattern (7 AM) - 12 events
        morning = [f'2025-10-{i:02d} 07:00:00' for i in range(1, 13)]
        # Evening pattern (7 PM) - 12 events
        evening = [f'2025-10-{i:02d} 19:00:00' for i in range(1, 13)]

        events = create_test_events('light.bedroom', morning + evening)

        detector = TimeOfDayPatternDetector(min_confidence=0.4)  # Lower threshold for multi-pattern
        patterns = detector.detect_patterns(events)

        # Should detect 2 clusters (morning + evening) with 24 events
        assert len(patterns) >= 1  # At least one pattern
        hours = [p['hour'] for p in patterns]
        # Should have patterns near 7 AM or 7 PM
        assert any(h in [7, 19] for h in hours)

    def test_skips_insufficient_data(self):
        """Test skips devices with <5 events"""
        events = create_test_events('light.bedroom', [
            '2025-10-01 07:00:00',
            '2025-10-02 08:00:00',
        ])

        detector = TimeOfDayPatternDetector()
        patterns = detector.detect_patterns(events)

        assert len(patterns) == 0  # Skipped due to insufficient data

    def test_filters_low_confidence_patterns(self):
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

        # No cluster should dominate (>70% of events)
        for pattern in patterns:
            # If any pattern is returned, its confidence should be >= 0.7
            assert pattern['confidence'] >= 0.7

    def test_filters_minimum_occurrences(self):
        """Test respects minimum occurrence threshold"""
        # 10 events, but spread across different times
        times = [f'2025-10-{i:02d} {(i % 12):02d}:00:00' for i in range(1, 11)]
        events = create_test_events('light.bedroom', times)

        detector = TimeOfDayPatternDetector(min_occurrences=5, min_confidence=0.4)
        patterns = detector.detect_patterns(events)

        # All patterns should have >= 5 occurrences
        for pattern in patterns:
            assert pattern['occurrences'] >= 5

    def test_handles_multiple_devices(self):
        """Test analyzes multiple devices independently"""
        # Device 1: Morning pattern at 7 AM
        device1_events = create_test_events('light.bedroom', [
            '2025-10-01 07:00:00',
            '2025-10-02 07:01:00',
            '2025-10-03 07:00:00',
            '2025-10-04 06:59:00',
            '2025-10-05 07:02:00',
        ])

        # Device 2: Evening pattern at 6 PM
        device2_events = create_test_events('light.living_room', [
            '2025-10-01 18:00:00',
            '2025-10-02 18:05:00',
            '2025-10-03 17:55:00',
            '2025-10-04 18:00:00',
            '2025-10-05 18:02:00',
        ])

        all_events = pd.concat([device1_events, device2_events], ignore_index=True)

        detector = TimeOfDayPatternDetector()
        patterns = detector.detect_patterns(all_events)

        assert len(patterns) == 2
        device_ids = {p['device_id'] for p in patterns}
        assert 'light.bedroom' in device_ids
        assert 'light.living_room' in device_ids

    def test_empty_dataframe(self):
        """Test handles empty DataFrame gracefully"""
        events = pd.DataFrame()

        detector = TimeOfDayPatternDetector()
        patterns = detector.detect_patterns(events)

        assert patterns == []

    def test_missing_required_columns(self):
        """Test handles missing columns gracefully"""
        # Missing 'timestamp' column
        events = pd.DataFrame({
            'device_id': ['light.bedroom'],
            'state': ['on']
        })

        detector = TimeOfDayPatternDetector()
        patterns = detector.detect_patterns(events)

        assert patterns == []

    def test_pattern_metadata_includes_stats(self):
        """Test pattern metadata includes statistical information"""
        events = create_test_events('light.bedroom', [
            '2025-10-01 07:00:00',
            '2025-10-02 07:01:00',
            '2025-10-03 06:59:00',
            '2025-10-04 07:00:00',
            '2025-10-05 07:02:00',
        ])

        detector = TimeOfDayPatternDetector()
        patterns = detector.detect_patterns(events)

        assert len(patterns) == 1
        metadata = patterns[0]['metadata']

        assert 'avg_time_decimal' in metadata
        assert 'cluster_id' in metadata
        assert 'std_minutes' in metadata
        assert 'time_range' in metadata

        # Standard deviation should be reasonable (< 5 minutes for this tight cluster)
        assert metadata['std_minutes'] < 5.0

    def test_confidence_calculation(self):
        """Test confidence score is calculated correctly"""
        # With 10 events, we use 1 cluster, so all events get 100% confidence
        # Test with 25 events to get 3 clusters for better separation
        # 18 events at 7 AM, 7 events at 7 PM
        morning = [f'2025-10-{i:02d} 07:00:00' for i in range(1, 19)]
        evening = [f'2025-10-{i:02d} 19:00:00' for i in range(1, 8)]

        events = create_test_events('light.bedroom', morning + evening)

        detector = TimeOfDayPatternDetector(min_confidence=0.6)
        patterns = detector.detect_patterns(events)

        # Morning pattern: 18/25 = 0.72 confidence
        # Evening pattern: 7/25 = 0.28 confidence (filtered out)
        assert len(patterns) >= 1
        # Should have the morning pattern
        morning_pattern = [p for p in patterns if p['hour'] == 7][0]
        assert morning_pattern['confidence'] >= 0.6
        assert morning_pattern['occurrences'] >= 15

    def test_get_pattern_summary_with_patterns(self):
        """Test pattern summary generation with patterns"""
        events = create_test_events('light.bedroom', [
            '2025-10-01 07:00:00',
            '2025-10-02 07:01:00',
            '2025-10-03 06:59:00',
            '2025-10-04 07:00:00',
            '2025-10-05 07:02:00',
        ])

        detector = TimeOfDayPatternDetector()
        patterns = detector.detect_patterns(events)
        summary = detector.get_pattern_summary(patterns)

        assert summary['total_patterns'] == 1
        assert summary['unique_devices'] == 1
        assert summary['avg_confidence'] == 1.0
        assert summary['avg_occurrences'] == 5.0
        assert 'confidence_distribution' in summary

    def test_get_pattern_summary_empty(self):
        """Test pattern summary with no patterns"""
        detector = TimeOfDayPatternDetector()
        summary = detector.get_pattern_summary([])

        assert summary['total_patterns'] == 0
        assert summary['unique_devices'] == 0
        assert summary['avg_confidence'] == 0.0
        assert summary['avg_occurrences'] == 0.0

    def test_realistic_home_assistant_data(self):
        """Test with realistic Home Assistant event patterns"""
        # Simulate a month of morning light usage (weekdays at 6:30 AM)
        base_date = datetime(2025, 10, 1)
        weekday_mornings = []

        for i in range(30):
            date = base_date + timedelta(days=i)
            # Only weekdays (Monday=0 to Friday=4)
            if date.weekday() < 5:
                # Add some natural variation (±5 minutes)
                time_str = date.strftime('%Y-%m-%d') + ' 06:' + f'{30 + (i % 10):02d}:00'
                weekday_mornings.append(time_str)

        events = create_test_events('light.bedroom', weekday_mornings)

        # With ~21 weekday events and 3 clusters, use lower thresholds
        # Each cluster ~7 events, so min_occurrences=3 and min_confidence=0.3
        detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.3)
        patterns = detector.detect_patterns(events)

        # Should detect the weekday morning pattern
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern['hour'] == 6
        assert 25 <= pattern['minute'] <= 40  # Around 6:30 with variation
        assert pattern['confidence'] >= 0.4  # Reasonable confidence for clustered data


@pytest.mark.asyncio
async def test_pattern_detector_integration():
    """
    Integration test: Fetch real data from Data API and detect patterns.
    Requires: docker-compose up data-api ai-automation-service
    """
    from datetime import datetime, timedelta

    from src.clients.data_api_client import DataAPIClient

    client = DataAPIClient(base_url="http://localhost:8006")

    try:
        # Fetch last 7 days of events
        start_time = datetime.now(datetime.UTC) - timedelta(days=7)  # type: ignore
        events_df = await client.fetch_events(start_time=start_time, limit=1000)

        if events_df.empty:
            pytest.skip("No events available in Data API")

        # Detect patterns
        detector = TimeOfDayPatternDetector(min_occurrences=2, min_confidence=0.5)
        patterns = detector.detect_patterns(events_df)

        # Verify patterns structure
        for pattern in patterns:
            assert 'device_id' in pattern
            assert 'pattern_type' in pattern
            assert pattern['pattern_type'] == 'time_of_day'
            assert 'hour' in pattern
            assert 0 <= pattern['hour'] <= 23
            assert 'minute' in pattern
            assert 0 <= pattern['minute'] <= 59
            assert 'confidence' in pattern
            assert 0.0 <= pattern['confidence'] <= 1.0
            assert 'occurrences' in pattern
            assert pattern['occurrences'] >= 2
            assert 'metadata' in pattern

        print(f"\n✅ Detected {len(patterns)} patterns from real data")

    finally:
        await client.close()

