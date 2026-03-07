"""
Contextual Pattern Detector

Correlates device activation patterns with external context factors:
sunrise/sunset timing, weather conditions, and calendar events.

Epic 37, Story 37.8: Contextual Detector for pattern detection expansion.

Algorithm Overview:
    1. Approximate sunrise/sunset from day-of-year (or use provided sun data)
    2. Classify each event relative to sun position (before/after sunrise/sunset)
    3. Detect devices strongly correlated with sun transitions
    4. Optionally correlate with weather data (temperature, conditions)
    5. Score correlations and generate contextual automation suggestions

Example Use Cases:
    - Porch lights turn on within 30 min of sunset
    - Blinds open within 15 min of sunrise
    - Heating increases when outdoor temp drops below threshold
    - Sprinkler system correlates with dry/sunny weather

Configuration:
    - sun_window_minutes: Window around sunrise/sunset to count (default: 60)
    - min_events: Minimum events to establish correlation (default: 10)
    - min_confidence: Minimum confidence threshold (default: 0.7)
    - correlation_threshold: Minimum correlation to flag (default: 0.5)
    - latitude: Location latitude for sun calculations (default: 51.5, London)
    - longitude: Location longitude for sun calculations (default: -0.1)
"""

import logging
import math
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

# Context types detected
CONTEXT_SUNRISE = 'sunrise'
CONTEXT_SUNSET = 'sunset'
CONTEXT_TEMPERATURE = 'temperature'


@dataclass
class SunTimes:
    """Sunrise and sunset times for a specific date."""
    date: str
    sunrise_hour: float
    sunset_hour: float


@dataclass
class ContextCorrelation:
    """A detected correlation between device activity and context."""
    device_id: str
    context_type: str
    correlation_score: float
    avg_offset_minutes: float
    event_count: int
    total_events: int
    confidence: float


