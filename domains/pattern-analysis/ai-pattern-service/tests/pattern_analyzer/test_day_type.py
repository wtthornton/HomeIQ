"""
Unit tests for DayTypePatternDetector.

Epic 37, Story 37.3: Day Type Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.day_type import (
    DayTypePatternDetector,
    DayTypeProfile,
    WEEKEND_DAYS,
)


class TestDayTypeDetectorInit:
    """Tests for DayTypePatternDetector initialization."""

    def test_default_initialization(self):
        """Test detector initializes with default values."""
        detector = DayTypePatternDetector()

        assert detector.min_events_per_type == 5
        assert detector.min_confidence == 0.7
        assert detector.variance_threshold == 0.3
        assert detector.filter_system_noise is True
        assert detector.aggregate_client is None

    def test_custom_initialization(self):
        """Test detector initializes with custom values."""
        detector = DayTypePatternDetector(
            min_events_per_type=10,
            min_confidence=0.8,
            variance_threshold=0.5,
            filter_system_noise=False,
        )

        assert detector.min_events_per_type == 10
        assert detector.min_confidence == 0.8
        assert detector.variance_threshold == 0.5
        assert detector.filter_system_noise is False


class TestEventPartitioning:
    """Tests for weekday/weekend event partitioning."""

    def test_weekday_events_classified(self):
        """Test that weekday events are correctly classified."""
        # 2026-03-02 is a Monday
        monday = datetime(2026, 3, 2, 8, 0, 0)
        events = pd.DataFrame({
            'device_id': ['light.bedroom'] * 5,
            'timestamp': pd.to_datetime([
                monday,  # Mon
                monday + timedelta(days=1),  # Tue
                monday + timedelta(days=2),  # Wed
                monday + timedelta(days=3),  # Thu
                monday + timedelta(days=4),  # Fri
            ]),
            'state': ['on'] * 5,
        })

        weekday, weekend = DayTypePatternDetector._partition_by_day_type(events)
        assert len(weekday) == 5
        assert len(weekend) == 0

    def test_weekend_events_classified(self):
        """Test that weekend events are correctly classified."""
        # 2026-03-07 is a Saturday
        saturday = datetime(2026, 3, 7, 10, 0, 0)
        events = pd.DataFrame({
            'device_id': ['light.bedroom'] * 2,
            'timestamp': pd.to_datetime([
                saturday,  # Sat
                saturday + timedelta(days=1),  # Sun
            ]),
            'state': ['on'] * 2,
        })

        weekday, weekend = DayTypePatternDetector._partition_by_day_type(events)
        assert len(weekday) == 0
        assert len(weekend) == 2

    def test_mixed_events_split(self):
        """Test that mixed events are correctly split."""
        # 2026-03-02 is Monday
        monday = datetime(2026, 3, 2, 8, 0, 0)
        events = pd.DataFrame({
            'device_id': ['light.bedroom'] * 7,
            'timestamp': pd.to_datetime([
                monday + timedelta(days=i) for i in range(7)
            ]),
            'state': ['on'] * 7,
        })

        weekday, weekend = DayTypePatternDetector._partition_by_day_type(events)
        assert len(weekday) == 5
        assert len(weekend) == 2


class TestProfileBuilding:
    """Tests for activation profile building."""

    def test_basic_profile(self):
        """Test basic profile construction."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom'] * 6,
            'timestamp': pd.to_datetime([
                '2026-03-02 07:00', '2026-03-02 08:00',
                '2026-03-03 07:00', '2026-03-03 08:00',
                '2026-03-04 07:00', '2026-03-04 08:00',
            ]),
        })

        profile = DayTypePatternDetector._build_profile(events)
        assert profile.event_count == 6
        assert profile.day_count == 3
        assert profile.avg_daily_count == 2.0
        assert profile.peak_hour in (7, 8)

    def test_hourly_distribution_normalized(self):
        """Test that hourly distribution sums to ~1.0."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom'] * 10,
            'timestamp': pd.to_datetime([
                '2026-03-02 07:00', '2026-03-02 07:30',
                '2026-03-02 08:00', '2026-03-02 08:15',
                '2026-03-02 08:30', '2026-03-02 12:00',
                '2026-03-03 07:00', '2026-03-03 08:00',
                '2026-03-04 07:00', '2026-03-04 08:00',
            ]),
        })

        profile = DayTypePatternDetector._build_profile(events)
        total = sum(profile.hourly_distribution.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_single_event_profile(self):
        """Test profile with single event."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom'],
            'timestamp': pd.to_datetime(['2026-03-02 09:00']),
        })

        profile = DayTypePatternDetector._build_profile(events)
        assert profile.event_count == 1
        assert profile.day_count == 1
        assert profile.std_hour == 0.0


