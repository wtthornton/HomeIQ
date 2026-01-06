"""
Co-Occurrence Pattern Detector

Detects devices that are frequently used together within a time window.
Uses simple sliding window approach with association rule mining concepts.

Story AI5.3: Converted to incremental processing with aggregate storage.
Epic 39, Story 39.5: Extracted to ai-pattern-service.
"""

import logging
from collections import defaultdict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# System noise filtering constants (Task 2: Filter System Noise)
# Phase 1: Domain-level exclusions
EXCLUDED_DOMAINS = {
    'image',      # Maps, camera images
    'event',      # System events
    'update',     # Software updates
    'camera',     # Camera entities
    'button',     # Buttons (not automation targets)
}

EXCLUDED_ENTITY_PREFIXES = [
    'sensor.home_assistant_',  # System sensors
    'sensor.slzb_',            # Coordinator sensors
    'image.',                  # Images/maps (Roborock, cameras)
    'event.',                  # System events
    'binary_sensor.system_',   # System binary sensors
    'camera.',                 # Camera entities
    'button.',                 # Button entities
    'update.',                 # Update entities
]

# Patterns to match (using contains check)
EXCLUDED_PATTERNS = [
    '_tracker',                # External API trackers (sports, etc.)
    'team_tracker',            # Sports team tracker entities
    'nfl_', 'nhl_', 'mlb_', 'nba_', 'ncaa_',  # Sports league entities
    'weather_',                # Weather API entities
    'openweathermap_',         # OpenWeatherMap integration
    'carbon_intensity_',       # Carbon intensity API
    'electricity_pricing_',    # Electricity pricing API
    'national_grid_',          # National Grid API
    'calendar_',               # Calendar entities (external events)
    '_cpu_',                   # CPU/monitoring sensors
    '_temp',                   # Temperature sensors (system)
    '_chip_',                  # Chip temperature sensors
    'coordinator_',            # Coordinator-related sensors
    '_battery',                # Battery level sensors
    '_memory_',                # Memory sensors
    '_signal_strength',        # Signal strength
    '_linkquality',            # Zigbee link quality
    '_update_',                # Update status
    '_uptime',                 # Uptime sensors
    '_last_seen',              # Last seen timestamps
]

# Domain categorization for pattern validation
ACTIONABLE_DOMAINS = {
    'light', 'switch', 'climate', 'media_player',
    'lock', 'cover', 'fan', 'vacuum', 'scene'
}

TRIGGER_DOMAINS = {
    'binary_sensor', 'sensor', 'device_tracker',
    'person', 'input_boolean', 'input_select'
}

PASSIVE_DOMAINS = {
    'image', 'camera', 'weather', 'sun', 'event', 'update', 'calendar'
}


