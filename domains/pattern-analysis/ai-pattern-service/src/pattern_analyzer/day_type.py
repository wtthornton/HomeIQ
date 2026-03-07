"""
Day Type Pattern Detector

Compares device activation patterns between weekdays and weekends.
Identifies devices with significantly different behavior by day type.

Epic 37, Story 37.3: Day Type Detector for pattern detection expansion.

Algorithm Overview:
    1. Partition events into weekday vs weekend groups
    2. Per device, compute activation counts and timing distributions per day type
    3. Compare distributions using variance scoring
    4. Flag entities with >30% variance between day types
    5. Return day-type patterns with weekday/weekend profiles

Example Use Cases:
    - Office light: on at 7am weekdays, 9am weekends
    - Coffee maker: every weekday 6:30am, irregular weekends
    - TV: 2 hours weekdays, 6+ hours weekends
    - Alarm: active weekdays only, off weekends

Configuration:
    - min_events_per_type: Minimum events per day type to compare (default: 5)
    - min_confidence: Minimum confidence threshold (default: 0.7)
    - variance_threshold: Minimum variance to flag as different (default: 0.3)
"""

import logging
from dataclasses import dataclass, field
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

# Weekend day numbers (Monday=0 ... Sunday=6)
WEEKEND_DAYS = {5, 6}  # Saturday, Sunday


@dataclass
class DayTypeProfile:
    """Activation profile for a single day type (weekday or weekend)."""
    event_count: int = 0
    day_count: int = 0
    avg_daily_count: float = 0.0
    hourly_distribution: dict[int, float] = field(default_factory=dict)
    peak_hour: int = 0
    avg_hour: float = 0.0
    std_hour: float = 0.0


@dataclass
class DayTypeComparison:
    """Comparison result between weekday and weekend profiles."""
    device_id: str
    weekday_profile: DayTypeProfile
    weekend_profile: DayTypeProfile
    count_variance: float = 0.0
    timing_variance: float = 0.0
    overall_variance: float = 0.0
    confidence: float = 0.0


