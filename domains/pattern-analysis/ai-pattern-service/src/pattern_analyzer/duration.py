"""
Duration Pattern Detector

Detects devices with consistent on/off durations.
Identifies patterns like bathroom light always on for 5-7 minutes.

Epic 37, Story 37.2: Duration Detector for pattern detection expansion.

Algorithm Overview:
    1. Parse events into state transitions (on→off, off→on)
    2. Calculate duration for each state period
    3. Compute statistical distribution (mean, std, min, max)
    4. Identify patterns with low coefficient of variation (consistent)
    5. Flag anomalous durations (>2 standard deviations from mean)

Example Use Cases:
    - Bathroom light: consistently on for 5-7 minutes
    - Coffee maker: always runs for 4-5 minutes
    - Garage door: open for 10-15 seconds (quick in/out)
    - Washing machine: cycle duration 45-60 minutes

Configuration:
    - min_state_changes: Minimum state changes to establish baseline (default: 10)
    - min_confidence: Minimum confidence threshold (default: 0.7)
    - anomaly_threshold_std: Standard deviations for anomaly (default: 2.0)
    - max_cv: Maximum coefficient of variation for pattern (default: 0.5)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
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

ON_STATES = {'on', 'true', 'home', 'open', 'unlocked', 'playing', 'active'}
OFF_STATES = {'off', 'false', 'away', 'closed', 'locked', 'idle', 'standby', 'paused'}


@dataclass
class StateDuration:
    """Represents a single state duration measurement."""
    device_id: str
    state: str
    duration_seconds: float
    start_time: pd.Timestamp
    end_time: pd.Timestamp


@dataclass
class DurationStats:
    """Statistical summary of durations for a device state."""
    device_id: str
    state: str
    count: int
    mean_seconds: float
    std_seconds: float
    min_seconds: float
    max_seconds: float
    coefficient_of_variation: float
    durations: list[float]


class DurationPatternDetector:
    """
    Detects devices with consistent state durations.
    Finds patterns like: bathroom light consistently on for 5-7 minutes.

    Examples:
        - Bathroom light: 5-7 min on duration (morning routine)
        - Coffee maker: 4-5 min brew cycle
        - Garage door: 10-15 sec open during arrivals
        - TV: 2-3 hour viewing sessions in evenings
    """

    def __init__(
        self,
        min_state_changes: int = 10,
        min_confidence: float = 0.7,
        anomaly_threshold_std: float = 2.0,
        max_cv: float = 0.5,
        min_duration_seconds: float = 1.0,
        max_duration_hours: float = 24.0,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        """
        Initialize duration detector.

        Args:
            min_state_changes: Minimum state changes to establish baseline (default: 10)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.7)
            anomaly_threshold_std: Standard deviations to flag anomaly (default: 2.0)
            max_cv: Maximum coefficient of variation for pattern (default: 0.5)
            min_duration_seconds: Minimum duration to consider (default: 1.0)
            max_duration_hours: Maximum duration to consider (default: 24.0)
            filter_system_noise: Filter out system sensors/trackers (default: True)
            aggregate_client: PatternAggregateClient for storing daily aggregates
        """
        self.min_state_changes = min_state_changes
        self.min_confidence = min_confidence
        self.anomaly_threshold_std = anomaly_threshold_std
        self.max_cv = max_cv
        self.min_duration_seconds = min_duration_seconds
        self.max_duration_hours = max_duration_hours
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client

        logger.info(
            "DurationPatternDetector initialized: "
            f"min_state_changes={min_state_changes}, min_confidence={min_confidence}, "
            f"anomaly_threshold={anomaly_threshold_std}σ, max_cv={max_cv}, "
            f"duration_range={min_duration_seconds}s-{max_duration_hours}h"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect consistent duration patterns for device states.

        Args:
            events: DataFrame with columns [device_id, timestamp, state]
                    device_id: str - Device identifier (e.g., "light.bedroom")
                    timestamp: datetime - Event timestamp
                    state: str - Device state (e.g., "on", "off")

        Returns:
            List of duration pattern dictionaries with keys:
                - pattern_type: "duration"
                - device_id: Device identifier
                - state: State being analyzed ("on" or "off")
                - occurrences: Number of duration samples
                - confidence: Confidence score
                - avg_duration: Average duration in seconds
                - std_duration: Standard deviation in seconds
                - min_duration: Minimum duration in seconds
                - max_duration: Maximum duration in seconds
                - anomalies: List of anomalous durations detected
                - metadata: Additional pattern metadata
        """
        if events.empty:
            logger.warning("No events provided for duration detection")
            return []

        required_cols = ['device_id', 'timestamp', 'state']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        logger.info(f"Analyzing {len(events)} events for duration patterns")

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

        durations = self._extract_durations(events)

        duration_stats = self._calculate_statistics(durations)

        patterns = self._build_patterns(duration_stats)

        logger.info(f"Detected {len(patterns)} duration patterns")

        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _extract_durations(self, events: pd.DataFrame) -> list[StateDuration]:
        """
        Extract state durations from events.

        Tracks state transitions and calculates time spent in each state.

        Args:
            events: Sorted DataFrame with device_id, timestamp, state columns.

        Returns:
            List of StateDuration objects.
        """
        durations: list[StateDuration] = []
        device_states: dict[str, tuple[str, pd.Timestamp]] = {}
        max_duration_seconds = self.max_duration_hours * 3600

        for _, event in events.iterrows():
            device_id = event['device_id']
            timestamp = event['timestamp']
            state = str(event['state']).lower()

            normalized_state = self._normalize_state(state)

            if device_id in device_states:
                prev_state, prev_time = device_states[device_id]

                if normalized_state != prev_state:
                    duration_seconds = (timestamp - prev_time).total_seconds()

                    if self.min_duration_seconds <= duration_seconds <= max_duration_seconds:
                        durations.append(StateDuration(
                            device_id=device_id,
                            state=prev_state,
                            duration_seconds=duration_seconds,
                            start_time=prev_time,
                            end_time=timestamp,
                        ))

            device_states[device_id] = (normalized_state, timestamp)

        return durations

    def _normalize_state(self, state: str) -> str:
        """
        Normalize state to 'on', 'off', or original value.

        Args:
            state: Raw state string.

        Returns:
            Normalized state string.
        """
        state_lower = state.lower().strip()

        if state_lower in ON_STATES:
            return 'on'
        if state_lower in OFF_STATES:
            return 'off'

        try:
            value = float(state_lower)
            return 'on' if value > 0 else 'off'
        except (ValueError, TypeError):
            pass

        return state_lower

    def _calculate_statistics(
        self, durations: list[StateDuration]
    ) -> dict[tuple[str, str], DurationStats]:
        """
        Calculate statistical distributions for each device/state combination.

        Args:
            durations: List of StateDuration objects.

        Returns:
            Dictionary mapping (device_id, state) to DurationStats.
        """
        grouped: dict[tuple[str, str], list[float]] = defaultdict(list)

        for d in durations:
            key = (d.device_id, d.state)
            grouped[key].append(d.duration_seconds)

        stats: dict[tuple[str, str], DurationStats] = {}

        for (device_id, state), duration_list in grouped.items():
            if len(duration_list) < self.min_state_changes:
                logger.debug(
                    f"Skipping {device_id} ({state}): only {len(duration_list)} samples "
                    f"(need {self.min_state_changes})"
                )
                continue

            arr = np.array(duration_list)
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr))
            min_val = float(np.min(arr))
            max_val = float(np.max(arr))

            cv = std_val / mean_val if mean_val > 0 else float('inf')

            stats[(device_id, state)] = DurationStats(
                device_id=device_id,
                state=state,
                count=len(duration_list),
                mean_seconds=mean_val,
                std_seconds=std_val,
                min_seconds=min_val,
                max_seconds=max_val,
                coefficient_of_variation=cv,
                durations=duration_list,
            )

        return stats

    def _build_patterns(
        self, stats: dict[tuple[str, str], DurationStats]
    ) -> list[dict]:
        """
        Build pattern dictionaries from duration statistics.

        Filters by coefficient of variation and confidence thresholds.
        Identifies anomalous durations within each pattern.

        Args:
            stats: Dictionary from _calculate_statistics.

        Returns:
            List of pattern dictionaries sorted by confidence (descending).
        """
        patterns = []

        for (device_id, state), duration_stats in stats.items():
            cv = duration_stats.coefficient_of_variation
            if cv > self.max_cv:
                logger.debug(
                    f"Skipping {device_id} ({state}): CV {cv:.2f} > {self.max_cv}"
                )
                continue

            confidence = self._calculate_confidence(duration_stats)
            if confidence < self.min_confidence:
                logger.debug(
                    f"Skipping {device_id} ({state}): confidence {confidence:.2f} < {self.min_confidence}"
                )
                continue

            anomalies = self._detect_anomalies(duration_stats)

            human_readable = self._format_duration(duration_stats.mean_seconds)

            pattern = {
                'pattern_type': 'duration',
                'device_id': device_id,
                'state': state,
                'occurrences': duration_stats.count,
                'confidence': float(confidence),
                'avg_duration': duration_stats.mean_seconds,
                'std_duration': duration_stats.std_seconds,
                'min_duration': duration_stats.min_seconds,
                'max_duration': duration_stats.max_seconds,
                'anomalies': anomalies,
                'metadata': {
                    'coefficient_of_variation': float(cv),
                    'human_readable_duration': human_readable,
                    'anomaly_count': len(anomalies),
                    'thresholds': {
                        'min_state_changes': self.min_state_changes,
                        'min_confidence': self.min_confidence,
                        'max_cv': self.max_cv,
                        'anomaly_threshold_std': self.anomaly_threshold_std,
                    }
                }
            }

            patterns.append(pattern)

            logger.info(
                f"✅ Duration pattern: {device_id} ({state}) "
                f"avg={human_readable}, CV={cv:.2%}, "
                f"confidence={confidence:.0%}, anomalies={len(anomalies)}"
            )

        patterns.sort(key=lambda p: p['confidence'], reverse=True)

        return patterns

    def _calculate_confidence(self, stats: DurationStats) -> float:
        """
        Calculate confidence score for duration pattern.

        Based on:
        - Sample size (more samples = higher confidence)
        - Coefficient of variation (lower CV = higher confidence)
        - Distribution normality (not implemented yet)

        Args:
            stats: DurationStats object.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        sample_factor = min(stats.count / (self.min_state_changes * 2), 1.0)

        cv = stats.coefficient_of_variation
        cv_factor = max(0.0, 1.0 - (cv / self.max_cv))

        confidence = (0.6 * sample_factor) + (0.4 * cv_factor)

        return min(max(confidence, 0.0), 1.0)

    def _detect_anomalies(self, stats: DurationStats) -> list[dict]:
        """
        Detect anomalous durations (>N standard deviations from mean).

        Args:
            stats: DurationStats object.

        Returns:
            List of anomaly dictionaries with duration and deviation info.
        """
        anomalies = []

        if stats.std_seconds == 0:
            return anomalies

        threshold = self.anomaly_threshold_std * stats.std_seconds

        for duration in stats.durations:
            deviation = abs(duration - stats.mean_seconds)
            if deviation > threshold:
                std_deviations = deviation / stats.std_seconds
                direction = 'long' if duration > stats.mean_seconds else 'short'

                anomalies.append({
                    'duration_seconds': duration,
                    'deviation_seconds': deviation,
                    'std_deviations': float(std_deviations),
                    'direction': direction,
                    'human_readable': self._format_duration(duration),
                })

        return anomalies

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

            logger.info(f"Storing {len(patterns)} duration aggregates for {date_str}")

            for pattern in patterns:
                try:
                    self.aggregate_client.write_duration_daily(
                        date=date_str,
                        device_id=pattern['device_id'],
                        state=pattern['state'],
                        avg_duration=pattern['avg_duration'],
                        std_duration=pattern['std_duration'],
                        occurrences=pattern['occurrences'],
                        confidence=pattern['confidence'],
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store aggregate for {pattern['device_id']}: {e}",
                        exc_info=True
                    )

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'unique_devices': 0,
                'avg_confidence': 0.0,
                'avg_duration': 0.0,
                'total_anomalies': 0,
            }

        unique_devices = len({p['device_id'] for p in patterns})

        return {
            'total_patterns': len(patterns),
            'unique_devices': unique_devices,
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'avg_duration': float(np.mean([p['avg_duration'] for p in patterns])),
            'min_confidence': float(np.min([p['confidence'] for p in patterns])),
            'max_confidence': float(np.max([p['confidence'] for p in patterns])),
            'total_anomalies': sum(len(p['anomalies']) for p in patterns),
            'state_distribution': {
                'on': sum(1 for p in patterns if p['state'] == 'on'),
                'off': sum(1 for p in patterns if p['state'] == 'off'),
                'other': sum(1 for p in patterns if p['state'] not in ('on', 'off')),
            },
            'confidence_distribution': {
                '70-80%': sum(1 for p in patterns if 0.7 <= p['confidence'] < 0.8),
                '80-90%': sum(1 for p in patterns if 0.8 <= p['confidence'] < 0.9),
                '90-100%': sum(1 for p in patterns if 0.9 <= p['confidence'] <= 1.0),
            }
        }

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """
        Suggest automation from duration pattern.

        Duration patterns can suggest:
        - Auto-off after typical duration (energy saving)
        - Alerts for anomalous durations (security/safety)
        - Schedule optimizations based on typical durations

        Args:
            pattern: Duration pattern dictionary

        Returns:
            Automation suggestion dictionary
        """
        if pattern.get('pattern_type') != 'duration':
            logger.warning(f"Pattern type {pattern.get('pattern_type')} is not duration")
            return {}

        device_id = pattern.get('device_id', '')
        state = pattern.get('state', '')
        avg_duration = pattern.get('avg_duration', 0)
        std_duration = pattern.get('std_duration', 0)
        confidence = pattern.get('confidence', 0.0)

        if not device_id or avg_duration <= 0:
            return {}

        domain = self._get_domain(device_id)

        if state == 'on' and domain in ('light', 'switch', 'fan'):
            auto_off_delay = avg_duration + (2 * std_duration)

            suggestion = {
                'automation_type': 'duration_auto_off',
                'trigger': {
                    'platform': 'state',
                    'entity_id': device_id,
                    'to': 'on',
                    'for': {'seconds': int(auto_off_delay)},
                },
                'action': {
                    'service': f"{domain}.turn_off",
                    'entity_id': device_id,
                    'target': {'entity_id': device_id},
                },
                'confidence': float(confidence),
                'description': (
                    f"Auto-off {device_id} after {self._format_duration(auto_off_delay)} "
                    f"(typical: {self._format_duration(avg_duration)})"
                ),
                'device_id': device_id,
                'requires_confirmation': True,
                'safety_level': 'normal',
                'safety_warnings': [],
                'metadata': {
                    'source': 'duration_pattern',
                    'avg_duration': avg_duration,
                    'std_duration': std_duration,
                    'auto_off_delay': auto_off_delay,
                }
            }
        else:
            anomaly_threshold = avg_duration + (self.anomaly_threshold_std * std_duration)

            suggestion = {
                'automation_type': 'duration_alert',
                'trigger': {
                    'platform': 'state',
                    'entity_id': device_id,
                    'to': state,
                    'for': {'seconds': int(anomaly_threshold)},
                },
                'action': {
                    'service': 'notify.notify',
                    'data': {
                        'message': (
                            f"{device_id} has been {state} for longer than usual "
                            f"(>{self._format_duration(anomaly_threshold)})"
                        ),
                    },
                },
                'confidence': float(confidence),
                'description': (
                    f"Alert if {device_id} stays {state} > {self._format_duration(anomaly_threshold)}"
                ),
                'device_id': device_id,
                'requires_confirmation': False,
                'safety_level': 'informational',
                'safety_warnings': [],
                'metadata': {
                    'source': 'duration_pattern',
                    'avg_duration': avg_duration,
                    'std_duration': std_duration,
                    'anomaly_threshold': anomaly_threshold,
                }
            }

        logger.info(
            f"✅ Suggested duration automation: {suggestion['description']} "
            f"(confidence={confidence:.0%})"
        )

        return suggestion

    def get_anomalies_for_device(
        self, patterns: list[dict], device_id: str
    ) -> list[dict]:
        """
        Get all anomalies for a specific device across all states.

        Args:
            patterns: List of detected duration patterns.
            device_id: Device to filter for.

        Returns:
            List of anomaly dictionaries for the device.
        """
        anomalies = []
        for pattern in patterns:
            if pattern['device_id'] == device_id:
                for anomaly in pattern.get('anomalies', []):
                    anomalies.append({
                        **anomaly,
                        'state': pattern['state'],
                        'device_id': device_id,
                    })
        return anomalies
