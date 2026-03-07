"""
Sequence Pattern Detector

Detects sequential device activations (A → B → C patterns).
Finds consistent chains of events that happen in the same order.

Epic 37, Story 37.1: Sequence Detector for pattern detection expansion.

Algorithm Overview:
    1. Sort events by timestamp
    2. Use sliding window to extract candidate sequences
    3. Count sequence occurrences (including subsequences)
    4. Calculate confidence based on completion rate
    5. Adjust confidence by timing consistency
    6. Filter by min_occurrences and min_confidence thresholds

Example Use Cases:
    - Morning routine: bedroom light → bathroom light → coffee maker
    - Arrival sequence: garage door → hallway motion → living room light
    - Security pattern: door sensor → alarm panel → notification

Configuration:
    - window_minutes: Total time window for sequence (default: 30)
    - gap_tolerance_minutes: Max gap between consecutive steps (default: 5)
    - min_occurrences: Minimum times sequence must occur (default: 3)
    - min_confidence: Minimum confidence threshold (default: 0.7)
"""

import logging
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Reuse filter constants from co_occurrence
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


class SequencePatternDetector:
    """
    Detects sequential device activation patterns.
    Finds chains like: motion sensor → light → thermostat.

    Examples:
        - Garage door opens → Interior door opens → Kitchen light on
        - Motion in hallway → Living room light on → TV turns on
        - Wake up routine: Bedroom light → Bathroom light → Coffee maker
    """

    def __init__(
        self,
        min_occurrences: int = 3,
        min_confidence: float = 0.7,
        window_minutes: int = 30,
        gap_tolerance_minutes: int = 5,
        min_sequence_length: int = 2,
        max_sequence_length: int = 5,
        filter_system_noise: bool = True,
        aggregate_client: Any = None,
    ):
        """
        Initialize sequence detector.

        Args:
            min_occurrences: Minimum times a sequence must occur (default: 3)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.7)
            window_minutes: Total time window for sequence (default: 30 minutes)
            gap_tolerance_minutes: Max time between consecutive steps (default: 5 minutes)
            min_sequence_length: Minimum devices in sequence (default: 2)
            max_sequence_length: Maximum devices in sequence (default: 5)
            filter_system_noise: Filter out system sensors/trackers (default: True)
            aggregate_client: PatternAggregateClient for storing daily aggregates
        """
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence
        self.window_minutes = window_minutes
        self.gap_tolerance_minutes = gap_tolerance_minutes
        self.min_sequence_length = min_sequence_length
        self.max_sequence_length = max_sequence_length
        self.filter_system_noise = filter_system_noise
        self.aggregate_client = aggregate_client

        logger.info(
            "SequencePatternDetector initialized: "
            f"min_occurrences={min_occurrences}, min_confidence={min_confidence}, "
            f"window={window_minutes}min, gap_tolerance={gap_tolerance_minutes}min, "
            f"seq_length={min_sequence_length}-{max_sequence_length}"
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect sequential device activation patterns.

        Args:
            events: DataFrame with columns [device_id, timestamp, state]
                    device_id: str - Device identifier (e.g., "light.bedroom")
                    timestamp: datetime - Event timestamp
                    state: str - Device state (e.g., "on", "off")

        Returns:
            List of sequence pattern dictionaries with keys:
                - pattern_type: "sequence"
                - device_id: First device in sequence (for compatibility)
                - sequence: List of device IDs in order
                - occurrences: Number of times sequence occurred
                - confidence: Confidence score
                - avg_step_times: Average time between each step (seconds)
                - total_duration: Average total sequence duration (seconds)
                - metadata: Additional pattern metadata
        """
        if events.empty:
            logger.warning("No events provided for sequence detection")
            return []

        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        logger.info(f"Analyzing {len(events)} events for sequence patterns")

        # Filter system noise
        if self.filter_system_noise:
            original_count = len(events)
            events = self._filter_system_noise(events)
            if len(events) < original_count:
                logger.info(
                    f"Filtered system noise: {original_count} → {len(events)} events"
                )

        if events.empty or len(events) < self.min_sequence_length:
            logger.warning("Insufficient events after filtering")
            return []

        # Sort by timestamp
        events = events.sort_values('timestamp').copy()
        events = events.reset_index(drop=True)

        # Extract sequences using sliding window
        sequences = self._extract_sequences(events)

        # Count sequence occurrences
        sequence_counts = self._count_sequences(sequences)

        # Build patterns from frequent sequences
        patterns = self._build_patterns(sequence_counts, events)

        logger.info(f"Detected {len(patterns)} sequence patterns")

        # Store aggregates if client provided
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _extract_sequences(
        self, events: pd.DataFrame
    ) -> list[tuple[tuple[str, ...], list[float]]]:
        """
        Extract all potential sequences from events using sliding window.

        Iterates through each event as a potential sequence start, then builds
        sequences by following subsequent events within gap_tolerance. Sequences
        are terminated when gap exceeds tolerance or max_sequence_length is reached.

        Args:
            events: Sorted DataFrame with device_id and timestamp columns.

        Returns:
            List of (sequence_tuple, step_times) pairs where:
            - sequence_tuple: Tuple of device IDs in order
            - step_times: List of time deltas (seconds) between steps
        """
        sequences = []
        gap_tolerance = pd.Timedelta(minutes=self.gap_tolerance_minutes)
        window_duration = pd.Timedelta(minutes=self.window_minutes)

        n_events = len(events)

        for start_idx in range(n_events):
            start_event = events.iloc[start_idx]
            start_time = start_event['timestamp']
            window_end = start_time + window_duration

            # Build sequence from this starting point
            current_sequence = [start_event['device_id']]
            step_times = []
            last_time = start_time

            for next_idx in range(start_idx + 1, n_events):
                next_event = events.iloc[next_idx]
                next_time = next_event['timestamp']

                # Check if within window
                if next_time > window_end:
                    break

                # Check gap tolerance
                time_gap = next_time - last_time
                if time_gap > gap_tolerance:
                    # Gap too large, save current sequence and start new one
                    if len(current_sequence) >= self.min_sequence_length:
                        seq_tuple = tuple(current_sequence)
                        sequences.append((seq_tuple, step_times.copy()))
                    break

                # Skip if same device (no self-loops)
                if next_event['device_id'] == current_sequence[-1]:
                    continue

                # Add to sequence
                step_times.append(time_gap.total_seconds())
                current_sequence.append(next_event['device_id'])
                last_time = next_time

                # Check max length
                if len(current_sequence) >= self.max_sequence_length:
                    break

            # Save final sequence if valid
            if len(current_sequence) >= self.min_sequence_length:
                seq_tuple = tuple(current_sequence)
                sequences.append((seq_tuple, step_times.copy()))

        return sequences

    def _count_sequences(
        self, sequences: list[tuple[tuple[str, ...], list[float]]]
    ) -> dict[tuple[str, ...], dict]:
        """
        Count occurrences and aggregate timing statistics for each unique sequence.

        Also counts all valid subsequences to capture partial pattern matches.
        For example, A→B→C also counts as A→B and B→C patterns.

        Args:
            sequences: List of (sequence_tuple, step_times) pairs from extraction.

        Returns:
            Dictionary mapping sequence tuples to statistics dict containing:
            - count: Number of occurrences
            - step_times: List of step time lists for variance calculation
            - total_durations: List of total sequence durations
        """
        sequence_data: dict[tuple[str, ...], dict] = defaultdict(
            lambda: {
                'count': 0,
                'step_times': [],  # List of step time lists
                'total_durations': [],
            }
        )

        for seq_tuple, step_times in sequences:
            # Also count all subsequences of length >= min_sequence_length
            for length in range(self.min_sequence_length, len(seq_tuple) + 1):
                for start in range(len(seq_tuple) - length + 1):
                    subseq = seq_tuple[start:start + length]
                    substep_times = step_times[start:start + length - 1] if step_times else []

                    sequence_data[subseq]['count'] += 1
                    if substep_times:
                        sequence_data[subseq]['step_times'].append(substep_times)
                        sequence_data[subseq]['total_durations'].append(sum(substep_times))

        return dict(sequence_data)

    def _build_patterns(
        self,
        sequence_counts: dict[tuple[str, ...], dict],
        events: pd.DataFrame
    ) -> list[dict]:
        """
        Build pattern dictionaries from counted sequences.

        Filters sequences by min_occurrences and min_confidence thresholds.
        Calculates timing statistics and adjusts confidence by timing consistency.

        Args:
            sequence_counts: Dictionary from _count_sequences with occurrence data.
            events: Original events DataFrame for confidence calculation.

        Returns:
            List of pattern dictionaries sorted by confidence (descending).
        """
        patterns = []

        for sequence, data in sequence_counts.items():
            count = data['count']

            if count < self.min_occurrences:
                continue

            # Calculate confidence based on occurrence consistency
            # Higher counts relative to opportunities = higher confidence
            first_device = sequence[0]
            first_device_count = len(events[events['device_id'] == first_device])

            if first_device_count == 0:
                continue

            # Confidence: how often does this sequence complete when first device fires?
            confidence = min(count / first_device_count, 1.0)

            if confidence < self.min_confidence:
                continue

            # Calculate timing statistics
            step_times_list = data['step_times']
            total_durations = data['total_durations']

            avg_step_times = []
            step_time_stds = []

            if step_times_list:
                # Transpose to get times per step
                n_steps = len(sequence) - 1
                for step_idx in range(n_steps):
                    step_values = [
                        st[step_idx]
                        for st in step_times_list
                        if len(st) > step_idx
                    ]
                    if step_values:
                        avg_step_times.append(float(np.mean(step_values)))
                        step_time_stds.append(float(np.std(step_values)))
                    else:
                        avg_step_times.append(0.0)
                        step_time_stds.append(0.0)

            avg_total_duration = float(np.mean(total_durations)) if total_durations else 0.0
            std_total_duration = float(np.std(total_durations)) if len(total_durations) > 1 else 0.0

            # Calculate timing consistency score
            timing_consistency = self._calculate_timing_consistency(step_time_stds, avg_step_times)

            # Adjust confidence based on timing consistency
            adjusted_confidence = confidence * (0.7 + 0.3 * timing_consistency)
            adjusted_confidence = min(adjusted_confidence, 1.0)

            pattern = {
                'pattern_type': 'sequence',
                'device_id': sequence[0],  # First device for compatibility
                'sequence': list(sequence),
                'occurrences': count,
                'confidence': float(adjusted_confidence),
                'avg_step_times': avg_step_times,
                'total_duration': avg_total_duration,
                'metadata': {
                    'sequence_length': len(sequence),
                    'first_device_count': first_device_count,
                    'raw_confidence': float(confidence),
                    'timing_consistency': float(timing_consistency),
                    'step_time_stds': step_time_stds,
                    'std_total_duration': std_total_duration,
                    'sequence_str': ' → '.join(sequence),
                    'thresholds': {
                        'min_occurrences': self.min_occurrences,
                        'min_confidence': self.min_confidence,
                        'window_minutes': self.window_minutes,
                        'gap_tolerance_minutes': self.gap_tolerance_minutes,
                    }
                }
            }

            patterns.append(pattern)

            logger.info(
                f"✅ Sequence pattern: {' → '.join(sequence)} "
                f"({count} times, {adjusted_confidence:.0%} confidence, "
                f"avg_duration={avg_total_duration:.1f}s)"
            )

        # Sort by confidence descending
        patterns.sort(key=lambda p: p['confidence'], reverse=True)

        return patterns

    def _calculate_timing_consistency(
        self,
        step_stds: list[float],
        step_avgs: list[float]
    ) -> float:
        """
        Calculate timing consistency score (0-1).
        Lower variance relative to mean = higher consistency.
        """
        if not step_stds or not step_avgs:
            return 0.5  # Neutral if no timing data

        consistency_scores = []
        for std, avg in zip(step_stds, step_avgs, strict=True):
            if avg > 0:
                # Coefficient of variation (CV) - lower is more consistent
                cv = std / avg
                # Convert CV to consistency score (CV of 0 = 1.0, CV of 1 = 0.5, CV of 2+ = low)
                score = max(0.0, 1.0 - cv / 2)
                consistency_scores.append(score)
            else:
                consistency_scores.append(0.5)

        return float(np.mean(consistency_scores)) if consistency_scores else 0.5

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

    def _store_daily_aggregates(
        self, patterns: list[dict], events: pd.DataFrame
    ) -> None:
        """Store daily aggregates to InfluxDB."""
        try:
            if events.empty or 'timestamp' not in events.columns:
                return

            date = events['timestamp'].min().date()
            date_str = date.strftime("%Y-%m-%d")

            logger.info(f"Storing {len(patterns)} sequence aggregates for {date_str}")

            for pattern in patterns:
                try:
                    sequence = pattern.get('sequence', [])
                    self.aggregate_client.write_sequence_daily(
                        date=date_str,
                        sequence=sequence,
                        occurrences=pattern.get('occurrences', 0),
                        confidence=pattern.get('confidence', 0.0),
                        avg_duration=pattern.get('total_duration', 0.0),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store aggregate for sequence: {e}",
                        exc_info=True
                    )

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """Get summary statistics for detected patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'unique_sequences': 0,
                'avg_confidence': 0.0,
                'avg_sequence_length': 0.0,
                'avg_duration': 0.0,
            }

        return {
            'total_patterns': len(patterns),
            'unique_sequences': len(patterns),
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'avg_sequence_length': float(np.mean([len(p['sequence']) for p in patterns])),
            'avg_duration': float(np.mean([p['total_duration'] for p in patterns])),
            'min_confidence': float(np.min([p['confidence'] for p in patterns])),
            'max_confidence': float(np.max([p['confidence'] for p in patterns])),
            'sequence_lengths': {
                '2-step': sum(1 for p in patterns if len(p['sequence']) == 2),
                '3-step': sum(1 for p in patterns if len(p['sequence']) == 3),
                '4-step': sum(1 for p in patterns if len(p['sequence']) == 4),
                '5-step': sum(1 for p in patterns if len(p['sequence']) >= 5),
            },
            'confidence_distribution': {
                '70-80%': sum(1 for p in patterns if 0.7 <= p['confidence'] < 0.8),
                '80-90%': sum(1 for p in patterns if 0.8 <= p['confidence'] < 0.9),
                '90-100%': sum(1 for p in patterns if 0.9 <= p['confidence'] <= 1.0),
            }
        }

    def suggest_automation(self, pattern: dict) -> dict[str, Any]:
        """
        Suggest automation from sequence pattern.

        Converts sequence patterns to trigger-based automation suggestions.
        First device in sequence triggers the remaining devices.

        Args:
            pattern: Sequence pattern dictionary

        Returns:
            Automation suggestion dictionary
        """
        if pattern.get('pattern_type') != 'sequence':
            logger.warning(f"Pattern type {pattern.get('pattern_type')} is not sequence")
            return {}

        sequence = pattern.get('sequence', [])
        if len(sequence) < 2:
            return {}

        trigger_device = sequence[0]
        action_devices = sequence[1:]
        avg_step_times = pattern.get('avg_step_times', [])
        confidence = pattern.get('confidence', 0.0)

        # Extract domains
        trigger_domain = self._get_domain(trigger_device)

        # Build actions with delays
        actions = []
        cumulative_delay = 0

        for i, device in enumerate(action_devices):
            domain = self._get_domain(device)
            service = self._get_default_service(domain)

            action: dict[str, Any] = {
                'service': f"{domain}.{service}",
                'entity_id': device,
                'target': {'entity_id': device},
            }

            # Add delay if we have timing data
            if i < len(avg_step_times):
                cumulative_delay += avg_step_times[i]
                if cumulative_delay > 0:
                    action['delay'] = {'seconds': int(cumulative_delay)}

            actions.append(action)

        # Build description
        sequence_str = pattern.get('metadata', {}).get('sequence_str', ' → '.join(sequence))
        description = f"Sequence automation: {sequence_str}"

        # Determine trigger type based on domain
        trigger = self._build_trigger(trigger_device, trigger_domain)

        suggestion = {
            'automation_type': 'sequence',
            'trigger': trigger,
            'action': actions if len(actions) > 1 else actions[0],
            'confidence': float(confidence),
            'description': description,
            'device_id': trigger_device,
            'requires_confirmation': False,
            'safety_level': 'normal',
            'safety_warnings': [],
            'metadata': {
                'source': 'sequence_pattern',
                'sequence': sequence,
                'occurrences': pattern.get('occurrences', 0),
                'avg_duration': pattern.get('total_duration', 0.0),
            }
        }

        logger.info(
            f"✅ Suggested sequence automation: {description} "
            f"(confidence={confidence:.0%})"
        )

        return suggestion

    def _build_trigger(self, device_id: str, domain: str) -> dict:
        """Build appropriate trigger based on device domain."""
        if domain == 'binary_sensor':
            return {
                'platform': 'state',
                'entity_id': device_id,
                'to': 'on',
            }
        elif domain in ('sensor', 'input_number'):
            return {
                'platform': 'state',
                'entity_id': device_id,
            }
        elif domain in ('light', 'switch', 'fan'):
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

    def _get_default_service(self, domain: str) -> str:
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
