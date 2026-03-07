"""
Anomaly Pattern Detector

Statistical outlier detection on established device behavior patterns.
Identifies unusual deviations for security and diagnostic purposes.

Epic 37, Story 37.6: Anomaly Detector for pattern detection expansion.

Algorithm Overview:
    1. Build behavioral baselines from historical data (7+ days)
    2. Analyze current events against established baselines
    3. Detect anomalies in timing, frequency, and sequences
    4. Calculate severity scores based on deviation magnitude
    5. Return categorized anomalies with context

Anomaly Types:
    - timing: Device activated at unusual time of day
    - frequency: Device activation count deviates from normal
    - sequence: Unexpected device activation pattern
    - duration: State duration significantly different from baseline
    - absence: Expected device activity missing

Example Use Cases:
    - Security: Front door opened at 3am (unusual timing)
    - Diagnostics: Furnace cycling more than usual (frequency anomaly)
    - Behavior change: No morning coffee maker activation (absence)
    - Equipment issue: Garage door open 2 hours (duration anomaly)

Configuration:
    - min_baseline_days: Minimum days of data for baseline (default: 7)
    - sensitivity: Anomaly sensitivity 0.0-1.0 (default: 0.7)
    - z_score_threshold: Standard deviations for anomaly (default: 2.5)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

EXCLUDED_DOMAINS = {
    'image', 'event', 'update', 'camera', 'button',
}

EXCLUDED_ENTITY_PREFIXES = [
    'sensor.home_assistant_',
    'sensor.slzb_',
    'image.',
    'event.',
    'binary_sensor.system_',
    'camera.',
    'button.',
    'update.',
]

EXCLUDED_PATTERNS = [
    '_tracker', 'team_tracker',
    'nfl_', 'nhl_', 'mlb_', 'nba_', 'ncaa_',
    'weather_', 'openweathermap_',
    'carbon_intensity_', 'electricity_pricing_', 'national_grid_',
    'calendar_',
    '_cpu_', '_temp', '_chip_',
    'coordinator_', '_battery', '_memory_',
    '_signal_strength', '_linkquality',
    '_update_', '_uptime', '_last_seen',
]


class AnomalyType(Enum):
    """Types of anomalies that can be detected."""
    TIMING = "timing"
    FREQUENCY = "frequency"
    SEQUENCE = "sequence"
    DURATION = "duration"
    ABSENCE = "absence"


class SeverityLevel(Enum):
    """Severity levels for detected anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DeviceBaseline:
    """Behavioral baseline for a single device."""
    device_id: str
    total_events: int = 0
    daily_counts: list[int] = field(default_factory=list)
    hourly_distribution: dict[int, int] = field(default_factory=dict)
    avg_daily_count: float = 0.0
    std_daily_count: float = 0.0
    typical_hours: set[int] = field(default_factory=set)
    avg_duration_seconds: float = 0.0
    std_duration_seconds: float = 0.0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    baseline_days: int = 0


@dataclass
class Anomaly:
    """Represents a detected anomaly."""
    device_id: str
    anomaly_type: AnomalyType
    severity: SeverityLevel
    timestamp: datetime
    description: str
    context: dict = field(default_factory=dict)
    z_score: float = 0.0
    confidence: float = 0.0


