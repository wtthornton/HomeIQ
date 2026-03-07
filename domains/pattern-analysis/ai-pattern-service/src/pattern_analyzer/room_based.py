"""
Room-Based Pattern Detector

Correlates device activity within the same area/room using area_id.
Detects room-level behavioral patterns like "living room evening routine".

Epic 37, Story 37.4: Room-Based Detector for pattern detection expansion.

Algorithm Overview:
    1. Group events by area_id (fall back to entity_id prefix if unavailable)
    2. Within each room, find co-occurring events in 2-minute windows
    3. Build room activity profiles (which devices activate together)
    4. Detect recurring room-level routines by time of day
    5. Calculate confidence based on consistency of co-activation

Example Use Cases:
    - Living room evening: TV + ambient light + thermostat adjust
    - Bedroom morning: light on + blinds open + alarm off
    - Kitchen cooking: range hood + kitchen light + exhaust fan
    - Bathroom routine: light + fan + water heater

Configuration:
    - window_minutes: Co-occurrence window within room (default: 2)
    - min_occurrences: Minimum times pattern must occur (default: 3)
    - min_confidence: Minimum confidence threshold (default: 0.7)
    - min_devices: Minimum devices in room pattern (default: 2)
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

# Time-of-day period definitions (hour ranges)
TIME_PERIODS = {
    'night': (0, 6),
    'morning': (6, 12),
    'afternoon': (12, 17),
    'evening': (17, 22),
    'late_night': (22, 24),
}


@dataclass
class RoomActivityWindow:
    """A window of co-occurring device activity in a room."""
    area_id: str
    devices: frozenset[str]
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    period: str


@dataclass
class RoomRoutine:
    """A detected room-level routine pattern."""
    area_id: str
    devices: frozenset[str]
    period: str
    occurrences: int
    avg_hour: float
    std_hour: float
    confidence: float
    hours: list[float] = field(default_factory=list)


class RoomBasedPatternDetector:
    """
    Detects room-level behavioral patterns by correlating device
    activity within the same area/room.

    Groups co-occurring events by area_id and detects recurring
    routines like "living room evening" or "bedroom morning".
    """

    def __init__(
        self,
        window_minutes: float = 2.0,
        min_occurrences: int = 3,
        min_confidence: float = 0.7,
        min_devices: int = 2,
        max_devices: int = 8,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        """
        Initialize room-based pattern detector.

        Args:
            window_minutes: Co-occurrence window within room (default: 2 minutes)
            min_occurrences: Minimum times pattern must occur (default: 3)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.7)
            min_devices: Minimum devices in room pattern (default: 2)
            max_devices: Maximum devices in room pattern (default: 8)
            filter_system_noise: Filter out system sensors/trackers (default: True)
            aggregate_client: PatternAggregateClient for storing daily aggregates
        """
        self.window_minutes = window_minutes
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence
        self.min_devices = min_devices
        self.max_devices = max_devices
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client

        logger.info(
            "RoomBasedPatternDetector initialized: "
            f"window={window_minutes}min, min_occurrences={min_occurrences}, "
            f"min_confidence={min_confidence}, devices={min_devices}-{max_devices}"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect room-level behavioral patterns.

        Args:
            events: DataFrame with columns [device_id, timestamp, state]
                    Optional column: area_id (falls back to entity prefix parsing)

        Returns:
            List of room-based pattern dictionaries with keys:
                - pattern_type: "room_based"
                - area_id: Room/area identifier
                - device_group: List of devices in the pattern
                - period: Time-of-day period (morning, evening, etc.)
                - occurrences: Number of times pattern occurred
                - confidence: Confidence score
                - avg_hour: Average hour of day for pattern
                - metadata: Additional pattern metadata
        """
        if events.empty:
            logger.warning("No events provided for room-based detection")
            return []

        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        logger.info(f"Analyzing {len(events)} events for room-based patterns")

        # Filter system noise
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

        # Ensure area_id column exists
        events = self._ensure_area_id(events)

        # Sort by timestamp
        events = events.sort_values('timestamp').copy()
        events = events.reset_index(drop=True)

        # Group events by area and find co-occurring windows
        activity_windows = self._find_activity_windows(events)

        if not activity_windows:
            logger.info("No room activity windows found")
            return []

        # Detect recurring routines from windows
        routines = self._detect_routines(activity_windows)

        # Build pattern output
        patterns = self._build_patterns(routines)

        logger.info(f"Detected {len(patterns)} room-based patterns")

        # Store aggregates if client provided
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _ensure_area_id(self, events: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure area_id column exists. Falls back to entity_id prefix parsing.

        Extracts room/area from entity ID patterns like:
            light.living_room_lamp -> living_room
            binary_sensor.bedroom_motion -> bedroom
            switch.kitchen_fan -> kitchen
        """
        if 'area_id' in events.columns and events['area_id'].notna().any():
            # Fill missing area_ids with prefix-based fallback
            mask = events['area_id'].isna() | (events['area_id'] == '')
            if mask.any():
                events = events.copy()
                events.loc[mask, 'area_id'] = events.loc[mask, 'device_id'].apply(
                    self._extract_area_from_entity_id
                )
            return events

        # No area_id column - parse from entity IDs
        events = events.copy()
        events['area_id'] = events['device_id'].apply(
            self._extract_area_from_entity_id
        )
        return events

    @staticmethod
    def _extract_area_from_entity_id(entity_id: str) -> str:
        """
        Extract area/room name from entity_id by convention.

        Parses the object_id part (after domain.) and takes the first
        meaningful segment as the area name.

        Examples:
            light.living_room_lamp -> living_room
            binary_sensor.bedroom_motion -> bedroom
            switch.kitchen_exhaust_fan -> kitchen
            climate.upstairs_thermostat -> upstairs
            light.hallway -> hallway
        """
        if not entity_id or '.' not in str(entity_id):
            return 'unknown'

        # Get object_id (after domain.)
        object_id = str(entity_id).split('.', 1)[1]

        # Split by underscore
        parts = object_id.split('_')

        if not parts:
            return 'unknown'

        # Common room names that may be multi-word
        multi_word_rooms = {
            'living_room', 'dining_room', 'family_room', 'laundry_room',
            'guest_room', 'master_bedroom', 'kids_room', 'front_door',
            'back_door', 'side_door', 'front_yard', 'back_yard',
        }

        # Check for two-word room names first
        if len(parts) >= 2:
            two_word = f"{parts[0]}_{parts[1]}"
            if two_word in multi_word_rooms:
                return two_word

        # Single-word room name (first part)
        return parts[0]

    def _find_activity_windows(
        self, events: pd.DataFrame
    ) -> list[RoomActivityWindow]:
        """
        Find co-occurring device activity windows within each room.

        Groups events by area_id and finds clusters of events within
        the configured window duration.

        Args:
            events: Sorted DataFrame with device_id, timestamp, area_id columns.

        Returns:
            List of RoomActivityWindow objects representing co-occurring events.
        """
        windows: list[RoomActivityWindow] = []
        window_delta = pd.Timedelta(minutes=self.window_minutes)

        # Group by area
        for area_id, area_events in events.groupby('area_id'):
            if area_id == 'unknown':
                continue

            area_events = area_events.sort_values('timestamp')
            n_events = len(area_events)

            if n_events < self.min_devices:
                continue

            # Sliding window to find co-occurring events
            i = 0
            while i < n_events:
                window_start = area_events.iloc[i]['timestamp']
                window_end = window_start + window_delta

                # Collect all events within window
                devices_in_window: set[str] = set()
                j = i

                while j < n_events:
                    event_time = area_events.iloc[j]['timestamp']
                    if event_time > window_end:
                        break
                    devices_in_window.add(area_events.iloc[j]['device_id'])
                    j += 1

                # Only keep windows with enough unique devices
                if len(devices_in_window) >= self.min_devices:
                    # Limit to max_devices (keep the most frequent)
                    if len(devices_in_window) > self.max_devices:
                        devices_in_window = set(list(devices_in_window)[:self.max_devices])

                    actual_end = area_events.iloc[min(j - 1, n_events - 1)]['timestamp']
                    period = self._get_time_period(window_start)

                    windows.append(RoomActivityWindow(
                        area_id=str(area_id),
                        devices=frozenset(devices_in_window),
                        start_time=window_start,
                        end_time=actual_end,
                        period=period,
                    ))

                # Advance past this window
                i = max(i + 1, j)

        logger.info(f"Found {len(windows)} room activity windows")
        return windows

    def _detect_routines(
        self, windows: list[RoomActivityWindow]
    ) -> list[RoomRoutine]:
        """
        Detect recurring routines from activity windows.

        Groups windows by (area_id, device_set, period) and counts
        occurrences. Calculates confidence based on consistency.

        Args:
            windows: List of activity windows from _find_activity_windows.

        Returns:
            List of RoomRoutine objects that meet occurrence and confidence thresholds.
        """
        routine_groups = self._group_windows(windows)
        subset_groups = self._expand_subsets(routine_groups)
        routines = self._filter_routines(subset_groups)

        routines.sort(key=lambda r: r.confidence, reverse=True)
        logger.info(f"Detected {len(routines)} recurring room routines")
        return routines

    @staticmethod
    def _group_windows(
        windows: list[RoomActivityWindow],
    ) -> dict[tuple[str, frozenset[str], str], list[RoomActivityWindow]]:
        """Group activity windows by (area_id, device_set, period)."""
        groups: dict[tuple[str, frozenset[str], str], list[RoomActivityWindow]] = defaultdict(list)
        for window in windows:
            key = (window.area_id, window.devices, window.period)
            groups[key].append(window)
        return groups

    def _expand_subsets(
        self,
        routine_groups: dict[tuple[str, frozenset[str], str], list[RoomActivityWindow]],
    ) -> dict[tuple[str, frozenset[str], str], list[RoomActivityWindow]]:
        """Expand routine groups to include device subsets."""
        subset_groups: dict[tuple[str, frozenset[str], str], list[RoomActivityWindow]] = defaultdict(list)

        for (area_id, devices, period), group_windows in routine_groups.items():
            subset_groups[(area_id, devices, period)].extend(group_windows)

            if len(devices) > self.min_devices:
                device_list = sorted(devices)
                for size in range(self.min_devices, len(device_list)):
                    for subset in self._combinations(device_list, size):
                        subset_key = (area_id, frozenset(subset), period)
                        subset_groups[subset_key].extend(group_windows)

        return subset_groups

    def _is_subset_of_seen(
        self,
        area_id: str,
        devices: frozenset[str],
        period: str,
        seen_keys: set[tuple[str, frozenset[str], str]],
    ) -> bool:
        """Check if a device group is a subset of an already-seen group."""
        for seen_area, seen_devices, seen_period in seen_keys:
            if seen_area == area_id and seen_period == period and devices < seen_devices:
                return True
        return False

    def _filter_routines(
        self,
        subset_groups: dict[tuple[str, frozenset[str], str], list[RoomActivityWindow]],
    ) -> list[RoomRoutine]:
        """Filter and build routines from subset groups that meet thresholds."""
        routines: list[RoomRoutine] = []
        seen_keys: set[tuple[str, frozenset[str], str]] = set()

        # Process larger device groups first
        all_groups = sorted(
            subset_groups.items(),
            key=lambda x: len(x[0][1]),
            reverse=True,
        )

        for (area_id, devices, period), group_windows in all_groups:
            if len(group_windows) < self.min_occurrences:
                continue

            key = (area_id, devices, period)
            if key in seen_keys:
                continue

            if self._is_subset_of_seen(area_id, devices, period, seen_keys):
                continue

            routine = self._build_routine(area_id, devices, period, group_windows)
            routine.confidence = self._calculate_confidence(
                occurrences=routine.occurrences,
                std_hour=routine.std_hour,
                n_devices=len(devices),
            )
            if routine.confidence < self.min_confidence:
                continue

            seen_keys.add(key)
            routines.append(routine)

        return routines

    @staticmethod
    def _build_routine(
        area_id: str,
        devices: frozenset[str],
        period: str,
        group_windows: list[RoomActivityWindow],
    ) -> RoomRoutine:
        """Build a RoomRoutine from a group of matching windows."""
        hours = [w.start_time.hour + w.start_time.minute / 60.0 for w in group_windows]
        avg_hour = float(np.mean(hours))
        std_hour = float(np.std(hours)) if len(hours) > 1 else 0.0

        return RoomRoutine(
            area_id=area_id,
            devices=devices,
            period=period,
            occurrences=len(group_windows),
            avg_hour=avg_hour,
            std_hour=std_hour,
            confidence=0.0,  # Placeholder, calculated by caller
            hours=hours,
        )

    @staticmethod
    def _combinations(items: list[str], size: int) -> list[tuple[str, ...]]:
        """Generate combinations of given size from items list."""
        if size == 0:
            return [()]
        if size > len(items):
            return []

        result: list[tuple[str, ...]] = []

        def _backtrack(start: int, current: list[str]) -> None:
            if len(current) == size:
                result.append(tuple(current))
                return
            for i in range(start, len(items)):
                current.append(items[i])
                _backtrack(i + 1, current)
                current.pop()

        _backtrack(0, [])
        return result

    def _calculate_confidence(
        self,
        occurrences: int,
        std_hour: float,
        n_devices: int,
    ) -> float:
        """
        Calculate confidence score for a room routine.

        Factors:
            - Occurrence count (more = higher confidence)
            - Timing consistency (lower std = higher confidence)
            - Number of devices (more devices = slightly higher confidence)
        """
        # Occurrence factor: saturates around 10 occurrences
        occurrence_factor = min(occurrences / 10.0, 1.0)

        # Timing consistency: std_hour of 0 = perfect, >4 hours = poor
        if std_hour <= 0.5:
            timing_factor = 1.0
        elif std_hour <= 2.0:
            timing_factor = 1.0 - (std_hour - 0.5) / 4.5
        else:
            timing_factor = max(0.0, 1.0 - std_hour / 6.0)

        # Device count factor: slight bonus for more devices (2 = baseline)
        device_factor = min(1.0, 0.8 + 0.1 * (n_devices - 1))

        confidence = (
            0.5 * occurrence_factor
            + 0.35 * timing_factor
            + 0.15 * device_factor
        )

        return min(max(confidence, 0.0), 1.0)

    def _build_patterns(self, routines: list[RoomRoutine]) -> list[dict]:
        """
        Build pattern dictionaries from detected routines.

        Args:
            routines: List of RoomRoutine objects.

        Returns:
            List of pattern dictionaries sorted by confidence.
        """
        patterns = []

        for routine in routines:
            device_list = sorted(routine.devices)
            period_range = TIME_PERIODS.get(routine.period, (0, 24))

            pattern = {
                'pattern_type': 'room_based',
                'device_id': device_list[0],  # First device for compatibility
                'area_id': routine.area_id,
                'device_group': device_list,
                'period': routine.period,
                'occurrences': routine.occurrences,
                'confidence': float(routine.confidence),
                'avg_hour': float(routine.avg_hour),
                'metadata': {
                    'n_devices': len(device_list),
                    'std_hour': float(routine.std_hour),
                    'period_range': list(period_range),
                    'routine_label': f"{routine.area_id} {routine.period}",
                    'device_domains': [
                        self._get_domain(d) for d in device_list
                    ],
                    'thresholds': {
                        'window_minutes': self.window_minutes,
                        'min_occurrences': self.min_occurrences,
                        'min_confidence': self.min_confidence,
                        'min_devices': self.min_devices,
                    },
                },
            }

            patterns.append(pattern)

            logger.info(
                f"Room pattern: {routine.area_id} {routine.period} "
                f"({len(device_list)} devices, {routine.occurrences} times, "
                f"{routine.confidence:.0%} confidence)"
            )

        # Sort by confidence descending
        patterns.sort(key=lambda p: p['confidence'], reverse=True)
        return patterns

    @staticmethod
    def _get_time_period(timestamp: pd.Timestamp) -> str:
        """Map a timestamp to a time-of-day period."""
        hour = timestamp.hour
        for period_name, (start, end) in TIME_PERIODS.items():
            if start <= hour < end:
                return period_name
        return 'night'  # fallback

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

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """
        Suggest automation from room-based pattern.

        Creates scene-based automations that activate all devices in a
        room pattern based on a trigger device.

        Args:
            pattern: Room-based pattern dictionary.

        Returns:
            Automation suggestion dictionary.
        """
        if pattern.get('pattern_type') != 'room_based':
            logger.warning(
                f"Pattern type {pattern.get('pattern_type')} is not room_based"
            )
            return {}

        device_group = pattern.get('device_group', [])
        if len(device_group) < 2:
            return {}

        area_id = pattern.get('area_id', 'unknown')
        period = pattern.get('period', 'unknown')
        confidence = pattern.get('confidence', 0.0)

        # First device (typically a sensor/trigger) triggers the rest
        trigger_device = device_group[0]
        action_devices = device_group[1:]
        trigger_domain = self._get_domain(trigger_device)

        # Build actions for each device in the group
        actions = []
        for device in action_devices:
            domain = self._get_domain(device)
            service = self._get_default_service(domain)
            actions.append({
                'service': f"{domain}.{service}",
                'entity_id': device,
                'target': {'entity_id': device},
            })

        description = (
            f"Room routine: {area_id} {period} "
            f"({len(device_group)} devices)"
        )

        trigger = self._build_trigger(trigger_device, trigger_domain)

        suggestion = {
            'automation_type': 'room_routine',
            'trigger': trigger,
            'action': actions if len(actions) > 1 else actions[0],
            'confidence': float(confidence),
            'description': description,
            'device_id': trigger_device,
            'area_id': area_id,
            'requires_confirmation': False,
            'safety_level': 'normal',
            'safety_warnings': [],
            'metadata': {
                'source': 'room_based_pattern',
                'area_id': area_id,
                'period': period,
                'device_group': device_group,
                'occurrences': pattern.get('occurrences', 0),
            },
        }

        logger.info(
            f"Suggested room automation: {description} "
            f"(confidence={confidence:.0%})"
        )

        return suggestion

    @staticmethod
    def _build_trigger(device_id: str, domain: str) -> dict:
        """Build appropriate trigger based on device domain."""
        if domain == 'binary_sensor' or domain in ('light', 'switch', 'fan'):
            return {
                'platform': 'state',
                'entity_id': device_id,
                'to': 'on',
            }
        else:
            return {
                'platform': 'state',
                'entity_id': device_id,
            }

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

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected room-based patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'unique_rooms': 0,
                'avg_confidence': 0.0,
                'avg_devices_per_pattern': 0.0,
                'periods': {},
            }

        rooms = {p['area_id'] for p in patterns}
        period_counts: dict[str, int] = defaultdict(int)
        for p in patterns:
            period_counts[p['period']] += 1

        return {
            'total_patterns': len(patterns),
            'unique_rooms': len(rooms),
            'rooms': sorted(rooms),
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'avg_devices_per_pattern': float(
                np.mean([len(p['device_group']) for p in patterns])
            ),
            'periods': dict(period_counts),
            'confidence_distribution': {
                '70-80%': sum(1 for p in patterns if 0.7 <= p['confidence'] < 0.8),
                '80-90%': sum(1 for p in patterns if 0.8 <= p['confidence'] < 0.9),
                '90-100%': sum(1 for p in patterns if 0.9 <= p['confidence'] <= 1.0),
            },
        }

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
                f"Storing {len(patterns)} room-based aggregates for {date_str}"
            )

            for pattern in patterns:
                try:
                    self.aggregate_client.write_room_daily(
                        date=date_str,
                        area_id=pattern.get('area_id', 'unknown'),
                        device_group=pattern.get('device_group', []),
                        period=pattern.get('period', 'unknown'),
                        occurrences=pattern.get('occurrences', 0),
                        confidence=pattern.get('confidence', 0.0),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store aggregate for room pattern: {e}",
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
