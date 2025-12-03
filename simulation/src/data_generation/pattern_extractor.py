"""
Pattern Extractor

Advanced pattern extraction from events for ground truth generation.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class PatternExtractor:
    """
    Advanced pattern extractor for event analysis.
    
    Extracts:
    - Temporal patterns (time-based)
    - Sequential patterns (state transitions)
    - Correlation patterns (device relationships)
    """

    def __init__(self):
        """Initialize pattern extractor."""
        logger.info("PatternExtractor initialized")

    def extract_temporal_patterns(
        self,
        events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extract temporal patterns (time-based).
        
        Args:
            events: List of event dictionaries
            
        Returns:
            List of temporal patterns
        """
        patterns = []
        
        # Group events by hour of day
        hourly_events = defaultdict(list)
        for event in events:
            timestamp = event.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    else:
                        dt = timestamp
                    hour = dt.hour
                    hourly_events[hour].append(event)
                except (ValueError, AttributeError, TypeError) as e:
                    logger.debug(f"Skipping invalid timestamp: {timestamp}, error: {e}")
                    continue
        
        # Find peak hours (hours with most events)
        if hourly_events:
            max_count = max(len(events) for events in hourly_events.values())
            for hour, hour_events in hourly_events.items():
                if len(hour_events) >= max_count * 0.7:  # 70% of peak
                    patterns.append({
                        "pattern_type": "temporal",
                        "hour": hour,
                        "occurrences": len(hour_events),
                        "confidence": min(1.0, len(hour_events) / 100.0)
                    })
        
        return patterns

    def extract_sequential_patterns(
        self,
        events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extract sequential patterns (state transitions).
        
        Args:
            events: List of event dictionaries
            
        Returns:
            List of sequential patterns
        """
        patterns = []
        
        # Group by entity
        entity_events = defaultdict(list)
        for event in events:
            entity_id = event.get("entity_id")
            if entity_id:
                entity_events[entity_id].append(event)
        
        # Extract sequences
        for entity_id, entity_event_list in entity_events.items():
            if len(entity_event_list) < 2:
                continue
            
            # Sort by timestamp
            try:
                sorted_events = sorted(
                    entity_event_list,
                    key=lambda e: e.get("timestamp", "")
                )
            except (TypeError, ValueError) as e:
                logger.debug(f"Skipping entity {entity_id} due to sort error: {e}")
                continue
            
            # Find state sequences
            sequences = []
            for i in range(len(sorted_events) - 1):
                prev_state = sorted_events[i].get("state")
                next_state = sorted_events[i + 1].get("state")
                
                if prev_state != next_state:
                    sequences.append({
                        "from": prev_state,
                        "to": next_state
                    })
            
            if sequences:
                patterns.append({
                    "entity_id": entity_id,
                    "pattern_type": "sequential",
                    "sequences": sequences,
                    "occurrences": len(sequences),
                    "confidence": min(1.0, len(sequences) / 20.0)
                })
        
        return patterns

    def extract_correlation_patterns(
        self,
        events: list[dict[str, Any]],
        time_window_minutes: int = 5
    ) -> list[dict[str, Any]]:
        """
        Extract correlation patterns (device relationships).
        
        Args:
            events: List of event dictionaries
            time_window_minutes: Time window for correlation (default: 5 minutes)
            
        Returns:
            List of correlation patterns
        """
        patterns = []
        
        # Group events by time windows
        time_windows = defaultdict(list)
        for event in events:
            timestamp = event.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    else:
                        dt = timestamp
                    # Round to time window
                    window_start = dt.replace(
                        minute=(dt.minute // time_window_minutes) * time_window_minutes,
                        second=0,
                        microsecond=0
                    )
                    time_windows[window_start].append(event)
                except (ValueError, AttributeError, TypeError) as e:
                    logger.debug(f"Skipping invalid timestamp: {timestamp}, error: {e}")
                    continue
        
        # Find correlated entities (appear in same time window)
        entity_correlations = defaultdict(int)
        for window_events in time_windows.values():
            entities = set(e.get("entity_id") for e in window_events if e.get("entity_id"))
            # Count pairs
            entity_list = list(entities)
            for i, entity1 in enumerate(entity_list):
                for entity2 in entity_list[i + 1:]:
                    pair = tuple(sorted([entity1, entity2]))
                    entity_correlations[pair] += 1
        
        # Create patterns for strong correlations
        for (entity1, entity2), count in entity_correlations.items():
            if count >= 3:  # Minimum occurrences
                patterns.append({
                    "pattern_type": "correlation",
                    "entity_1": entity1,
                    "entity_2": entity2,
                    "occurrences": count,
                    "confidence": min(1.0, count / 10.0)
                })
        
        return patterns

