"""
Unit tests for DurationPatternDetector.

Epic 37, Story 37.2: Duration Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.duration import (
    DurationPatternDetector,
    StateDuration,
    DurationStats,
)


class TestDurationPatternDetectorInit:
    """Tests for DurationPatternDetector initialization."""

    def test_default_initialization(self):
        """Test detector initializes with default values."""
        detector = DurationPatternDetector()

        assert detector.min_state_changes == 10
        assert detector.min_confidence == 0.7
        assert detector.anomaly_threshold_std == 2.0
        assert detector.max_cv == 0.5
        assert detector.min_duration_seconds == 1.0
        assert detector.max_duration_hours == 24.0
        assert detector.filter_system_noise is True
        assert detector.aggregate_client is None

    def test_custom_initialization(self):
        """Test detector initializes with custom values."""
        detector = DurationPatternDetector(
            min_state_changes=5,
            min_confidence=0.8,
            anomaly_threshold_std=3.0,
            max_cv=0.3,
            min_duration_seconds=5.0,
            max_duration_hours=12.0,
            filter_system_noise=False,
        )

        assert detector.min_state_changes == 5
        assert detector.min_confidence == 0.8
        assert detector.anomaly_threshold_std == 3.0
        assert detector.max_cv == 0.3
        assert detector.min_duration_seconds == 5.0
        assert detector.max_duration_hours == 12.0
        assert detector.filter_system_noise is False


class TestDurationPatternDetection:
    """Tests for pattern detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector with relaxed thresholds for testing."""
        return DurationPatternDetector(
            min_state_changes=3,
            min_confidence=0.5,
            max_cv=0.8,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        """Base timestamp for test events."""
        return datetime(2026, 3, 6, 8, 0, 0)

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

    def test_missing_state_column(self, detector):
        """Test with missing state column."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom'],
            'timestamp': [datetime.now()],
        })
        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_single_event(self, detector, base_time):
        """Test with single event (no state transition)."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom'],
            'timestamp': [base_time],
            'state': ['on'],
        })
        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_consistent_on_duration(self, detector, base_time):
        """Test detection of consistent on duration pattern."""
        events = []
        for i in range(8):
            on_time = base_time + timedelta(hours=i * 2)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'light.bathroom', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.bathroom', 'timestamp': off_time, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        assert len(patterns) >= 1
        on_pattern = next(
            (p for p in patterns if p['state'] == 'on'),
            None
        )
        assert on_pattern is not None
        assert on_pattern['device_id'] == 'light.bathroom'
        assert on_pattern['avg_duration'] == pytest.approx(300.0, rel=0.1)

    def test_consistent_off_duration(self, detector, base_time):
        """Test detection of consistent off duration pattern."""
        events = []
        for i in range(8):
            off_time = base_time + timedelta(hours=i * 2)
            on_time = off_time + timedelta(minutes=10)
            events.append({'device_id': 'switch.coffee', 'timestamp': off_time, 'state': 'off'})
            events.append({'device_id': 'switch.coffee', 'timestamp': on_time, 'state': 'on'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        assert len(patterns) >= 1
        off_pattern = next(
            (p for p in patterns if p['state'] == 'off'),
            None
        )
        assert off_pattern is not None
        assert off_pattern['device_id'] == 'switch.coffee'
        assert off_pattern['avg_duration'] == pytest.approx(600.0, rel=0.1)

    def test_variable_duration_filtered(self, base_time):
        """Test that highly variable durations are filtered out."""
        detector = DurationPatternDetector(
            min_state_changes=3,
            min_confidence=0.5,
            max_cv=0.2,
            filter_system_noise=False,
        )

        events = []
        durations = [60, 600, 30, 1200]
        for i, duration in enumerate(durations):
            on_time = base_time + timedelta(hours=i * 2)
            off_time = on_time + timedelta(seconds=duration)
            events.append({'device_id': 'light.random', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.random', 'timestamp': off_time, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        on_patterns = [p for p in patterns if p['device_id'] == 'light.random' and p['state'] == 'on']
        assert len(on_patterns) == 0

    def test_multiple_devices(self, detector, base_time):
        """Test detection across multiple devices."""
        events = []

        for i in range(5):
            on_time = base_time + timedelta(hours=i)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'light.bedroom', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.bedroom', 'timestamp': off_time, 'state': 'off'})

        for i in range(5):
            on_time = base_time + timedelta(hours=i, minutes=30)
            off_time = on_time + timedelta(minutes=10)
            events.append({'device_id': 'light.kitchen', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.kitchen', 'timestamp': off_time, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        devices = set(p['device_id'] for p in patterns)
        assert 'light.bedroom' in devices
        assert 'light.kitchen' in devices

    def test_insufficient_samples(self, base_time):
        """Test that patterns with insufficient samples are skipped."""
        detector = DurationPatternDetector(
            min_state_changes=10,
            filter_system_noise=False,
        )

        events = []
        for i in range(3):
            on_time = base_time + timedelta(hours=i)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'light.bedroom', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.bedroom', 'timestamp': off_time, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        assert len(patterns) == 0


class TestStateNormalization:
    """Tests for state normalization."""

    @pytest.fixture
    def detector(self):
        return DurationPatternDetector(filter_system_noise=False)

    def test_normalize_on_states(self, detector):
        """Test normalization of various 'on' states."""
        assert detector._normalize_state('on') == 'on'
        assert detector._normalize_state('ON') == 'on'
        assert detector._normalize_state('true') == 'on'
        assert detector._normalize_state('True') == 'on'
        assert detector._normalize_state('home') == 'on'
        assert detector._normalize_state('open') == 'on'
        assert detector._normalize_state('unlocked') == 'on'
        assert detector._normalize_state('playing') == 'on'
        assert detector._normalize_state('active') == 'on'

    def test_normalize_off_states(self, detector):
        """Test normalization of various 'off' states."""
        assert detector._normalize_state('off') == 'off'
        assert detector._normalize_state('OFF') == 'off'
        assert detector._normalize_state('false') == 'off'
        assert detector._normalize_state('False') == 'off'
        assert detector._normalize_state('away') == 'off'
        assert detector._normalize_state('closed') == 'off'
        assert detector._normalize_state('locked') == 'off'
        assert detector._normalize_state('idle') == 'off'
        assert detector._normalize_state('standby') == 'off'
        assert detector._normalize_state('paused') == 'off'

    def test_normalize_numeric_states(self, detector):
        """Test normalization of numeric states."""
        assert detector._normalize_state('1') == 'on'
        assert detector._normalize_state('100') == 'on'
        assert detector._normalize_state('0.5') == 'on'
        assert detector._normalize_state('0') == 'off'
        assert detector._normalize_state('0.0') == 'off'

    def test_normalize_unknown_states(self, detector):
        """Test that unknown states are preserved."""
        assert detector._normalize_state('heating') == 'heating'
        assert detector._normalize_state('cooling') == 'cooling'
        assert detector._normalize_state('unknown') == 'unknown'


class TestAnomalyDetection:
    """Tests for anomaly detection functionality."""

    @pytest.fixture
    def detector(self):
        return DurationPatternDetector(
            min_state_changes=3,
            min_confidence=0.3,
            anomaly_threshold_std=2.0,
            max_cv=1.0,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 6, 8, 0, 0)

    def test_detects_long_anomaly(self, detector, base_time):
        """Test detection of anomalously long duration."""
        events = []
        for i in range(5):
            on_time = base_time + timedelta(hours=i)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'light.test', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.test', 'timestamp': off_time, 'state': 'off'})

        anomaly_on = base_time + timedelta(hours=10)
        anomaly_off = anomaly_on + timedelta(minutes=30)
        events.append({'device_id': 'light.test', 'timestamp': anomaly_on, 'state': 'on'})
        events.append({'device_id': 'light.test', 'timestamp': anomaly_off, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        on_pattern = next(
            (p for p in patterns if p['state'] == 'on'),
            None
        )
        assert on_pattern is not None
        anomalies = on_pattern['anomalies']
        long_anomalies = [a for a in anomalies if a['direction'] == 'long']
        assert len(long_anomalies) >= 1

    def test_detects_short_anomaly(self, detector, base_time):
        """Test detection of anomalously short duration."""
        events = []
        for i in range(5):
            on_time = base_time + timedelta(hours=i)
            off_time = on_time + timedelta(minutes=10)
            events.append({'device_id': 'light.test', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.test', 'timestamp': off_time, 'state': 'off'})

        anomaly_on = base_time + timedelta(hours=10)
        anomaly_off = anomaly_on + timedelta(seconds=30)
        events.append({'device_id': 'light.test', 'timestamp': anomaly_on, 'state': 'on'})
        events.append({'device_id': 'light.test', 'timestamp': anomaly_off, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        on_pattern = next(
            (p for p in patterns if p['state'] == 'on'),
            None
        )
        assert on_pattern is not None
        anomalies = on_pattern['anomalies']
        short_anomalies = [a for a in anomalies if a['direction'] == 'short']
        assert len(short_anomalies) >= 1

    def test_no_anomalies_for_consistent_data(self, detector, base_time):
        """Test no anomalies detected for perfectly consistent data."""
        events = []
        for i in range(6):
            on_time = base_time + timedelta(hours=i)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'light.test', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.test', 'timestamp': off_time, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        on_pattern = next(
            (p for p in patterns if p['state'] == 'on'),
            None
        )
        assert on_pattern is not None
        assert len(on_pattern['anomalies']) == 0


class TestSystemNoiseFiltering:
    """Tests for system noise filtering."""

    @pytest.fixture
    def detector_with_filter(self):
        return DurationPatternDetector(
            min_state_changes=3,
            min_confidence=0.5,
            filter_system_noise=True,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 6, 8, 0, 0)

    def test_filters_system_sensors(self, detector_with_filter, base_time):
        """Test that system sensors are filtered out."""
        events = []
        for i in range(5):
            on_time = base_time + timedelta(hours=i)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'sensor.home_assistant_cpu', 'timestamp': on_time, 'state': '50'})
            events.append({'device_id': 'sensor.home_assistant_cpu', 'timestamp': off_time, 'state': '60'})
            events.append({'device_id': 'light.bedroom', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.bedroom', 'timestamp': off_time, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector_with_filter.detect_patterns(df)

        for pattern in patterns:
            assert 'home_assistant' not in pattern['device_id']

    def test_filters_external_trackers(self, detector_with_filter, base_time):
        """Test that external trackers are filtered out."""
        events = []
        for i in range(5):
            time = base_time + timedelta(hours=i)
            events.append({'device_id': 'sensor.nfl_team_tracker', 'timestamp': time, 'state': 'on'})
            events.append({'device_id': 'sensor.nfl_team_tracker', 'timestamp': time + timedelta(minutes=5), 'state': 'off'})
            events.append({'device_id': 'light.living_room', 'timestamp': time, 'state': 'on'})
            events.append({'device_id': 'light.living_room', 'timestamp': time + timedelta(minutes=5), 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector_with_filter.detect_patterns(df)

        for pattern in patterns:
            assert 'tracker' not in pattern['device_id']

    def test_keeps_actionable_devices(self, detector_with_filter, base_time):
        """Test that actionable devices are kept."""
        events = []
        for i in range(5):
            on_time = base_time + timedelta(hours=i)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'light.bedroom', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.bedroom', 'timestamp': off_time, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector_with_filter.detect_patterns(df)

        devices = [p['device_id'] for p in patterns]
        assert 'light.bedroom' in devices


class TestPatternSummary:
    """Tests for pattern summary functionality."""

    def test_empty_patterns_summary(self):
        """Test summary with no patterns."""
        detector = DurationPatternDetector()
        summary = detector.get_pattern_summary([])

        assert summary['total_patterns'] == 0
        assert summary['unique_devices'] == 0
        assert summary['avg_confidence'] == 0.0
        assert summary['total_anomalies'] == 0

    def test_patterns_summary(self):
        """Test summary calculation."""
        detector = DurationPatternDetector()
        patterns = [
            {
                'pattern_type': 'duration',
                'device_id': 'light.bedroom',
                'state': 'on',
                'confidence': 0.8,
                'avg_duration': 300.0,
                'anomalies': [{'direction': 'long'}],
            },
            {
                'pattern_type': 'duration',
                'device_id': 'light.kitchen',
                'state': 'on',
                'confidence': 0.9,
                'avg_duration': 600.0,
                'anomalies': [],
            },
        ]

        summary = detector.get_pattern_summary(patterns)

        assert summary['total_patterns'] == 2
        assert summary['unique_devices'] == 2
        assert summary['avg_confidence'] == pytest.approx(0.85, rel=0.01)
        assert summary['avg_duration'] == pytest.approx(450.0, rel=0.01)
        assert summary['total_anomalies'] == 1


class TestAutomationSuggestion:
    """Tests for automation suggestion functionality."""

    @pytest.fixture
    def detector(self):
        return DurationPatternDetector()

    def test_suggest_auto_off_for_light(self, detector):
        """Test auto-off suggestion for light pattern."""
        pattern = {
            'pattern_type': 'duration',
            'device_id': 'light.bathroom',
            'state': 'on',
            'occurrences': 20,
            'confidence': 0.85,
            'avg_duration': 300.0,
            'std_duration': 30.0,
        }

        suggestion = detector.suggest_automation(pattern)

        assert suggestion['automation_type'] == 'duration_auto_off'
        assert suggestion['confidence'] == 0.85
        assert 'trigger' in suggestion
        assert 'action' in suggestion
        assert suggestion['trigger']['entity_id'] == 'light.bathroom'
        assert suggestion['action']['service'] == 'light.turn_off'

    def test_suggest_alert_for_off_state(self, detector):
        """Test alert suggestion for off state pattern."""
        pattern = {
            'pattern_type': 'duration',
            'device_id': 'sensor.motion',
            'state': 'off',
            'occurrences': 15,
            'confidence': 0.8,
            'avg_duration': 3600.0,
            'std_duration': 300.0,
        }

        suggestion = detector.suggest_automation(pattern)

        assert suggestion['automation_type'] == 'duration_alert'
        assert suggestion['safety_level'] == 'informational'
        assert 'notify' in suggestion['action']['service']

    def test_suggest_automation_wrong_type(self, detector):
        """Test that non-duration patterns return empty."""
        pattern = {
            'pattern_type': 'sequence',
            'device_id': 'light.bedroom',
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion == {}

    def test_suggest_automation_invalid_duration(self, detector):
        """Test that zero/negative duration returns empty."""
        pattern = {
            'pattern_type': 'duration',
            'device_id': 'light.bedroom',
            'state': 'on',
            'avg_duration': 0,
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion == {}


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_domain(self):
        """Test domain extraction."""
        detector = DurationPatternDetector()

        assert detector._get_domain('light.bedroom') == 'light'
        assert detector._get_domain('binary_sensor.motion') == 'binary_sensor'
        assert detector._get_domain('switch.coffee_maker') == 'switch'
        assert detector._get_domain('no_domain') == 'default'
        assert detector._get_domain('') == 'default'

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        detector = DurationPatternDetector()

        assert detector._format_duration(30) == '30s'
        assert detector._format_duration(59) == '59s'

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        detector = DurationPatternDetector()

        assert detector._format_duration(60) == '1.0min'
        assert detector._format_duration(300) == '5.0min'
        assert detector._format_duration(3599) == '60.0min'

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        detector = DurationPatternDetector()

        assert detector._format_duration(3600) == '1.0h'
        assert detector._format_duration(7200) == '2.0h'
        assert detector._format_duration(86400) == '24.0h'

    def test_is_actionable_entity(self):
        """Test actionable entity detection."""
        detector = DurationPatternDetector()

        assert detector._is_actionable_entity('light.bedroom') is True
        assert detector._is_actionable_entity('switch.coffee_maker') is True
        assert detector._is_actionable_entity('binary_sensor.motion') is True

        assert detector._is_actionable_entity('sensor.home_assistant_cpu') is False
        assert detector._is_actionable_entity('image.roborock_map') is False
        assert detector._is_actionable_entity('camera.front_door') is False

    def test_get_anomalies_for_device(self):
        """Test retrieving anomalies for specific device."""
        detector = DurationPatternDetector()
        patterns = [
            {
                'device_id': 'light.bedroom',
                'state': 'on',
                'anomalies': [
                    {'duration_seconds': 1800, 'direction': 'long'},
                ],
            },
            {
                'device_id': 'light.kitchen',
                'state': 'on',
                'anomalies': [
                    {'duration_seconds': 10, 'direction': 'short'},
                ],
            },
        ]

        bedroom_anomalies = detector.get_anomalies_for_device(patterns, 'light.bedroom')
        assert len(bedroom_anomalies) == 1
        assert bedroom_anomalies[0]['direction'] == 'long'
        assert bedroom_anomalies[0]['device_id'] == 'light.bedroom'


class TestDurationExtraction:
    """Tests for duration extraction logic."""

    @pytest.fixture
    def detector(self):
        return DurationPatternDetector(
            min_duration_seconds=1.0,
            max_duration_hours=24.0,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 6, 8, 0, 0)

    def test_filters_too_short_durations(self, base_time):
        """Test that durations below minimum are filtered."""
        detector = DurationPatternDetector(
            min_duration_seconds=10.0,
            filter_system_noise=False,
        )

        events = pd.DataFrame({
            'device_id': ['light.test', 'light.test'],
            'timestamp': [base_time, base_time + timedelta(seconds=5)],
            'state': ['on', 'off'],
        })

        durations = detector._extract_durations(events)
        assert len(durations) == 0

    def test_filters_too_long_durations(self, base_time):
        """Test that durations above maximum are filtered."""
        detector = DurationPatternDetector(
            max_duration_hours=1.0,
            filter_system_noise=False,
        )

        events = pd.DataFrame({
            'device_id': ['light.test', 'light.test'],
            'timestamp': [base_time, base_time + timedelta(hours=2)],
            'state': ['on', 'off'],
        })

        durations = detector._extract_durations(events)
        assert len(durations) == 0

    def test_handles_same_state_transitions(self, detector, base_time):
        """Test that same-state 'transitions' don't create durations."""
        events = pd.DataFrame({
            'device_id': ['light.test', 'light.test', 'light.test'],
            'timestamp': [
                base_time,
                base_time + timedelta(minutes=5),
                base_time + timedelta(minutes=10),
            ],
            'state': ['on', 'on', 'off'],
        })

        durations = detector._extract_durations(events)

        assert len(durations) == 1
        assert durations[0].duration_seconds == pytest.approx(600.0, rel=0.1)