class TestVarianceCalculation:
    """Tests for variance scoring between profiles."""

    @pytest.fixture
    def detector(self):
        return DayTypePatternDetector(filter_system_noise=False)

    def test_relative_difference(self):
        """Test relative difference calculation."""
        assert DayTypePatternDetector._relative_difference(10.0, 10.0) == 0.0
        assert DayTypePatternDetector._relative_difference(10.0, 5.0) == pytest.approx(0.5)
        assert DayTypePatternDetector._relative_difference(0.0, 0.0) == 0.0
        assert DayTypePatternDetector._relative_difference(10.0, 0.0) == 1.0

    def test_identical_profiles_low_variance(self, detector):
        """Test that identical profiles produce low variance."""
        profile = DayTypeProfile(
            event_count=20, day_count=5, avg_daily_count=4.0,
            hourly_distribution={8: 0.5, 9: 0.5}, peak_hour=8,
            avg_hour=8.5, std_hour=0.5,
        )

        comp = detector._compute_variance("light.test", profile, profile)
        assert comp.count_variance == 0.0
        assert comp.overall_variance < 0.1

    def test_different_profiles_high_variance(self, detector):
        """Test that very different profiles produce high variance."""
        wd_profile = DayTypeProfile(
            event_count=50, day_count=10, avg_daily_count=5.0,
            hourly_distribution={7: 0.8, 8: 0.2}, peak_hour=7,
            avg_hour=7.2, std_hour=0.5,
        )
        we_profile = DayTypeProfile(
            event_count=10, day_count=4, avg_daily_count=2.5,
            hourly_distribution={10: 0.6, 11: 0.4}, peak_hour=10,
            avg_hour=10.4, std_hour=0.5,
        )

        comp = detector._compute_variance("light.test", wd_profile, we_profile)
        assert comp.count_variance > 0.3
        assert comp.timing_variance > 0.2
        assert comp.overall_variance > 0.3

    def test_timing_variance_circular(self):
        """Test timing variance handles circular hour distances."""
        wd_profile = DayTypeProfile(
            event_count=10, day_count=5, avg_daily_count=2.0,
            hourly_distribution={23: 1.0}, peak_hour=23,
            avg_hour=23.0, std_hour=0.0,
        )
        we_profile = DayTypeProfile(
            event_count=10, day_count=5, avg_daily_count=2.0,
            hourly_distribution={1: 1.0}, peak_hour=1,
            avg_hour=1.0, std_hour=0.0,
        )

        variance = DayTypePatternDetector._timing_variance(wd_profile, we_profile)
        # 23 to 1 = 2 hours circular distance, not 22
        assert variance <= 0.5  # Should be small since only 2 hours apart