class DayTypePatternDetector:
    """
    Detects differences in device behavior between weekdays and weekends.

    Compares activation counts, timing distributions, and peak hours
    to identify devices with significantly different day-type behavior.
    """

    def __init__(
        self,
        min_events_per_type: int = 5,
        min_confidence: float = 0.7,
        variance_threshold: float = 0.3,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        """
        Initialize day type pattern detector.

        Args:
            min_events_per_type: Minimum events per day type to compare (default: 5)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.7)
            variance_threshold: Minimum variance to flag (0.0-1.0, default: 0.3)
            filter_system_noise: Filter out system sensors/trackers (default: True)
            aggregate_client: PatternAggregateClient for storing daily aggregates
        """
        self.min_events_per_type = min_events_per_type
        self.min_confidence = min_confidence
        self.variance_threshold = variance_threshold
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client

        logger.info(
            "DayTypePatternDetector initialized: "
            f"min_events={min_events_per_type}, min_confidence={min_confidence}, "
            f"variance_threshold={variance_threshold}"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect day-type behavioral patterns.

        Args:
            events: DataFrame with columns [device_id, timestamp, state]

        Returns:
            List of day-type pattern dictionaries with keys:
                - pattern_type: "day_type"
                - device_id: Device identifier
                - weekday_pattern: Weekday activation profile
                - weekend_pattern: Weekend activation profile
                - variance_score: Overall variance between day types
                - confidence: Confidence score
                - metadata: Additional pattern metadata
        """
        if events.empty:
            logger.warning("No events provided for day-type detection")
            return []

        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        logger.info(f"Analyzing {len(events)} events for day-type patterns")

        if self.filter_system_noise:
            original_count = len(events)
            events = self._filter_system_noise(events)
            if len(events) < original_count:
                logger.info(
                    f"Filtered system noise: {original_count} -> {len(events)} events"
                )

        if events.empty:
            logger.warning("No events remaining after filtering")
            return []

        events = events.sort_values('timestamp').copy()
        events = events.reset_index(drop=True)

        # Partition events by day type
        weekday_events, weekend_events = self._partition_by_day_type(events)

        # Build per-device comparisons
        comparisons = self._compare_day_types(weekday_events, weekend_events)

        # Build patterns from significant comparisons
        patterns = self._build_patterns(comparisons)

        logger.info(f"Detected {len(patterns)} day-type patterns")

        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    @staticmethod
    def _partition_by_day_type(
        events: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split events into weekday and weekend groups."""
        day_of_week = events['timestamp'].dt.dayofweek
        weekend_mask = day_of_week.isin(WEEKEND_DAYS)
        return events[~weekend_mask].copy(), events[weekend_mask].copy()

    def _compare_day_types(
        self,
        weekday_events: pd.DataFrame,
        weekend_events: pd.DataFrame,
    ) -> list[DayTypeComparison]:
        """Compare weekday vs weekend profiles for each device."""
        all_devices = set()
        if not weekday_events.empty:
            all_devices.update(weekday_events['device_id'].unique())
        if not weekend_events.empty:
            all_devices.update(weekend_events['device_id'].unique())

        comparisons: list[DayTypeComparison] = []

        for device_id in all_devices:
            wd_device = weekday_events[weekday_events['device_id'] == device_id]
            we_device = weekend_events[weekend_events['device_id'] == device_id]

            # Need sufficient data in both types
            if len(wd_device) < self.min_events_per_type:
                continue
            if len(we_device) < self.min_events_per_type:
                continue

            wd_profile = self._build_profile(wd_device)
            we_profile = self._build_profile(we_device)

            comparison = self._compute_variance(device_id, wd_profile, we_profile)
            comparisons.append(comparison)

        return comparisons

    @staticmethod
    def _build_profile(device_events: pd.DataFrame) -> DayTypeProfile:
        """Build an activation profile from device events."""
        profile = DayTypeProfile()
        profile.event_count = len(device_events)

        # Count unique days
        dates = device_events['timestamp'].dt.date.unique()
        profile.day_count = len(dates)

        # Average daily count
        if profile.day_count > 0:
            profile.avg_daily_count = profile.event_count / profile.day_count

        # Hourly distribution (normalized to fraction of events)
        hours = device_events['timestamp'].dt.hour
        hour_counts = hours.value_counts().to_dict()
        total = sum(hour_counts.values())
        if total > 0:
            profile.hourly_distribution = {
                h: c / total for h, c in hour_counts.items()
            }

        # Peak hour
        if hour_counts:
            profile.peak_hour = max(hour_counts, key=hour_counts.get)

        # Hour statistics
        hour_values = hours.values.astype(float)
        if len(hour_values) > 0:
            profile.avg_hour = float(np.mean(hour_values))
            profile.std_hour = float(np.std(hour_values)) if len(hour_values) > 1 else 0.0

        return profile

    def _compute_variance(
        self,
        device_id: str,
        wd_profile: DayTypeProfile,
        we_profile: DayTypeProfile,
    ) -> DayTypeComparison:
        """Compute variance scores between weekday and weekend profiles."""
        # Count variance: relative difference in daily activation counts
        count_variance = self._relative_difference(
            wd_profile.avg_daily_count, we_profile.avg_daily_count
        )

        # Timing variance: difference in peak hours and distribution overlap
        timing_variance = self._timing_variance(wd_profile, we_profile)

        # Overall variance: weighted combination
        overall_variance = 0.6 * count_variance + 0.4 * timing_variance

        # Confidence based on data volume
        confidence = self._calculate_confidence(wd_profile, we_profile)

        return DayTypeComparison(
            device_id=device_id,
            weekday_profile=wd_profile,
            weekend_profile=we_profile,
            count_variance=count_variance,
            timing_variance=timing_variance,
            overall_variance=overall_variance,
            confidence=confidence,
        )

    @staticmethod
    def _relative_difference(a: float, b: float) -> float:
        """Calculate relative difference between two values (0.0-1.0)."""
        if a == 0.0 and b == 0.0:
            return 0.0
        max_val = max(abs(a), abs(b))
        if max_val == 0:
            return 0.0
        return abs(a - b) / max_val

    @staticmethod
    def _timing_variance(
        wd_profile: DayTypeProfile,
        we_profile: DayTypeProfile,
    ) -> float:
        """Calculate timing variance between two profiles."""
        # Peak hour difference (normalized to 0-1, max diff = 12 hours)
        peak_diff = abs(wd_profile.peak_hour - we_profile.peak_hour)
        peak_diff = min(peak_diff, 24 - peak_diff)  # Circular distance
        peak_variance = peak_diff / 12.0

        # Average hour difference
        avg_diff = abs(wd_profile.avg_hour - we_profile.avg_hour)
        avg_diff = min(avg_diff, 24 - avg_diff)
        avg_variance = avg_diff / 12.0

        # Distribution overlap (Bhattacharyya-style)
        overlap = 0.0
        all_hours = set(wd_profile.hourly_distribution) | set(we_profile.hourly_distribution)
        for hour in all_hours:
            wd_frac = wd_profile.hourly_distribution.get(hour, 0.0)
            we_frac = we_profile.hourly_distribution.get(hour, 0.0)
            overlap += (wd_frac * we_frac) ** 0.5

        distribution_variance = 1.0 - min(overlap, 1.0)

        return (
            0.3 * peak_variance
            + 0.3 * avg_variance
            + 0.4 * distribution_variance
        )

    @staticmethod
    def _calculate_confidence(
        wd_profile: DayTypeProfile,
        we_profile: DayTypeProfile,
    ) -> float:
        """Calculate confidence based on data volume and coverage."""
        # More days = higher confidence (saturates around 14 days per type)
        wd_day_factor = min(wd_profile.day_count / 14.0, 1.0)
        we_day_factor = min(we_profile.day_count / 14.0, 1.0)
        day_factor = (wd_day_factor + we_day_factor) / 2.0

        # More events = higher confidence (saturates around 50 per type)
        wd_event_factor = min(wd_profile.event_count / 50.0, 1.0)
        we_event_factor = min(we_profile.event_count / 50.0, 1.0)
        event_factor = (wd_event_factor + we_event_factor) / 2.0

        return 0.6 * day_factor + 0.4 * event_factor

    def _build_patterns(
        self, comparisons: list[DayTypeComparison]
    ) -> list[dict]:
        """Build pattern dictionaries from comparisons that meet thresholds."""
        patterns = []

        for comp in comparisons:
            if comp.overall_variance < self.variance_threshold:
                continue
            if comp.confidence < self.min_confidence:
                continue

            pattern = {
                'pattern_type': 'day_type',
                'device_id': comp.device_id,
                'weekday_pattern': self._profile_to_dict(comp.weekday_profile),
                'weekend_pattern': self._profile_to_dict(comp.weekend_profile),
                'variance_score': float(comp.overall_variance),
                'confidence': float(comp.confidence),
                'metadata': {
                    'count_variance': float(comp.count_variance),
                    'timing_variance': float(comp.timing_variance),
                    'weekday_peak_hour': comp.weekday_profile.peak_hour,
                    'weekend_peak_hour': comp.weekend_profile.peak_hour,
                    'weekday_avg_daily': float(comp.weekday_profile.avg_daily_count),
                    'weekend_avg_daily': float(comp.weekend_profile.avg_daily_count),
                    'domain': self._get_domain(comp.device_id),
                    'thresholds': {
                        'min_events_per_type': self.min_events_per_type,
                        'min_confidence': self.min_confidence,
                        'variance_threshold': self.variance_threshold,
                    },
                },
            }

            patterns.append(pattern)

            logger.info(
                f"Day-type pattern: {comp.device_id} "
                f"(variance={comp.overall_variance:.0%}, "
                f"weekday_peak={comp.weekday_profile.peak_hour}h, "
                f"weekend_peak={comp.weekend_profile.peak_hour}h, "
                f"confidence={comp.confidence:.0%})"
            )

        patterns.sort(key=lambda p: p['variance_score'], reverse=True)
        return patterns

    @staticmethod
    def _profile_to_dict(profile: DayTypeProfile) -> dict:
        """Convert a DayTypeProfile to a serializable dictionary."""
        return {
            'event_count': profile.event_count,
            'day_count': profile.day_count,
            'avg_daily_count': float(profile.avg_daily_count),
            'peak_hour': profile.peak_hour,
            'avg_hour': float(profile.avg_hour),
            'std_hour': float(profile.std_hour),
            'hourly_distribution': {
                str(h): round(v, 4) for h, v in profile.hourly_distribution.items()
            },
        }

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """
        Suggest automation from day-type pattern.

        Creates time-based automations that adjust behavior by day type.

        Args:
            pattern: Day-type pattern dictionary.

        Returns:
            Automation suggestion dictionary.
        """
        if pattern.get('pattern_type') != 'day_type':
            logger.warning(
                f"Pattern type {pattern.get('pattern_type')} is not day_type"
            )
            return {}

        device_id = pattern.get('device_id', '')
        if not device_id:
            return {}

        weekday = pattern.get('weekday_pattern', {})
        weekend = pattern.get('weekend_pattern', {})
        confidence = pattern.get('confidence', 0.0)

        wd_peak = weekday.get('peak_hour', 8)
        we_peak = weekend.get('peak_hour', 9)

        domain = self._get_domain(device_id)
        service = self._get_default_service(domain)

        description = (
            f"Day-type automation: {device_id} "
            f"(weekday {wd_peak}:00, weekend {we_peak}:00)"
        )

        suggestion = {
            'automation_type': 'day_type_schedule',
            'trigger': {
                'platform': 'time',
                'at': f"{wd_peak:02d}:00:00",
            },
            'condition': {
                'condition': 'time',
                'weekday': ['mon', 'tue', 'wed', 'thu', 'fri'],
            },
            'action': {
                'service': f"{domain}.{service}",
                'entity_id': device_id,
                'target': {'entity_id': device_id},
            },
            'confidence': float(confidence),
            'description': description,
            'device_id': device_id,
            'requires_confirmation': False,
            'safety_level': 'normal',
            'safety_warnings': [],
            'metadata': {
                'source': 'day_type_pattern',
                'weekday_peak_hour': wd_peak,
                'weekend_peak_hour': we_peak,
                'variance_score': pattern.get('variance_score', 0.0),
            },
        }

        logger.info(
            f"Suggested day-type automation: {description} "
            f"(confidence={confidence:.0%})"
        )

        return suggestion

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected day-type patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'avg_variance': 0.0,
                'avg_confidence': 0.0,
                'high_variance_count': 0,
            }

        variances = [p['variance_score'] for p in patterns]
        return {
            'total_patterns': len(patterns),
            'avg_variance': float(np.mean(variances)),
            'max_variance': float(np.max(variances)),
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'high_variance_count': sum(1 for v in variances if v > 0.5),
            'domains': dict(
                pd.Series([
                    self._get_domain(p['device_id']) for p in patterns
                ]).value_counts().to_dict()
            ),
            'variance_distribution': {
                '30-50%': sum(1 for v in variances if 0.3 <= v < 0.5),
                '50-70%': sum(1 for v in variances if 0.5 <= v < 0.7),
                '70-100%': sum(1 for v in variances if 0.7 <= v <= 1.0),
            },
        }

    @staticmethod
    def _get_domain(device_id: str) -> str:
        """Extract entity domain from device ID."""
        if not device_id or '.' not in str(device_id):
            return 'default'
        return str(device_id).split('.', 1)[0]

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
    def _get_default_service(domain: str) -> str:
        """Get default service for domain."""
        service_map = {
            'light': 'turn_on',
            'switch': 'turn_on',
            'fan': 'turn_on',
            'cover': 'open_cover',
            'lock': 'lock',
            'climate': 'set_temperature',
            'media_player': 'turn_on',
            'vacuum': 'start',
            'scene': 'turn_on',
        }
        return service_map.get(domain, 'turn_on')

    def _store_daily_aggregates(
        self, patterns: list[dict], events: pd.DataFrame
    ) -> None:
        """Store daily aggregates to InfluxDB."""
        try:
            if events.empty or 'timestamp' not in events.columns:
                return

            date = events['timestamp'].min().date()
            date_str = date.strftime("%Y-%m-%d")

            logger.info(
                f"Storing {len(patterns)} day-type aggregates for {date_str}"
            )

            for pattern in patterns:
                try:
                    self.aggregate_client.write_day_type_daily(
                        date=date_str,
                        device_id=pattern.get('device_id', ''),
                        variance_score=pattern.get('variance_score', 0.0),
                        confidence=pattern.get('confidence', 0.0),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store aggregate for day-type pattern: {e}",
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