class AnomalyPatternDetector:
    """
    Detects anomalous device behavior patterns.
    Identifies unusual timing, frequency, and sequence deviations.

    Examples:
        - Motion sensor triggered at 3am (unusual timing)
        - Garage door opened 15 times today vs normal 2-3 (frequency)
        - Coffee maker not activated in morning (absence)
        - HVAC running continuously for 8 hours (duration)
    """

    def __init__(
        self,
        min_baseline_days: int = 7,
        sensitivity: float = 0.7,
        z_score_threshold: float = 2.5,
        absence_threshold_hours: int = 24,
        min_events_for_baseline: int = 10,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        """
        Initialize anomaly detector.

        Args:
            min_baseline_days: Minimum days of data for baseline (default: 7)
            sensitivity: Anomaly sensitivity 0.0-1.0, higher = more sensitive (default: 0.7)
            z_score_threshold: Standard deviations to flag anomaly (default: 2.5)
            absence_threshold_hours: Hours without activity to flag absence (default: 24)
            min_events_for_baseline: Minimum events to establish baseline (default: 10)
            filter_system_noise: Filter out system sensors/trackers (default: True)
            aggregate_client: PatternAggregateClient for storing results
        """
        self.min_baseline_days = min_baseline_days
        self.sensitivity = sensitivity
        self.z_score_threshold = z_score_threshold
        self.absence_threshold_hours = absence_threshold_hours
        self.min_events_for_baseline = min_events_for_baseline
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client

        self._baselines: dict[str, DeviceBaseline] = {}

        logger.info(
            "AnomalyPatternDetector initialized: "
            f"min_baseline_days={min_baseline_days}, sensitivity={sensitivity}, "
            f"z_score_threshold={z_score_threshold}, "
            f"absence_threshold={absence_threshold_hours}h"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect anomalous patterns in device behavior.

        Args:
            events: DataFrame with columns [device_id, timestamp, state]
                    device_id: str - Device identifier
                    timestamp: datetime - Event timestamp
                    state: str - Device state

        Returns:
            List of anomaly pattern dictionaries with keys:
                - pattern_type: "anomaly"
                - device_id: Device identifier
                - anomaly_type: Type of anomaly detected
                - severity: Severity level (low/medium/high/critical)
                - timestamp: When the anomaly occurred
                - description: Human-readable description
                - confidence: Confidence score
                - z_score: Statistical deviation score
                - metadata: Additional context
        """
        if events.empty:
            logger.warning("No events provided for anomaly detection")
            return []

        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        logger.info(f"Analyzing {len(events)} events for anomalies")

        if self.filter_system_noise:
            original_count = len(events)
            events = self._filter_system_noise(events)
            if len(events) < original_count:
                logger.info(
                    f"Filtered system noise: {original_count} → {len(events)} events"
                )

        if events.empty:
            logger.warning("No events remaining after filtering")
            return []

        events = events.sort_values('timestamp').copy()
        events = events.reset_index(drop=True)

        self._build_baselines(events)

        anomalies = self._detect_all_anomalies(events)

        patterns = self._build_patterns(anomalies)

        logger.info(f"Detected {len(patterns)} anomaly patterns")

        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _build_baselines(self, events: pd.DataFrame) -> None:
        """
        Build behavioral baselines from historical events.

        Calculates typical timing, frequency, and duration patterns
        for each device based on historical data.

        Args:
            events: Sorted DataFrame with device events.
        """
        if events.empty:
            return

        events['date'] = events['timestamp'].dt.date
        events['hour'] = events['timestamp'].dt.hour

        min_date = events['timestamp'].min().date()
        max_date = events['timestamp'].max().date()
        total_days = (max_date - min_date).days + 1

        for device_id in events['device_id'].unique():
            device_events = events[events['device_id'] == device_id]

            if len(device_events) < self.min_events_for_baseline:
                logger.debug(
                    f"Skipping baseline for {device_id}: "
                    f"only {len(device_events)} events"
                )
                continue

            daily_counts = device_events.groupby('date').size().tolist()

            hourly_dist = device_events['hour'].value_counts().to_dict()

            typical_hours = set()
            if hourly_dist:
                threshold = max(hourly_dist.values()) * 0.3
                typical_hours = {h for h, c in hourly_dist.items() if c >= threshold}

            durations = self._calculate_state_durations(device_events)
            avg_duration = float(np.mean(durations)) if durations else 0.0
            std_duration = float(np.std(durations)) if len(durations) > 1 else 0.0

            baseline = DeviceBaseline(
                device_id=device_id,
                total_events=len(device_events),
                daily_counts=daily_counts,
                hourly_distribution=hourly_dist,
                avg_daily_count=float(np.mean(daily_counts)) if daily_counts else 0.0,
                std_daily_count=float(np.std(daily_counts)) if len(daily_counts) > 1 else 0.0,
                typical_hours=typical_hours,
                avg_duration_seconds=avg_duration,
                std_duration_seconds=std_duration,
                first_seen=device_events['timestamp'].min(),
                last_seen=device_events['timestamp'].max(),
                baseline_days=total_days,
            )

            self._baselines[device_id] = baseline

        logger.info(f"Built baselines for {len(self._baselines)} devices")

    def _calculate_state_durations(self, events: pd.DataFrame) -> list[float]:
        """Calculate state durations from sequential events."""
        durations = []
        prev_time = None
        prev_state = None

        for _, event in events.iterrows():
            curr_time = event['timestamp']
            curr_state = event.get('state', 'unknown')

            if prev_time is not None and prev_state != curr_state:
                duration = (curr_time - prev_time).total_seconds()
                if 1 <= duration <= 86400:
                    durations.append(duration)

            prev_time = curr_time
            prev_state = curr_state

        return durations

    def _detect_all_anomalies(self, events: pd.DataFrame) -> list[Anomaly]:
        """
        Detect all types of anomalies in the event data.

        Args:
            events: Sorted DataFrame with device events.

        Returns:
            List of Anomaly objects.
        """
        anomalies = []

        timing_anomalies = self._detect_timing_anomalies(events)
        anomalies.extend(timing_anomalies)

        frequency_anomalies = self._detect_frequency_anomalies(events)
        anomalies.extend(frequency_anomalies)

        duration_anomalies = self._detect_duration_anomalies(events)
        anomalies.extend(duration_anomalies)

        absence_anomalies = self._detect_absence_anomalies(events)
        anomalies.extend(absence_anomalies)

        return anomalies

    def _detect_timing_anomalies(self, events: pd.DataFrame) -> list[Anomaly]:
        """
        Detect events occurring at unusual times.

        Args:
            events: DataFrame with device events.

        Returns:
            List of timing anomalies.
        """
        anomalies = []

        for _, event in events.iterrows():
            device_id = event['device_id']
            timestamp = event['timestamp']
            hour = timestamp.hour

            baseline = self._baselines.get(device_id)
            if not baseline or baseline.baseline_days < self.min_baseline_days:
                continue

            if not baseline.typical_hours:
                continue

            if hour not in baseline.typical_hours:
                hourly_counts = list(baseline.hourly_distribution.values())
                if not hourly_counts:
                    continue

                expected = np.mean(hourly_counts)
                actual = baseline.hourly_distribution.get(hour, 0)
                std = np.std(hourly_counts) if len(hourly_counts) > 1 else 1.0

                z_score = abs(actual - expected) / std if std > 0 else 0.0

                if z_score >= self.z_score_threshold * self.sensitivity:
                    severity = self._calculate_severity(z_score)
                    confidence = min(z_score / (self.z_score_threshold * 2), 1.0)

                    is_night = 0 <= hour < 6
                    time_desc = "late night" if is_night else f"{hour}:00"

                    anomalies.append(Anomaly(
                        device_id=device_id,
                        anomaly_type=AnomalyType.TIMING,
                        severity=severity,
                        timestamp=timestamp,
                        description=f"{device_id} activated at unusual time ({time_desc})",
                        context={
                            'hour': hour,
                            'typical_hours': list(baseline.typical_hours),
                            'is_night': is_night,
                        },
                        z_score=float(z_score),
                        confidence=float(confidence),
                    ))

        return anomalies

    def _detect_frequency_anomalies(self, events: pd.DataFrame) -> list[Anomaly]:
        """
        Detect unusual activation frequency.

        Args:
            events: DataFrame with device events.

        Returns:
            List of frequency anomalies.
        """
        anomalies = []

        events['date'] = events['timestamp'].dt.date
        daily_counts = events.groupby(['device_id', 'date']).size().reset_index(name='count')

        for _, row in daily_counts.iterrows():
            device_id = row['device_id']
            date = row['date']
            count = row['count']

            baseline = self._baselines.get(device_id)
            if not baseline or baseline.baseline_days < self.min_baseline_days:
                continue

            if baseline.std_daily_count == 0:
                continue

            z_score = abs(count - baseline.avg_daily_count) / baseline.std_daily_count

            if z_score >= self.z_score_threshold * self.sensitivity:
                severity = self._calculate_severity(z_score)
                confidence = min(z_score / (self.z_score_threshold * 2), 1.0)

                direction = "high" if count > baseline.avg_daily_count else "low"
                expected = baseline.avg_daily_count

                anomalies.append(Anomaly(
                    device_id=device_id,
                    anomaly_type=AnomalyType.FREQUENCY,
                    severity=severity,
                    timestamp=datetime.combine(date, datetime.min.time()),
                    description=(
                        f"{device_id} had {direction} activity: "
                        f"{count} events vs typical {expected:.1f}"
                    ),
                    context={
                        'actual_count': int(count),
                        'expected_count': float(expected),
                        'direction': direction,
                        'date': str(date),
                    },
                    z_score=float(z_score),
                    confidence=float(confidence),
                ))

        return anomalies

    def _detect_duration_anomalies(self, events: pd.DataFrame) -> list[Anomaly]:
        """
        Detect unusual state durations.

        Args:
            events: DataFrame with device events.

        Returns:
            List of duration anomalies.
        """
        anomalies = []

        for device_id in events['device_id'].unique():
            baseline = self._baselines.get(device_id)
            if not baseline or baseline.baseline_days < self.min_baseline_days:
                continue

            if baseline.std_duration_seconds == 0:
                continue

            device_events = events[events['device_id'] == device_id].copy()
            device_events = device_events.sort_values('timestamp')

            prev_time = None
            prev_state = None

            for _, event in device_events.iterrows():
                curr_time = event['timestamp']
                curr_state = event.get('state', 'unknown')

                if prev_time is not None and prev_state != curr_state:
                    duration = (curr_time - prev_time).total_seconds()

                    if duration > 0:
                        z_score = abs(duration - baseline.avg_duration_seconds) / baseline.std_duration_seconds

                        if z_score >= self.z_score_threshold * self.sensitivity:
                            severity = self._calculate_severity(z_score)
                            confidence = min(z_score / (self.z_score_threshold * 2), 1.0)

                            direction = "long" if duration > baseline.avg_duration_seconds else "short"
                            duration_str = self._format_duration(duration)
                            expected_str = self._format_duration(baseline.avg_duration_seconds)

                            anomalies.append(Anomaly(
                                device_id=device_id,
                                anomaly_type=AnomalyType.DURATION,
                                severity=severity,
                                timestamp=curr_time,
                                description=(
                                    f"{device_id} had {direction} duration: "
                                    f"{duration_str} vs typical {expected_str}"
                                ),
                                context={
                                    'actual_duration': float(duration),
                                    'expected_duration': float(baseline.avg_duration_seconds),
                                    'direction': direction,
                                    'state': str(prev_state),
                                },
                                z_score=float(z_score),
                                confidence=float(confidence),
                            ))

                prev_time = curr_time
                prev_state = curr_state

        return anomalies

    def _detect_absence_anomalies(self, events: pd.DataFrame) -> list[Anomaly]:
        """
        Detect expected device activity that is missing.

        Args:
            events: DataFrame with device events.

        Returns:
            List of absence anomalies.
        """
        anomalies = []

        if events.empty:
            return anomalies

        current_time = events['timestamp'].max()
        threshold = timedelta(hours=self.absence_threshold_hours)

        for device_id, baseline in self._baselines.items():
            if baseline.baseline_days < self.min_baseline_days:
                continue

            if baseline.avg_daily_count < 1:
                continue

            if baseline.last_seen is None:
                continue

            time_since_last = current_time - baseline.last_seen

            if time_since_last > threshold:
                expected_events = baseline.avg_daily_count * (time_since_last.total_seconds() / 86400)

                if expected_events >= 1:
                    hours_missing = time_since_last.total_seconds() / 3600
                    severity = self._calculate_absence_severity(hours_missing, baseline.avg_daily_count)
                    confidence = min(hours_missing / (self.absence_threshold_hours * 2), 1.0)

                    anomalies.append(Anomaly(
                        device_id=device_id,
                        anomaly_type=AnomalyType.ABSENCE,
                        severity=severity,
                        timestamp=current_time,
                        description=(
                            f"{device_id} has been inactive for {hours_missing:.1f} hours "
                            f"(typically {baseline.avg_daily_count:.1f} events/day)"
                        ),
                        context={
                            'hours_inactive': float(hours_missing),
                            'expected_daily_events': float(baseline.avg_daily_count),
                            'last_seen': baseline.last_seen.isoformat(),
                        },
                        z_score=float(hours_missing / self.absence_threshold_hours),
                        confidence=float(confidence),
                    ))

        return anomalies

    def _calculate_severity(self, z_score: float) -> SeverityLevel:
        """Calculate severity level based on z-score."""
        if z_score >= 4.0:
            return SeverityLevel.CRITICAL
        elif z_score >= 3.0:
            return SeverityLevel.HIGH
        elif z_score >= 2.5:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW

    def _calculate_absence_severity(
        self, hours_missing: float, avg_daily_count: float
    ) -> SeverityLevel:
        """Calculate severity for absence anomalies."""
        expected_missing = hours_missing / 24 * avg_daily_count

        if expected_missing >= 10 or hours_missing >= 72:
            return SeverityLevel.CRITICAL
        elif expected_missing >= 5 or hours_missing >= 48:
            return SeverityLevel.HIGH
        elif expected_missing >= 2 or hours_missing >= 24:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW

    def _build_patterns(self, anomalies: list[Anomaly]) -> list[dict]:
        """
        Convert Anomaly objects to pattern dictionaries.

        Args:
            anomalies: List of detected anomalies.

        Returns:
            List of pattern dictionaries sorted by severity and confidence.
        """
        patterns = []

        for anomaly in anomalies:
            pattern = {
                'pattern_type': 'anomaly',
                'device_id': anomaly.device_id,
                'anomaly_type': anomaly.anomaly_type.value,
                'severity': anomaly.severity.value,
                'timestamp': anomaly.timestamp.isoformat(),
                'description': anomaly.description,
                'confidence': anomaly.confidence,
                'z_score': anomaly.z_score,
                'metadata': {
                    **anomaly.context,
                    'thresholds': {
                        'z_score_threshold': self.z_score_threshold,
                        'sensitivity': self.sensitivity,
                        'min_baseline_days': self.min_baseline_days,
                    }
                }
            }
            patterns.append(pattern)

            logger.info(
                f"✅ Anomaly: {anomaly.anomaly_type.value} - {anomaly.device_id} "
                f"({anomaly.severity.value}, z={anomaly.z_score:.2f})"
            )

        severity_order = {
            'critical': 0, 'high': 1, 'medium': 2, 'low': 3
        }
        patterns.sort(key=lambda p: (
            severity_order.get(p['severity'], 4),
            -p['confidence']
        ))

        return patterns

    def _filter_system_noise(self, events: pd.DataFrame) -> pd.DataFrame:
        """Filter out system sensors, trackers, and non-actionable entities."""
        if 'device_id' not in events.columns:
            return events

        mask = events['device_id'].apply(self._is_actionable_entity)
        return events[mask].copy()

    def _is_actionable_entity(self, device_id: str) -> bool:
        """Check if entity represents actionable device or meaningful trigger."""
        if not device_id:
            return False

        domain = self._get_domain(device_id)
        if domain in EXCLUDED_DOMAINS:
            return False

        for prefix in EXCLUDED_ENTITY_PREFIXES:
            if device_id.startswith(prefix):
                return False

        device_lower = device_id.lower()
        return all(pattern not in device_lower for pattern in EXCLUDED_PATTERNS)

    @staticmethod
    def _get_domain(device_id: str) -> str:
        """Extract entity domain from device ID."""
        if not device_id or '.' not in str(device_id):
            return 'default'
        return str(device_id).split('.', 1)[0]

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}min"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def _store_daily_aggregates(
        self, patterns: list[dict], events: pd.DataFrame
    ) -> None:
        """Store daily aggregates to InfluxDB."""
        try:
            if events.empty or 'timestamp' not in events.columns:
                return

            date = events['timestamp'].min().date()
            date_str = date.strftime("%Y-%m-%d")

            logger.info(f"Storing {len(patterns)} anomaly aggregates for {date_str}")

            for pattern in patterns:
                try:
                    self.aggregate_client.write_anomaly_daily(
                        date=date_str,
                        device_id=pattern['device_id'],
                        anomaly_type=pattern['anomaly_type'],
                        severity=pattern['severity'],
                        confidence=pattern['confidence'],
                        z_score=pattern['z_score'],
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store aggregate for {pattern['device_id']}: {e}",
                        exc_info=True
                    )

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected anomalies."""
        if not patterns:
            return {
                'total_anomalies': 0,
                'unique_devices': 0,
                'by_type': {},
                'by_severity': {},
                'avg_confidence': 0.0,
            }

        unique_devices = len({p['device_id'] for p in patterns})

        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        for p in patterns:
            by_type[p['anomaly_type']] += 1
            by_severity[p['severity']] += 1

        return {
            'total_anomalies': len(patterns),
            'unique_devices': unique_devices,
            'by_type': dict(by_type),
            'by_severity': dict(by_severity),
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'avg_z_score': float(np.mean([p['z_score'] for p in patterns])),
            'critical_count': by_severity.get('critical', 0),
            'high_count': by_severity.get('high', 0),
        }

    def get_baselines(self) -> dict[str, dict]:
        """
        Get computed baselines for all devices.

        Returns:
            Dictionary of device baselines.
        """
        return {
            device_id: {
                'total_events': b.total_events,
                'avg_daily_count': b.avg_daily_count,
                'std_daily_count': b.std_daily_count,
                'typical_hours': list(b.typical_hours),
                'avg_duration_seconds': b.avg_duration_seconds,
                'baseline_days': b.baseline_days,
            }
            for device_id, b in self._baselines.items()
        }

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """
        Suggest automation or alert from anomaly pattern.

        Anomaly patterns typically suggest:
        - Notifications for security-relevant anomalies
        - Diagnostic alerts for equipment issues
        - Behavior change notifications

        Args:
            pattern: Anomaly pattern dictionary

        Returns:
            Automation suggestion dictionary
        """
        if pattern.get('pattern_type') != 'anomaly':
            logger.warning(f"Pattern type {pattern.get('pattern_type')} is not anomaly")
            return {}

        device_id = pattern.get('device_id', '')
        anomaly_type = pattern.get('anomaly_type', '')
        severity = pattern.get('severity', 'low')
        description = pattern.get('description', '')

        if not device_id:
            return {}

        notify_service = 'notify.notify'
        if severity == 'critical':
            notify_service = 'notify.mobile_app'

        suggestion = {
            'automation_type': 'anomaly_alert',
            'trigger': {
                'platform': 'event',
                'event_type': 'homeiq_anomaly',
                'event_data': {
                    'device_id': device_id,
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                },
            },
            'action': {
                'service': notify_service,
                'data': {
                    'title': f"Anomaly Detected: {device_id}",
                    'message': description,
                    'data': {
                        'importance': 'high' if severity in ('critical', 'high') else 'default',
                    },
                },
            },
            'confidence': pattern.get('confidence', 0.0),
            'description': f"Alert on {anomaly_type} anomaly for {device_id}",
            'device_id': device_id,
            'requires_confirmation': False,
            'safety_level': 'informational',
            'safety_warnings': [],
            'metadata': {
                'source': 'anomaly_pattern',
                'anomaly_type': anomaly_type,
                'severity': severity,
                'z_score': pattern.get('z_score', 0.0),
            }
        }

        logger.info(
            f"✅ Suggested anomaly alert: {anomaly_type} for {device_id} "
            f"(severity={severity})"
        )

        return suggestion

    def get_anomalies_for_device(
        self, patterns: list[dict], device_id: str
    ) -> list[dict]:
        """
        Get all anomalies for a specific device.

        Args:
            patterns: List of detected anomaly patterns.
            device_id: Device to filter for.

        Returns:
            List of anomaly patterns for the device.
        """
        return [p for p in patterns if p['device_id'] == device_id]

    def get_anomalies_by_severity(
        self, patterns: list[dict], min_severity: str = 'medium'
    ) -> list[dict]:
        """
        Get anomalies at or above a minimum severity level.

        Args:
            patterns: List of detected anomaly patterns.
            min_severity: Minimum severity level to include.

        Returns:
            List of anomaly patterns meeting severity threshold.
        """
        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        min_level = severity_order.get(min_severity, 1)

        return [
            p for p in patterns
            if severity_order.get(p['severity'], 0) >= min_level
        ]