class TestConfidenceCalculation:
    """Tests for confidence calculation."""

    def test_high_confidence_for_many_samples_low_cv(self):
        """Test high confidence with many samples and low CV."""
        detector = DurationPatternDetector(min_state_changes=5)

        stats = DurationStats(
            device_id='light.test',
            state='on',
            count=50,
            mean_seconds=300.0,
            std_seconds=15.0,
            min_seconds=270.0,
            max_seconds=330.0,
            coefficient_of_variation=0.05,
            durations=[300.0] * 50,
        )

        confidence = detector._calculate_confidence(stats)
        assert confidence > 0.8

    def test_lower_confidence_for_few_samples(self):
        """Test lower confidence with few samples."""
        detector = DurationPatternDetector(min_state_changes=5)

        stats = DurationStats(
            device_id='light.test',
            state='on',
            count=6,
            mean_seconds=300.0,
            std_seconds=15.0,
            min_seconds=270.0,
            max_seconds=330.0,
            coefficient_of_variation=0.05,
            durations=[300.0] * 6,
        )

        confidence = detector._calculate_confidence(stats)
        assert 0.5 < confidence < 0.9

    def test_lower_confidence_for_high_cv(self):
        """Test lower confidence with high coefficient of variation."""
        detector = DurationPatternDetector(min_state_changes=5, max_cv=1.0)

        stats = DurationStats(
            device_id='light.test',
            state='on',
            count=50,
            mean_seconds=300.0,
            std_seconds=150.0,
            min_seconds=100.0,
            max_seconds=500.0,
            coefficient_of_variation=0.5,
            durations=[300.0] * 50,
        )

        confidence = detector._calculate_confidence(stats)
        assert confidence < 0.8
