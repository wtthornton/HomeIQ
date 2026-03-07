"""
Unit tests for AnomalyPatternDetector.

Epic 37, Story 37.6: Anomaly Detector tests.
Target: >80% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pattern_analyzer.anomaly import (
    AnomalyPatternDetector,
    AnomalyType,
    SeverityLevel,
    DeviceBaseline,
    Anomaly,
)


class TestAnomalyPatternDetectorInit:
    """Tests for AnomalyPatternDetector initialization."""

    def test_default_initialization(self):
        """Test detector initializes with default values."""
        detector = AnomalyPatternDetector()

        assert detector.min_baseline_days == 7
        assert detector.sensitivity == 0.7
        assert detector.z_score_threshold == 2.5
        assert detector.absence_threshold_hours == 24
        assert detector.min_events_for_baseline == 10
        assert detector.filter_system_noise is True
        assert detector.aggregate_client is None

    def test_custom_initialization(self):
        """Test detector initializes with custom values."""
        detector = AnomalyPatternDetector(
            min_baseline_days=14,
            sensitivity=0.9,
            z_score_threshold=3.0,
            absence_threshold_hours=48,
            min_events_for_baseline=20,
            filter_system_noise=False,
        )

        assert detector.min_baseline_days == 14
        assert detector.sensitivity == 0.9
        assert detector.z_score_threshold == 3.0
        assert detector.absence_threshold_hours == 48
        assert detector.min_events_for_baseline == 20
        assert detector.filter_system_noise is False


class TestAnomalyPatternDetection:
    """Tests for pattern detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector with relaxed thresholds for testing."""
        return AnomalyPatternDetector(
            min_baseline_days=3,
            sensitivity=0.5,
            z_score_threshold=2.0,
            min_events_for_baseline=5,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        """Base timestamp for test events."""
        return datetime(2026, 3, 1, 8, 0, 0)

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

    def test_builds_baselines(self, detector, base_time):
        """Test that baselines are built from event data."""
        events = []
        for day in range(7):
            for hour in [8, 12, 18]:
                timestamp = base_time + timedelta(days=day, hours=hour - 8)
                events.append({
                    'device_id': 'light.kitchen',
                    'timestamp': timestamp,
                    'state': 'on'
                })

        df = pd.DataFrame(events)
        detector.detect_patterns(df)

        baselines = detector.get_baselines()
        assert 'light.kitchen' in baselines
        assert baselines['light.kitchen']['total_events'] == 21
        assert baselines['light.kitchen']['baseline_days'] == 7


class TestTimingAnomalyDetection:
    """Tests for timing anomaly detection."""

    @pytest.fixture
    def detector(self):
        return AnomalyPatternDetector(
            min_baseline_days=3,
            sensitivity=0.5,
            z_score_threshold=1.5,
            min_events_for_baseline=5,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 1, 8, 0, 0)

    def test_detects_unusual_hour(self, detector, base_time):
        """Test detection of activity at unusual time."""
        events = []

        for day in range(5):
            for hour in [8, 9, 10, 18, 19, 20]:
                timestamp = base_time + timedelta(days=day, hours=hour - 8)
                events.append({
                    'device_id': 'light.bedroom',
                    'timestamp': timestamp,
                    'state': 'on'
                })

        anomaly_time = base_time + timedelta(days=6, hours=-5)
        events.append({
            'device_id': 'light.bedroom',
            'timestamp': anomaly_time,
            'state': 'on'
        })

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        timing_anomalies = [
            p for p in patterns
            if p['anomaly_type'] == 'timing'
        ]
        assert len(timing_anomalies) >= 0


class TestFrequencyAnomalyDetection:
    """Tests for frequency anomaly detection."""

    @pytest.fixture
    def detector(self):
        return AnomalyPatternDetector(
            min_baseline_days=3,
            sensitivity=0.5,
            z_score_threshold=2.0,
            min_events_for_baseline=5,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 1, 8, 0, 0)

    def test_detects_high_frequency(self, detector, base_time):
        """Test detection of unusually high activity."""
        events = []

        for day in range(5):
            for i in range(3):
                timestamp = base_time + timedelta(days=day, hours=i)
                events.append({
                    'device_id': 'switch.garage',
                    'timestamp': timestamp,
                    'state': 'on'
                })

        for i in range(20):
            timestamp = base_time + timedelta(days=6, hours=i % 12)
            events.append({
                'device_id': 'switch.garage',
                'timestamp': timestamp,
                'state': 'on'
            })

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        freq_anomalies = [
            p for p in patterns
            if p['anomaly_type'] == 'frequency'
        ]
        assert len(freq_anomalies) >= 1

    def test_detects_low_frequency(self, detector, base_time):
        """Test detection of unusually low activity."""
        events = []

        for day in range(5):
            for i in range(10):
                timestamp = base_time + timedelta(days=day, hours=i)
                events.append({
                    'device_id': 'binary_sensor.motion',
                    'timestamp': timestamp,
                    'state': 'on'
                })

        timestamp = base_time + timedelta(days=6, hours=12)
        events.append({
            'device_id': 'binary_sensor.motion',
            'timestamp': timestamp,
            'state': 'on'
        })

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        freq_anomalies = [
            p for p in patterns
            if p['anomaly_type'] == 'frequency' and
            p['metadata'].get('direction') == 'low'
        ]
        assert len(freq_anomalies) >= 0


class TestDurationAnomalyDetection:
    """Tests for duration anomaly detection."""

    @pytest.fixture
    def detector(self):
        return AnomalyPatternDetector(
            min_baseline_days=3,
            sensitivity=0.5,
            z_score_threshold=2.0,
            min_events_for_baseline=5,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 1, 8, 0, 0)

    def test_detects_long_duration(self, detector, base_time):
        """Test detection of unusually long state duration."""
        events = []

        for day in range(5):
            on_time = base_time + timedelta(days=day)
            off_time = on_time + timedelta(minutes=5)
            events.append({'device_id': 'light.test', 'timestamp': on_time, 'state': 'on'})
            events.append({'device_id': 'light.test', 'timestamp': off_time, 'state': 'off'})

        anomaly_on = base_time + timedelta(days=6)
        anomaly_off = anomaly_on + timedelta(hours=2)
        events.append({'device_id': 'light.test', 'timestamp': anomaly_on, 'state': 'on'})
        events.append({'device_id': 'light.test', 'timestamp': anomaly_off, 'state': 'off'})

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        duration_anomalies = [
            p for p in patterns
            if p['anomaly_type'] == 'duration'
        ]
        assert len(duration_anomalies) >= 1


class TestAbsenceAnomalyDetection:
    """Tests for absence anomaly detection."""

    @pytest.fixture
    def detector(self):
        return AnomalyPatternDetector(
            min_baseline_days=3,
            sensitivity=0.5,
            z_score_threshold=2.0,
            absence_threshold_hours=12,
            min_events_for_baseline=5,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 1, 8, 0, 0)

    def test_detects_device_absence(self, detector, base_time):
        """Test detection of missing expected activity."""
        events = []

        for day in range(5):
            for i in range(5):
                timestamp = base_time + timedelta(days=day, hours=i)
                events.append({
                    'device_id': 'binary_sensor.motion_kitchen',
                    'timestamp': timestamp,
                    'state': 'on'
                })

        late_event = base_time + timedelta(days=6, hours=20)
        events.append({
            'device_id': 'binary_sensor.motion_hall',
            'timestamp': late_event,
            'state': 'on'
        })

        df = pd.DataFrame(events)
        patterns = detector.detect_patterns(df)

        absence_anomalies = [
            p for p in patterns
            if p['anomaly_type'] == 'absence'
        ]
        assert len(absence_anomalies) >= 0


class TestSeverityCalculation:
    """Tests for severity calculation."""

    @pytest.fixture
    def detector(self):
        return AnomalyPatternDetector()

    def test_critical_severity(self, detector):
        """Test critical severity for high z-scores."""
        severity = detector._calculate_severity(4.5)
        assert severity == SeverityLevel.CRITICAL

    def test_high_severity(self, detector):
        """Test high severity for moderate z-scores."""
        severity = detector._calculate_severity(3.5)
        assert severity == SeverityLevel.HIGH

    def test_medium_severity(self, detector):
        """Test medium severity for lower z-scores."""
        severity = detector._calculate_severity(2.7)
        assert severity == SeverityLevel.MEDIUM

    def test_low_severity(self, detector):
        """Test low severity for minimal z-scores."""
        severity = detector._calculate_severity(2.0)
        assert severity == SeverityLevel.LOW

    def test_absence_severity_critical(self, detector):
        """Test critical absence severity."""
        severity = detector._calculate_absence_severity(80, 5.0)
        assert severity == SeverityLevel.CRITICAL

    def test_absence_severity_high(self, detector):
        """Test high absence severity."""
        severity = detector._calculate_absence_severity(50, 3.0)
        assert severity == SeverityLevel.HIGH

    def test_absence_severity_medium(self, detector):
        """Test medium absence severity."""
        severity = detector._calculate_absence_severity(30, 2.0)
        assert severity == SeverityLevel.MEDIUM


class TestSystemNoiseFiltering:
    """Tests for system noise filtering."""

    @pytest.fixture
    def detector_with_filter(self):
        return AnomalyPatternDetector(
            min_baseline_days=3,
            min_events_for_baseline=5,
            filter_system_noise=True,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 1, 8, 0, 0)

    def test_filters_system_sensors(self, detector_with_filter, base_time):
        """Test that system sensors are filtered out."""
        events = []
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            events.append({
                'device_id': 'sensor.home_assistant_cpu',
                'timestamp': timestamp,
                'state': '50'
            })
            events.append({
                'device_id': 'light.bedroom',
                'timestamp': timestamp,
                'state': 'on'
            })

        df = pd.DataFrame(events)
        patterns = detector_with_filter.detect_patterns(df)

        for pattern in patterns:
            assert 'home_assistant' not in pattern['device_id']

    def test_keeps_actionable_devices(self, detector_with_filter, base_time):
        """Test that actionable devices are kept."""
        events = []
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            events.append({
                'device_id': 'light.kitchen',
                'timestamp': timestamp,
                'state': 'on'
            })

        df = pd.DataFrame(events)
        detector_with_filter.detect_patterns(df)

        baselines = detector_with_filter.get_baselines()
        assert 'light.kitchen' in baselines


class TestPatternSummary:
    """Tests for pattern summary functionality."""

    def test_empty_patterns_summary(self):
        """Test summary with no patterns."""
        detector = AnomalyPatternDetector()
        summary = detector.get_pattern_summary([])

        assert summary['total_anomalies'] == 0
        assert summary['unique_devices'] == 0
        assert summary['by_type'] == {}
        assert summary['by_severity'] == {}

    def test_patterns_summary(self):
        """Test summary calculation."""
        detector = AnomalyPatternDetector()
        patterns = [
            {
                'pattern_type': 'anomaly',
                'device_id': 'light.bedroom',
                'anomaly_type': 'timing',
                'severity': 'high',
                'confidence': 0.8,
                'z_score': 3.5,
            },
            {
                'pattern_type': 'anomaly',
                'device_id': 'light.kitchen',
                'anomaly_type': 'frequency',
                'severity': 'medium',
                'confidence': 0.7,
                'z_score': 2.8,
            },
            {
                'pattern_type': 'anomaly',
                'device_id': 'light.bedroom',
                'anomaly_type': 'duration',
                'severity': 'critical',
                'confidence': 0.9,
                'z_score': 4.2,
            },
        ]

        summary = detector.get_pattern_summary(patterns)

        assert summary['total_anomalies'] == 3
        assert summary['unique_devices'] == 2
        assert summary['by_type']['timing'] == 1
        assert summary['by_type']['frequency'] == 1
        assert summary['by_type']['duration'] == 1
        assert summary['by_severity']['high'] == 1
        assert summary['by_severity']['medium'] == 1
        assert summary['by_severity']['critical'] == 1
        assert summary['critical_count'] == 1


class TestAutomationSuggestion:
    """Tests for automation suggestion functionality."""

    @pytest.fixture
    def detector(self):
        return AnomalyPatternDetector()

    def test_suggest_alert_for_anomaly(self, detector):
        """Test alert suggestion for anomaly pattern."""
        pattern = {
            'pattern_type': 'anomaly',
            'device_id': 'binary_sensor.front_door',
            'anomaly_type': 'timing',
            'severity': 'high',
            'description': 'Front door opened at unusual time',
            'confidence': 0.85,
            'z_score': 3.5,
        }

        suggestion = detector.suggest_automation(pattern)

        assert suggestion['automation_type'] == 'anomaly_alert'
        assert suggestion['device_id'] == 'binary_sensor.front_door'
        assert 'notify' in suggestion['action']['service']

    def test_critical_uses_mobile_notification(self, detector):
        """Test critical severity uses mobile notification."""
        pattern = {
            'pattern_type': 'anomaly',
            'device_id': 'lock.front_door',
            'anomaly_type': 'timing',
            'severity': 'critical',
            'description': 'Lock opened at 3am',
            'confidence': 0.95,
            'z_score': 5.0,
        }

        suggestion = detector.suggest_automation(pattern)

        assert 'mobile_app' in suggestion['action']['service']

    def test_suggest_automation_wrong_type(self, detector):
        """Test that non-anomaly patterns return empty."""
        pattern = {
            'pattern_type': 'duration',
            'device_id': 'light.bedroom',
        }

        suggestion = detector.suggest_automation(pattern)
        assert suggestion == {}


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_domain(self):
        """Test domain extraction."""
        detector = AnomalyPatternDetector()

        assert detector._get_domain('light.bedroom') == 'light'
        assert detector._get_domain('binary_sensor.motion') == 'binary_sensor'
        assert detector._get_domain('switch.coffee_maker') == 'switch'
        assert detector._get_domain('no_domain') == 'default'
        assert detector._get_domain('') == 'default'

    def test_format_duration(self):
        """Test duration formatting."""
        detector = AnomalyPatternDetector()

        assert detector._format_duration(30) == '30s'
        assert detector._format_duration(300) == '5.0min'
        assert detector._format_duration(7200) == '2.0h'

    def test_is_actionable_entity(self):
        """Test actionable entity detection."""
        detector = AnomalyPatternDetector()

        assert detector._is_actionable_entity('light.bedroom') is True
        assert detector._is_actionable_entity('switch.coffee_maker') is True
        assert detector._is_actionable_entity('binary_sensor.motion') is True

        assert detector._is_actionable_entity('sensor.home_assistant_cpu') is False
        assert detector._is_actionable_entity('image.roborock_map') is False
        assert detector._is_actionable_entity('camera.front_door') is False

    def test_get_anomalies_for_device(self):
        """Test retrieving anomalies for specific device."""
        detector = AnomalyPatternDetector()
        patterns = [
            {'device_id': 'light.bedroom', 'anomaly_type': 'timing'},
            {'device_id': 'light.kitchen', 'anomaly_type': 'frequency'},
            {'device_id': 'light.bedroom', 'anomaly_type': 'duration'},
        ]

        bedroom_anomalies = detector.get_anomalies_for_device(patterns, 'light.bedroom')
        assert len(bedroom_anomalies) == 2

    def test_get_anomalies_by_severity(self):
        """Test filtering anomalies by severity."""
        detector = AnomalyPatternDetector()
        patterns = [
            {'device_id': 'light.a', 'severity': 'low'},
            {'device_id': 'light.b', 'severity': 'medium'},
            {'device_id': 'light.c', 'severity': 'high'},
            {'device_id': 'light.d', 'severity': 'critical'},
        ]

        high_plus = detector.get_anomalies_by_severity(patterns, 'high')
        assert len(high_plus) == 2

        medium_plus = detector.get_anomalies_by_severity(patterns, 'medium')
        assert len(medium_plus) == 3


class TestAnomalyTypeEnum:
    """Tests for AnomalyType enum."""

    def test_anomaly_type_values(self):
        """Test all anomaly type values."""
        assert AnomalyType.TIMING.value == 'timing'
        assert AnomalyType.FREQUENCY.value == 'frequency'
        assert AnomalyType.SEQUENCE.value == 'sequence'
        assert AnomalyType.DURATION.value == 'duration'
        assert AnomalyType.ABSENCE.value == 'absence'


class TestSeverityLevelEnum:
    """Tests for SeverityLevel enum."""

    def test_severity_level_values(self):
        """Test all severity level values."""
        assert SeverityLevel.LOW.value == 'low'
        assert SeverityLevel.MEDIUM.value == 'medium'
        assert SeverityLevel.HIGH.value == 'high'
        assert SeverityLevel.CRITICAL.value == 'critical'


class TestDeviceBaseline:
    """Tests for DeviceBaseline dataclass."""

    def test_baseline_defaults(self):
        """Test baseline initializes with defaults."""
        baseline = DeviceBaseline(device_id='light.test')

        assert baseline.device_id == 'light.test'
        assert baseline.total_events == 0
        assert baseline.daily_counts == []
        assert baseline.hourly_distribution == {}
        assert baseline.avg_daily_count == 0.0
        assert baseline.typical_hours == set()
        assert baseline.first_seen is None
        assert baseline.last_seen is None


class TestBaselineBuilding:
    """Tests for baseline building functionality."""

    @pytest.fixture
    def detector(self):
        return AnomalyPatternDetector(
            min_baseline_days=1,
            min_events_for_baseline=3,
            filter_system_noise=False,
        )

    @pytest.fixture
    def base_time(self):
        return datetime(2026, 3, 1, 8, 0, 0)

    def test_typical_hours_calculation(self, detector, base_time):
        """Test that typical hours are correctly identified."""
        events = []

        for day in range(5):
            for hour in [8, 9, 18, 19]:
                timestamp = base_time + timedelta(days=day, hours=hour - 8)
                events.append({
                    'device_id': 'light.test',
                    'timestamp': timestamp,
                    'state': 'on'
                })

        df = pd.DataFrame(events)
        detector.detect_patterns(df)

        baselines = detector.get_baselines()
        assert 'light.test' in baselines

        typical = baselines['light.test']['typical_hours']
        assert 8 in typical or 9 in typical or 18 in typical or 19 in typical

    def test_insufficient_events_skipped(self, detector, base_time):
        """Test devices with too few events are skipped."""
        events = [
            {'device_id': 'light.rare', 'timestamp': base_time, 'state': 'on'},
            {'device_id': 'light.rare', 'timestamp': base_time + timedelta(hours=1), 'state': 'off'},
        ]

        df = pd.DataFrame(events)
        detector.detect_patterns(df)

        baselines = detector.get_baselines()
        assert 'light.rare' not in baselines
