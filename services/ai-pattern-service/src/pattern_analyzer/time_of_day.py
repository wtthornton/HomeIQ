"""
Time-of-Day Pattern Detector

Detects when devices are consistently used at specific times of day using KMeans clustering.
Simple, proven algorithm with low resource usage.

Story AI5.3: Converted to incremental processing with aggregate storage.
Epic 39, Story 39.5: Extracted to ai-pattern-service.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class TimeOfDayPatternDetector:
    """
    Detects time-of-day patterns using simple KMeans clustering.
    Finds when devices are consistently used at the same time.
    
    Examples:
        - Bedroom light turns on at 7:00 AM daily
        - Thermostat adjusts at 6:00 PM in evening
        - Coffee maker starts at 6:30 AM weekdays
    """

    def __init__(
        self,
        min_occurrences: int = 3,
        min_confidence: float = 0.7,
        aggregate_client=None,
        domain_occurrence_overrides: dict[str, int] | None = None,
        domain_confidence_overrides: dict[str, float] | None = None
    ):
        """
        Initialize pattern detector.
        
        Args:
            min_occurrences: Minimum number of occurrences for a pattern (default: 3)
            min_confidence: Minimum confidence threshold (0.0-1.0, default: 0.7)
            aggregate_client: PatternAggregateClient for storing daily aggregates (Story AI5.3)
        """
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence
        self.aggregate_client = aggregate_client
        self.domain_occurrence_overrides = domain_occurrence_overrides or {}
        self.domain_confidence_overrides = domain_confidence_overrides or {}
        logger.info(
            "TimeOfDayPatternDetector initialized: min_occurrences=%s, min_confidence=%s, domain_occurrence_overrides=%s, domain_confidence_overrides=%s",
            min_occurrences,
            min_confidence,
            list((domain_occurrence_overrides or {}).keys()),
            list((domain_confidence_overrides or {}).keys())
        )

    def detect_patterns(self, events: pd.DataFrame) -> list[dict]:
        """
        Detect time-of-day patterns using KMeans clustering.
        
        Args:
            events: DataFrame with columns [device_id, timestamp, state]
                    device_id: str - Device identifier (e.g., "light.bedroom")
                    timestamp: datetime - Event timestamp
                    state: str - Device state (e.g., "on", "off")
        
        Returns:
            List of pattern dictionaries with keys:
                - device_id: Device identifier
                - pattern_type: "time_of_day"
                - hour: Hour of day (0-23)
                - minute: Minute (0-59)
                - occurrences: Number of events in pattern
                - total_events: Total events for device
                - confidence: Confidence score (occurrences / total_events)
                - metadata: Additional pattern metadata
        """
        if events.empty:
            logger.warning("No events provided for pattern detection")
            return []

        # Validate required columns
        required_cols = ['device_id', 'timestamp']
        missing_cols = [col for col in required_cols if col not in events.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return []

        # 1. Feature engineering (keep simple!)
        logger.info(f"Analyzing {len(events)} events for time-of-day patterns")

        events = events.copy()  # Avoid modifying original
        events['hour'] = events['timestamp'].dt.hour
        events['minute'] = events['timestamp'].dt.minute
        events['time_decimal'] = events['hour'] + events['minute'] / 60.0

        patterns = []

        # 2. Analyze each device separately
        unique_devices = events['device_id'].unique()
        logger.info(f"Analyzing {len(unique_devices)} unique devices")

        for device_id in unique_devices:
            device_events = events[events['device_id'] == device_id]
            domain = self._get_domain(device_id)
            required_occurrences = self.domain_occurrence_overrides.get(domain, self.min_occurrences)
            required_confidence = self.domain_confidence_overrides.get(domain, self.min_confidence)

            # Need minimum data (5 events to form meaningful clusters)
            if len(device_events) < 5:
                logger.debug(f"Skipping {device_id}: insufficient data ({len(device_events)} events)")
                continue

            try:
                # 3. Cluster time patterns (simple KMeans)
                times = device_events[['time_decimal']].values
                # Smart cluster count: 1 cluster for small datasets, up to 3 for large ones
                # This ensures each cluster has enough data points
                if len(times) <= 10:
                    n_clusters = 1
                elif len(times) <= 20:
                    n_clusters = 2
                else:
                    n_clusters = 3

                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                labels = kmeans.fit_predict(times)

                # 4. Find consistent clusters (confidence = size / total)
                for cluster_id in range(n_clusters):
                    cluster_mask = labels == cluster_id
                    cluster_times = times[cluster_mask]

                    if len(cluster_times) >= required_occurrences:
                        avg_time = cluster_times.mean()
                        # Calculate confidence based on occurrence ratio and consistency
                        occurrence_ratio = len(cluster_times) / len(times)

                        # Penalize high variance (less consistent = lower confidence)
                        std_minutes = float(cluster_times.std() * 60) if len(cluster_times) > 1 else 0.0
                        variance_penalty = min(std_minutes / 120.0, 0.3)  # Max 30% penalty for high variance

                        # Boost for high occurrence count
                        if len(cluster_times) >= self.min_occurrences * 2:
                            threshold_boost = 0.1
                        else:
                            threshold_boost = 0.0

                        # Calculate confidence: occurrence ratio adjusted for variance
                        confidence = min(0.95, occurrence_ratio * (1 - variance_penalty) + threshold_boost)
                        confidence = max(0.5, confidence)  # Minimum 50% confidence

                        if confidence >= required_confidence:
                            hour = int(avg_time)
                            minute = int((avg_time % 1) * 60)

                            # Calculate variability (standard deviation in minutes)
                            std_minutes = float(cluster_times.std() * 60) if len(cluster_times) > 1 else 0.0

                            pattern = {
                                'device_id': str(device_id),
                                'pattern_type': 'time_of_day',
                                'hour': hour,
                                'minute': minute,
                                'occurrences': int(len(cluster_times)),
                                'total_events': int(len(times)),
                                'confidence': float(confidence),  # Now calculated with variance penalty
                                'metadata': {
                                    'avg_time_decimal': float(avg_time),
                                    'cluster_id': int(cluster_id),
                                    'std_minutes': std_minutes,
                                    'time_range': f"{hour:02d}:{minute:02d} ± {int(std_minutes)}min",
                                    'occurrence_ratio': float(occurrence_ratio),
                                    'thresholds': {
                                        'required_occurrences': required_occurrences,
                                        'required_confidence': required_confidence,
                                        'domain': domain
                                    }
                                }
                            }

                            patterns.append(pattern)

                            logger.info(
                                f"✅ Pattern detected: {device_id} at {hour:02d}:{minute:02d} "
                                f"({len(cluster_times)}/{len(times)} = {confidence:.0%}, "
                                f"std={std_minutes:.1f}min)"
                            )

            except Exception as e:
                logger.error(f"Error analyzing {device_id}: {e}", exc_info=True)
                continue

        logger.info(f"✅ Detected {len(patterns)} time-of-day patterns across {len(unique_devices)} devices")

        # Story AI5.3: Store daily aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)

        return patterns

    @staticmethod
    def _get_domain(device_id: str) -> str:
        """Extract entity domain (prefix before dot) from device ID."""
        if not device_id or '.' not in str(device_id):
            return 'default'
        return str(device_id).split('.', 1)[0]

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

            # Calculate hourly distribution for each device
            events['hour'] = events['timestamp'].dt.hour

            for pattern in patterns:
                device_id = pattern['device_id']
                domain = device_id.split('.')[0] if '.' in device_id else 'unknown'

                # Get device events for this date
                device_events = events[events['device_id'] == device_id]

                if device_events.empty:
                    continue

                # Calculate hourly distribution (24 values)
                hourly_distribution = [0] * 24
                for hour in range(24):
                    hourly_distribution[hour] = len(device_events[device_events['hour'] == hour])

                # Get peak hours (top 25% of hours)
                sorted_hours = sorted(range(24), key=lambda h: hourly_distribution[h], reverse=True)
                top_count = max(1, len([h for h in sorted_hours if hourly_distribution[h] > 0]) // 4)
                peak_hours = sorted_hours[:top_count] if top_count > 0 else sorted_hours[:6]

                # Calculate metrics
                frequency = sum(hourly_distribution) / 24.0
                confidence = pattern.get('confidence', 0.0)
                occurrences = pattern.get('occurrences', len(device_events))

                # Store aggregate
                try:
                    self.aggregate_client.write_time_based_daily(
                        date=date_str,
                        entity_id=device_id,
                        domain=domain,
                        hourly_distribution=hourly_distribution,
                        peak_hours=peak_hours,
                        frequency=frequency,
                        confidence=confidence,
                        occurrences=occurrences
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {device_id}: {e}", exc_info=True)

            logger.info(f"✅ Stored {len(patterns)} daily aggregates to InfluxDB")

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)

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
                'unique_devices': 0,
                'avg_confidence': 0.0,
                'avg_occurrences': 0.0
            }

        return {
            'total_patterns': len(patterns),
            'unique_devices': len(set(p['device_id'] for p in patterns)),
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

