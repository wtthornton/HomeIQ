"""
Unit tests for ContextualPatternDetector.

Epic 37, Story 37.8: Contextual Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.contextual import (
    ContextualPatternDetector,
    ContextCorrelation,
    CONTEXT_SUNRISE,
    CONTEXT_SUNSET,
    CONTEXT_TEMPERATURE,
)


class TestContextualDetectorInit:
    def test_default_initialization(self):
        detector = ContextualPatternDetector()
        assert detector.sun_window_minutes == 60
        assert detector.min_events == 10
        assert detector.min_confidence == 0.7
        assert detector.correlation_threshold == 0.5
        assert detector.latitude == 51.5
        assert detector.filter_system_noise is True

    def test_custom_initialization(self):
        detector = ContextualPatternDetector(
            sun_window_minutes=30, min_events=5,
            min_confidence=0.5, correlation_threshold=0.3,
            latitude=40.7, longitude=-74.0,
            filter_system_noise=False,
        )
        assert detector.sun_window_minutes == 30
        assert detector.min_events == 5
        assert detector.latitude == 40.7
        assert detector.longitude == -74.0


class TestSunApproximation:
    def test_summer_solstice_long_day(self):
        detector = ContextualPatternDetector(latitude=51.5)
        sunrise = detector._approx_sunrise(172)  # ~June 21
        sunset = detector._approx_sunset(172)
        assert sunrise < 5.0  # Before 5am
        assert sunset > 20.0  # After 8pm
        assert sunset - sunrise > 15  # Long day

    def test_winter_solstice_short_day(self):
        detector = ContextualPatternDetector(latitude=51.5)
        sunrise = detector._approx_sunrise(355)  # ~Dec 21
        sunset = detector._approx_sunset(355)
        assert sunrise > 7.0  # After 7am
        assert sunset < 17.0  # Before 5pm
        assert sunset - sunrise < 10  # Short day

    def test_equinox_balanced(self):
        detector = ContextualPatternDetector(latitude=51.5)
        sunrise = detector._approx_sunrise(80)  # ~March 21
        sunset = detector._approx_sunset(80)
        day_length = sunset - sunrise
        assert 11.0 < day_length < 13.0  # ~12 hours

    def test_equator_consistent(self):
        detector = ContextualPatternDetector(latitude=0.0, longitude=0.0)
        summer = detector._approx_sunset(172) - detector._approx_sunrise(172)
        winter = detector._approx_sunset(355) - detector._approx_sunrise(355)
        assert abs(summer - winter) < 1.0  # Nearly equal year-round

    def test_sunrise_before_sunset(self):
        detector = ContextualPatternDetector(latitude=45.0)
        for doy in [1, 80, 172, 266, 355]:
            assert detector._approx_sunrise(doy) < detector._approx_sunset(doy)


class TestContextualDetection:
    @pytest.fixture
    def detector(self):
        return ContextualPatternDetector(
            sun_window_minutes=60,
            min_events=5,
            min_confidence=0.1,
            correlation_threshold=0.3,
            latitude=51.5,
            filter_system_noise=False,
        )

    def _make_sunset_events(self, device_id, num_days=30, offset_minutes=10):
        """Generate events that occur near sunset each day."""
        detector = ContextualPatternDetector(latitude=51.5)
        events_data = []
        base = datetime(2025, 6, 1)

        for day in range(num_days):
            dt = base + timedelta(days=day)
            doy = dt.timetuple().tm_yday
            sunset_hour = detector._approx_sunset(doy)
            event_hour = sunset_hour + offset_minutes / 60.0
            hour_int = int(event_hour)
            minute_int = int((event_hour - hour_int) * 60)
            event_time = dt.replace(hour=hour_int, minute=minute_int)
            events_data.append({
                'device_id': device_id,
                'timestamp': event_time,
                'state': 'on',
            })

        df = pd.DataFrame(events_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def _make_random_events(self, device_id, num_events=50):
        """Generate events at random hours throughout the day."""
        rng = np.random.default_rng(42)
        base = datetime(2025, 6, 1)
        events_data = []

        for i in range(num_events):
            day = rng.integers(0, 60)
            hour = rng.integers(0, 24)
            minute = rng.integers(0, 60)
            dt = base + timedelta(days=int(day), hours=int(hour), minutes=int(minute))
            events_data.append({
                'device_id': device_id,
                'timestamp': dt,
                'state': 'on',
            })

        df = pd.DataFrame(events_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def test_empty_events(self, detector):
        events = pd.DataFrame(columns=['device_id', 'timestamp', 'state'])
        assert detector.detect_patterns(events) == []

    def test_missing_columns(self, detector):
        events = pd.DataFrame({'device_id': ['light.porch']})
        assert detector.detect_patterns(events) == []

    def test_detects_sunset_correlation(self, detector):
        events = self._make_sunset_events('light.porch', num_days=30)
        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1
        sunset_patterns = [
            p for p in patterns if p['context_type'] == 'sunset'
        ]
        assert len(sunset_patterns) >= 1
        p = sunset_patterns[0]
        assert p['pattern_type'] == 'contextual'
        assert p['device_id'] == 'light.porch'

    def test_no_correlation_for_random(self, detector):
        """Random events should not show strong sun correlation."""
        detector_strict = ContextualPatternDetector(
            sun_window_minutes=30,
            min_events=5,
            min_confidence=0.6,
            correlation_threshold=0.7,
            filter_system_noise=False,
        )
        events = self._make_random_events('light.hallway', num_events=100)
        patterns = detector_strict.detect_patterns(events)
        # With strict thresholds, random events should not correlate
        assert len(patterns) == 0

    def test_sunrise_correlation(self, detector):
        """Events near sunrise should be detected."""
        det = ContextualPatternDetector(latitude=51.5)
        events_data = []
        base = datetime(2025, 6, 1)

        for day in range(30):
            dt = base + timedelta(days=day)
            doy = dt.timetuple().tm_yday
            sunrise_hour = det._approx_sunrise(doy)
            hour_int = int(sunrise_hour)
            minute_int = int((sunrise_hour - hour_int) * 60) + 5
            if minute_int >= 60:
                hour_int += 1
                minute_int -= 60
            event_time = dt.replace(hour=hour_int, minute=minute_int)
            events_data.append({
                'device_id': 'cover.blinds',
                'timestamp': event_time,
                'state': 'open',
            })

        df = pd.DataFrame(events_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        detector_lenient = ContextualPatternDetector(
            min_events=5, min_confidence=0.1,
            correlation_threshold=0.3, filter_system_noise=False,
        )
        patterns = detector_lenient.detect_patterns(df)
        sunrise_patterns = [
            p for p in patterns if p['context_type'] == 'sunrise'
        ]
        assert len(sunrise_patterns) >= 1

    def test_pattern_output_structure(self, detector):
        events = self._make_sunset_events('light.porch', num_days=30)
        patterns = detector.detect_patterns(events)
        if patterns:
            p = patterns[0]
            assert 'pattern_type' in p
            assert 'device_id' in p
            assert 'context_type' in p
            assert 'correlation_score' in p
            assert 'confidence' in p
            assert 'metadata' in p
            assert 'avg_offset_minutes' in p['metadata']
            assert 'thresholds' in p['metadata']

    def test_multiple_devices(self, detector):
        events1 = self._make_sunset_events('light.porch', num_days=30)
        events2 = self._make_sunset_events('light.garden', num_days=30)
        events = pd.concat([events1, events2], ignore_index=True)
        patterns = detector.detect_patterns(events)
        devices = {p['device_id'] for p in patterns}
        assert len(devices) >= 1

    def test_insufficient_events(self):
        detector = ContextualPatternDetector(
            min_events=100, filter_system_noise=False,
        )
        events = pd.DataFrame({
            'device_id': ['light.porch'] * 5,
            'timestamp': pd.to_datetime([
                '2025-06-01 21:00', '2025-06-02 21:05',
                '2025-06-03 21:10', '2025-06-04 21:00',
                '2025-06-05 21:05',
            ]),
            'state': ['on'] * 5,
        })
        assert detector.detect_patterns(events) == []


class TestTemperatureCorrelation:
    def test_positive_correlation(self):
        """AC usage increases with temperature."""
        detector = ContextualPatternDetector(
            min_events=5, min_confidence=0.1,
            correlation_threshold=0.3, filter_system_noise=False,
        )
        events_data = []
        base = datetime(2025, 6, 1)

        for day in range(30):
            dt = base + timedelta(days=day)
            temp = 15 + day * 0.5  # Increasing temp
            count = max(1, int(day * 0.5))  # More events on hotter days
            for i in range(count):
                events_data.append({
                    'device_id': 'climate.ac',
                    'timestamp': dt + timedelta(hours=12, minutes=i * 10),
                    'state': 'on',
                    'outdoor_temp': temp,
                })

        df = pd.DataFrame(events_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        patterns = detector.detect_patterns(df)

        temp_patterns = [
            p for p in patterns if p['context_type'] == 'temperature'
        ]
        assert len(temp_patterns) >= 1
        assert temp_patterns[0]['correlation_score'] > 0

    def test_no_temp_column_skipped(self):
        detector = ContextualPatternDetector(
            min_events=5, min_confidence=0.1,
            correlation_threshold=0.3, filter_system_noise=False,
        )
        events = pd.DataFrame({
            'device_id': ['climate.ac'] * 20,
            'timestamp': pd.to_datetime([
                f'2025-06-{d:02d} 12:00' for d in range(1, 21)
            ]),
            'state': ['on'] * 20,
        })
        patterns = detector.detect_patterns(events)
        temp_patterns = [
            p for p in patterns if p['context_type'] == 'temperature'
        ]
        assert len(temp_patterns) == 0


class TestSafeCorrelation:
    def test_normal(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        assert ContextualPatternDetector._safe_correlation(x, y) > 0.99

    def test_no_correlation(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([5.0, 1.0, 4.0, 2.0, 3.0])
        assert abs(ContextualPatternDetector._safe_correlation(x, y)) < 0.5

    def test_too_few_points(self):
        assert ContextualPatternDetector._safe_correlation(
            np.array([1.0, 2.0]), np.array([3.0, 4.0])
        ) == 0.0

    def test_zero_std(self):
        x = np.array([1.0, 1.0, 1.0])
        y = np.array([2.0, 3.0, 4.0])
        assert ContextualPatternDetector._safe_correlation(x, y) == 0.0


class TestConfidence:
    def test_sun_high_confidence(self):
        confidence = ContextualPatternDetector._calculate_sun_confidence(
            near_count=40, total=50, offset_std=5.0
        )
        assert confidence > 0.7

    def test_sun_low_confidence(self):
        confidence = ContextualPatternDetector._calculate_sun_confidence(
            near_count=3, total=100, offset_std=50.0
        )
        assert confidence < 0.3

    def test_temp_high_confidence(self):
        confidence = ContextualPatternDetector._calculate_temp_confidence(
            day_count=30, abs_corr=0.9
        )
        assert confidence > 0.8

    def test_temp_low_confidence(self):
        confidence = ContextualPatternDetector._calculate_temp_confidence(
            day_count=5, abs_corr=0.3
        )
        assert confidence < 0.3


class TestAutomationSuggestion:
    @pytest.fixture
    def detector(self):
        return ContextualPatternDetector()

    def test_sunset_suggestion(self, detector):
        pattern = {
            'pattern_type': 'contextual',
            'device_id': 'light.porch',
            'context_type': 'sunset',
            'correlation_score': 0.8,
            'confidence': 0.9,
            'metadata': {
                'avg_offset_minutes': 15.0,
                'description': 'light.porch activates ~15min after sunset',
            },
        }
        suggestion = detector.suggest_automation(pattern)
        assert suggestion['automation_type'] == 'contextual_trigger'
        assert suggestion['trigger']['platform'] == 'sun'
        assert suggestion['trigger']['event'] == 'sunset'
        assert suggestion['requires_confirmation'] is True

    def test_sunrise_suggestion(self, detector):
        pattern = {
            'pattern_type': 'contextual',
            'device_id': 'cover.blinds',
            'context_type': 'sunrise',
            'correlation_score': 0.7,
            'confidence': 0.85,
            'metadata': {
                'avg_offset_minutes': -10.0,
                'description': 'cover.blinds activates ~10min before sunrise',
            },
        }
        suggestion = detector.suggest_automation(pattern)
        assert suggestion['trigger']['platform'] == 'sun'
        assert suggestion['trigger']['event'] == 'sunrise'

    def test_temperature_suggestion(self, detector):
        pattern = {
            'pattern_type': 'contextual',
            'device_id': 'climate.ac',
            'context_type': 'temperature',
            'correlation_score': 0.85,
            'confidence': 0.8,
            'metadata': {
                'avg_offset_minutes': 0.0,
                'description': 'climate.ac usage increases with temperature',
            },
        }
        suggestion = detector.suggest_automation(pattern)
        assert suggestion['trigger']['platform'] == 'numeric_state'

    def test_wrong_pattern_type(self, detector):
        assert detector.suggest_automation({'pattern_type': 'sequence'}) == {}

    def test_empty_device(self, detector):
        assert detector.suggest_automation({
            'pattern_type': 'contextual', 'device_id': ''
        }) == {}


class TestBuildDescription:
    def test_sunset_after(self):
        corr = ContextCorrelation(
            device_id='light.porch', context_type='sunset',
            correlation_score=0.8, avg_offset_minutes=15.0,
            event_count=30, total_events=40, confidence=0.9,
        )
        desc = ContextualPatternDetector._build_description(corr)
        assert 'after' in desc
        assert 'sunset' in desc
        assert '15min' in desc

    def test_sunrise_before(self):
        corr = ContextCorrelation(
            device_id='cover.blinds', context_type='sunrise',
            correlation_score=0.7, avg_offset_minutes=-10.0,
            event_count=25, total_events=30, confidence=0.85,
        )
        desc = ContextualPatternDetector._build_description(corr)
        assert 'before' in desc
        assert 'sunrise' in desc

    def test_temperature(self):
        corr = ContextCorrelation(
            device_id='climate.ac', context_type='temperature',
            correlation_score=0.85, avg_offset_minutes=0.0,
            event_count=100, total_events=100, confidence=0.8,
        )
        desc = ContextualPatternDetector._build_description(corr)
        assert 'temperature' in desc
        assert 'increases' in desc


class TestPatternSummary:
    def test_empty(self):
        detector = ContextualPatternDetector()
        summary = detector.get_pattern_summary([])
        assert summary['total_patterns'] == 0

    def test_with_patterns(self):
        detector = ContextualPatternDetector()
        patterns = [
            {'context_type': 'sunset', 'confidence': 0.9},
            {'context_type': 'sunrise', 'confidence': 0.8},
            {'context_type': 'sunset', 'confidence': 0.85},
        ]
        summary = detector.get_pattern_summary(patterns)
        assert summary['total_patterns'] == 3
        assert summary['context_types']['sunset'] == 2
        assert summary['context_types']['sunrise'] == 1


class TestNoiseFiltering:
    def test_filters_system(self):
        detector = ContextualPatternDetector()
        assert detector._is_actionable_entity("light.porch") is True
        assert detector._is_actionable_entity("update.core") is False
        assert detector._is_actionable_entity("") is False


class TestGetDomain:
    def test_normal(self):
        assert ContextualPatternDetector._get_domain("light.porch") == "light"

    def test_empty(self):
        assert ContextualPatternDetector._get_domain("") == "default"


class TestDailyAggregates:
    def test_handles_error(self):
        class FailingClient:
            def write_contextual_daily(self, **kwargs):
                raise RuntimeError("fail")

        detector = ContextualPatternDetector(
            min_events=5, min_confidence=0.1,
            correlation_threshold=0.3,
            filter_system_noise=False,
            aggregate_client=FailingClient(),
        )

        det_helper = ContextualPatternDetector(latitude=51.5)
        events_data = []
        base = datetime(2025, 6, 1)
        for day in range(30):
            dt = base + timedelta(days=day)
            doy = dt.timetuple().tm_yday
            sunset_hour = det_helper._approx_sunset(doy)
            hour_int = int(sunset_hour)
            minute_int = int((sunset_hour - hour_int) * 60) + 5
            if minute_int >= 60:
                hour_int += 1
                minute_int -= 60
            event_time = dt.replace(hour=hour_int, minute=minute_int)
            events_data.append({
                'device_id': 'light.porch',
                'timestamp': event_time,
                'state': 'on',
            })

        df = pd.DataFrame(events_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Should not raise
        patterns = detector.detect_patterns(df)
        assert isinstance(patterns, list)


class TestBuildTrigger:
    def test_sunset_positive_offset(self):
        trigger = ContextualPatternDetector._build_trigger(
            'sunset', {'avg_offset_minutes': 15}
        )
        assert trigger['platform'] == 'sun'
        assert trigger['event'] == 'sunset'
        assert '00:15:00' in trigger['offset']

    def test_sunrise_negative_offset(self):
        trigger = ContextualPatternDetector._build_trigger(
            'sunrise', {'avg_offset_minutes': -10}
        )
        assert trigger['platform'] == 'sun'
        assert trigger['event'] == 'sunrise'
        assert '-' in trigger['offset']

    def test_temperature_trigger(self):
        trigger = ContextualPatternDetector._build_trigger(
            'temperature', {}
        )
        assert trigger['platform'] == 'numeric_state'

    def test_unknown_context(self):
        trigger = ContextualPatternDetector._build_trigger('unknown', {})
        assert trigger['platform'] == 'state'
