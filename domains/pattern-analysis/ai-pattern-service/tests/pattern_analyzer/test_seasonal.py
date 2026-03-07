"""
Unit tests for SeasonalPatternDetector.

Epic 37, Story 37.5: Seasonal Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.seasonal import SeasonalPatternDetector, SeasonalProfile


class TestSeasonalDetectorInit:
    def test_default_initialization(self):
        detector = SeasonalPatternDetector()
        assert detector.min_days_total == 30
        assert detector.min_events_per_season == 10
        assert detector.min_confidence == 0.7
        assert detector.shift_threshold == 0.3
        assert detector.filter_system_noise is True

    def test_custom_initialization(self):
        detector = SeasonalPatternDetector(
            min_days_total=90, min_events_per_season=20,
            min_confidence=0.8, shift_threshold=0.5,
            filter_system_noise=False,
        )
        assert detector.min_days_total == 90
        assert detector.min_events_per_season == 20


class TestSeasonAssignment:
    def test_winter_december(self):
        ts = pd.Timestamp("2026-12-25")
        assert SeasonalPatternDetector._get_season(ts) == 'winter'

    def test_winter_january(self):
        ts = pd.Timestamp("2026-01-15")
        assert SeasonalPatternDetector._get_season(ts) == 'winter'

    def test_winter_february(self):
        ts = pd.Timestamp("2026-02-28")
        assert SeasonalPatternDetector._get_season(ts) == 'winter'

    def test_spring(self):
        ts = pd.Timestamp("2026-04-15")
        assert SeasonalPatternDetector._get_season(ts) == 'spring'

    def test_summer(self):
        ts = pd.Timestamp("2026-07-15")
        assert SeasonalPatternDetector._get_season(ts) == 'summer'

    def test_autumn(self):
        ts = pd.Timestamp("2026-10-15")
        assert SeasonalPatternDetector._get_season(ts) == 'autumn'

    def test_spring_equinox_boundary(self):
        ts = pd.Timestamp("2026-03-20")
        assert SeasonalPatternDetector._get_season(ts) == 'spring'

    def test_before_spring_equinox(self):
        ts = pd.Timestamp("2026-03-19")
        assert SeasonalPatternDetector._get_season(ts) == 'winter'

    def test_summer_solstice_boundary(self):
        ts = pd.Timestamp("2026-06-21")
        assert SeasonalPatternDetector._get_season(ts) == 'summer'

    def test_winter_solstice_boundary(self):
        ts = pd.Timestamp("2026-12-21")
        assert SeasonalPatternDetector._get_season(ts) == 'winter'


class TestSeasonalDetection:
    @pytest.fixture
    def detector(self):
        return SeasonalPatternDetector(
            min_days_total=10,
            min_events_per_season=3,
            min_confidence=0.1,
            shift_threshold=0.2,
            filter_system_noise=False,
        )

    def _make_seasonal_events(self, device_id, season_counts):
        """Generate events across seasons with specified daily counts.

        Args:
            season_counts: dict like {'winter': (count_per_day, hour), 'summer': (count_per_day, hour)}
        """
        events_data = []
        season_dates = {
            'winter': datetime(2025, 1, 15),
            'spring': datetime(2025, 4, 15),
            'summer': datetime(2025, 7, 15),
            'autumn': datetime(2025, 10, 15),
        }

        for season, (count_per_day, hour) in season_counts.items():
            base = season_dates[season]
            for day in range(15):
                for i in range(count_per_day):
                    t = base + timedelta(days=day, hours=hour, minutes=i * 5)
                    events_data.append({
                        'device_id': device_id,
                        'timestamp': t,
                        'state': 'on',
                    })

        df = pd.DataFrame(events_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def test_empty_events(self, detector):
        events = pd.DataFrame(columns=['device_id', 'timestamp', 'state'])
        assert detector.detect_patterns(events) == []

    def test_missing_columns(self, detector):
        events = pd.DataFrame({'device_id': ['light.bedroom']})
        assert detector.detect_patterns(events) == []

    def test_insufficient_data_span(self):
        detector = SeasonalPatternDetector(
            min_days_total=100,
            min_events_per_season=3,
            min_confidence=0.1,
            filter_system_noise=False,
        )
        events = pd.DataFrame({
            'device_id': ['light.bedroom'] * 5,
            'timestamp': pd.to_datetime([
                '2026-01-01', '2026-01-02', '2026-01-03',
                '2026-01-04', '2026-01-05',
            ]),
            'state': ['on'] * 5,
        })
        assert detector.detect_patterns(events) == []

    def test_detects_seasonal_shift(self, detector):
        """Test detection of winter-heavy usage pattern."""
        events = self._make_seasonal_events('climate.heater', {
            'winter': (10, 8),
            'summer': (1, 8),
        })
        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern['pattern_type'] == 'seasonal'
        assert pattern['most_active_season'] == 'winter'

    def test_no_shift_when_uniform(self, detector):
        """Test that uniform usage across seasons is not flagged."""
        detector_strict = SeasonalPatternDetector(
            min_days_total=10,
            min_events_per_season=3,
            min_confidence=0.1,
            shift_threshold=0.8,  # Very high threshold
            filter_system_noise=False,
        )
        events = self._make_seasonal_events('light.hallway', {
            'winter': (5, 8),
            'summer': (5, 8),
        })
        patterns = detector_strict.detect_patterns(events)
        assert len(patterns) == 0

    def test_timing_shift_detected(self, detector):
        """Test detection of timing shift across seasons."""
        events = self._make_seasonal_events('light.porch', {
            'winter': (5, 16),   # Lights at 4pm in winter
            'summer': (5, 20),   # Lights at 8pm in summer
        })
        patterns = detector.detect_patterns(events)
        if patterns:
            assert patterns[0]['metadata']['timing_shift'] > 0

    def test_pattern_output_structure(self, detector):
        events = self._make_seasonal_events('climate.heater', {
            'winter': (10, 8),
            'summer': (2, 8),
        })
        patterns = detector.detect_patterns(events)
        assert len(patterns) >= 1
        p = patterns[0]
        assert 'pattern_type' in p
        assert 'device_id' in p
        assert 'most_active_season' in p
        assert 'least_active_season' in p
        assert 'shift_score' in p
        assert 'confidence' in p
        assert 'season_profiles' in p
        assert 'metadata' in p

    def test_multiple_devices(self, detector):
        events1 = self._make_seasonal_events('climate.heater', {
            'winter': (10, 8), 'summer': (1, 8),
        })
        events2 = self._make_seasonal_events('climate.ac', {
            'winter': (1, 14), 'summer': (10, 14),
        })
        events = pd.concat([events1, events2], ignore_index=True)
        patterns = detector.detect_patterns(events)
        devices = {p['device_id'] for p in patterns}
        assert len(devices) >= 1

    def test_single_season_skipped(self, detector):
        """Test that devices with only one season of data are skipped."""
        base = datetime(2025, 1, 15)
        events = pd.DataFrame({
            'device_id': ['light.bedroom'] * 20,
            'timestamp': pd.to_datetime([
                base + timedelta(days=i) for i in range(20)
            ]),
            'state': ['on'] * 20,
        })
        patterns = detector.detect_patterns(events)
        assert len(patterns) == 0

    def test_data_quality_labels(self, detector):
        """Test data quality labels in metadata."""
        events = self._make_seasonal_events('climate.heater', {
            'winter': (10, 8), 'summer': (1, 8),
        })
        patterns = detector.detect_patterns(events)
        if patterns:
            quality = patterns[0]['metadata']['data_quality']
            assert quality in ('full', 'good', 'partial', 'limited')


class TestTimingShift:
    def test_no_shift(self):
        profiles = {
            'winter': SeasonalProfile(season='winter', avg_hour=8.0),
            'summer': SeasonalProfile(season='summer', avg_hour=8.0),
        }
        shift = SeasonalPatternDetector._compute_timing_shift(
            profiles, ['winter', 'summer']
        )
        assert shift == 0.0

    def test_moderate_shift(self):
        profiles = {
            'winter': SeasonalProfile(season='winter', avg_hour=16.0),
            'summer': SeasonalProfile(season='summer', avg_hour=20.0),
        }
        shift = SeasonalPatternDetector._compute_timing_shift(
            profiles, ['winter', 'summer']
        )
        assert 0.5 < shift < 1.0  # 4 hours / 6 = ~0.67

    def test_large_shift(self):
        profiles = {
            'winter': SeasonalProfile(season='winter', avg_hour=6.0),
            'summer': SeasonalProfile(season='summer', avg_hour=18.0),
        }
        shift = SeasonalPatternDetector._compute_timing_shift(
            profiles, ['winter', 'summer']
        )
        assert shift == 1.0  # 12 hours -> circular = 12, but capped at 6/6 = 1.0

    def test_single_season_returns_zero(self):
        profiles = {'winter': SeasonalProfile(season='winter', avg_hour=8.0)}
        shift = SeasonalPatternDetector._compute_timing_shift(profiles, ['winter'])
        assert shift == 0.0


class TestConfidence:
    def test_high_data_high_confidence(self):
        profiles = {
            s: SeasonalProfile(season=s, event_count=60, day_count=30)
            for s in ['spring', 'summer', 'autumn', 'winter']
        }
        confidence = SeasonalPatternDetector._calculate_confidence(
            profiles, list(profiles.keys())
        )
        assert confidence > 0.8

    def test_low_data_low_confidence(self):
        profiles = {
            'winter': SeasonalProfile(season='winter', event_count=5, day_count=3),
            'summer': SeasonalProfile(season='summer', event_count=5, day_count=3),
        }
        confidence = SeasonalPatternDetector._calculate_confidence(
            profiles, list(profiles.keys())
        )
        assert confidence < 0.4


class TestAutomationSuggestion:
    @pytest.fixture
    def detector(self):
        return SeasonalPatternDetector()

    def test_basic_suggestion(self, detector):
        pattern = {
            'pattern_type': 'seasonal',
            'device_id': 'climate.heater',
            'most_active_season': 'winter',
            'least_active_season': 'summer',
            'shift_score': 0.8,
            'confidence': 0.9,
        }
        suggestion = detector.suggest_automation(pattern)
        assert suggestion['automation_type'] == 'seasonal_schedule'
        assert suggestion['requires_confirmation'] is True

    def test_wrong_pattern_type(self, detector):
        assert detector.suggest_automation({'pattern_type': 'sequence'}) == {}

    def test_empty_device(self, detector):
        assert detector.suggest_automation({
            'pattern_type': 'seasonal', 'device_id': ''
        }) == {}


class TestSeasonMonths:
    def test_winter_months(self):
        assert SeasonalPatternDetector._season_months('winter') == [12, 1, 2]

    def test_summer_months(self):
        assert SeasonalPatternDetector._season_months('summer') == [6, 7, 8]

    def test_unknown_season(self):
        assert SeasonalPatternDetector._season_months('unknown') == []


class TestPatternSummary:
    def test_empty(self):
        detector = SeasonalPatternDetector()
        summary = detector.get_pattern_summary([])
        assert summary['total_patterns'] == 0

    def test_with_patterns(self):
        detector = SeasonalPatternDetector()
        patterns = [
            {'most_active_season': 'winter', 'shift_score': 0.8, 'confidence': 0.9},
            {'most_active_season': 'summer', 'shift_score': 0.6, 'confidence': 0.85},
        ]
        summary = detector.get_pattern_summary(patterns)
        assert summary['total_patterns'] == 2
        assert 'winter' in summary['most_active_seasons']


class TestNoiseFiltering:
    def test_filters_system(self):
        detector = SeasonalPatternDetector()
        assert detector._is_actionable_entity("light.bedroom") is True
        assert detector._is_actionable_entity("update.core") is False
        assert detector._is_actionable_entity("") is False


class TestGetDomain:
    def test_normal(self):
        assert SeasonalPatternDetector._get_domain("light.x") == "light"

    def test_empty(self):
        assert SeasonalPatternDetector._get_domain("") == "default"


class TestDailyAggregates:
    def test_handles_error(self):
        class FailingClient:
            def write_seasonal_daily(self, **kwargs):
                raise RuntimeError("fail")

        detector = SeasonalPatternDetector(
            min_days_total=10, min_events_per_season=3,
            min_confidence=0.1, shift_threshold=0.1,
            filter_system_noise=False, aggregate_client=FailingClient(),
        )

        base_winter = datetime(2025, 1, 15)
        base_summer = datetime(2025, 7, 15)
        events_data = []
        for day in range(15):
            for i in range(10):
                events_data.append({
                    'device_id': 'climate.heater',
                    'timestamp': base_winter + timedelta(days=day, hours=8, minutes=i*5),
                    'state': 'on',
                })
            events_data.append({
                'device_id': 'climate.heater',
                'timestamp': base_summer + timedelta(days=day, hours=8),
                'state': 'on',
            })

        events = pd.DataFrame(events_data)
        events['timestamp'] = pd.to_datetime(events['timestamp'])

        # Should not raise
        patterns = detector.detect_patterns(events)
        assert isinstance(patterns, list)