class TestDayTypePatternDetection:
    """Tests for end-to-end pattern detection."""

    @pytest.fixture
    def detector(self):
        """Relaxed thresholds for testing."""
        return DayTypePatternDetector(
            min_events_per_type=3,
            min_confidence=0.1,
            variance_threshold=0.2,
            filter_system_noise=False,
        )

    def _make_events(self, device_id, weekday_hour, weekend_hour, n_weeks=3):
        """Helper to generate events with different weekday/weekend hours."""
        events_data = []
        # Start from a Monday
        start = datetime(2026, 3, 2, 0, 0, 0)

        for week in range(n_weeks):
            week_start = start + timedelta(weeks=week)
            # Weekday events (Mon-Fri)
            for day in range(5):
                t = week_start + timedelta(days=day, hours=weekday_hour)
                events_data.append({
                    'device_id': device_id,
                    'timestamp': t,
                    'state': 'on',
                })
            # Weekend events (Sat-Sun)
            for day in (5, 6):
                t = week_start + timedelta(days=day, hours=weekend_hour)
                events_data.append({
                    'device_id': device_id,
                    'timestamp': t,
                    'state': 'on',
                })

        df = pd.DataFrame(events_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def test_empty_events(self, detector):
        """Test with empty DataFrame."""
        events = pd.DataFrame(columns=['device_id', 'timestamp', 'state'])
        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_missing_columns(self, detector):
        """Test with missing required columns."""
        events = pd.DataFrame({'device_id': ['light.bedroom']})
        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_detects_different_weekday_weekend(self, detector):
        """Test detection of different weekday vs weekend behavior."""
        events = self._make_events('light.bedroom', weekday_hour=7, weekend_hour=10, n_weeks=3)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern['pattern_type'] == 'day_type'
        assert pattern['device_id'] == 'light.bedroom'
        assert pattern['variance_score'] > 0.2

    def test_similar_behavior_not_detected(self):
        """Test that similar weekday/weekend behavior is not flagged."""
        detector = DayTypePatternDetector(
            min_events_per_type=3,
            min_confidence=0.1,
            variance_threshold=0.5,  # High threshold
            filter_system_noise=False,
        )

        # Same hour on weekdays and weekends
        events = self._make_events('light.bedroom', weekday_hour=8, weekend_hour=8, n_weeks=3)
        patterns = detector.detect_patterns(events)

        # Should have low variance, likely filtered
        high_variance = [p for p in patterns if p['variance_score'] > 0.5]
        assert len(high_variance) == 0

    def test_insufficient_events_skipped(self):
        """Test that devices with insufficient events are skipped."""
        detector = DayTypePatternDetector(
            min_events_per_type=10,
            min_confidence=0.1,
            variance_threshold=0.1,
            filter_system_noise=False,
        )

        # Only 2 weekend events
        events = self._make_events('light.bedroom', weekday_hour=7, weekend_hour=10, n_weeks=1)
        patterns = detector.detect_patterns(events)
        assert len(patterns) == 0

    def test_pattern_output_structure(self, detector):
        """Test that output has all required fields."""
        events = self._make_events('light.bedroom', weekday_hour=7, weekend_hour=11, n_weeks=3)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]
        assert 'pattern_type' in pattern
        assert 'device_id' in pattern
        assert 'weekday_pattern' in pattern
        assert 'weekend_pattern' in pattern
        assert 'variance_score' in pattern
        assert 'confidence' in pattern
        assert 'metadata' in pattern
        assert 'count_variance' in pattern['metadata']
        assert 'timing_variance' in pattern['metadata']

    def test_weekday_pattern_fields(self, detector):
        """Test weekday/weekend pattern sub-dictionaries."""
        events = self._make_events('light.bedroom', weekday_hour=7, weekend_hour=11, n_weeks=3)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        wd = patterns[0]['weekday_pattern']
        assert 'event_count' in wd
        assert 'day_count' in wd
        assert 'avg_daily_count' in wd
        assert 'peak_hour' in wd
        assert 'avg_hour' in wd
        assert 'hourly_distribution' in wd

    def test_multiple_devices(self, detector):
        """Test detection across multiple devices."""
        events1 = self._make_events('light.bedroom', weekday_hour=7, weekend_hour=10, n_weeks=3)
        events2 = self._make_events('switch.coffee', weekday_hour=6, weekend_hour=9, n_weeks=3)
        events = pd.concat([events1, events2], ignore_index=True)

        patterns = detector.detect_patterns(events)
        devices = {p['device_id'] for p in patterns}
        assert len(devices) >= 1  # At least one should be detected

    def test_patterns_sorted_by_variance(self, detector):
        """Test that patterns are sorted by variance descending."""
        # Device with big difference
        events1 = self._make_events('light.bedroom', weekday_hour=6, weekend_hour=14, n_weeks=3)
        # Device with small difference
        events2 = self._make_events('light.kitchen', weekday_hour=7, weekend_hour=8, n_weeks=3)
        events = pd.concat([events1, events2], ignore_index=True)

        patterns = detector.detect_patterns(events)
        if len(patterns) >= 2:
            assert patterns[0]['variance_score'] >= patterns[1]['variance_score']