class CoOccurrencePatternDetector:
    """
    Detects device co-occurrence patterns.
    Finds devices frequently used together within time window.
    
    Examples:
        - Motion sensor triggers → Light turns on (within 30 seconds)
        - Door opens → Alarm activates (within 2 minutes)
        - Thermostat adjusts → Fan turns on (within 1 minute)
    """

    def __init__(
        self,
        window_minutes: int = 5,
        min_support: int = 5,
        min_confidence: float = 0.7,
        aggregate_client=None,
        filter_system_noise: bool = True,
        max_variance_minutes: float = 30.0,
        domain_support_overrides: dict[str, int] | None = None,
        domain_confidence_overrides: dict[str, float] | None = None,
        feedback_client=None
    ):
        """
        Initialize co-occurrence detector.
        
        Args:
            window_minutes: Time window for co-occurrence (default: 5 minutes)
            min_support: Minimum number of co-occurrences (default: 5)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.7)
            aggregate_client: PatternAggregateClient for storing daily aggregates (Story AI5.3)
            filter_system_noise: Filter out system sensors/trackers/images (default: True) - Task 2
            max_variance_minutes: Maximum time variance in minutes for patterns (default: 30) - Task 3
            feedback_client: Optional FeedbackClient for integrating user feedback (Recommendation 2.1)
        """
        self.window_minutes = window_minutes
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.aggregate_client = aggregate_client
        self.filter_system_noise = filter_system_noise
        self.max_variance_minutes = max_variance_minutes
        self.domain_support_overrides = domain_support_overrides or {}
        self.domain_confidence_overrides = domain_confidence_overrides or {}
        self.feedback_client = feedback_client
        logger.info(
            f"CoOccurrencePatternDetector initialized: "
            f"window={window_minutes}min, min_support={min_support}, min_confidence={min_confidence}, "
            f"filter_system_noise={filter_system_noise}, max_variance={max_variance_minutes}min, "
            f"support_overrides={list((domain_support_overrides or {}).keys())}, "
            f"confidence_overrides={list((domain_confidence_overrides or {}).keys())}, "
            f"feedback_client={'enabled' if feedback_client else 'disabled'}"
        )

    async def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Find devices used together within time window.
        Simple approach: sliding window + counting.
        
        Args:
            events: DataFrame with columns [device_id, timestamp, state]
                    device_id: str - Device identifier
                    timestamp: datetime - Event timestamp
                    state: str - Device state
        
        Returns:
            List of co-occurrence pattern dictionaries with keys:
                - pattern_type: "co_occurrence"
                - device_id: Primary device (for storage compatibility)
                - device1: First device in pair
                - device2: Second device in pair
                - occurrences: Number of co-occurrences
                - total_events: Total events analyzed
                - confidence: Confidence score
                - metadata: Additional statistics
        """
        if events.empty:
            logger.warning("No events provided for co-occurrence detection")
            return []

        # Validate required columns
        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        logger.info(f"Analyzing {len(events)} events for co-occurrence patterns")

        # Task 2: Filter system noise before processing
        if self.filter_system_noise:
            original_count = len(events)
            events = self._filter_system_noise(events)
            filtered_count = len(events)
            if filtered_count < original_count:
                logger.info(
                    f"✅ Filtered system noise: {original_count} → {filtered_count} events "
                    f"({original_count - filtered_count} system events removed)"
                )

        if events.empty:
            logger.warning("No events remaining after filtering for co-occurrence detection")
            return []

        # 1. Sort by time for efficient windowing
        events = events.sort_values('timestamp').copy()
        events = events.reset_index(drop=True)

        # 2. Find co-occurrences using sliding window
        co_occurrences = defaultdict(int)
        device_event_counts = defaultdict(int)

        # Track individual device events for confidence calculation
        for device_id in events['device_id']:
            device_event_counts[device_id] += 1

        # Task 3: Track time deltas for variance calculation
        pair_time_deltas = defaultdict(list)  # Store time deltas for each pair

        # Sliding window approach
        for i, event in events.iterrows():
            device_a = event['device_id']
            timestamp_a = event['timestamp']

            # Look ahead within window
            window_end = timestamp_a + pd.Timedelta(minutes=self.window_minutes)

            # Find nearby events
            nearby_mask = (
                (events['timestamp'] > timestamp_a) &
                (events['timestamp'] <= window_end)
            )
            nearby = events[nearby_mask]

            # Count co-occurrences with different devices
            for _, nearby_event in nearby.iterrows():
                device_b = nearby_event['device_id']

                if device_b != device_a:
                    # Task 2: Filter system noise in pairs (double-check)
                    if self.filter_system_noise:
                        if not self._is_meaningful_automation_pattern(device_a, device_b):
                            continue

                    # Create sorted pair to avoid duplicates (A,B) vs (B,A)
                    pair = tuple(sorted([device_a, device_b]))
                    co_occurrences[pair] += 1

                    # Task 3: Track time delta for variance calculation
                    time_delta = (nearby_event['timestamp'] - timestamp_a).total_seconds()
                    pair_time_deltas[pair].append(time_delta)

        logger.info(f"Found {len(co_occurrences)} unique device pairs")

        # 3. Filter for significant patterns
        patterns = []
        total_events = len(events)

        for (device1, device2), count in co_occurrences.items():
            # Calculate confidence as co-occurrence rate
            # Confidence = co_occurrences / min(device1_events, device2_events)
            device1_count = device_event_counts[device1]
            device2_count = device_event_counts[device2]

            # Support: how often the pair occurs relative to all events
            support = count / total_events

            # Confidence: how reliable the association is
            # Use the smaller device count to get a conservative estimate
            # Cap at 1.0 (100%) to prevent values over 100%
            confidence = min(count / min(device1_count, device2_count), 1.0)

            # Determine dynamic thresholds based on device domains
            domain1 = self._get_domain(device1)
            domain2 = self._get_domain(device2)
            support_threshold = min(
                self._support_threshold_for(domain1),
                self._support_threshold_for(domain2)
            )
            confidence_threshold = min(
                self._confidence_threshold_for(domain1),
                self._confidence_threshold_for(domain2)
            )

            # Filter by thresholds
            if count >= support_threshold and confidence >= confidence_threshold:
                # Quality check: Ensure meaningful automation pattern
                if self.filter_system_noise:
                    if not self._is_meaningful_automation_pattern(device1, device2):
                        logger.debug(
                            f"❌ Rejected pattern {device1}+{device2}: not a meaningful automation pattern"
                        )
                        continue

                # Task 3: Calculate time variance and filter by threshold
                time_deltas = pair_time_deltas.get((device1, device2), [])

                if time_deltas:
                    # Calculate statistics
                    avg_time_delta = float(np.mean(time_deltas))
                    time_variance_seconds = float(np.var(time_deltas))
                    time_variance_minutes = time_variance_seconds / 60.0
                    time_std_seconds = float(np.std(time_deltas))
                    time_std_minutes = time_std_seconds / 60.0

                    # Task 3: Filter patterns with standard deviation > threshold
                    # Note: We check std (not variance) since threshold is in minutes (like "± 30min")
                    if time_std_minutes > self.max_variance_minutes:
                        logger.debug(
                            f"❌ Rejected pattern {device1}+{device2}: std {time_std_minutes:.1f}min "
                            f"> threshold {self.max_variance_minutes}min"
                        )
                        continue
                else:
                    # Fallback to old method if no deltas tracked
                    avg_time_delta = self._calculate_avg_time_delta(
                        events, device1, device2, self.window_minutes
                    )
                    time_variance_minutes = None
                    time_std_minutes = None

                pattern = {
                    'pattern_type': 'co_occurrence',
                    'device_id': f"{device1}+{device2}",  # Combined ID for storage
                    'device1': device1,
                    'device2': device2,
                    'occurrences': int(count),
                    'total_events': int(total_events),
                    'confidence': float(confidence),
                    'metadata': {
                        'window_minutes': self.window_minutes,
                        'support': float(support),
                        'device1_count': int(device1_count),
                        'device2_count': int(device2_count),
                        'avg_time_delta_seconds': float(avg_time_delta) if avg_time_delta is not None else None,
                        'time_variance_minutes': float(time_variance_minutes) if time_variance_minutes is not None else None,
                        'time_std_minutes': float(time_std_minutes) if time_std_minutes is not None else None,
                        'thresholds': {
                            'required_support': support_threshold,
                            'required_confidence': confidence_threshold,
                            'domain1': domain1,
                            'domain2': domain2
                        }
                    }
                }

                patterns.append(pattern)

                logger.info(
                    f"✅ Co-occurrence: {device1} + {device2} "
                    f"({count} times, {confidence:.0%} confidence, "
                    f"avg_delta={avg_time_delta:.1f}s)" if avg_time_delta else
                    f"({count} times, {confidence:.0%} confidence)"
                )

        logger.info(f"✅ Detected {len(patterns)} co-occurrence patterns")

        # Recommendation 2.1: Integrate feedback into pattern detection
        if self.feedback_client and patterns:
            patterns = await self._apply_feedback_adjustments(patterns)

        # Story AI5.3: Store daily aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    def _store_daily_aggregates(self, patterns: list[dict], events: pd.DataFrame) -> None:
        """
        Store daily aggregates to InfluxDB.
        
        Story AI5.3: Incremental pattern processing with aggregate storage.
        
        Args:
            patterns: List of detected patterns
            events: Original events DataFrame
        """
        try:
            # Get date from events
            if events.empty or 'timestamp' not in events.columns:
                logger.warning("Cannot determine date from events for aggregate storage")
                return

            # Use the date of the first event (assuming 24h window)
            date = events['timestamp'].min().date()
            date_str = date.strftime("%Y-%m-%d")

            logger.info(f"Storing daily aggregates for {date_str}")

            for pattern in patterns:
                device1 = pattern.get('device1')
                device2 = pattern.get('device2')
                combined_id = pattern.get('device_id', f"{device1}+{device2}")

                if not device1 or not device2:
                    continue

                # Extract domains
                domain1 = device1.split('.')[0] if '.' in device1 else 'unknown'
                domain2 = device2.split('.')[0] if '.' in device2 else 'unknown'

                # Calculate metrics
                occurrences = pattern.get('occurrences', 0)
                confidence = pattern.get('confidence', 0.0)
                support = pattern.get('metadata', {}).get('support', 0.0)
                avg_time_delta = pattern.get('metadata', {}).get('avg_time_delta_seconds')

                # Store aggregate
                try:
                    # Calculate typical hours (simplified - could be enhanced)
                    typical_hours = []  # Could extract from pattern metadata if available

                    # Convert window_minutes to seconds
                    time_window_seconds = self.window_minutes * 60

                    self.aggregate_client.write_co_occurrence_daily(
                        date=date_str,
                        device_pair=combined_id,
                        co_occurrence_count=occurrences,
                        time_window_seconds=time_window_seconds,
                        confidence=confidence,
                        typical_hours=typical_hours
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {combined_id}: {e}", exc_info=True)

            logger.info(f"✅ Stored {len(patterns)} daily aggregates to InfluxDB")

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)

    async def detect_patterns_optimized(self, events: pd.DataFrame) -> list[dict]:
        """
        Optimized version for large event counts using intelligent sampling.
        
        Note: System noise filtering and variance thresholding are applied
        by calling detect_patterns() which handles these filters.
        
        Args:
            events: DataFrame with columns [device_id, timestamp, state]
        
        Returns:
            List of co-occurrence patterns
        """
        # Task 2: Filter system noise first (before sampling to save processing)
        if self.filter_system_noise:
            original_count = len(events)
            events = self._filter_system_noise(events)
            filtered_count = len(events)
            if filtered_count < original_count:
                logger.info(
                    f"✅ Filtered system noise before optimization: {original_count} → {filtered_count} events"
                )

        # If too many events, sample intelligently
        if len(events) > 50000:
            logger.info(f"Large dataset detected ({len(events)} events), applying sampling")

            # Keep all recent events (last 7 days), sample older ones
            max_timestamp = events['timestamp'].max()
            recent_threshold = max_timestamp - pd.Timedelta(days=7)

            recent = events[events['timestamp'] > recent_threshold]
            older = events[events['timestamp'] <= recent_threshold]

            # Sample older events
            sample_size = min(20000, len(older))
            older_sampled = older.sample(n=sample_size, random_state=42) if len(older) > 0 else pd.DataFrame()

            # Combine
            events = pd.concat([recent, older_sampled]) if len(older_sampled) > 0 else recent
            events = events.sort_values('timestamp')

            logger.info(f"✅ Sampled dataset: {len(events)} events (recent: {len(recent)}, sampled older: {len(older_sampled)})")

        return await self.detect_patterns(events)

    @staticmethod
    def _get_domain(device_id: str) -> str:
        """Extract entity domain (prefix before dot) from a device ID."""
        if not device_id or '.' not in str(device_id):
            return 'default'
        return str(device_id).split('.', 1)[0]

    def _support_threshold_for(self, domain: str) -> int:
        """Get support threshold for a given domain."""
        return self.domain_support_overrides.get(domain, self.min_support)

    def _confidence_threshold_for(self, domain: str) -> float:
        """Get confidence threshold for a given domain."""
        return self.domain_confidence_overrides.get(domain, self.min_confidence)

    def _calculate_avg_time_delta(
        self,
        events: pd.DataFrame,
        device1: str,
        device2: str,
        window_minutes: int
    ) -> float | None:
        """
        Calculate average time delta between device1 and device2 events.
        
        Returns:
            Average time delta in seconds, or None if insufficient data
        """
        try:
            device1_events = events[events['device_id'] == device1].copy()
            device2_events = events[events['device_id'] == device2].copy()

            time_deltas = []

            for _, event1 in device1_events.iterrows():
                window_end = event1['timestamp'] + pd.Timedelta(minutes=window_minutes)

                # Find device2 events within window
                nearby = device2_events[
                    (device2_events['timestamp'] > event1['timestamp']) &
                    (device2_events['timestamp'] <= window_end)
                ]

                if len(nearby) > 0:
                    # Take the closest event
                    closest = nearby.iloc[0]
                    delta = (closest['timestamp'] - event1['timestamp']).total_seconds()
                    time_deltas.append(delta)

            if time_deltas:
                return float(np.mean(time_deltas))

            return None

        except Exception as e:
            logger.warning(f"Failed to calculate time delta for {device1}+{device2}: {e}")
            return None

    def _filter_system_noise(self, events: pd.DataFrame) -> pd.DataFrame:
        """
        Filter out system sensors, trackers, images, and events.
        
        Task 2: Filter System Noise from Co-occurrence Detector
        
        Args:
            events: DataFrame with device_id column
            
        Returns:
            Filtered DataFrame with only actionable events
        """
        if 'device_id' not in events.columns:
            return events

        # Create mask for actionable events
        mask = events['device_id'].apply(lambda device_id: self._is_actionable_entity(device_id))

        filtered = events[mask].copy()
        return filtered

    def _is_actionable_entity(self, device_id: str) -> bool:
        """
        Check if an entity ID represents an actionable (user-controllable) device.
        
        Task 2: Filter System Noise
        
        Args:
            device_id: Entity ID to check
            
        Returns:
            True if actionable, False if system noise
        """
        # Check domain-level exclusions
        domain = self._get_domain(device_id)
        if domain in EXCLUDED_DOMAINS:
            return False

        # Check prefixes
        for prefix in EXCLUDED_ENTITY_PREFIXES:
            if device_id.startswith(prefix):
                return False

        # Check patterns (contains)
        for pattern in EXCLUDED_PATTERNS:
            if pattern in device_id.lower():
                return False

        return True

    def _is_meaningful_automation_pattern(self, device1: str, device2: str) -> bool:
        """
        Validate that pattern represents a meaningful automation opportunity.
        
        Rules:
        1. At least one device must be actionable (controllable)
        2. At least one device must be a trigger or both actionable
        3. Avoid sensor-to-sensor patterns (no action possible)
        4. Avoid status-to-status patterns (informational only)
        
        Args:
            device1: First device ID
            device2: Second device ID
            
        Returns:
            True if meaningful automation pattern, False otherwise
        """
        # First check basic actionable entity filter
        if not (self._is_actionable_entity(device1) and self._is_actionable_entity(device2)):
            return False

        # Get domains
        domain1 = self._get_domain(device1)
        domain2 = self._get_domain(device2)

        # Both must be actionable OR one trigger + one actionable
        both_actionable = domain1 in ACTIONABLE_DOMAINS and domain2 in ACTIONABLE_DOMAINS
        trigger_action = ((domain1 in TRIGGER_DOMAINS and domain2 in ACTIONABLE_DOMAINS) or
                         (domain2 in TRIGGER_DOMAINS and domain1 in ACTIONABLE_DOMAINS))

        if not (both_actionable or trigger_action):
            return False

        # Additional quality checks
        if self._is_redundant_pairing(device1, device2):
            return False

        return True

    def _is_redundant_pairing(self, device1: str, device2: str) -> bool:
        """
        Check for redundant/meaningless pairings.
        
        Args:
            device1: First device ID
            device2: Second device ID
            
        Returns:
            True if redundant pairing, False otherwise
        """
        # Same device (shouldn't happen but check)
        if device1 == device2:
            return True

        # Both are passive sensors (no actionable automation)
        domain1 = self._get_domain(device1)
        domain2 = self._get_domain(device2)

        sensor_domains = {'sensor', 'binary_sensor'}
        if (domain1 in sensor_domains and domain2 in sensor_domains):
            return True

        # Both are informational only
        if (domain1 in PASSIVE_DOMAINS and domain2 in PASSIVE_DOMAINS):
            return True

        return False

    def _is_actionable_pattern(self, device1: str, device2: str) -> bool:
        """
        Check if a device pair represents an actionable pattern.
        
        DEPRECATED: Use _is_meaningful_automation_pattern() instead.
        Kept for backward compatibility.
        
        Args:
            device1: First device ID
            device2: Second device ID
            
        Returns:
            True if both devices are actionable
        """
        return self._is_meaningful_automation_pattern(device1, device2)

    def get_pattern_summary(self, patterns: list[dict]) -> dict:
        """
        Get summary statistics for detected patterns.
        
        Args:
            patterns: List of pattern dictionaries
        
        Returns:
            Summary dictionary with counts and statistics
        """
        if not patterns:
            return {
                'total_patterns': 0,
                'unique_device_pairs': 0,
                'avg_confidence': 0.0,
                'avg_occurrences': 0.0
            }

        return {
            'total_patterns': len(patterns),
            'unique_device_pairs': len(patterns),  # Each pattern is a unique pair
            'avg_confidence': float(np.mean([p['confidence'] for p in patterns])),
            'avg_occurrences': float(np.mean([p['occurrences'] for p in patterns])),
            'min_confidence': float(np.min([p['confidence'] for p in patterns])),
            'max_confidence': float(np.max([p['confidence'] for p in patterns])),
            'confidence_distribution': {
                '70-80%': sum(1 for p in patterns if 0.7 <= p['confidence'] < 0.8),
                '80-90%': sum(1 for p in patterns if 0.8 <= p['confidence'] < 0.9),
                '90-100%': sum(1 for p in patterns if 0.9 <= p['confidence'] <= 1.0)
            }
        }