class ContextualPatternDetector:
    """
    Detects device activation patterns correlated with external context.

    Correlates activity timing with sunrise/sunset and optionally
    with weather data when available.
    """

    def __init__(
        self,
        sun_window_minutes: int = 60,
        min_events: int = 10,
        min_confidence: float = 0.7,
        correlation_threshold: float = 0.5,
        latitude: float = 51.5,
        longitude: float = -0.1,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        self.sun_window_minutes = sun_window_minutes
        self.min_events = min_events
        self.min_confidence = min_confidence
        self.correlation_threshold = correlation_threshold
        self.latitude = latitude
        self.longitude = longitude
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client

        logger.info(
            "ContextualPatternDetector initialized: "
            f"sun_window={sun_window_minutes}min, "
            f"min_events={min_events}, lat={latitude:.1f}"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect contextual patterns in device events.

        Args:
            events: DataFrame with columns [device_id, timestamp, state].
                    Optional columns: sunrise_hour, sunset_hour, outdoor_temp.

        Returns:
            List of contextual pattern dictionaries.
        """
        events = self._validate_and_prepare(events)
        if events is None:
            return []

        events = self._enrich_with_sun_times(events)

        correlations = self._find_correlations(events)

        patterns = [
            self._correlation_to_pattern(c) for c in correlations
        ]
        patterns.sort(key=lambda p: p['confidence'], reverse=True)

        logger.info(f"Detected {len(patterns)} contextual patterns")

        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _validate_and_prepare(self, events: pd.DataFrame) -> pd.DataFrame | None:
        """Validate input and apply noise filtering."""
        if events.empty:
            logger.warning("No events provided for contextual detection")
            return None

        required_cols = ['device_id', 'timestamp']
        missing = [c for c in required_cols if c not in events.columns]
        if missing:
            logger.error(f"Missing required columns: {missing}")
            return None

        logger.info(f"Analyzing {len(events)} events for contextual patterns")

        if self.filter_system_noise:
            original_count = len(events)
            events = self._filter_system_noise(events)
            if len(events) < original_count:
                logger.info(
                    f"Filtered noise: {original_count} -> {len(events)} events"
                )

        if events.empty:
            return None

        events = events.sort_values('timestamp').copy()
        return events.reset_index(drop=True)

    def _enrich_with_sun_times(self, events: pd.DataFrame) -> pd.DataFrame:
        """Add sunrise/sunset hours to events if not already present."""
        events = events.copy()

        if 'sunrise_hour' not in events.columns:
            events['sunrise_hour'] = events['timestamp'].apply(
                lambda ts: self._approx_sunrise(ts.timetuple().tm_yday)
            )
        if 'sunset_hour' not in events.columns:
            events['sunset_hour'] = events['timestamp'].apply(
                lambda ts: self._approx_sunset(ts.timetuple().tm_yday)
            )

        events['event_hour'] = (
            events['timestamp'].dt.hour
            + events['timestamp'].dt.minute / 60.0
        )
        events['sunrise_offset'] = (
            (events['event_hour'] - events['sunrise_hour']) * 60
        )
        events['sunset_offset'] = (
            (events['event_hour'] - events['sunset_hour']) * 60
        )
        events['event_date'] = events['timestamp'].dt.date

        return events

    def _find_correlations(
        self, events: pd.DataFrame
    ) -> list[ContextCorrelation]:
        """Find all significant context correlations across devices."""
        correlations: list[ContextCorrelation] = []

        for device_id, dev_events in events.groupby('device_id'):
            if len(dev_events) < self.min_events:
                continue

            sunrise_corr = self._check_sun_correlation(
                str(device_id), dev_events, CONTEXT_SUNRISE
            )
            if sunrise_corr is not None:
                correlations.append(sunrise_corr)

            sunset_corr = self._check_sun_correlation(
                str(device_id), dev_events, CONTEXT_SUNSET
            )
            if sunset_corr is not None:
                correlations.append(sunset_corr)

            if 'outdoor_temp' in dev_events.columns:
                temp_corr = self._check_temp_correlation(
                    str(device_id), dev_events
                )
                if temp_corr is not None:
                    correlations.append(temp_corr)

        return correlations

    def _check_sun_correlation(
        self,
        device_id: str,
        dev_events: pd.DataFrame,
        context_type: str,
    ) -> ContextCorrelation | None:
        """Check if device activity correlates with sunrise or sunset."""
        offset_col = f"{context_type}_offset"
        window = self.sun_window_minutes

        near_sun = dev_events[dev_events[offset_col].abs() <= window]
        near_count = len(near_sun)
        total = len(dev_events)

        if near_count < self.min_events:
            return None

        correlation = near_count / total
        if correlation < self.correlation_threshold:
            return None

        avg_offset = float(near_sun[offset_col].mean())
        confidence = self._calculate_sun_confidence(
            near_count, total, near_sun[offset_col].std()
        )

        if confidence < self.min_confidence:
            return None

        return ContextCorrelation(
            device_id=device_id,
            context_type=context_type,
            correlation_score=correlation,
            avg_offset_minutes=avg_offset,
            event_count=near_count,
            total_events=total,
            confidence=confidence,
        )

    def _check_temp_correlation(
        self,
        device_id: str,
        dev_events: pd.DataFrame,
    ) -> ContextCorrelation | None:
        """Check if device activity correlates with temperature."""
        temps = dev_events['outdoor_temp'].dropna()
        if len(temps) < self.min_events:
            return None

        daily = dev_events.groupby('event_date').agg(
            count=('device_id', 'size'),
            avg_temp=('outdoor_temp', 'mean'),
        ).dropna()

        if len(daily) < 7:
            return None

        corr_val = self._safe_correlation(
            daily['count'].values, daily['avg_temp'].values
        )
        abs_corr = abs(corr_val)

        if abs_corr < self.correlation_threshold:
            return None

        confidence = self._calculate_temp_confidence(len(daily), abs_corr)
        if confidence < self.min_confidence:
            return None

        return ContextCorrelation(
            device_id=device_id,
            context_type=CONTEXT_TEMPERATURE,
            correlation_score=corr_val,
            avg_offset_minutes=0.0,
            event_count=len(temps),
            total_events=len(dev_events),
            confidence=confidence,
        )

    def _correlation_to_pattern(self, corr: ContextCorrelation) -> dict:
        """Convert a ContextCorrelation to a pattern dict."""
        description = self._build_description(corr)

        return {
            'pattern_type': 'contextual',
            'device_id': corr.device_id,
            'context_type': corr.context_type,
            'correlation_score': float(corr.correlation_score),
            'confidence': float(corr.confidence),
            'metadata': {
                'avg_offset_minutes': float(corr.avg_offset_minutes),
                'events_in_window': corr.event_count,
                'total_events': corr.total_events,
                'domain': self._get_domain(corr.device_id),
                'description': description,
                'thresholds': {
                    'sun_window_minutes': self.sun_window_minutes,
                    'min_events': self.min_events,
                    'min_confidence': self.min_confidence,
                    'correlation_threshold': self.correlation_threshold,
                },
            },
        }

    @staticmethod
    def _build_description(corr: ContextCorrelation) -> str:
        """Build a human-readable description of a correlation."""
        if corr.context_type in (CONTEXT_SUNRISE, CONTEXT_SUNSET):
            offset = corr.avg_offset_minutes
            before_after = "after" if offset >= 0 else "before"
            mins = abs(int(offset))
            return (
                f"{corr.device_id} activates ~{mins}min "
                f"{before_after} {corr.context_type}"
            )
        if corr.context_type == CONTEXT_TEMPERATURE:
            direction = "increases" if corr.correlation_score > 0 else "decreases"
            return (
                f"{corr.device_id} usage {direction} with temperature"
            )
        return f"{corr.device_id} correlates with {corr.context_type}"

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """Suggest automation from contextual pattern."""
        if pattern.get('pattern_type') != 'contextual':
            return {}

        device_id = pattern.get('device_id', '')
        if not device_id:
            return {}

        context_type = pattern.get('context_type', '')
        confidence = pattern.get('confidence', 0.0)
        metadata = pattern.get('metadata', {})

        domain = self._get_domain(device_id)
        service = self._get_default_service(domain)

        trigger = self._build_trigger(context_type, metadata)
        description = metadata.get('description', f"Contextual: {device_id}")

        return {
            'automation_type': 'contextual_trigger',
            'trigger': trigger,
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
                'source': 'contextual_pattern',
                'context_type': context_type,
                'correlation_score': pattern.get('correlation_score', 0.0),
            },
        }

    @staticmethod
    def _build_trigger(context_type: str, metadata: dict) -> dict:
        """Build automation trigger based on context type."""
        if context_type in (CONTEXT_SUNRISE, CONTEXT_SUNSET):
            offset_min = int(metadata.get('avg_offset_minutes', 0))
            return {
                'platform': 'sun',
                'event': context_type,
                'offset': f"00:{abs(offset_min):02d}:00"
                if offset_min >= 0
                else f"-00:{abs(offset_min):02d}:00",
            }
        if context_type == CONTEXT_TEMPERATURE:
            return {
                'platform': 'numeric_state',
                'entity_id': 'sensor.outdoor_temperature',
                'above': 0,
            }
        return {'platform': 'state'}

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected contextual patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'avg_confidence': 0.0,
                'context_types': {},
            }

        type_counts: dict[str, int] = {}
        for p in patterns:
            ct = p.get('context_type', 'unknown')
            type_counts[ct] = type_counts.get(ct, 0) + 1

        return {
            'total_patterns': len(patterns),
            'avg_confidence': float(
                np.mean([p['confidence'] for p in patterns])
            ),
            'context_types': type_counts,
        }

    def _approx_sunrise(self, day_of_year: int) -> float:
        """Approximate sunrise hour for a given day of year."""
        return self._approx_sun_event(day_of_year, is_sunrise=True)

    def _approx_sunset(self, day_of_year: int) -> float:
        """Approximate sunset hour for a given day of year."""
        return self._approx_sun_event(day_of_year, is_sunrise=False)

    def _approx_sun_event(
        self, day_of_year: int, *, is_sunrise: bool
    ) -> float:
        """
        Approximate sunrise/sunset hour using simplified solar calculation.

        Uses the NOAA simplified equation for solar noon and day length.
        Accurate to ~15 minutes for mid-latitudes.
        """
        lat_rad = math.radians(self.latitude)

        # Solar declination (simplified)
        declination = 23.45 * math.sin(
            math.radians(360 / 365 * (day_of_year - 81))
        )
        decl_rad = math.radians(declination)

        # Hour angle at sunrise/sunset
        cos_ha = -math.tan(lat_rad) * math.tan(decl_rad)
        cos_ha = max(-1.0, min(1.0, cos_ha))  # Clamp for polar regions
        ha_degrees = math.degrees(math.acos(cos_ha))

        # Day length in hours
        day_length = 2 * ha_degrees / 15.0

        # Approximate solar noon (12:00 adjusted for longitude)
        solar_noon = 12.0 - self.longitude / 15.0

        if is_sunrise:
            return solar_noon - day_length / 2.0
        return solar_noon + day_length / 2.0

    @staticmethod
    def _calculate_sun_confidence(
        near_count: int, total: int, offset_std: float
    ) -> float:
        """Calculate confidence for sun correlation."""
        # Volume factor: saturates at 30 events near sun event
        volume = min(near_count / 30.0, 1.0)

        # Consistency: lower std = higher confidence (saturates at 10 min std)
        std_val = float(offset_std) if not np.isnan(offset_std) else 60.0
        consistency = max(0.0, 1.0 - std_val / 60.0)

        # Ratio factor
        ratio = near_count / total if total > 0 else 0.0

        return 0.3 * volume + 0.35 * consistency + 0.35 * ratio

    @staticmethod
    def _calculate_temp_confidence(day_count: int, abs_corr: float) -> float:
        """Calculate confidence for temperature correlation."""
        volume = min(day_count / 30.0, 1.0)
        strength = abs_corr
        return 0.4 * volume + 0.6 * strength

    @staticmethod
    def _safe_correlation(x: np.ndarray, y: np.ndarray) -> float:
        """Compute Pearson correlation, returning 0.0 on error."""
        if len(x) < 3:
            return 0.0
        std_x = np.std(x)
        std_y = np.std(y)
        if std_x == 0 or std_y == 0:
            return 0.0
        corr_matrix = np.corrcoef(x, y)
        val = float(corr_matrix[0, 1])
        return val if not np.isnan(val) else 0.0

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
                    self.aggregate_client.write_contextual_daily(
                        date=date_str,
                        device_id=pattern.get('device_id', ''),
                        context_type=pattern.get('context_type', ''),
                        correlation_score=pattern.get('correlation_score', 0.0),
                        confidence=pattern.get('confidence', 0.0),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store contextual aggregate: {e}",
                        exc_info=True,
                    )
        except Exception as e:
            logger.error(
                f"Error storing daily aggregates: {e}", exc_info=True
            )
