"""
Seasonal Pattern Detector

Tracks how device activation patterns shift across seasons.
Detects heating/cooling transitions and daylight-dependent behaviors.

Epic 37, Story 37.5: Seasonal Detector for pattern detection expansion.

Algorithm Overview:
    1. Assign each event to an astronomical season
    2. Group events by device and season
    3. Compare activation profiles across seasons
    4. Detect significant seasonal shifts (count, timing, duration)
    5. Gracefully degrade with insufficient data (<90 days)

Example Use Cases:
    - Heating on in winter, off in summer (HVAC transition)
    - Lights turn on earlier in winter (daylight shift)
    - AC usage spikes in summer months
    - Window sensors more active in spring/fall (ventilation)

Configuration:
    - min_days_total: Minimum total days of data (default: 30, ideal: 90+)
    - min_events_per_season: Minimum events per season to compare (default: 10)
    - min_confidence: Minimum confidence threshold (default: 0.7)
    - shift_threshold: Minimum shift to flag as seasonal (default: 0.3)
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

# Astronomical season boundaries (month, day) for Northern Hemisphere
SEASON_BOUNDARIES = {
    'spring': (3, 20),
    'summer': (6, 21),
    'autumn': (9, 22),
    'winter': (12, 21),
}

SEASON_ORDER = ['spring', 'summer', 'autumn', 'winter']


@dataclass
class SeasonalProfile:
    """Activation profile for a single season."""
    season: str
    event_count: int = 0
    day_count: int = 0
    avg_daily_count: float = 0.0
    avg_hour: float = 0.0
    std_hour: float = 0.0
    peak_hour: int = 0


@dataclass
class SeasonalShift:
    """A detected seasonal shift for a device."""
    device_id: str
    profiles: dict[str, SeasonalProfile] = field(default_factory=dict)
    most_active_season: str = ''
    least_active_season: str = ''
    count_shift: float = 0.0
    timing_shift: float = 0.0
    overall_shift: float = 0.0
    confidence: float = 0.0


class SeasonalPatternDetector:
    """
    Detects how device activation patterns shift across seasons.

    Compares activation counts, timing distributions, and peak hours
    across spring, summer, autumn, and winter.
    """

    def __init__(
        self,
        min_days_total: int = 30,
        min_events_per_season: int = 10,
        min_confidence: float = 0.7,
        shift_threshold: float = 0.3,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        self.min_days_total = min_days_total
        self.min_events_per_season = min_events_per_season
        self.min_confidence = min_confidence
        self.shift_threshold = shift_threshold
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client

        logger.info(
            "SeasonalPatternDetector initialized: "
            f"min_days={min_days_total}, min_events_per_season={min_events_per_season}, "
            f"min_confidence={min_confidence}, shift_threshold={shift_threshold}"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect seasonal behavioral patterns.

        Args:
            events: DataFrame with columns [device_id, timestamp, state]

        Returns:
            List of seasonal pattern dictionaries.
        """
        events = self._validate_and_prepare(events)
        if events is None:
            return []

        total_days = (events['timestamp'].max() - events['timestamp'].min()).days + 1
        if total_days < self.min_days_total:
            logger.warning(
                f"Insufficient data span: {total_days} days "
                f"(need {self.min_days_total})"
            )
            return []

        events = events.copy()
        events['season'] = events['timestamp'].apply(self._get_season)

        shifts = self._build_shifts(events)
        patterns = self._build_patterns(shifts, total_days)

        logger.info(f"Detected {len(patterns)} seasonal patterns")

        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _validate_and_prepare(self, events: pd.DataFrame) -> pd.DataFrame | None:
        """Validate input and apply noise filtering. Returns None if invalid."""
        if events.empty:
            logger.warning("No events provided for seasonal detection")
            return None

        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return None

        logger.info(f"Analyzing {len(events)} events for seasonal patterns")

        if self.filter_system_noise:
            original_count = len(events)
            events = self._filter_system_noise(events)
            if len(events) < original_count:
                logger.info(
                    f"Filtered system noise: {original_count} -> {len(events)} events"
                )

        if events.empty:
            return None

        events = events.sort_values('timestamp').copy()
        return events.reset_index(drop=True)

    @staticmethod
    def _get_season(timestamp: pd.Timestamp) -> str:
        """Assign an astronomical season to a timestamp."""
        month, day = timestamp.month, timestamp.day

        if (month, day) >= (12, 21) or (month, day) < (3, 20):
            return 'winter'
        elif (month, day) < (6, 21):
            return 'spring'
        elif (month, day) < (9, 22):
            return 'summer'
        else:
            return 'autumn'

    def _build_shifts(self, events: pd.DataFrame) -> list[SeasonalShift]:
        """Build seasonal shift analysis for each device."""
        shifts: list[SeasonalShift] = []

        for device_id, device_events in events.groupby('device_id'):
            profiles = self._build_seasonal_profiles(device_events)

            # Need at least 2 seasons with sufficient data
            valid_seasons = [
                s for s, p in profiles.items()
                if p.event_count >= self.min_events_per_season
            ]
            if len(valid_seasons) < 2:
                continue

            shift = self._compute_shift(str(device_id), profiles, valid_seasons)
            shifts.append(shift)

        return shifts

    @staticmethod
    def _build_seasonal_profiles(
        device_events: pd.DataFrame,
    ) -> dict[str, SeasonalProfile]:
        """Build activation profiles per season for a device."""
        profiles: dict[str, SeasonalProfile] = {}

        for season, season_events in device_events.groupby('season'):
            profile = SeasonalProfile(season=str(season))
            profile.event_count = len(season_events)

            dates = season_events['timestamp'].dt.date.unique()
            profile.day_count = len(dates)

            profile.avg_daily_count = (
                profile.event_count / profile.day_count
                if profile.day_count > 0 else 0.0
            )

            hours = season_events['timestamp'].dt.hour
            if len(hours) > 0:
                hour_counts = hours.value_counts()
                profile.peak_hour = int(hour_counts.idxmax())
                hour_values = hours.values.astype(float)
                profile.avg_hour = float(np.mean(hour_values))
                profile.std_hour = (
                    float(np.std(hour_values)) if len(hour_values) > 1 else 0.0
                )

            profiles[str(season)] = profile

        return profiles

    def _compute_shift(
        self,
        device_id: str,
        profiles: dict[str, SeasonalProfile],
        valid_seasons: list[str],
    ) -> SeasonalShift:
        """Compute seasonal shift scores."""
        # Count shift: max relative difference in daily counts across seasons
        daily_counts = {
            s: profiles[s].avg_daily_count for s in valid_seasons
        }
        max_count = max(daily_counts.values())
        min_count = min(daily_counts.values())
        count_shift = (
            (max_count - min_count) / max_count if max_count > 0 else 0.0
        )

        most_active = max(valid_seasons, key=lambda s: daily_counts[s])
        least_active = min(valid_seasons, key=lambda s: daily_counts[s])

        # Timing shift: max difference in peak/avg hours
        timing_shift = self._compute_timing_shift(profiles, valid_seasons)

        overall_shift = 0.6 * count_shift + 0.4 * timing_shift

        confidence = self._calculate_confidence(profiles, valid_seasons)

        return SeasonalShift(
            device_id=device_id,
            profiles=profiles,
            most_active_season=most_active,
            least_active_season=least_active,
            count_shift=count_shift,
            timing_shift=timing_shift,
            overall_shift=overall_shift,
            confidence=confidence,
        )

    @staticmethod
    def _compute_timing_shift(
        profiles: dict[str, SeasonalProfile],
        valid_seasons: list[str],
    ) -> float:
        """Compute timing shift across seasons."""
        if len(valid_seasons) < 2:
            return 0.0

        avg_hours = [profiles[s].avg_hour for s in valid_seasons]
        max_diff = 0.0
        for i in range(len(avg_hours)):
            for j in range(i + 1, len(avg_hours)):
                diff = abs(avg_hours[i] - avg_hours[j])
                diff = min(diff, 24 - diff)  # Circular distance
                max_diff = max(max_diff, diff)

        # Normalize: 6-hour shift = 1.0, 0 = 0.0
        return min(max_diff / 6.0, 1.0)

    @staticmethod
    def _calculate_confidence(
        profiles: dict[str, SeasonalProfile],
        valid_seasons: list[str],
    ) -> float:
        """Calculate confidence based on data coverage."""
        # More seasons = higher confidence
        season_factor = len(valid_seasons) / 4.0

        # More events per season = higher confidence (saturates at 50)
        avg_events = np.mean([
            profiles[s].event_count for s in valid_seasons
        ])
        event_factor = min(float(avg_events) / 50.0, 1.0)

        # More days per season = higher confidence (saturates at 30)
        avg_days = np.mean([
            profiles[s].day_count for s in valid_seasons
        ])
        day_factor = min(float(avg_days) / 30.0, 1.0)

        return 0.3 * season_factor + 0.35 * event_factor + 0.35 * day_factor

    def _build_patterns(
        self,
        shifts: list[SeasonalShift],
        total_days: int,
    ) -> list[dict]:
        """Build pattern dictionaries from shifts that meet thresholds."""
        significant = [
            s for s in shifts
            if s.overall_shift >= self.shift_threshold
            and s.confidence >= self.min_confidence
        ]

        patterns = [
            self._shift_to_pattern(shift, total_days)
            for shift in significant
        ]

        patterns.sort(key=lambda p: p['shift_score'], reverse=True)
        return patterns

    def _shift_to_pattern(self, shift: SeasonalShift, total_days: int) -> dict:
        """Convert a single SeasonalShift to a pattern dict."""
        season_profiles = {
            season: self._serialize_profile(profile)
            for season, profile in shift.profiles.items()
        }

        logger.info(
            f"Seasonal pattern: {shift.device_id} "
            f"(most_active={shift.most_active_season}, "
            f"shift={shift.overall_shift:.0%}, "
            f"confidence={shift.confidence:.0%})"
        )

        return {
            'pattern_type': 'seasonal',
            'device_id': shift.device_id,
            'most_active_season': shift.most_active_season,
            'least_active_season': shift.least_active_season,
            'shift_score': float(shift.overall_shift),
            'confidence': float(shift.confidence),
            'season_profiles': season_profiles,
            'metadata': self._build_metadata(shift, total_days),
        }

    @staticmethod
    def _serialize_profile(profile: SeasonalProfile) -> dict:
        """Serialize a SeasonalProfile to a dict."""
        return {
            'event_count': profile.event_count,
            'day_count': profile.day_count,
            'avg_daily_count': float(profile.avg_daily_count),
            'peak_hour': profile.peak_hour,
            'avg_hour': float(profile.avg_hour),
        }

    def _build_metadata(self, shift: SeasonalShift, total_days: int) -> dict:
        """Build metadata dict for a seasonal pattern."""
        return {
            'count_shift': float(shift.count_shift),
            'timing_shift': float(shift.timing_shift),
            'total_days_analyzed': total_days,
            'seasons_with_data': len(shift.profiles),
            'domain': self._get_domain(shift.device_id),
            'data_quality': self._data_quality_label(total_days),
            'thresholds': {
                'min_days_total': self.min_days_total,
                'min_events_per_season': self.min_events_per_season,
                'min_confidence': self.min_confidence,
                'shift_threshold': self.shift_threshold,
            },
        }

    @staticmethod
    def _data_quality_label(total_days: int) -> str:
        """Return data quality label based on total days of data."""
        if total_days >= 365:
            return 'full'
        if total_days >= 180:
            return 'good'
        if total_days >= 90:
            return 'partial'
        return 'limited'

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """Suggest automation from seasonal pattern."""
        if pattern.get('pattern_type') != 'seasonal':
            return {}

        device_id = pattern.get('device_id', '')
        if not device_id:
            return {}

        most_active = pattern.get('most_active_season', '')
        least_active = pattern.get('least_active_season', '')
        confidence = pattern.get('confidence', 0.0)

        domain = self._get_domain(device_id)
        service = self._get_default_service(domain)

        description = (
            f"Seasonal schedule: {device_id} "
            f"(active in {most_active}, reduced in {least_active})"
        )

        suggestion = {
            'automation_type': 'seasonal_schedule',
            'trigger': {
                'platform': 'time',
                'at': '00:00:00',
            },
            'condition': {
                'condition': 'template',
                'value_template': (
                    f"{{{{ now().month in "
                    f"{self._season_months(most_active)} }}}}"
                ),
            },
            'action': {
                'service': f"{domain}.{service}",
                'entity_id': device_id,
                'target': {'entity_id': device_id},
            },
            'confidence': float(confidence),
            'description': description,
            'device_id': device_id,
            'requires_confirmation': True,
            'safety_level': 'normal',
            'safety_warnings': [],
            'metadata': {
                'source': 'seasonal_pattern',
                'most_active_season': most_active,
                'least_active_season': least_active,
                'shift_score': pattern.get('shift_score', 0.0),
            },
        }

        return suggestion

    @staticmethod
    def _season_months(season: str) -> list[int]:
        """Get months belonging to a season."""
        mapping = {
            'spring': [3, 4, 5],
            'summer': [6, 7, 8],
            'autumn': [9, 10, 11],
            'winter': [12, 1, 2],
        }
        return mapping.get(season, [])

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected seasonal patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'avg_shift': 0.0,
                'avg_confidence': 0.0,
                'most_active_seasons': {},
            }

        season_counts: dict[str, int] = defaultdict(int)
        for p in patterns:
            season_counts[p['most_active_season']] += 1

        return {
            'total_patterns': len(patterns),
            'avg_shift': float(np.mean([p['shift_score'] for p in patterns])),
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'most_active_seasons': dict(season_counts),
        }

    @staticmethod
    def _get_domain(device_id: str) -> str:
        if not device_id or '.' not in str(device_id):
            return 'default'
        return str(device_id).split('.', 1)[0]

    def _filter_system_noise(self, events: pd.DataFrame) -> pd.DataFrame:
        if 'device_id' not in events.columns:
            return events
        mask = events['device_id'].apply(self._is_actionable_entity)
        return events[mask].copy()

    def _is_actionable_entity(self, device_id: str) -> bool:
        if not device_id:
            return False
        if self._get_domain(device_id) in EXCLUDED_DOMAINS:
            return False
        if any(device_id.startswith(p) for p in EXCLUDED_ENTITY_PREFIXES):
            return False
        device_lower = device_id.lower()
        return all(pat not in device_lower for pat in EXCLUDED_PATTERNS)

    @staticmethod
    def _get_default_service(domain: str) -> str:
        service_map = {
            'light': 'turn_on', 'switch': 'turn_on', 'fan': 'turn_on',
            'cover': 'open_cover', 'lock': 'lock',
            'climate': 'set_temperature', 'media_player': 'turn_on',
        }
        return service_map.get(domain, 'turn_on')

    def _store_daily_aggregates(
        self, patterns: list[dict], events: pd.DataFrame
    ) -> None:
        try:
            if events.empty or 'timestamp' not in events.columns:
                return
            date_str = events['timestamp'].min().date().strftime("%Y-%m-%d")
            for pattern in patterns:
                try:
                    self.aggregate_client.write_seasonal_daily(
                        date=date_str,
                        device_id=pattern.get('device_id', ''),
                        most_active_season=pattern.get('most_active_season', ''),
                        shift_score=pattern.get('shift_score', 0.0),
                        confidence=pattern.get('confidence', 0.0),
                    )
                except Exception as e:
                    logger.error(f"Failed to store seasonal aggregate: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
