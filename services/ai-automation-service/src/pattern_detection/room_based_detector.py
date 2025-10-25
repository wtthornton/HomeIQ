"""
Room-Based Pattern Detector

Detects room-specific behavior patterns using spatial analysis and ML clustering.
Analyzes device interactions within and between rooms to identify spatial patterns.

Story AI5.3: Converted to incremental processing with aggregate storage.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class RoomBasedDetector(MLPatternDetector):
    """
    Detects room-specific behavior patterns and spatial relationships.
    
    Analyzes patterns based on:
    - Room-specific device usage patterns
    - Room transition patterns (movement between rooms)
    - Room activity clustering
    - Spatial device interactions
    """
    
    def __init__(
        self,
        min_room_occurrences: int = 5,
        room_transition_window_minutes: int = 15,
        min_device_diversity: float = 0.3,
        spatial_weight: float = 0.4,
        temporal_weight: float = 0.3,
        device_weight: float = 0.3,
        aggregate_client=None,
        **kwargs
    ):
        """
        Initialize room-based detector.
        
        Args:
            min_room_occurrences: Minimum occurrences for valid room patterns
            room_transition_window_minutes: Window for detecting room transitions
            min_device_diversity: Minimum device diversity within room
            spatial_weight: Weight for spatial features in clustering
            temporal_weight: Weight for temporal features in clustering
            device_weight: Weight for device features in clustering
            aggregate_client: PatternAggregateClient for storing daily aggregates (Story AI5.3)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.min_room_occurrences = min_room_occurrences
        self.room_transition_window_minutes = room_transition_window_minutes
        self.min_device_diversity = min_device_diversity
        self.spatial_weight = spatial_weight
        self.temporal_weight = temporal_weight
        self.device_weight = device_weight
        self.aggregate_client = aggregate_client
        
        # Feature weights for clustering
        self.feature_weights = {
            'spatial': spatial_weight,
            'temporal': temporal_weight,
            'device': device_weight
        }
        
        logger.info(f"RoomBasedDetector initialized: min_occurrences={min_room_occurrences}, transition_window={room_transition_window_minutes}min")
    
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect room-based patterns in events.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state, area columns
            
        Returns:
            List of room-based pattern dictionaries
        """
        start_time = datetime.utcnow()
        
        if not self._validate_events_dataframe(events_df):
            return []
        
        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)
        
        # Ensure area column exists
        if 'area' not in events_df.columns:
            logger.warning("No 'area' column found, creating default areas")
            events_df['area'] = 'unknown'
        
        # Detect different types of room patterns
        patterns = []
        
        # 1. Room-specific device patterns
        room_device_patterns = self._detect_room_device_patterns(events_df)
        patterns.extend(room_device_patterns)
        
        # 2. Room transition patterns
        room_transition_patterns = self._detect_room_transition_patterns(events_df)
        patterns.extend(room_transition_patterns)
        
        # 3. Room activity clustering
        room_activity_patterns = self._detect_room_activity_patterns(events_df)
        patterns.extend(room_activity_patterns)
        
        # 4. Spatial device interaction patterns
        spatial_interaction_patterns = self._detect_spatial_interaction_patterns(events_df)
        patterns.extend(spatial_interaction_patterns)
        
        # Cluster similar room patterns using ML
        if self.enable_ml and len(patterns) > 2:
            patterns = self._cluster_room_patterns(patterns)
        
        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats['total_patterns'] += len(patterns)
        self.detection_stats['processing_time'] += processing_time
        
        logger.info(f"Detected {len(patterns)} room-based patterns in {processing_time:.2f}s")
        
        # Story AI5.3: Store daily aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events_df)
        
        return patterns
    
    def _store_daily_aggregates(self, patterns: List[Dict], events_df: pd.DataFrame) -> None:
        """
        Store daily aggregates to InfluxDB.
        
        Story AI5.3: Incremental pattern processing with aggregate storage.
        
        Args:
            patterns: List of detected patterns
            events_df: Original events DataFrame
        """
        try:
            # Get date from events
            if events_df.empty or 'time' not in events_df.columns:
                logger.warning("Cannot determine date from events for aggregate storage")
                return
            
            # Use the date of the first event (assuming 24h window)
            date = pd.to_datetime(events_df['time'].min()).date()
            date_str = date.strftime("%Y-%m-%d")
            
            logger.info(f"Storing daily aggregates for {date_str}")
            
            for pattern in patterns:
                entity_id = pattern.get('entity_id', 'unknown')
                room = pattern.get('metadata', {}).get('room', pattern.get('room', 'unknown'))
                domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                
                # Calculate metrics
                occurrences = pattern.get('occurrences', 0)
                confidence = pattern.get('confidence', 0.0)
                device_count = len(pattern.get('devices', []))
                
                # Store aggregate
                try:
                    self.aggregate_client.write_room_based_daily(
                        date=date_str,
                        entity_id=entity_id,
                        domain=domain,
                        room=room,
                        occurrences=occurrences,
                        confidence=confidence,
                        device_count=device_count
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {entity_id}: {e}", exc_info=True)
            
            logger.info(f"✅ Stored {len(patterns)} daily aggregates to InfluxDB")
            
        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
    
    def _detect_room_device_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect device usage patterns within specific rooms.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of room device patterns
        """
        patterns = []
        
        # Group by room and analyze device usage
        for room, room_events in events_df.groupby('area'):
            if len(room_events) < self.min_room_occurrences:
                continue
            
            # Analyze device diversity in room
            device_counts = room_events['entity_id'].value_counts()
            unique_devices = len(device_counts)
            total_events = len(room_events)
            
            # Calculate device diversity
            device_diversity = unique_devices / total_events if total_events > 0 else 0
            
            if device_diversity < self.min_device_diversity:
                continue
            
            # Analyze temporal patterns within room
            time_consistency = self._calculate_room_time_consistency(room_events)
            
            # Analyze device state patterns
            state_patterns = self._analyze_room_state_patterns(room_events)
            
            # Calculate confidence
            confidence = self._calculate_room_device_confidence(
                total_events, device_diversity, time_consistency, state_patterns
            )
            
            if confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type='room_device',
                    pattern_id=self._generate_pattern_id('room_dev'),
                    confidence=confidence,
                    occurrences=total_events,
                    devices=list(device_counts.index),
                    metadata={
                        'room': room,
                        'device_diversity': device_diversity,
                        'unique_devices': unique_devices,
                        'time_consistency': time_consistency,
                        'state_patterns': state_patterns,
                        'most_active_device': device_counts.index[0],
                        'device_activity_distribution': device_counts.to_dict(),
                        'first_occurrence': room_events['time'].min().isoformat(),
                        'last_occurrence': room_events['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_room_transition_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect patterns of movement between rooms.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of room transition patterns
        """
        patterns = []
        
        # Sort events by time and user (if available)
        events_sorted = events_df.sort_values('time')
        
        # Find room transitions
        transitions = self._find_room_transitions(events_sorted)
        
        if not transitions:
            return patterns
        
        # Group transitions by pattern
        transition_groups = self._group_transition_patterns(transitions)
        
        for transition_pattern, transition_events in transition_groups.items():
            if len(transition_events) < self.min_occurrences:
                continue
            
            # Analyze transition pattern
            from_room, to_room = transition_pattern
            transition_confidence = self._calculate_transition_confidence(transition_events)
            
            if transition_confidence >= self.min_confidence:
                # Get devices involved in transitions
                transition_devices = set()
                for transition in transition_events:
                    transition_devices.update(transition.get('devices', []))
                
                pattern = self._create_pattern_dict(
                    pattern_type='room_transition',
                    pattern_id=self._generate_pattern_id('room_trans'),
                    confidence=transition_confidence,
                    occurrences=len(transition_events),
                    devices=list(transition_devices),
                    metadata={
                        'from_room': from_room,
                        'to_room': to_room,
                        'transition_pattern': f"{from_room} → {to_room}",
                        'avg_transition_time': self._calculate_avg_transition_time(transition_events),
                        'transition_consistency': self._calculate_transition_consistency(transition_events),
                        'devices_involved': list(transition_devices),
                        'first_transition': min(t['time'] for t in transition_events).isoformat(),
                        'last_transition': max(t['time'] for t in transition_events).isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_room_activity_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect activity patterns within rooms using ML clustering.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of room activity patterns
        """
        patterns = []
        
        # Group by room and analyze activity patterns
        for room, room_events in events_df.groupby('area'):
            if len(room_events) < self.min_room_occurrences:
                continue
            
            # Extract activity features
            activity_features = self._extract_room_activity_features(room_events)
            
            if len(activity_features) < 3:
                continue
            
            # Cluster activity patterns
            try:
                from sklearn.cluster import KMeans
                
                # Determine optimal number of clusters
                n_clusters = min(3, len(activity_features) // 2)
                if n_clusters < 2:
                    continue
                
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                cluster_labels = kmeans.fit_predict(activity_features)
                
                # Analyze each cluster
                for cluster_id in range(n_clusters):
                    cluster_events = room_events[cluster_labels == cluster_id]
                    
                    if len(cluster_events) < self.min_occurrences:
                        continue
                    
                    cluster_confidence = self._calculate_activity_cluster_confidence(
                        cluster_events, cluster_id, kmeans
                    )
                    
                    if cluster_confidence >= self.min_confidence:
                        pattern = self._create_pattern_dict(
                            pattern_type='room_activity',
                            pattern_id=self._generate_pattern_id('room_act'),
                            confidence=cluster_confidence,
                            occurrences=len(cluster_events),
                            devices=list(cluster_events['entity_id'].unique()),
                            metadata={
                                'room': room,
                                'activity_cluster': cluster_id,
                                'cluster_size': len(cluster_events),
                                'activity_characteristics': self._describe_activity_cluster(
                                    cluster_events, cluster_id
                                ),
                                'first_activity': cluster_events['time'].min().isoformat(),
                                'last_activity': cluster_events['time'].max().isoformat()
                            }
                        )
                        patterns.append(pattern)
                        
            except Exception as e:
                logger.warning(f"Room activity clustering failed for {room}: {e}")
        
        return patterns
    
    def _detect_spatial_interaction_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect spatial device interaction patterns across rooms.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of spatial interaction patterns
        """
        patterns = []
        
        # Find devices that interact across rooms
        spatial_interactions = self._find_spatial_interactions(events_df)
        
        for interaction, interaction_events in spatial_interactions.items():
            if len(interaction_events) < self.min_occurrences:
                continue
            
            # Analyze spatial interaction pattern
            interaction_confidence = self._calculate_spatial_interaction_confidence(
                interaction_events
            )
            
            if interaction_confidence >= self.min_confidence:
                devices = list(set().union(*[e.get('devices', []) for e in interaction_events]))
                rooms = list(set().union(*[e.get('rooms', []) for e in interaction_events]))
                
                pattern = self._create_pattern_dict(
                    pattern_type='spatial_interaction',
                    pattern_id=self._generate_pattern_id('spatial'),
                    confidence=interaction_confidence,
                    occurrences=len(interaction_events),
                    devices=devices,
                    metadata={
                        'interaction_type': interaction,
                        'rooms_involved': rooms,
                        'devices_involved': devices,
                        'spatial_consistency': self._calculate_spatial_consistency(interaction_events),
                        'interaction_frequency': len(interaction_events),
                        'first_interaction': min(e['time'] for e in interaction_events).isoformat(),
                        'last_interaction': max(e['time'] for e in interaction_events).isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _find_room_transitions(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Find room transitions in events.
        
        Args:
            events_df: Sorted events DataFrame
            
        Returns:
            List of room transition events
        """
        transitions = []
        window_size = pd.Timedelta(minutes=self.room_transition_window_minutes)
        
        # Group by time windows to find transitions
        for i in range(len(events_df) - 1):
            current_event = events_df.iloc[i]
            next_event = events_df.iloc[i + 1]
            
            # Check if events are within transition window
            time_diff = next_event['time'] - current_event['time']
            if time_diff <= window_size:
                current_room = current_event.get('area', 'unknown')
                next_room = next_event.get('area', 'unknown')
                
                # Check if rooms are different
                if current_room != next_room and current_room != 'unknown' and next_room != 'unknown':
                    transitions.append({
                        'time': next_event['time'],
                        'from_room': current_room,
                        'to_room': next_room,
                        'devices': [current_event['entity_id'], next_event['entity_id']],
                        'rooms': [current_room, next_room]
                    })
        
        return transitions
    
    def _group_transition_patterns(self, transitions: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
        """
        Group transitions by pattern (from_room, to_room).
        
        Args:
            transitions: List of transition events
            
        Returns:
            Dictionary of transition patterns
        """
        groups = defaultdict(list)
        
        for transition in transitions:
            pattern = (transition['from_room'], transition['to_room'])
            groups[pattern].append(transition)
        
        return dict(groups)
    
    def _find_spatial_interactions(self, events_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """
        Find spatial device interactions across rooms.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Dictionary of spatial interactions
        """
        interactions = defaultdict(list)
        window_size = pd.Timedelta(minutes=10)  # 10-minute window for interactions
        
        # Group events by time windows
        events_sorted = events_df.sort_values('time')
        
        for i in range(len(events_sorted) - 1):
            current_event = events_sorted.iloc[i]
            
            # Find events within interaction window
            window_end = current_event['time'] + window_size
            window_events = events_sorted[
                (events_sorted['time'] > current_event['time']) & 
                (events_sorted['time'] <= window_end)
            ]
            
            if len(window_events) > 1:
                # Check for cross-room interactions
                rooms = set(window_events['area'].unique())
                if len(rooms) > 1:
                    devices = list(window_events['entity_id'].unique())
                    interaction_key = f"multi_room_{len(rooms)}_rooms"
                    
                    interactions[interaction_key].append({
                        'time': current_event['time'],
                        'devices': devices,
                        'rooms': list(rooms),
                        'event_count': len(window_events)
                    })
        
        return dict(interactions)
    
    def _calculate_room_time_consistency(self, room_events: pd.DataFrame) -> float:
        """
        Calculate time consistency for room events.
        
        Args:
            room_events: Events in a specific room
            
        Returns:
            Time consistency score (0.0 to 1.0)
        """
        if len(room_events) < 2:
            return 0.0
        
        # Calculate time differences
        time_diffs = room_events['time'].diff().dt.total_seconds().dropna()
        
        if len(time_diffs) == 0:
            return 0.0
        
        # Calculate coefficient of variation
        mean_diff = time_diffs.mean()
        std_diff = time_diffs.std()
        
        if mean_diff == 0:
            return 0.0
        
        cv = std_diff / mean_diff
        consistency = max(0.0, 1.0 - cv)
        
        return min(consistency, 1.0)
    
    def _analyze_room_state_patterns(self, room_events: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze state patterns within a room.
        
        Args:
            room_events: Events in a specific room
            
        Returns:
            State pattern analysis
        """
        state_counts = room_events['state'].value_counts()
        total_events = len(room_events)
        
        return {
            'most_common_state': state_counts.index[0] if len(state_counts) > 0 else 'unknown',
            'state_distribution': (state_counts / total_events).to_dict(),
            'state_diversity': len(state_counts) / total_events if total_events > 0 else 0
        }
    
    def _calculate_room_device_confidence(
        self, 
        total_events: int, 
        device_diversity: float, 
        time_consistency: float, 
        state_patterns: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence for room device patterns.
        
        Args:
            total_events: Total number of events
            device_diversity: Device diversity score
            time_consistency: Time consistency score
            state_patterns: State pattern analysis
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from events
        base_confidence = min(total_events / 20.0, 1.0)
        
        # Device diversity bonus
        diversity_bonus = device_diversity * 0.3
        
        # Time consistency bonus
        time_bonus = time_consistency * 0.2
        
        # State consistency bonus
        state_diversity = state_patterns.get('state_diversity', 0.0)
        state_bonus = (1.0 - state_diversity) * 0.2  # Lower diversity = higher consistency
        
        total_confidence = base_confidence + diversity_bonus + time_bonus + state_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_transition_confidence(self, transition_events: List[Dict]) -> float:
        """
        Calculate confidence for room transition patterns.
        
        Args:
            transition_events: List of transition events
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        occurrences = len(transition_events)
        base_confidence = min(occurrences / 10.0, 1.0)
        
        # Consistency bonus
        consistency = self._calculate_transition_consistency(transition_events)
        consistency_bonus = consistency * 0.3
        
        total_confidence = base_confidence + consistency_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_transition_consistency(self, transition_events: List[Dict]) -> float:
        """
        Calculate consistency for room transitions.
        
        Args:
            transition_events: List of transition events
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        if len(transition_events) < 2:
            return 0.0
        
        # Calculate time differences between transitions
        times = [t['time'] for t in transition_events]
        time_diffs = [(times[i+1] - times[i]).total_seconds() for i in range(len(times)-1)]
        
        if not time_diffs:
            return 0.0
        
        # Calculate coefficient of variation
        mean_diff = np.mean(time_diffs)
        std_diff = np.std(time_diffs)
        
        if mean_diff == 0:
            return 0.0
        
        cv = std_diff / mean_diff
        consistency = max(0.0, 1.0 - cv)
        
        return min(consistency, 1.0)
    
    def _calculate_avg_transition_time(self, transition_events: List[Dict]) -> float:
        """
        Calculate average time between transitions.
        
        Args:
            transition_events: List of transition events
            
        Returns:
            Average transition time in seconds
        """
        if len(transition_events) < 2:
            return 0.0
        
        times = [t['time'] for t in transition_events]
        time_diffs = [(times[i+1] - times[i]).total_seconds() for i in range(len(times)-1)]
        
        return np.mean(time_diffs) if time_diffs else 0.0
    
    def _extract_room_activity_features(self, room_events: pd.DataFrame) -> np.ndarray:
        """
        Extract features for room activity clustering.
        
        Args:
            room_events: Events in a specific room
            
        Returns:
            Feature matrix for clustering
        """
        features = []
        
        # Group events by time windows (hourly)
        room_events['hour'] = room_events['time'].dt.hour
        room_events['dayofweek'] = room_events['time'].dt.dayofweek
        
        for hour in room_events['hour'].unique():
            hour_events = room_events[room_events['hour'] == hour]
            
            feature_vector = [
                len(hour_events),  # Event count
                hour_events['entity_id'].nunique(),  # Device count
                hour_events['state'].nunique(),  # State diversity
                hour,  # Hour of day
                hour_events['dayofweek'].iloc[0],  # Day of week
                hour_events['time'].dt.date.nunique()  # Days with activity
            ]
            features.append(feature_vector)
        
        return np.array(features) if features else np.array([])
    
    def _calculate_activity_cluster_confidence(
        self, 
        cluster_events: pd.DataFrame, 
        cluster_id: int, 
        kmeans_model
    ) -> float:
        """
        Calculate confidence for activity cluster patterns.
        
        Args:
            cluster_events: Events in cluster
            cluster_id: Cluster identifier
            kmeans_model: Fitted KMeans model
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        occurrences = len(cluster_events)
        base_confidence = min(occurrences / 15.0, 1.0)
        
        # Cluster cohesion bonus
        try:
            features = self._extract_room_activity_features(cluster_events)
            if len(features) > 0:
                distances = kmeans_model.transform(features)
                avg_distance = np.mean(distances[:, cluster_id])
                cohesion_bonus = max(0.0, 1.0 - avg_distance) * 0.2
                base_confidence += cohesion_bonus
        except Exception:
            pass
        
        return min(base_confidence, 1.0)
    
    def _describe_activity_cluster(self, cluster_events: pd.DataFrame, cluster_id: int) -> Dict[str, Any]:
        """
        Describe characteristics of an activity cluster.
        
        Args:
            cluster_events: Events in cluster
            cluster_id: Cluster identifier
            
        Returns:
            Cluster characteristics
        """
        return {
            'event_count': len(cluster_events),
            'device_count': cluster_events['entity_id'].nunique(),
            'state_count': cluster_events['state'].nunique(),
            'hour_distribution': cluster_events['time'].dt.hour.value_counts().to_dict(),
            'most_active_device': cluster_events['entity_id'].value_counts().index[0] if len(cluster_events) > 0 else 'unknown'
        }
    
    def _calculate_spatial_interaction_confidence(self, interaction_events: List[Dict]) -> float:
        """
        Calculate confidence for spatial interaction patterns.
        
        Args:
            interaction_events: List of interaction events
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        occurrences = len(interaction_events)
        base_confidence = min(occurrences / 8.0, 1.0)
        
        # Spatial consistency bonus
        consistency = self._calculate_spatial_consistency(interaction_events)
        consistency_bonus = consistency * 0.3
        
        total_confidence = base_confidence + consistency_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_spatial_consistency(self, interaction_events: List[Dict]) -> float:
        """
        Calculate spatial consistency for interactions.
        
        Args:
            interaction_events: List of interaction events
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        if len(interaction_events) < 2:
            return 0.0
        
        # Calculate consistency of rooms and devices involved
        room_sets = [set(e.get('rooms', [])) for e in interaction_events]
        device_sets = [set(e.get('devices', [])) for e in interaction_events]
        
        # Room consistency
        room_consistency = len(set.intersection(*room_sets)) / len(set.union(*room_sets)) if room_sets else 0.0
        
        # Device consistency
        device_consistency = len(set.intersection(*device_sets)) / len(set.union(*device_sets)) if device_sets else 0.0
        
        return (room_consistency + device_consistency) / 2.0
    
    def _cluster_room_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """
        Cluster similar room patterns using ML.
        
        Args:
            patterns: List of room patterns
            
        Returns:
            Clustered patterns with cluster information
        """
        if len(patterns) < 3:
            return patterns
        
        try:
            # Extract features for clustering
            features = self._extract_room_pattern_features(patterns)
            
            # Cluster patterns
            patterns = self._cluster_patterns(patterns, features)
            
            logger.info(f"Clustered {len(patterns)} room patterns")
            
        except Exception as e:
            logger.warning(f"Room pattern clustering failed: {e}")
        
        return patterns
    
    def _extract_room_pattern_features(self, patterns: List[Dict]) -> np.ndarray:
        """
        Extract features for room pattern clustering.
        
        Args:
            patterns: List of room patterns
            
        Returns:
            Feature matrix for clustering
        """
        features = []
        
        for pattern in patterns:
            metadata = pattern['metadata']
            
            # Extract numerical features
            feature_vector = [
                pattern['occurrences'],
                pattern['confidence'],
                len(pattern['devices']),
                metadata.get('device_diversity', 0.0),
                metadata.get('time_consistency', 0.0),
                metadata.get('unique_devices', 0),
                metadata.get('spatial_consistency', 0.0)
            ]
            
            # Add pattern type encoding
            pattern_type = pattern['pattern_type']
            type_encoding = {
                'room_device': 0,
                'room_transition': 1,
                'room_activity': 2,
                'spatial_interaction': 3
            }.get(pattern_type, 0)
            feature_vector.append(type_encoding)
            
            features.append(feature_vector)
        
        return np.array(features)
