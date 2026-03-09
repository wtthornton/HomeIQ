"""
Frequency Pattern Detector

Detects devices with consistent daily/weekly activation counts.
Identifies frequency changes that may indicate issues or behavior changes.

Epic 37, Story 37.7: Frequency Detector for pattern detection expansion.

Algorithm Overview:
    1. Group events by device and date
    2. Calculate daily activation counts per device
    3. Compute rolling averages (7-day and 30-day windows)
    4. Detect significant frequency changes (>50% from baseline)
    5. Determine trend direction (increasing/decreasing/stable)

Example Use Cases:
    - Furnace cycling 20x/day suddenly jumps to 40x/day (equipment issue)
    - Motion sensor averaging 50 triggers/day drops to 5 (occupancy change)
    - Garage door averages 4 opens/day, consistent pattern
    - Smart plug toggling 100x/day (possible malfunction)

Configuration:
    - min_days: Minimum days of data to establish baseline (default: 7)
    - min_confidence: Minimum confidence threshold (default: 0.7)
    - change_threshold: Minimum change to flag (0.0-1.0, default: 0.5)
"""

import logging
from collections import defaultdict
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


@dataclass
class FrequencyProfile:
    """Frequency statistics for a single device."""
    device_id: str
    total_events: int = 0
    total_days: int = 0
    daily_counts: list[int] = field(default_factory=list)
    avg_daily: float = 0.0
    std_daily: float = 0.0
    min_daily: int = 0
    max_daily: int = 0
    coefficient_of_variation: float = 0.0
    trend: str = 'stable'  # 'increasing', 'decreasing', 'stable'
    trend_slope: float = 0.0
    recent_avg: float = 0.0  # Last 7 days average
    baseline_avg: float = 0.0  # Overall average


@dataclass
class FrequencyChange:
    """A detected frequency change for a device."""
    device_id: str
    change_ratio: float  # e.g., 2.0 = doubled, 0.5 = halved
    direction: str  # 'increase' or 'decrease'
    baseline_avg: float
    recent_avg: float
    confidence: float


class SeasonalDecomposer:
    """Lightweight time-series decomposition. Story 40.6.

    Replaces Prophet with a manual STL-like decomposition using
    moving averages for trend and seasonal component extraction.
    Falls back to linear regression when data < 14 days.
    """

    def __init__(self, period: int = 7):
        """period: seasonality period in days (default: 7 = weekly)."""
        self.period = period

    def decompose(self, daily_counts: list[int]) -> dict:
        """Decompose daily counts into trend, seasonal, and residual."""
        if len(daily_counts) < self.period * 2:
            return {}

        y = np.array(daily_counts, dtype=float)
        n = len(y)

        # Extract trend via moving average
        trend = np.full(n, np.nan)
        half = self.period // 2
        for i in range(half, n - half):
            trend[i] = np.mean(y[max(0, i - half):i + half + 1])

        # Fill edges
        first_valid = np.nanmean(trend[:self.period * 2]) if not np.all(np.isnan(trend[:self.period * 2])) else y[0]
        last_valid = np.nanmean(trend[-self.period * 2:]) if not np.all(np.isnan(trend[-self.period * 2:])) else y[-1]
        trend = np.where(np.isnan(trend), first_valid, trend)

        # Detrended series
        detrended = y - trend

        # Seasonal component: average detrended values for each day-of-week
        seasonal = np.zeros(n)
        for day in range(self.period):
            indices = list(range(day, n, self.period))
            day_values = detrended[indices]
            day_avg = float(np.mean(day_values))
            for idx in indices:
                seasonal[idx] = day_avg

        # Residual
        residual = y - trend - seasonal

        # Detect changepoints (where residual exceeds 2 std)
        residual_std = float(np.std(residual)) if len(residual) > 1 else 1.0
        changepoints = []
        for i in range(1, n):
            if abs(residual[i]) > 2 * residual_std:
                changepoints.append(i)

        # Forecast next 7 days
        forecast = []
        for day in range(7):
            future_day = (n + day) % self.period
            trend_val = float(trend[-1])
            seasonal_val = float(seasonal[future_day]) if future_day < len(seasonal) else 0.0
            forecast.append(max(0.0, trend_val + seasonal_val))

        return {
            'trend_direction': 'increasing' if trend[-1] > trend[0] else ('decreasing' if trend[-1] < trend[0] else 'stable'),
            'trend_slope': float((trend[-1] - trend[0]) / n) if n > 0 else 0.0,
            'seasonal_amplitude': float(np.max(seasonal) - np.min(seasonal)),
            'residual_std': residual_std,
            'changepoints': changepoints,
            'forecast_7d': forecast,
            'has_weekly_seasonality': float(np.max(seasonal) - np.min(seasonal)) > 1.0,
        }


