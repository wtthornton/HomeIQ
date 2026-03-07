"""
Unit tests for RoomBasedPatternDetector.

Epic 37, Story 37.4: Room-Based Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.room_based import RoomBasedPatternDetector


class TestRoomBasedDetectorInit:
    """Tests for RoomBasedPatternDetector initialization."""

    def test_default_initialization(self):
        """Test detector initializes with default values."""
        detector = RoomBasedPatternDetector()

        assert detector.window_minutes == 2.0
        assert detector.min_occurrences == 3
        assert detector.min_confidence == 0.7
        assert detector.min_devices == 2
        assert detector.max_devices == 8
        assert detector.filter_system_noise is True
        assert detector.aggregate_client is None

    def test_custom_initialization(self):
        """Test detector initializes with custom values."""
        detector = RoomBasedPatternDetector(
            window_minutes=5.0,
            min_occurrences=5,
            min_confidence=0.8,
            min_devices=3,
            max_devices=6,
            filter_system_noise=False,
        )

        assert detector.window_minutes == 5.0
        assert detector.min_occurrences == 5
        assert detector.min_confidence == 0.8
        assert detector.min_devices == 3
        assert detector.max_devices == 6
        assert detector.filter_system_noise is False


class TestAreaIdExtraction:
    """Tests for area_id extraction from entity IDs."""

    def test_single_word_room(self):
        """Test extraction of single-word room names."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id(
            "light.bedroom_lamp"
        )
        assert result == "bedroom"

    def test_multi_word_room(self):
        """Test extraction of multi-word room names."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id(
            "light.living_room_lamp"
        )
        assert result == "living_room"

    def test_dining_room(self):
        """Test dining_room extraction."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id(
            "switch.dining_room_chandelier"
        )
        assert result == "dining_room"

    def test_simple_entity(self):
        """Test entity with just domain.room."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id(
            "light.hallway"
        )
        assert result == "hallway"

    def test_binary_sensor(self):
        """Test binary sensor extraction."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id(
            "binary_sensor.bedroom_motion"
        )
        assert result == "bedroom"

    def test_climate_entity(self):
        """Test climate entity extraction."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id(
            "climate.upstairs_thermostat"
        )
        assert result == "upstairs"

    def test_empty_entity(self):
        """Test empty entity ID."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id("")
        assert result == "unknown"

    def test_no_dot_entity(self):
        """Test entity without domain separator."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id("nodot")
        assert result == "unknown"

    def test_none_entity(self):
        """Test None entity ID."""
        result = RoomBasedPatternDetector._extract_area_from_entity_id(None)
        assert result == "unknown"


class TestRoomPatternDetection:
    """Tests for room-based pattern detection."""

    @pytest.fixture
    def detector(self):
        """Create detector with relaxed thresholds for testing."""
        return RoomBasedPatternDetector(
            window_minutes=2.0,
            min_occurrences=2,
            min_confidence=0.3,
            min_devices=2,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        """Base timestamp for test events."""
        return datetime(2026, 3, 6, 20, 0, 0)  # 8 PM evening

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

    def test_basic_room_pattern_with_area_id(self, detector, base_time):
        """Test detection with explicit area_id column."""
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.living_room_lamp', 'timestamp': t,
                 'state': 'on', 'area_id': 'living_room'},
                {'device_id': 'media_player.living_room_tv', 'timestamp': t + timedelta(seconds=30),
                 'state': 'on', 'area_id': 'living_room'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1

        pattern = patterns[0]
        assert pattern['pattern_type'] == 'room_based'
        assert pattern['area_id'] == 'living_room'
        assert len(pattern['device_group']) == 2
        assert pattern['period'] == 'evening'

    def test_basic_room_pattern_without_area_id(self, detector, base_time):
        """Test detection using entity_id prefix fallback."""
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.kitchen_light', 'timestamp': t, 'state': 'on'},
                {'device_id': 'switch.kitchen_fan', 'timestamp': t + timedelta(seconds=20),
                 'state': 'on'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1
        assert patterns[0]['area_id'] == 'kitchen'

    def test_multiple_rooms(self, detector, base_time):
        """Test detection across multiple rooms."""
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            # Living room evening
            events_data.extend([
                {'device_id': 'light.living_room_lamp', 'timestamp': t,
                 'state': 'on', 'area_id': 'living_room'},
                {'device_id': 'switch.living_room_fan', 'timestamp': t + timedelta(seconds=30),
                 'state': 'on', 'area_id': 'living_room'},
            ])
            # Bedroom morning
            morning = base_time.replace(hour=7) + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.bedroom_light', 'timestamp': morning,
                 'state': 'on', 'area_id': 'bedroom'},
                {'device_id': 'cover.bedroom_blinds', 'timestamp': morning + timedelta(seconds=45),
                 'state': 'open', 'area_id': 'bedroom'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        areas = {p['area_id'] for p in patterns}
        assert 'living_room' in areas
        assert 'bedroom' in areas

    def test_devices_outside_window_not_grouped(self, detector, base_time):
        """Test that events outside the window are not grouped."""
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.kitchen_light', 'timestamp': t,
                 'state': 'on', 'area_id': 'kitchen'},
                # 10 minutes later - outside 2-minute window
                {'device_id': 'switch.kitchen_fan', 'timestamp': t + timedelta(minutes=10),
                 'state': 'on', 'area_id': 'kitchen'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        # Should not detect any patterns since devices are too far apart
        assert len(patterns) == 0

    def test_single_device_room_not_detected(self, detector, base_time):
        """Test that single-device rooms are not detected."""
        events_data = []
        for day in range(5):
            t = base_time + timedelta(days=day)
            events_data.append(
                {'device_id': 'light.garage_light', 'timestamp': t,
                 'state': 'on', 'area_id': 'garage'},
            )

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        assert len(patterns) == 0

    def test_insufficient_occurrences(self, base_time):
        """Test that patterns below min_occurrences are not detected."""
        detector = RoomBasedPatternDetector(
            min_occurrences=5,
            min_confidence=0.3,
            min_devices=2,
            filter_system_noise=False,
        )

        # Only 2 occurrences
        events_data = []
        for day in range(2):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.bedroom_light', 'timestamp': t,
                 'state': 'on', 'area_id': 'bedroom'},
                {'device_id': 'fan.bedroom_fan', 'timestamp': t + timedelta(seconds=30),
                 'state': 'on', 'area_id': 'bedroom'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        assert len(patterns) == 0

    def test_three_device_room_pattern(self, detector, base_time):
        """Test detection with 3 devices in a room."""
        events_data = []
        for day in range(4):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.living_room_lamp', 'timestamp': t,
                 'state': 'on', 'area_id': 'living_room'},
                {'device_id': 'media_player.living_room_tv', 'timestamp': t + timedelta(seconds=20),
                 'state': 'on', 'area_id': 'living_room'},
                {'device_id': 'climate.living_room_ac', 'timestamp': t + timedelta(seconds=50),
                 'state': 'cool', 'area_id': 'living_room'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1
        # Should find the 3-device pattern
        three_device = [p for p in patterns if len(p['device_group']) == 3]
        assert len(three_device) >= 1

    def test_pattern_output_structure(self, detector, base_time):
        """Test that pattern output has all required fields."""
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.bedroom_light', 'timestamp': t,
                 'state': 'on', 'area_id': 'bedroom'},
                {'device_id': 'fan.bedroom_fan', 'timestamp': t + timedelta(seconds=30),
                 'state': 'on', 'area_id': 'bedroom'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1

        pattern = patterns[0]
        assert 'pattern_type' in pattern
        assert 'device_id' in pattern
        assert 'area_id' in pattern
        assert 'device_group' in pattern
        assert 'period' in pattern
        assert 'occurrences' in pattern
        assert 'confidence' in pattern
        assert 'avg_hour' in pattern
        assert 'metadata' in pattern
        assert 'n_devices' in pattern['metadata']
        assert 'std_hour' in pattern['metadata']
        assert 'thresholds' in pattern['metadata']

    def test_unknown_area_filtered(self, detector, base_time):
        """Test that events with unknown area are filtered out."""
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.x', 'timestamp': t,
                 'state': 'on', 'area_id': 'unknown'},
                {'device_id': 'switch.y', 'timestamp': t + timedelta(seconds=10),
                 'state': 'on', 'area_id': 'unknown'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        # unknown areas should be skipped
        assert all(p['area_id'] != 'unknown' for p in patterns)


class TestTimePeriods:
    """Tests for time period classification."""

    def test_morning_period(self):
        """Test morning period detection."""
        ts = pd.Timestamp("2026-03-06 08:30:00")
        result = RoomBasedPatternDetector._get_time_period(ts)
        assert result == 'morning'

    def test_evening_period(self):
        """Test evening period detection."""
        ts = pd.Timestamp("2026-03-06 20:00:00")
        result = RoomBasedPatternDetector._get_time_period(ts)
        assert result == 'evening'

    def test_afternoon_period(self):
        """Test afternoon period detection."""
        ts = pd.Timestamp("2026-03-06 14:00:00")
        result = RoomBasedPatternDetector._get_time_period(ts)
        assert result == 'afternoon'

    def test_night_period(self):
        """Test night period detection."""
        ts = pd.Timestamp("2026-03-06 03:00:00")
        result = RoomBasedPatternDetector._get_time_period(ts)
        assert result == 'night'

    def test_late_night_period(self):
        """Test late night period detection."""
        ts = pd.Timestamp("2026-03-06 23:00:00")
        result = RoomBasedPatternDetector._get_time_period(ts)
        assert result == 'late_night'


class TestSystemNoiseFiltering:
    """Tests for system noise filtering."""

    @pytest.fixture
    def detector(self):
        return RoomBasedPatternDetector(filter_system_noise=True)

    def test_filters_system_entities(self, detector):
        """Test that system entities are filtered."""
        assert detector._is_actionable_entity("light.bedroom") is True
        assert detector._is_actionable_entity("sensor.home_assistant_uptime") is False
        assert detector._is_actionable_entity("update.core") is False
        assert detector._is_actionable_entity("camera.front_door") is False

    def test_filters_tracker_entities(self, detector):
        """Test that tracker entities are filtered."""
        assert detector._is_actionable_entity("sensor.nfl_team_tracker") is False
        assert detector._is_actionable_entity("sensor.nhl_scores") is False

    def test_filters_excluded_patterns(self, detector):
        """Test that excluded patterns are filtered."""
        assert detector._is_actionable_entity("sensor.cpu_temp") is False
        assert detector._is_actionable_entity("sensor.zigbee_linkquality") is False

    def test_empty_entity(self, detector):
        """Test empty entity returns False."""
        assert detector._is_actionable_entity("") is False
        assert detector._is_actionable_entity(None) is False

    def test_noise_filtering_in_detection(self):
        """Test that noise filtering works during detection."""
        detector = RoomBasedPatternDetector(
            min_occurrences=2,
            min_confidence=0.3,
            min_devices=2,
            filter_system_noise=True,
        )

        base_time = datetime(2026, 3, 6, 20, 0, 0)
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                # System noise - should be filtered
                {'device_id': 'sensor.home_assistant_cpu', 'timestamp': t,
                 'state': '45', 'area_id': 'server'},
                {'device_id': 'update.core', 'timestamp': t + timedelta(seconds=10),
                 'state': 'on', 'area_id': 'server'},
                # Real devices - should be kept
                {'device_id': 'light.kitchen_light', 'timestamp': t,
                 'state': 'on', 'area_id': 'kitchen'},
                {'device_id': 'switch.kitchen_fan', 'timestamp': t + timedelta(seconds=20),
                 'state': 'on', 'area_id': 'kitchen'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)
        # Should only find kitchen pattern, not server
        areas = {p['area_id'] for p in patterns}
        assert 'server' not in areas


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    def test_high_occurrence_high_confidence(self):
        """Test that many occurrences with consistent timing gives high confidence."""
        detector = RoomBasedPatternDetector()
        confidence = detector._calculate_confidence(
            occurrences=10, std_hour=0.3, n_devices=3
        )
        assert confidence > 0.8

    def test_low_occurrence_lower_confidence(self):
        """Test that few occurrences gives lower confidence."""
        detector = RoomBasedPatternDetector()
        confidence = detector._calculate_confidence(
            occurrences=2, std_hour=0.3, n_devices=2
        )
        assert confidence < 0.7

    def test_high_variance_lowers_confidence(self):
        """Test that high timing variance lowers confidence."""
        detector = RoomBasedPatternDetector()
        low_var = detector._calculate_confidence(
            occurrences=5, std_hour=0.3, n_devices=2
        )
        high_var = detector._calculate_confidence(
            occurrences=5, std_hour=5.0, n_devices=2
        )
        assert low_var > high_var

    def test_more_devices_slight_bonus(self):
        """Test that more devices gives a slight confidence bonus."""
        detector = RoomBasedPatternDetector()
        two_devices = detector._calculate_confidence(
            occurrences=5, std_hour=1.0, n_devices=2
        )
        four_devices = detector._calculate_confidence(
            occurrences=5, std_hour=1.0, n_devices=4
        )
        assert four_devices >= two_devices

    def test_confidence_bounds(self):
        """Test confidence stays within 0-1 bounds."""
        detector = RoomBasedPatternDetector()
        # Edge cases
        assert 0.0 <= detector._calculate_confidence(0, 100.0, 1) <= 1.0
        assert 0.0 <= detector._calculate_confidence(100, 0.0, 10) <= 1.0


class TestAutomationSuggestion:
    """Tests for automation suggestion generation."""

    @pytest.fixture
    def detector(self):
        return RoomBasedPatternDetector()

    def test_basic_suggestion(self, detector):
        """Test basic automation suggestion from room pattern."""
        pattern = {
            'pattern_type': 'room_based',
            'area_id': 'living_room',
            'device_group': [
                'binary_sensor.living_room_motion',
                'light.living_room_lamp',
                'media_player.living_room_tv',
            ],
            'period': 'evening',
            'occurrences': 5,
            'confidence': 0.85,
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion['automation_type'] == 'room_routine'
        assert suggestion['confidence'] == 0.85
        assert suggestion['area_id'] == 'living_room'
        assert 'trigger' in suggestion
        assert suggestion['trigger']['entity_id'] == 'binary_sensor.living_room_motion'

    def test_wrong_pattern_type(self, detector):
        """Test that wrong pattern type returns empty."""
        pattern = {'pattern_type': 'sequence', 'device_group': ['a', 'b']}
        result = detector.suggest_automation(pattern)
        assert result == {}

    def test_too_few_devices(self, detector):
        """Test that single device returns empty."""
        pattern = {
            'pattern_type': 'room_based',
            'device_group': ['light.bedroom'],
        }
        result = detector.suggest_automation(pattern)
        assert result == {}

    def test_suggestion_metadata(self, detector):
        """Test suggestion includes proper metadata."""
        pattern = {
            'pattern_type': 'room_based',
            'area_id': 'kitchen',
            'device_group': ['switch.kitchen_fan', 'light.kitchen_light'],
            'period': 'evening',
            'occurrences': 7,
            'confidence': 0.9,
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion['metadata']['source'] == 'room_based_pattern'
        assert suggestion['metadata']['area_id'] == 'kitchen'
        assert suggestion['metadata']['period'] == 'evening'


class TestPatternSummary:
    """Tests for pattern summary generation."""

    def test_empty_summary(self):
        """Test summary with no patterns."""
        detector = RoomBasedPatternDetector()
        summary = detector.get_pattern_summary([])
        assert summary['total_patterns'] == 0
        assert summary['unique_rooms'] == 0

    def test_summary_with_patterns(self):
        """Test summary with multiple patterns."""
        detector = RoomBasedPatternDetector()
        patterns = [
            {
                'area_id': 'living_room',
                'device_group': ['light.a', 'switch.b'],
                'period': 'evening',
                'confidence': 0.85,
            },
            {
                'area_id': 'bedroom',
                'device_group': ['light.c', 'fan.d', 'cover.e'],
                'period': 'morning',
                'confidence': 0.75,
            },
        ]

        summary = detector.get_pattern_summary(patterns)
        assert summary['total_patterns'] == 2
        assert summary['unique_rooms'] == 2
        assert summary['avg_confidence'] == pytest.approx(0.8, abs=0.01)
        assert summary['avg_devices_per_pattern'] == pytest.approx(2.5, abs=0.01)
        assert 'evening' in summary['periods']
        assert 'morning' in summary['periods']


class TestCombinations:
    """Tests for the combinations utility."""

    def test_combinations_size_2(self):
        """Test generating combinations of size 2."""
        result = RoomBasedPatternDetector._combinations(['a', 'b', 'c'], 2)
        assert set(result) == {('a', 'b'), ('a', 'c'), ('b', 'c')}

    def test_combinations_size_0(self):
        """Test empty combinations."""
        result = RoomBasedPatternDetector._combinations(['a', 'b'], 0)
        assert result == [()]

    def test_combinations_size_exceeds(self):
        """Test when size exceeds items."""
        result = RoomBasedPatternDetector._combinations(['a'], 3)
        assert result == []

    def test_combinations_full_size(self):
        """Test combinations of full size."""
        result = RoomBasedPatternDetector._combinations(['a', 'b'], 2)
        assert result == [('a', 'b')]


class TestEnsureAreaId:
    """Tests for area_id column handling."""

    @pytest.fixture
    def detector(self):
        return RoomBasedPatternDetector(filter_system_noise=False)

    def test_with_area_id_column(self, detector):
        """Test events with area_id column are preserved."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom_lamp', 'switch.bedroom_fan'],
            'timestamp': pd.to_datetime(['2026-03-06 20:00', '2026-03-06 20:01']),
            'area_id': ['bedroom', 'bedroom'],
        })

        result = detector._ensure_area_id(events)
        assert list(result['area_id']) == ['bedroom', 'bedroom']

    def test_without_area_id_column(self, detector):
        """Test area_id is parsed from entity_id when column missing."""
        events = pd.DataFrame({
            'device_id': ['light.kitchen_lamp', 'switch.kitchen_fan'],
            'timestamp': pd.to_datetime(['2026-03-06 20:00', '2026-03-06 20:01']),
        })

        result = detector._ensure_area_id(events)
        assert 'area_id' in result.columns
        assert list(result['area_id']) == ['kitchen', 'kitchen']

    def test_partial_area_id(self, detector):
        """Test mix of present and missing area_ids."""
        events = pd.DataFrame({
            'device_id': ['light.bedroom_lamp', 'switch.kitchen_fan'],
            'timestamp': pd.to_datetime(['2026-03-06 20:00', '2026-03-06 20:01']),
            'area_id': ['bedroom', None],
        })

        result = detector._ensure_area_id(events)
        assert result.iloc[0]['area_id'] == 'bedroom'
        assert result.iloc[1]['area_id'] == 'kitchen'