class TestConfidence:
    """Tests for confidence calculation."""

    def test_high_data_high_confidence(self):
        """Test high data volume gives high confidence."""
        wd = DayTypeProfile(event_count=50, day_count=14)
        we = DayTypeProfile(event_count=50, day_count=14)
        confidence = DayTypePatternDetector._calculate_confidence(wd, we)
        assert confidence > 0.9

    def test_low_data_low_confidence(self):
        """Test low data volume gives low confidence."""
        wd = DayTypeProfile(event_count=5, day_count=2)
        we = DayTypeProfile(event_count=5, day_count=2)
        confidence = DayTypePatternDetector._calculate_confidence(wd, we)
        assert confidence < 0.3

    def test_asymmetric_data(self):
        """Test with asymmetric data volumes."""
        wd = DayTypeProfile(event_count=50, day_count=14)
        we = DayTypeProfile(event_count=5, day_count=2)
        confidence = DayTypePatternDetector._calculate_confidence(wd, we)
        # Should be between high and low
        assert 0.3 < confidence < 0.9


class TestSystemNoiseFiltering:
    """Tests for system noise filtering."""

    @pytest.fixture
    def detector(self):
        return DayTypePatternDetector(filter_system_noise=True)

    def test_filters_system_entities(self, detector):
        """Test that system entities are filtered."""
        assert detector._is_actionable_entity("light.bedroom") is True
        assert detector._is_actionable_entity("sensor.home_assistant_uptime") is False
        assert detector._is_actionable_entity("update.core") is False

    def test_filters_excluded_patterns(self, detector):
        """Test that excluded patterns are filtered."""
        assert detector._is_actionable_entity("sensor.cpu_temp") is False
        assert detector._is_actionable_entity("sensor.nfl_scores") is False

    def test_empty_entity(self, detector):
        """Test empty entity returns False."""
        assert detector._is_actionable_entity("") is False


