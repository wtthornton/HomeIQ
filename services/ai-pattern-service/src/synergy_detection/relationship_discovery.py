"""
Relationship Discovery Engine Module

Phase 2.1: Dynamic relationship discovery from event data.

Discovers new device relationships dynamically by analyzing event data
for device co-occurrence, temporal patterns, and attribute patterns.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class RelationshipDiscoveryEngine:
    """
    Discovers new device relationships dynamically from event data.
    
    Analyzes device interactions to find patterns that aren't in the
    hardcoded COMPATIBLE_RELATIONSHIPS dictionary.
    
    Attributes:
        min_confidence: Minimum confidence threshold for discovered relationships
        min_frequency: Minimum frequency threshold for co-occurrence
        time_window_seconds: Time window for co-occurrence detection (default: 30 seconds)
    """
    
    def __init__(
        self,
        min_confidence: float = 0.5,
        min_frequency: int = 3,
        time_window_seconds: int = 30
    ):
        """
        Initialize relationship discovery engine.
        
        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
            min_frequency: Minimum frequency for co-occurrence patterns
            time_window_seconds: Time window for detecting co-occurrence
        """
        self.min_confidence = min_confidence
        self.min_frequency = min_frequency
        self.time_window_seconds = time_window_seconds
    
    async def discover_from_events(
        self,
        events: pd.DataFrame,
        existing_relationships: Optional[set[tuple[str, str]]] = None
    ) -> list[dict[str, Any]]:
        """
        Discover new relationships from event data.
        
        Args:
            events: DataFrame with event data (must have: timestamp, entity_id, device_id, state)
            existing_relationships: Set of (device1, device2) tuples for known relationships
            
        Returns:
            List of discovered relationship dictionaries
        """
        if events.empty:
            logger.warning("No events provided for relationship discovery")
            return []
        
        if existing_relationships is None:
            existing_relationships = set()
        
        logger.info(f"🔍 Discovering relationships from {len(events)} events...")
        
        # Build relationship graph from events
        graph = await self.build_relationship_graph(events)
        
        # Score relationships
        scored_relationships = await self.score_relationships(graph, events)
        
        # Filter by thresholds and exclude existing relationships
        discovered: list[dict[str, Any]] = []
        for rel in scored_relationships:
            device1, device2 = rel['device1'], rel['device2']
            
            # Skip if already in existing relationships (both directions)
            if ((device1, device2) in existing_relationships or 
                (device2, device1) in existing_relationships):
                continue
            
            # Apply thresholds
            if rel['confidence'] >= self.min_confidence and rel['frequency'] >= self.min_frequency:
                discovered.append(rel)
        
        logger.info(f"✅ Discovered {len(discovered)} new relationships")
        return discovered
    
    async def build_relationship_graph(
        self,
        events: pd.DataFrame
    ) -> dict[str, dict[str, int]]:
        """
        Build relationship graph from events.
        
        Creates a graph structure where nodes are devices and edges represent
        co-occurrence frequencies.
        
        Args:
            events: DataFrame with event data
            
        Returns:
            Dictionary mapping device1 -> {device2: frequency}
        """
        graph: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        if events.empty or 'timestamp' not in events.columns:
            return {}
        
        # Sort events by timestamp
        events_sorted = events.sort_values('timestamp')
        
        # Group events by time window
        current_window_start = None
        window_entities: set[str] = set()
        
        for _, event in events_sorted.iterrows():
            timestamp = event['timestamp']
            entity_id = event.get('entity_id', '')
            device_id = event.get('device_id', entity_id.split('.')[0] if '.' in entity_id else '')
            
            if pd.isna(timestamp) or not device_id:
                continue
            
            # Convert to datetime if needed
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            
            # Start new window if needed
            if current_window_start is None:
                current_window_start = timestamp
                window_entities = set()
            
            # Check if we need to start a new window
            if (timestamp - current_window_start).total_seconds() > self.time_window_seconds:
                # Process current window: create edges between all devices
                devices_in_window = {e.split('.')[0] if '.' in e else e 
                                   for e in window_entities if e}
                device_list = list(devices_in_window)
                for i, dev1 in enumerate(device_list):
                    for dev2 in device_list[i+1:]:
                        graph[dev1][dev2] += 1
                        graph[dev2][dev1] += 1  # Undirected graph
                
                # Start new window
                current_window_start = timestamp
                window_entities = set()
            
            # Add entity to current window
            if entity_id:
                window_entities.add(entity_id)
        
        # Process final window
        if window_entities:
            devices_in_window = {e.split('.')[0] if '.' in e else e 
                               for e in window_entities if e}
            device_list = list(devices_in_window)
            for i, dev1 in enumerate(device_list):
                for dev2 in device_list[i+1:]:
                    graph[dev1][dev2] += 1
                    graph[dev2][dev1] += 1
        
        logger.debug(f"Built relationship graph with {len(graph)} devices")
        return dict(graph)
    
    async def score_relationships(
        self,
        graph: dict[str, dict[str, int]],
        events: pd.DataFrame
    ) -> list[dict[str, Any]]:
        """
        Score relationships by frequency and confidence.
        
        Args:
            graph: Relationship graph from build_relationship_graph
            events: Original event DataFrame for additional analysis
            
        Returns:
            List of scored relationship dictionaries
        """
        relationships: list[dict[str, Any]] = []
        seen_pairs: set[tuple[str, str]] = set()
        
        # Calculate total device frequencies
        device_frequencies: dict[str, int] = defaultdict(int)
        if not events.empty and 'device_id' in events.columns:
            for device_id in events['device_id'].dropna():
                device_id_str = str(device_id)
                if '.' in device_id_str:
                    domain = device_id_str.split('.')[0]
                    device_frequencies[domain] += 1
                else:
                    device_frequencies[device_id_str] += 1
        
        # Score each relationship
        for device1, neighbors in graph.items():
            for device2, frequency in neighbors.items():
                # Skip duplicates (undirected graph)
                pair = tuple(sorted([device1, device2]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                
                # Calculate confidence based on frequency and device popularity
                device1_freq = device_frequencies.get(device1, 1)
                device2_freq = device_frequencies.get(device2, 1)
                
                # Confidence = frequency / sqrt(device1_freq * device2_freq)
                # This normalizes by device popularity
                import math
                max_possible_frequency = min(device1_freq, device2_freq)
                if max_possible_frequency > 0:
                    confidence = min(1.0, frequency / math.sqrt(max_possible_frequency))
                else:
                    confidence = 0.0
                
                # Impact score based on frequency (higher frequency = higher impact)
                max_freq = max(device_frequencies.values()) if device_frequencies else 1
                impact_score = min(1.0, 0.3 + (frequency / max_freq) * 0.5)
                
                relationships.append({
                    'device1': device1,
                    'device2': device2,
                    'frequency': frequency,
                    'confidence': round(confidence, 4),
                    'impact_score': round(impact_score, 4),
                    'complexity': 'medium',  # Default for discovered relationships
                    'rationale': f'Discovered from {frequency} co-occurrence events',
                    'detection_method': 'dynamic_discovery'
                })
        
        # Sort by confidence descending
        relationships.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.debug(f"Scored {len(relationships)} relationships")
        return relationships
    
    async def suggest_new_relationships(
        self,
        relationships: list[dict[str, Any]],
        threshold: float = 0.6
    ) -> list[dict[str, Any]]:
        """
        Suggest new relationships above confidence threshold.
        
        Args:
            relationships: List of scored relationships
            threshold: Confidence threshold for suggestions
            
        Returns:
            List of suggested relationships (confidence >= threshold)
        """
        suggestions = [r for r in relationships if r['confidence'] >= threshold]
        logger.info(f"💡 Suggested {len(suggestions)} relationships (confidence >= {threshold})")
        return suggestions