class TestDailyAggregates:
    """Tests for daily aggregate storage."""

    def test_store_aggregates_called(self):
        """Test that aggregate client is called when provided."""

        class MockAggregateClient:
            def __init__(self):
                self.calls = []

            def write_room_daily(self, **kwargs):
                self.calls.append(kwargs)

        mock_client = MockAggregateClient()
        detector = RoomBasedPatternDetector(
            min_occurrences=2,
            min_confidence=0.3,
            min_devices=2,
            filter_system_noise=False,
            aggregate_client=mock_client,
        )

        base_time = datetime(2026, 3, 6, 20, 0, 0)
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.bedroom_light', 'timestamp': t,
                 'state': 'on', 'area_id': 'bedroom'},
                {'device_id': 'fan.bedroom_fan', 'timestamp': t + timedelta(seconds=30),
                 'state': 'on', 'area_id': 'bedroom'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        patterns = detector.detect_patterns(events)

        if patterns:
            assert len(mock_client.calls) > 0

    def test_store_aggregates_handles_error(self):
        """Test that aggregate storage errors don't crash detection."""

        class FailingClient:
            def write_room_daily(self, **kwargs):
                raise RuntimeError("Storage failed")

        detector = RoomBasedPatternDetector(
            min_occurrences=2,
            min_confidence=0.3,
            min_devices=2,
            filter_system_noise=False,
            aggregate_client=FailingClient(),
        )

        base_time = datetime(2026, 3, 6, 20, 0, 0)
        events_data = []
        for day in range(3):
            t = base_time + timedelta(days=day)
            events_data.extend([
                {'device_id': 'light.bedroom_light', 'timestamp': t,
                 'state': 'on', 'area_id': 'bedroom'},
                {'device_id': 'fan.bedroom_fan', 'timestamp': t + timedelta(seconds=30),
                 'state': 'on', 'area_id': 'bedroom'},
            ])

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        # Should not raise
        patterns = detector.detect_patterns(events)
        assert isinstance(patterns, list)


class TestGetDomain:
    """Tests for domain extraction."""

    def test_light_domain(self):
        assert RoomBasedPatternDetector._get_domain("light.bedroom") == "light"

    def test_binary_sensor_domain(self):
        assert RoomBasedPatternDetector._get_domain("binary_sensor.motion") == "binary_sensor"

    def test_empty_string(self):
        assert RoomBasedPatternDetector._get_domain("") == "default"

    def test_no_dot(self):
        assert RoomBasedPatternDetector._get_domain("nodot") == "default"
