"""
Unit tests for SequencePatternDetector.

Epic 37, Story 37.1: Sequence Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.sequence import SequencePatternDetector


class TestSequencePatternDetectorInit:
    """Tests for SequencePatternDetector initialization."""

    def test_default_initialization(self):
        """Test detector initializes with default values."""
        detector = SequencePatternDetector()

        assert detector.min_occurrences == 3
        assert detector.min_confidence == 0.7
        assert detector.window_minutes == 30
        assert detector.gap_tolerance_minutes == 5
        assert detector.min_sequence_length == 2
        assert detector.max_sequence_length == 5
        assert detector.filter_system_noise is True
        assert detector.aggregate_client is None

    def test_custom_initialization(self):
        """Test detector initializes with custom values."""
        detector = SequencePatternDetector(
            min_occurrences=5,
            min_confidence=0.8,
            window_minutes=15,
            gap_tolerance_minutes=3,
            min_sequence_length=3,
            max_sequence_length=4,
            filter_system_noise=False,
        )

        assert detector.min_occurrences == 5
        assert detector.min_confidence == 0.8
        assert detector.window_minutes == 15
        assert detector.gap_tolerance_minutes == 3
        assert detector.min_sequence_length == 3
        assert detector.max_sequence_length == 4
        assert detector.filter_system_noise is False


class TestSequencePatternDetection:
    """Tests for pattern detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector with relaxed thresholds for testing."""
        return SequencePatternDetector(
            min_occurrences=2,
            min_confidence=0.5,
            window_minutes=10,
            gap_tolerance_minutes=3,
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

    def test_single_event(self, detector, base_time):
        """Test with single event (too few for sequence)."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom'],
            'timestamp': [base_time],
            'state': ['on'],
        })
        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_simple_two_device_sequence(self, detector, base_time):
        """Test detection of simple A → B sequence."""
        events = pd.DataFrame({
            'device_id': [
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(seconds=30),
                base_time + timedelta(hours=1),
                base_time + timedelta(hours=1, seconds=30),
                base_time + timedelta(hours=2),
                base_time + timedelta(hours=2, seconds=30),
            ],
            'state': ['on', 'on', 'on', 'on', 'on', 'on'],
        })

        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        seq_pattern = next(
            (p for p in patterns if p['pattern_type'] == 'sequence'),
            None
        )
        assert seq_pattern is not None
        assert seq_pattern['sequence'] == ['binary_sensor.motion', 'light.bedroom']
        assert seq_pattern['occurrences'] >= 2

    def test_three_device_sequence(self, detector, base_time):
        """Test detection of A → B → C sequence."""
        events = pd.DataFrame({
            'device_id': [
                'binary_sensor.motion', 'light.hallway', 'light.living_room',
                'binary_sensor.motion', 'light.hallway', 'light.living_room',
                'binary_sensor.motion', 'light.hallway', 'light.living_room',
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(seconds=30),
                base_time + timedelta(seconds=60),
                base_time + timedelta(hours=1),
                base_time + timedelta(hours=1, seconds=30),
                base_time + timedelta(hours=1, seconds=60),
                base_time + timedelta(hours=2),
                base_time + timedelta(hours=2, seconds=30),
                base_time + timedelta(hours=2, seconds=60),
            ],
            'state': ['on'] * 9,
        })

        patterns = detector.detect_patterns(events)

        # Should detect 3-step sequence
        three_step = [p for p in patterns if len(p['sequence']) == 3]
        assert len(three_step) >= 1

        pattern = three_step[0]
        assert pattern['sequence'] == [
            'binary_sensor.motion', 'light.hallway', 'light.living_room'
        ]

    def test_no_self_loops(self, detector, base_time):
        """Test that same device repeated is not included in sequence."""
        events = pd.DataFrame({
            'device_id': [
                'light.bedroom', 'light.bedroom', 'light.living_room',
                'light.bedroom', 'light.bedroom', 'light.living_room',
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(seconds=10),
                base_time + timedelta(seconds=30),
                base_time + timedelta(hours=1),
                base_time + timedelta(hours=1, seconds=10),
                base_time + timedelta(hours=1, seconds=30),
            ],
            'state': ['on'] * 6,
        })

        patterns = detector.detect_patterns(events)

        # Should only have bedroom → living_room (no bedroom → bedroom)
        for pattern in patterns:
            seq = pattern['sequence']
            for i in range(len(seq) - 1):
                assert seq[i] != seq[i + 1]

    def test_gap_tolerance_exceeded(self, detector, base_time):
        """Test sequence breaks when gap exceeds tolerance."""
        # Gap is 5 minutes, tolerance is 3 minutes
        events = pd.DataFrame({
            'device_id': [
                'light.bedroom', 'light.living_room',
                'light.bedroom', 'light.living_room',
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(minutes=5),  # Exceeds 3 min tolerance
                base_time + timedelta(hours=1),
                base_time + timedelta(hours=1, minutes=5),
            ],
            'state': ['on'] * 4,
        })

        patterns = detector.detect_patterns(events)

        # Should not detect patterns due to gap tolerance
        two_step = [
            p for p in patterns
            if len(p['sequence']) == 2 and
            p['sequence'] == ['light.bedroom', 'light.living_room']
        ]
        assert len(two_step) == 0

    def test_window_exceeded(self, detector, base_time):
        """Test events outside window are not included."""
        # Window is 10 minutes
        events = pd.DataFrame({
            'device_id': [
                'light.bedroom', 'light.living_room',
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(minutes=15),  # Exceeds 10 min window
            ],
            'state': ['on'] * 2,
        })

        patterns = detector.detect_patterns(events)
        assert patterns == []

    def test_confidence_calculation(self, detector, base_time):
        """Test confidence is calculated correctly."""
        # Create events where sequence occurs 3 out of 4 times first device fires
        events = pd.DataFrame({
            'device_id': [
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion',  # No follow-up
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(seconds=30),
                base_time + timedelta(hours=1),
                base_time + timedelta(hours=1, seconds=30),
                base_time + timedelta(hours=2),
                base_time + timedelta(hours=2, seconds=30),
                base_time + timedelta(hours=3),  # Alone
            ],
            'state': ['on'] * 7,
        })

        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]
        # 3 completions / 4 triggers = 0.75 raw confidence
        assert 0.5 <= pattern['confidence'] <= 1.0

    def test_timing_statistics(self, detector, base_time):
        """Test that timing statistics are captured."""
        events = pd.DataFrame({
            'device_id': [
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
                'binary_sensor.motion', 'light.bedroom',
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(seconds=30),
                base_time + timedelta(hours=1),
                base_time + timedelta(hours=1, seconds=30),
                base_time + timedelta(hours=2),
                base_time + timedelta(hours=2, seconds=30),
            ],
            'state': ['on'] * 6,
        })

        patterns = detector.detect_patterns(events)

        assert len(patterns) >= 1
        pattern = patterns[0]

        assert 'avg_step_times' in pattern
        assert 'total_duration' in pattern
        assert len(pattern['avg_step_times']) == 1  # One step (A → B)
        assert pattern['avg_step_times'][0] == pytest.approx(30.0, rel=0.1)


