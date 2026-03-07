"""
Unit tests for FrequencyPatternDetector.

Epic 37, Story 37.7: Frequency Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.frequency import FrequencyPatternDetector, FrequencyProfile


class TestFrequencyDetectorInit:
    """Tests for FrequencyPatternDetector initialization."""

    def test_default_initialization(self):
        detector = FrequencyPatternDetector()
        assert detector.min_days == 7
        assert detector.min_confidence == 0.7
        assert detector.change_threshold == 0.5
        assert detector.recent_window_days == 7
        assert detector.filter_system_noise is True
        assert detector.aggregate_client is None

    def test_custom_initialization(self):
        detector = FrequencyPatternDetector(
            min_days=14,
            min_confidence=0.8,
            change_threshold=0.3,
            recent_window_days=3,
            filter_system_noise=False,
        )
        assert detector.min_days == 14
        assert detector.min_confidence == 0.8
        assert detector.change_threshold == 0.3
        assert detector.recent_window_days == 3
        assert detector.filter_system_noise is False


class TestTrendCalculation:
    """Tests for trend detection."""

    def test_increasing_trend(self):
        # Clearly increasing counts
        counts = [1, 2, 3, 5, 7, 10, 14, 18, 22, 28]
        trend, slope = FrequencyPatternDetector._calculate_trend(counts)
        assert trend == 'increasing'
        assert slope > 0

    def test_decreasing_trend(self):
        counts = [30, 25, 20, 16, 12, 8, 5, 3, 2, 1]
        trend, slope = FrequencyPatternDetector._calculate_trend(counts)
        assert trend == 'decreasing'
        assert slope < 0

    def test_stable_trend(self):
        counts = [10, 11, 9, 10, 10, 11, 10, 9, 10, 10]
        trend, slope = FrequencyPatternDetector._calculate_trend(counts)
        assert trend == 'stable'

    def test_too_few_data_points(self):
        trend, slope = FrequencyPatternDetector._calculate_trend([5, 10])
        assert trend == 'stable'
        assert slope == 0.0

    def test_empty_data(self):
        trend, slope = FrequencyPatternDetector._calculate_trend([])
        assert trend == 'stable'

    def test_constant_data(self):
        counts = [5, 5, 5, 5, 5, 5, 5]
        trend, slope = FrequencyPatternDetector._calculate_trend(counts)
        assert trend == 'stable'
        assert abs(slope) < 0.01


class TestFrequencyPatternDetection:
    """Tests for end-to-end pattern detection."""

    @pytest.fixture
    def detector(self):
        return FrequencyPatternDetector(
            min_days=3,
            min_confidence=0.1,
            change_threshold=0.5,
            recent_window_days=3,
            filter_system_noise=False,
        )

    def _make_events(self, device_id, daily_counts):
        """Helper to generate events with specific daily counts."""
        events_data = []
        start = datetime(2026, 3, 1, 0, 0, 0)
        for day_idx, count in enumerate(daily_counts):
            day = start + timedelta(days=day_idx)
            for i in range(count):
                t = day + timedelta(hours=8 + i % 12, minutes=i * 5 % 60)
                events_data.append({
                    'device_id': device_id,
                    'timestamp': t,
                    'state': 'on',
                })
        df = pd.DataFrame(events_data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def test_empty_events(self, detector):
        events = pd.DataFrame(columns=['device_id', 'timestamp', 'state'])
        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_missing_columns(self, detector):
        events = pd.DataFrame({'device_id': ['light.bedroom']})
        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_consistent_frequency_detected(self, detector):
        """Test that a device with consistent daily counts is detected."""
        counts = [10, 11, 9, 10, 12, 10, 11, 9, 10, 10]
        events = self._make_events('light.bedroom', counts)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern['pattern_type'] == 'frequency'
        assert pattern['device_id'] == 'light.bedroom'
        assert pattern['avg_daily'] == pytest.approx(10.2, abs=0.5)
        assert pattern['trend'] == 'stable'

    def test_frequency_change_detected(self, detector):
        """Test detection of a significant frequency change."""
        # Baseline: ~5/day, then jumps to ~15/day
        counts = [5, 5, 6, 5, 4, 5, 5, 15, 14, 16]
        events = self._make_events('switch.furnace', counts)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern['change_detected'] is True

    def test_no_change_below_threshold(self):
        """Test that small changes below threshold are not flagged."""
        detector = FrequencyPatternDetector(
            min_days=3,
            min_confidence=0.1,
            change_threshold=0.8,  # High threshold
            recent_window_days=3,
            filter_system_noise=False,
        )
        # Small variation
        counts = [10, 11, 9, 10, 12, 10, 13, 11, 12, 11]
        events = self._make_events('light.bedroom', counts)
        patterns = detector.detect_patterns(events)

        for p in patterns:
            assert p['change_detected'] is False

    def test_insufficient_days_skipped(self):
        """Test that devices with insufficient data are skipped."""
        detector = FrequencyPatternDetector(
            min_days=10,
            min_confidence=0.1,
            filter_system_noise=False,
        )
        counts = [5, 5, 5]  # Only 3 days
        events = self._make_events('light.bedroom', counts)
        patterns = detector.detect_patterns(events)
        assert len(patterns) == 0

    def test_pattern_output_structure(self, detector):
        """Test output has all required fields."""
        counts = [10, 11, 9, 10, 12, 10, 11]
        events = self._make_events('light.bedroom', counts)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]
        assert 'pattern_type' in pattern
        assert 'device_id' in pattern
        assert 'avg_daily' in pattern
        assert 'std_daily' in pattern
        assert 'trend' in pattern
        assert 'change_detected' in pattern
        assert 'variance_score' in pattern
        assert 'confidence' in pattern
        assert 'metadata' in pattern
        assert 'total_events' in pattern['metadata']
        assert 'total_days' in pattern['metadata']
        assert 'coefficient_of_variation' in pattern['metadata']

    def test_multiple_devices(self, detector):
        """Test detection across multiple devices."""
        events1 = self._make_events('light.bedroom', [10, 10, 10, 10, 10, 10, 10])
        events2 = self._make_events('switch.coffee', [5, 5, 5, 5, 5, 5, 5])
        events = pd.concat([events1, events2], ignore_index=True)

        patterns = detector.detect_patterns(events)
        devices = {p['device_id'] for p in patterns}
        assert len(devices) == 2

    def test_increasing_trend_detected(self, detector):
        """Test increasing trend is detected."""
        counts = [2, 4, 6, 8, 10, 14, 18, 22, 26, 30]
        events = self._make_events('binary_sensor.motion', counts)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        trending = [p for p in patterns if p['trend'] == 'increasing']
        assert len(trending) >= 1

    def test_decreasing_trend_detected(self, detector):
        """Test decreasing trend is detected."""
        counts = [30, 26, 22, 18, 14, 10, 8, 6, 4, 2]
        events = self._make_events('binary_sensor.motion', counts)
        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        trending = [p for p in patterns if p['trend'] == 'decreasing']
        assert len(trending) >= 1

    def test_patterns_sorted_changes_first(self, detector):
        """Test that patterns with changes sort before stable ones."""
        # Stable device
        events1 = self._make_events('light.stable', [10] * 10)
        # Changing device
        events2 = self._make_events('light.changing', [5, 5, 5, 5, 5, 5, 5, 15, 15, 15])
        events = pd.concat([events1, events2], ignore_index=True)

        patterns = detector.detect_patterns(events)
        if len(patterns) >= 2:
            # Changes should sort first
            changed_indices = [
                i for i, p in enumerate(patterns) if p['change_detected']
            ]
            stable_indices = [
                i for i, p in enumerate(patterns) if not p['change_detected']
            ]
            if changed_indices and stable_indices:
                assert min(changed_indices) < min(stable_indices)

    def test_zero_baseline_handling(self, detector):
        """Test handling of zero baseline (all zeros then activity)."""
        counts = [0, 0, 0, 0, 0, 0, 0, 5, 5, 5]
        events = self._make_events('light.new', counts)
        patterns = detector.detect_patterns(events)
        # Should handle gracefully, may or may not detect pattern
        assert isinstance(patterns, list)

    def test_fills_missing_days(self, detector):
        """Test that gaps between events are filled with 0-count days."""
        # Events only on day 0 and day 9
        start = datetime(2026, 3, 1, 8, 0, 0)
        events = pd.DataFrame({
            'device_id': ['light.sparse'] * 6,
            'timestamp': pd.to_datetime([
                start,
                start + timedelta(hours=1),
                start + timedelta(hours=2),
                start + timedelta(days=9),
                start + timedelta(days=9, hours=1),
                start + timedelta(days=9, hours=2),
            ]),
            'state': ['on'] * 6,
        })

        patterns = detector.detect_patterns(events)
        if patterns:
            # Should have 10 days total (including zeros)
            assert patterns[0]['metadata']['total_days'] == 10


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    def test_high_data_high_confidence(self):
        detector = FrequencyPatternDetector()
        profile = FrequencyProfile(
            device_id='test',
            total_events=200,
            total_days=30,
            coefficient_of_variation=0.2,
        )
        confidence = detector._calculate_confidence(profile)
        assert confidence > 0.8

    def test_low_data_low_confidence(self):
        detector = FrequencyPatternDetector()
        profile = FrequencyProfile(
            device_id='test',
            total_events=10,
            total_days=3,
            coefficient_of_variation=1.5,
        )
        confidence = detector._calculate_confidence(profile)
        assert confidence < 0.4

    def test_high_cv_lowers_confidence(self):
        detector = FrequencyPatternDetector()
        low_cv = FrequencyProfile(
            device_id='test', total_events=50, total_days=14,
            coefficient_of_variation=0.2,
        )
        high_cv = FrequencyProfile(
            device_id='test', total_events=50, total_days=14,
            coefficient_of_variation=2.0,
        )
        assert detector._calculate_confidence(low_cv) > detector._calculate_confidence(high_cv)

    def test_confidence_bounds(self):
        detector = FrequencyPatternDetector()
        profile = FrequencyProfile(
            device_id='test', total_events=1000, total_days=100,
            coefficient_of_variation=0.0,
        )
        confidence = detector._calculate_confidence(profile)
        assert 0.0 <= confidence <= 1.0


class TestChangeDetection:
    """Tests for frequency change detection."""

    @pytest.fixture
    def detector(self):
        return FrequencyPatternDetector(change_threshold=0.5)

    def test_detects_increase(self, detector):
        profile = FrequencyProfile(
            device_id='test',
            total_events=100,
            total_days=14,
            baseline_avg=5.0,
            recent_avg=10.0,
            coefficient_of_variation=0.3,
        )
        change = detector._detect_change(profile)
        assert change is not None
        assert change.direction == 'increase'
        assert change.change_ratio == pytest.approx(2.0)

    def test_detects_decrease(self, detector):
        profile = FrequencyProfile(
            device_id='test',
            total_events=100,
            total_days=14,
            baseline_avg=10.0,
            recent_avg=3.0,
            coefficient_of_variation=0.3,
        )
        change = detector._detect_change(profile)
        assert change is not None
        assert change.direction == 'decrease'

    def test_no_change_when_similar(self, detector):
        profile = FrequencyProfile(
            device_id='test',
            total_events=100,
            total_days=14,
            baseline_avg=10.0,
            recent_avg=11.0,
            coefficient_of_variation=0.3,
        )
        change = detector._detect_change(profile)
        assert change is None  # 10% change < 50% threshold

    def test_both_zero_no_change(self, detector):
        profile = FrequencyProfile(
            device_id='test',
            baseline_avg=0.0,
            recent_avg=0.0,
        )
        change = detector._detect_change(profile)
        assert change is None

    def test_zero_baseline_increase(self, detector):
        profile = FrequencyProfile(
            device_id='test',
            total_events=50,
            total_days=14,
            baseline_avg=0.0,
            recent_avg=5.0,
            coefficient_of_variation=0.5,
        )
        change = detector._detect_change(profile)
        assert change is not None
        assert change.direction == 'increase'


class TestSystemNoiseFiltering:
    """Tests for system noise filtering."""

    @pytest.fixture
    def detector(self):
        return FrequencyPatternDetector(filter_system_noise=True)

    def test_filters_system_entities(self, detector):
        assert detector._is_actionable_entity("light.bedroom") is True
        assert detector._is_actionable_entity("sensor.home_assistant_uptime") is False
        assert detector._is_actionable_entity("update.core") is False

    def test_empty_entity(self, detector):
        assert detector._is_actionable_entity("") is False


class TestAutomationSuggestion:
    """Tests for automation suggestion generation."""

    @pytest.fixture
    def detector(self):
        return FrequencyPatternDetector()

    def test_basic_suggestion(self, detector):
        pattern = {
            'pattern_type': 'frequency',
            'device_id': 'switch.furnace',
            'change_detected': True,
            'confidence': 0.85,
            'metadata': {
                'change': {'direction': 'increase', 'change_ratio': 2.0},
                'baseline_avg': 10.0,
                'recent_avg': 20.0,
            },
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion['automation_type'] == 'frequency_alert'
        assert suggestion['confidence'] == 0.85
        assert suggestion['requires_confirmation'] is True

    def test_no_suggestion_without_change(self, detector):
        pattern = {
            'pattern_type': 'frequency',
            'device_id': 'light.bedroom',
            'change_detected': False,
        }
        result = detector.suggest_automation(pattern)
        assert result == {}

    def test_wrong_pattern_type(self, detector):
        pattern = {'pattern_type': 'sequence', 'device_id': 'x'}
        assert detector.suggest_automation(pattern) == {}

    def test_empty_device_id(self, detector):
        pattern = {'pattern_type': 'frequency', 'device_id': ''}
        assert detector.suggest_automation(pattern) == {}


class TestPatternSummary:
    """Tests for pattern summary generation."""

    def test_empty_summary(self):
        detector = FrequencyPatternDetector()
        summary = detector.get_pattern_summary([])
        assert summary['total_patterns'] == 0
        assert summary['changes_detected'] == 0

    def test_summary_with_patterns(self):
        detector = FrequencyPatternDetector()
        patterns = [
            {
                'device_id': 'light.bedroom',
                'avg_daily': 10.0,
                'trend': 'stable',
                'change_detected': False,
                'confidence': 0.85,
            },
            {
                'device_id': 'switch.furnace',
                'avg_daily': 60.0,
                'trend': 'increasing',
                'change_detected': True,
                'confidence': 0.9,
            },
        ]

        summary = detector.get_pattern_summary(patterns)
        assert summary['total_patterns'] == 2
        assert summary['changes_detected'] == 1
        assert summary['high_frequency_devices'] == 1
        assert 'stable' in summary['trends']
        assert 'increasing' in summary['trends']


class TestGetDomain:
    """Tests for domain extraction."""

    def test_light_domain(self):
        assert FrequencyPatternDetector._get_domain("light.bedroom") == "light"

    def test_empty(self):
        assert FrequencyPatternDetector._get_domain("") == "default"

    def test_no_dot(self):
        assert FrequencyPatternDetector._get_domain("nodot") == "default"


class TestDailyAggregates:
    """Tests for daily aggregate storage."""

    def _make_events(self, device_id, daily_counts):
        events_data = []
        start = datetime(2026, 3, 1, 0, 0, 0)
        for day_idx, count in enumerate(daily_counts):
            day = start + timedelta(days=day_idx)
            for i in range(count):
                t = day + timedelta(hours=8 + i % 12, minutes=i * 5 % 60)
                events_data.append({
                    'device_id': device_id,
                    'timestamp': t,
                    'state': 'on',
                })
        df = pd.DataFrame(events_data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def test_store_aggregates_called(self):
        class MockClient:
            def __init__(self):
                self.calls = []

            def write_frequency_daily(self, **kwargs):
                self.calls.append(kwargs)

        mock = MockClient()
        detector = FrequencyPatternDetector(
            min_days=3, min_confidence=0.1,
            filter_system_noise=False, aggregate_client=mock,
        )

        events = self._make_events('light.bedroom', [10] * 7)
        patterns = detector.detect_patterns(events)

        if patterns:
            assert len(mock.calls) > 0

    def test_store_aggregates_handles_error(self):
        class FailingClient:
            def write_frequency_daily(self, **kwargs):
                raise RuntimeError("Storage failed")

        detector = FrequencyPatternDetector(
            min_days=3, min_confidence=0.1,
            filter_system_noise=False, aggregate_client=FailingClient(),
        )

        events = self._make_events('light.bedroom', [10] * 7)
        # Should not raise
        patterns = detector.detect_patterns(events)
        assert isinstance(patterns, list)