class FrequencyPatternDetector:
    """
    Detects devices with consistent daily/weekly activation counts
    and flags significant changes in frequency.

    Tracks rolling averages and identifies trend direction.
    """

    def __init__(
        self,
        min_days: int = 7,
        min_confidence: float = 0.7,
        change_threshold: float = 0.5,
        recent_window_days: int = 7,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        """
        Initialize frequency pattern detector.

        Args:
            min_days: Minimum days of data to establish baseline (default: 7)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.7)
            change_threshold: Minimum relative change to flag (default: 0.5 = 50%)
            recent_window_days: Days to consider as "recent" (default: 7)
            filter_system_noise: Filter out system sensors/trackers (default: True)
            aggregate_client: PatternAggregateClient for storing daily aggregates
        """
        self.min_days = min_days
        self.min_confidence = min_confidence
        self.change_threshold = change_threshold
        self.recent_window_days = recent_window_days
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client
        self.decomposer = SeasonalDecomposer(period=7)

        logger.info(
            "FrequencyPatternDetector initialized: "
            f"min_days={min_days}, min_confidence={min_confidence}, "
            f"change_threshold={change_threshold}, recent_window={recent_window_days}d"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect frequency-based patterns and changes.

        Args:
            events: DataFrame with columns [device_id, timestamp, state]

        Returns:
            List of frequency pattern dictionaries with keys:
                - pattern_type: "frequency"
                - device_id: Device identifier
                - avg_daily: Average daily activation count
                - trend: Trend direction (increasing/decreasing/stable)
                - change_detected: Whether a significant change was detected
                - variance_score: How much frequency changed (0.0-1.0+)
                - confidence: Confidence score
                - metadata: Additional pattern metadata
        """
        if events.empty:
            logger.warning("No events provided for frequency detection")
            return []

        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        logger.info(f"Analyzing {len(events)} events for frequency patterns")

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

        # Build frequency profiles per device
        profiles = self._build_profiles(events)

        # Detect changes and build patterns
        patterns = self._build_patterns(profiles)

        logger.info(f"Detected {len(patterns)} frequency patterns")

        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _build_profiles(
        self, events: pd.DataFrame
    ) -> list[FrequencyProfile]:
        """Build frequency profiles for each device."""
        profiles: list[FrequencyProfile] = []

        for device_id, device_events in events.groupby('device_id'):
            dates = device_events['timestamp'].dt.date
            daily_counts_series = dates.value_counts().sort_index()

            # Fill missing days with 0
            if len(daily_counts_series) >= 2:
                date_range = pd.date_range(
                    start=daily_counts_series.index.min(),
                    end=daily_counts_series.index.max(),
                    freq='D',
                )
                daily_counts_series = daily_counts_series.reindex(
                    date_range.date, fill_value=0
                )

            daily_counts = daily_counts_series.values.tolist()
            total_days = len(daily_counts)

            if total_days < self.min_days:
                continue

            avg_daily = float(np.mean(daily_counts))
            std_daily = float(np.std(daily_counts)) if total_days > 1 else 0.0
            cv = std_daily / avg_daily if avg_daily > 0 else 0.0

            # Calculate trend
            trend, slope = self._calculate_trend(daily_counts)

            # Recent vs baseline
            recent_days = min(self.recent_window_days, total_days)
            recent_counts = daily_counts[-recent_days:]
            recent_avg = float(np.mean(recent_counts))

            profile = FrequencyProfile(
                device_id=str(device_id),
                total_events=len(device_events),
                total_days=total_days,
                daily_counts=daily_counts,
                avg_daily=avg_daily,
                std_daily=std_daily,
                min_daily=int(min(daily_counts)),
                max_daily=int(max(daily_counts)),
                coefficient_of_variation=cv,
                trend=trend,
                trend_slope=slope,
                recent_avg=recent_avg,
                baseline_avg=avg_daily,
            )

            profiles.append(profile)

        return profiles

    @staticmethod
    def _calculate_trend(daily_counts: list[int]) -> tuple[str, float]:
        """
        Calculate trend direction from daily counts using linear regression.

        Returns:
            Tuple of (trend_direction, slope) where trend_direction is
            'increasing', 'decreasing', or 'stable'.
        """
        if len(daily_counts) < 3:
            return 'stable', 0.0

        x = np.arange(len(daily_counts), dtype=float)
        y = np.array(daily_counts, dtype=float)

        # Simple linear regression
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x * x)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 'stable', 0.0

        slope = float((n * sum_xy - sum_x * sum_y) / denominator)

        # Normalize slope by mean to get relative change per day
        mean_y = float(np.mean(y))
        relative_slope = slope / mean_y if mean_y > 0 else 0.0

        # Threshold for trend detection: >1% per day relative change
        if relative_slope > 0.01:
            return 'increasing', slope
        elif relative_slope < -0.01:
            return 'decreasing', slope
        else:
            return 'stable', slope

    def _detect_change(self, profile: FrequencyProfile) -> FrequencyChange | None:
        """Detect if a significant frequency change occurred."""
        if profile.baseline_avg == 0 and profile.recent_avg == 0:
            return None

        if profile.baseline_avg == 0:
            # Went from nothing to something
            change_ratio = float('inf')
            direction = 'increase'
        elif profile.recent_avg == 0:
            change_ratio = 0.0
            direction = 'decrease'
        else:
            change_ratio = profile.recent_avg / profile.baseline_avg
            direction = 'increase' if change_ratio > 1.0 else 'decrease'

        # Calculate relative change magnitude
        relative_change = abs(change_ratio - 1.0)

        if relative_change < self.change_threshold:
            return None

        confidence = self._calculate_confidence(profile)

        return FrequencyChange(
            device_id=profile.device_id,
            change_ratio=change_ratio,
            direction=direction,
            baseline_avg=profile.baseline_avg,
            recent_avg=profile.recent_avg,
            confidence=confidence,
        )

    def _calculate_confidence(self, profile: FrequencyProfile) -> float:
        """Calculate confidence based on data volume and consistency."""
        # More days = higher confidence (saturates around 30 days)
        day_factor = min(profile.total_days / 30.0, 1.0)

        # Lower CV = more consistent = higher confidence
        if profile.coefficient_of_variation <= 0.3:
            consistency_factor = 1.0
        elif profile.coefficient_of_variation <= 1.0:
            consistency_factor = 1.0 - (profile.coefficient_of_variation - 0.3) / 1.4
        else:
            consistency_factor = max(0.0, 0.5 - (profile.coefficient_of_variation - 1.0) / 4.0)

        # More events = higher confidence (saturates around 100)
        event_factor = min(profile.total_events / 100.0, 1.0)

        return 0.4 * day_factor + 0.35 * consistency_factor + 0.25 * event_factor

    def _build_patterns(
        self, profiles: list[FrequencyProfile]
    ) -> list[dict]:
        """Build pattern dictionaries from profiles."""
        patterns = []

        for profile in profiles:
            change = self._detect_change(profile)
            confidence = self._calculate_confidence(profile)

            if confidence < self.min_confidence:
                continue

            change_detected = change is not None
            variance_score = abs(profile.recent_avg / profile.baseline_avg - 1.0) if profile.baseline_avg > 0 else 0.0

            pattern = {
                'pattern_type': 'frequency',
                'device_id': profile.device_id,
                'avg_daily': float(profile.avg_daily),
                'std_daily': float(profile.std_daily),
                'trend': profile.trend,
                'change_detected': change_detected,
                'variance_score': float(variance_score),
                'confidence': float(confidence),
                'metadata': {
                    'total_events': profile.total_events,
                    'total_days': profile.total_days,
                    'min_daily': profile.min_daily,
                    'max_daily': profile.max_daily,
                    'coefficient_of_variation': float(profile.coefficient_of_variation),
                    'trend_slope': float(profile.trend_slope),
                    'recent_avg': float(profile.recent_avg),
                    'baseline_avg': float(profile.baseline_avg),
                    'domain': self._get_domain(profile.device_id),
                    'thresholds': {
                        'min_days': self.min_days,
                        'min_confidence': self.min_confidence,
                        'change_threshold': self.change_threshold,
                        'recent_window_days': self.recent_window_days,
                    },
                },
            }

            if change_detected and change is not None:
                pattern['metadata']['change'] = {
                    'direction': change.direction,
                    'change_ratio': float(change.change_ratio),
                }

            # Story 40.6: Seasonal decomposition
            if profile.total_days >= 14:
                try:
                    decomp = self.decomposer.decompose(profile.daily_counts)
                    if decomp:
                        pattern['metadata']['seasonal'] = decomp
                        if decomp.get('forecast_7d'):
                            pattern['metadata']['forecast_7d'] = decomp['forecast_7d']
                except Exception as e:
                    logger.debug(f"Seasonal decomposition failed for {profile.device_id}: {e}")

            patterns.append(pattern)

            if change_detected:
                logger.info(
                    f"Frequency change: {profile.device_id} "
                    f"({profile.baseline_avg:.1f}/day -> {profile.recent_avg:.1f}/day, "
                    f"trend={profile.trend}, confidence={confidence:.0%})"
                )

        # Sort: changes first, then by confidence
        patterns.sort(
            key=lambda p: (p['change_detected'], p['confidence']),
            reverse=True,
        )

        return patterns

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """
        Suggest automation from frequency pattern.

        Creates alert-based automations for frequency anomalies.

        Args:
            pattern: Frequency pattern dictionary.

        Returns:
            Automation suggestion dictionary.
        """
        if pattern.get('pattern_type') != 'frequency':
            logger.warning(
                f"Pattern type {pattern.get('pattern_type')} is not frequency"
            )
            return {}

        device_id = pattern.get('device_id', '')
        if not device_id:
            return {}

        if not pattern.get('change_detected', False):
            return {}

        metadata = pattern.get('metadata', {})
        change = metadata.get('change', {})
        confidence = pattern.get('confidence', 0.0)
        direction = change.get('direction', 'unknown')
        baseline = metadata.get('baseline_avg', 0)
        recent = metadata.get('recent_avg', 0)

        description = (
            f"Frequency alert: {device_id} "
            f"({direction} from {baseline:.0f}/day to {recent:.0f}/day)"
        )

        suggestion = {
            'automation_type': 'frequency_alert',
            'trigger': {
                'platform': 'template',
                'value_template': (
                    f"{{{{ states.counter.{device_id.replace('.', '_')}_daily "
                    f"| float > {baseline * 1.5:.0f} }}}}"
                ),
            },
            'action': {
                'service': 'notify.notify',
                'data': {
                    'title': f"Frequency Alert: {device_id}",
                    'message': description,
                },
            },
            'confidence': float(confidence),
            'description': description,
            'device_id': device_id,
            'requires_confirmation': True,
            'safety_level': 'informational',
            'safety_warnings': [],
            'metadata': {
                'source': 'frequency_pattern',
                'direction': direction,
                'baseline_avg': float(baseline),
                'recent_avg': float(recent),
            },
        }

        logger.info(
            f"Suggested frequency alert: {description} "
            f"(confidence={confidence:.0%})"
        )

        return suggestion

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected frequency patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'changes_detected': 0,
                'avg_confidence': 0.0,
                'trends': {},
            }

        trend_counts: dict[str, int] = defaultdict(int)
        for p in patterns:
            trend_counts[p['trend']] += 1

        return {
            'total_patterns': len(patterns),
            'changes_detected': sum(1 for p in patterns if p['change_detected']),
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'avg_daily_across_devices': float(
                np.mean([p['avg_daily'] for p in patterns])
            ),
            'trends': dict(trend_counts),
            'high_frequency_devices': sum(
                1 for p in patterns if p['avg_daily'] > 50
            ),
            'low_frequency_devices': sum(
                1 for p in patterns if p['avg_daily'] < 5
            ),
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
                f"Storing {len(patterns)} frequency aggregates for {date_str}"
            )

            for pattern in patterns:
                try:
                    self.aggregate_client.write_frequency_daily(
                        date=date_str,
                        device_id=pattern.get('device_id', ''),
                        avg_daily=pattern.get('avg_daily', 0.0),
                        trend=pattern.get('trend', 'stable'),
                        change_detected=pattern.get('change_detected', False),
                        confidence=pattern.get('confidence', 0.0),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store aggregate for frequency pattern: {e}",
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