class TestSystemNoiseFiltering:
    """Tests for system noise filtering."""

    @pytest.fixture
    def detector_with_filter(self):
        """Detector with filtering enabled."""
        return SequencePatternDetector(
            min_occurrences=2,
            min_confidence=0.5,
            filter_system_noise=True,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 6, 8, 0, 0)

    def test_filters_system_sensors(self, detector_with_filter, base_time):
        """Test that system sensors are filtered out."""
        events = pd.DataFrame({
            'device_id': [
                'sensor.home_assistant_cpu',
                'light.bedroom',
                'sensor.home_assistant_memory',
                'light.living_room',
            ],
            'timestamp': [
                base_time,
                base_time + timedelta(seconds=10),
                base_time + timedelta(seconds=20),
                base_time + timedelta(seconds=30),
            ],
            'state': ['50', 'on', '1024', 'on'],
        })

        patterns = detector_with_filter.detect_patterns(events)

        # Should only have light.bedroom → light.living_room
        for pattern in patterns:
            for device in pattern['sequence']:
                assert 'home_assistant' not in device

    def test_filters_external_trackers(self, detector_with_filter, base_time):
        """Test that external trackers are filtered out."""
        events = pd.DataFrame({
            'device_id': [
                'sensor.nfl_team_tracker',
                'light.bedroom',
                'sensor.weather_temperature',
                'light.living_room',
            ],
            'timestamp': [
                base_time + timedelta(seconds=i * 10) for i in range(4)
            ],
            'state': ['game', 'on', '72', 'on'],
        })

        patterns = detector_with_filter.detect_patterns(events)

        for pattern in patterns:
            for device in pattern['sequence']:
                assert 'tracker' not in device
                assert 'weather' not in device

    def test_keeps_actionable_devices(self, detector_with_filter, base_time):
        """Test that actionable devices are kept."""
        events = pd.DataFrame({
            'device_id': [
                'binary_sensor.motion_hallway',
                'light.bedroom',
                'switch.coffee_maker',
            ] * 3,
            'timestamp': [
                base_time + timedelta(hours=h, seconds=s)
                for h in range(3)
                for s in [0, 30, 60]
            ],
            'state': ['on'] * 9,
        })

        patterns = detector_with_filter.detect_patterns(events)

        # Should detect sequences with these devices
        assert len(patterns) >= 1