class TestAutomationSuggestion:
    """Tests for automation suggestion generation."""

    @pytest.fixture
    def detector(self):
        return DayTypePatternDetector()

    def test_basic_suggestion(self, detector):
        """Test basic automation suggestion."""
        pattern = {
            'pattern_type': 'day_type',
            'device_id': 'light.bedroom',
            'weekday_pattern': {'peak_hour': 7},
            'weekend_pattern': {'peak_hour': 9},
            'variance_score': 0.45,
            'confidence': 0.85,
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion['automation_type'] == 'day_type_schedule'
        assert suggestion['confidence'] == 0.85
        assert suggestion['trigger']['at'] == '07:00:00'
        assert 'weekday' in str(suggestion['condition'])

    def test_wrong_pattern_type(self, detector):
        """Test wrong pattern type returns empty."""
        pattern = {'pattern_type': 'sequence', 'device_id': 'x'}
        assert detector.suggest_automation(pattern) == {}

    def test_empty_device_id(self, detector):
        """Test empty device_id returns empty."""
        pattern = {'pattern_type': 'day_type', 'device_id': ''}
        assert detector.suggest_automation(pattern) == {}

    def test_suggestion_metadata(self, detector):
        """Test suggestion includes metadata."""
        pattern = {
            'pattern_type': 'day_type',
            'device_id': 'switch.coffee',
            'weekday_pattern': {'peak_hour': 6},
            'weekend_pattern': {'peak_hour': 9},
            'variance_score': 0.5,
            'confidence': 0.9,
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion['metadata']['source'] == 'day_type_pattern'
        assert suggestion['metadata']['weekday_peak_hour'] == 6
        assert suggestion['metadata']['weekend_peak_hour'] == 9


class TestPatternSummary:
    """Tests for pattern summary generation."""

    def test_empty_summary(self):
        detector = DayTypePatternDetector()
        summary = detector.get_pattern_summary([])
        assert summary['total_patterns'] == 0

    def test_summary_with_patterns(self):
        detector = DayTypePatternDetector()
        patterns = [
            {
                'device_id': 'light.bedroom',
                'variance_score': 0.6,
                'confidence': 0.8,
            },
            {
                'device_id': 'switch.coffee',
                'variance_score': 0.4,
                'confidence': 0.7,
            },
        ]

        summary = detector.get_pattern_summary(patterns)
        assert summary['total_patterns'] == 2
        assert summary['avg_variance'] == pytest.approx(0.5, abs=0.01)
        assert summary['high_variance_count'] == 1
        assert '30-50%' in summary['variance_distribution']


class TestGetDomain:
    """Tests for domain extraction."""

    def test_light_domain(self):
        assert DayTypePatternDetector._get_domain("light.bedroom") == "light"

    def test_empty(self):
        assert DayTypePatternDetector._get_domain("") == "default"

    def test_no_dot(self):
        assert DayTypePatternDetector._get_domain("nodot") == "default"


class TestDailyAggregates:
    """Tests for daily aggregate storage."""

    def test_store_aggregates_called(self):
        """Test that aggregate client is called when provided."""

        class MockClient:
            def __init__(self):
                self.calls = []

            def write_day_type_daily(self, **kwargs):
                self.calls.append(kwargs)

        mock = MockClient()
        detector = DayTypePatternDetector(
            min_events_per_type=3,
            min_confidence=0.1,
            variance_threshold=0.1,
            filter_system_noise=False,
            aggregate_client=mock,
        )

        start = datetime(2026, 3, 2, 0, 0, 0)
        events_data = []
        for week in range(3):
            for day in range(5):
                t = start + timedelta(weeks=week, days=day, hours=7)
                events_data.append({'device_id': 'light.bedroom', 'timestamp': t, 'state': 'on'})
            for day in (5, 6):
                t = start + timedelta(weeks=week, days=day, hours=11)
                events_data.append({'device_id': 'light.bedroom', 'timestamp': t, 'state': 'on'})

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        if patterns:
            assert len(mock.calls) > 0

    def test_store_aggregates_handles_error(self):
        """Test that aggregate storage errors don't crash detection."""

        class FailingClient:
            def write_day_type_daily(self, **kwargs):
                raise RuntimeError("Storage failed")

        detector = DayTypePatternDetector(
            min_events_per_type=3,
            min_confidence=0.1,
            variance_threshold=0.1,
            filter_system_noise=False,
            aggregate_client=FailingClient(),
        )

        start = datetime(2026, 3, 2, 0, 0, 0)
        events_data = []
        for week in range(3):
            for day in range(5):
                t = start + timedelta(weeks=week, days=day, hours=7)
                events_data.append({'device_id': 'light.bedroom', 'timestamp': t, 'state': 'on'})
            for day in (5, 6):
                t = start + timedelta(weeks=week, days=day, hours=11)
                events_data.append({'device_id': 'light.bedroom', 'timestamp': t, 'state': 'on'})

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        # Should not raise
        patterns = detector.detect_patterns(events)
        assert isinstance(patterns, list)


class TestWeekendDaysConstant:
    """Tests for the WEEKEND_DAYS constant."""

    def test_weekend_days_are_saturday_sunday(self):
        assert WEEKEND_DAYS == {5, 6}
