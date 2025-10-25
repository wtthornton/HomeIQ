"""
Co-Occurrence Pattern Detector

Detects devices that are frequently used together within a time window.
Uses simple sliding window approach with association rule mining concepts.

Story AI5.3: Converted to incremental processing with aggregate storage.
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


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
        aggregate_client=None
    ):
        """
        Initialize co-occurrence detector.
        
        Args:
            window_minutes: Time window for co-occurrence (default: 5 minutes)
            min_support: Minimum number of co-occurrences (default: 5)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.7)
            aggregate_client: PatternAggregateClient for storing daily aggregates (Story AI5.3)
        """
        self.window_minutes = window_minutes
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.aggregate_client = aggregate_client
        logger.info(
            f"CoOccurrencePatternDetector initialized: "
            f"window={window_minutes}min, min_support={min_support}, min_confidence={min_confidence}"
        )
    
    def detect_patterns(self, events: pd.DataFrame) -> List[Dict]:
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
        
        # 1. Sort by time for efficient windowing
        events = events.sort_values('timestamp').copy()
        events = events.reset_index(drop=True)
        
        # 2. Find co-occurrences using sliding window
        co_occurrences = defaultdict(int)
        device_event_counts = defaultdict(int)
        
        # Track individual device events for confidence calculation
        for device_id in events['device_id']:
            device_event_counts[device_id] += 1
        
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
                    # Create sorted pair to avoid duplicates (A,B) vs (B,A)
                    pair = tuple(sorted([device_a, device_b]))
                    co_occurrences[pair] += 1
        
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
            
            # Filter by thresholds
            if count >= self.min_support and confidence >= self.min_confidence:
                # Calculate additional statistics
                avg_time_delta = self._calculate_avg_time_delta(
                    events, device1, device2, self.window_minutes
                )
                
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
                        'avg_time_delta_seconds': float(avg_time_delta) if avg_time_delta is not None else None
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
        
        # Story AI5.3: Store daily aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events)
        
        return patterns
    
    def _store_daily_aggregates(self, patterns: List[Dict], events: pd.DataFrame) -> None:
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
                    self.aggregate_client.write_co_occurrence_daily(
                        date=date_str,
                        entity_id=combined_id,
                        domain=f"{domain1}_{domain2}",
                        device1=device1,
                        device2=device2,
                        occurrences=occurrences,
                        confidence=confidence,
                        support=support,
                        avg_time_delta_seconds=avg_time_delta,
                        window_minutes=self.window_minutes
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {combined_id}: {e}", exc_info=True)
            
            logger.info(f"✅ Stored {len(patterns)} daily aggregates to InfluxDB")
            
        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
    
    def detect_patterns_optimized(self, events: pd.DataFrame) -> List[Dict]:
        """
        Optimized version for large event counts using intelligent sampling.
        
        Args:
            events: DataFrame with columns [device_id, timestamp, state]
        
        Returns:
            List of co-occurrence patterns
        """
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
        
        return self.detect_patterns(events)
    
    def _calculate_avg_time_delta(
        self,
        events: pd.DataFrame,
        device1: str,
        device2: str,
        window_minutes: int
    ) -> Optional[float]:
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
    
    def get_pattern_summary(self, patterns: List[Dict]) -> Dict:
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