class TestPatternSummary:
    """Tests for pattern summary functionality."""

    def test_empty_patterns_summary(self):
        """Test summary with no patterns."""
        detector = SequencePatternDetector()
        summary = detector.get_pattern_summary([])

        assert summary['total_patterns'] == 0
        assert summary['unique_sequences'] == 0
        assert summary['avg_confidence'] == 0.0

    def test_patterns_summary(self):
        """Test summary calculation."""
        detector = SequencePatternDetector()
        patterns = [
            {
                'pattern_type': 'sequence',
                'sequence': ['a', 'b'],
                'confidence': 0.8,
                'total_duration': 30.0,
            },
            {
                'pattern_type': 'sequence',
                'sequence': ['c', 'd', 'e'],
                'confidence': 0.9,
                'total_duration': 60.0,
            },
        ]

        summary = detector.get_pattern_summary(patterns)

        assert summary['total_patterns'] == 2
        assert summary['avg_confidence'] == pytest.approx(0.85, rel=0.01)
        assert summary['avg_sequence_length'] == pytest.approx(2.5, rel=0.01)
        assert summary['avg_duration'] == pytest.approx(45.0, rel=0.01)


class TestAutomationSuggestion:
    """Tests for automation suggestion functionality."""

    @pytest.fixture
    def detector(self):
        return SequencePatternDetector()

    def test_suggest_automation_basic(self, detector):
        """Test basic automation suggestion from sequence pattern."""
        pattern = {
            'pattern_type': 'sequence',
            'device_id': 'binary_sensor.motion',
            'sequence': ['binary_sensor.motion', 'light.bedroom'],
            'occurrences': 10,
            'confidence': 0.85,
            'avg_step_times': [30.0],
            'total_duration': 30.0,
            'metadata': {
                'sequence_str': 'binary_sensor.motion → light.bedroom',
            },
        }

        suggestion = detector.suggest_automation(pattern)

        assert suggestion['automation_type'] == 'sequence'
        assert suggestion['confidence'] == 0.85
        assert 'trigger' in suggestion
        assert 'action' in suggestion
        assert suggestion['trigger']['entity_id'] == 'binary_sensor.motion'

    def test_suggest_automation_wrong_type(self, detector):
        """Test that non-sequence patterns return empty."""
        pattern = {
            'pattern_type': 'time_of_day',
            'device_id': 'light.bedroom',
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion == {}

    def test_suggest_automation_with_delays(self, detector):
        """Test automation with delay actions."""
        pattern = {
            'pattern_type': 'sequence',
            'device_id': 'binary_sensor.motion',
            'sequence': ['binary_sensor.motion', 'light.hallway', 'light.living_room'],
            'occurrences': 5,
            'confidence': 0.8,
            'avg_step_times': [15.0, 30.0],
            'total_duration': 45.0,
            'metadata': {},
        }

        suggestion = detector.suggest_automation(pattern)

        assert suggestion['automation_type'] == 'sequence'
        # Should have multiple actions
        actions = suggestion['action']
        assert isinstance(actions, list)
        assert len(actions) == 2


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_domain(self):
        """Test domain extraction."""
        detector = SequencePatternDetector()

        assert detector._get_domain('light.bedroom') == 'light'
        assert detector._get_domain('binary_sensor.motion') == 'binary_sensor'
        assert detector._get_domain('switch.coffee_maker') == 'switch'
        assert detector._get_domain('no_domain') == 'default'
        assert detector._get_domain('') == 'default'

    def test_is_actionable_entity(self):
        """Test actionable entity detection."""
        detector = SequencePatternDetector()

        # Should be actionable
        assert detector._is_actionable_entity('light.bedroom') is True
        assert detector._is_actionable_entity('switch.coffee_maker') is True
        assert detector._is_actionable_entity('binary_sensor.motion') is True

        # Should not be actionable
        assert detector._is_actionable_entity('sensor.home_assistant_cpu') is False
        assert detector._is_actionable_entity('image.roborock_map') is False
        assert detector._is_actionable_entity('camera.front_door') is False

    def test_calculate_timing_consistency(self):
        """Test timing consistency calculation."""
        detector = SequencePatternDetector()

        # Perfect consistency (no variance)
        score = detector._calculate_timing_consistency([0.0], [30.0])
        assert score == 1.0

        # Some variance
        score = detector._calculate_timing_consistency([15.0], [30.0])
        assert 0.5 < score < 1.0

        # High variance
        score = detector._calculate_timing_consistency([60.0], [30.0])
        assert score < 0.5

        # Empty data
        score = detector._calculate_timing_consistency([], [])
        assert score == 0.5

    def test_get_default_service(self):
        """Test default service mapping."""
        detector = SequencePatternDetector()

        assert detector._get_default_service('light') == 'turn_on'
        assert detector._get_default_service('switch') == 'turn_on'
        assert detector._get_default_service('cover') == 'open_cover'
        assert detector._get_default_service('lock') == 'lock'
        assert detector._get_default_service('vacuum') == 'start'
        assert detector._get_default_service('unknown') == 'turn_on'

    def test_build_trigger(self):
        """Test trigger building for different domains."""
        detector = SequencePatternDetector()

        trigger = detector._build_trigger('binary_sensor.motion', 'binary_sensor')
        assert trigger['platform'] == 'state'
        assert trigger['to'] == 'on'

        trigger = detector._build_trigger('light.bedroom', 'light')
        assert trigger['platform'] == 'state'
        assert trigger['to'] == 'on'

        trigger = detector._build_trigger('sensor.temperature', 'sensor')
        assert trigger['platform'] == 'state'
        assert 'to' not in trigger
