"""
Session Pattern Detector

Detects user session patterns and routines using temporal analysis and ML clustering.
Identifies user behavior sessions and routine patterns over time.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class SessionDetector(MLPatternDetector):
    """
    Detects user session patterns and routines.
    
    Analyzes patterns based on:
    - User session identification (activity periods)
    - Routine pattern detection (morning, evening, etc.)
    - Session duration analysis
    - User behavior clustering
    """
    
    def __init__(
        self,
        session_gap_minutes: int = 30,
        min_session_duration_minutes: int = 5,
        max_session_duration_hours: int = 8,
        min_session_occurrences: int = 3,
        routine_window_days: int = 7,
        aggregate_client=None,  # Story AI5.6: Weekly aggregation
        **kwargs
    ):
        """
        Initialize session detector.
        
        Args:
            session_gap_minutes: Gap between sessions (minutes)
            min_session_duration_minutes: Minimum session duration
            max_session_duration_hours: Maximum session duration
            min_session_occurrences: Minimum occurrences for valid session pattern
            routine_window_days: Window for routine pattern detection
            aggregate_client: PatternAggregateClient for storing weekly aggregates (Story AI5.6)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.session_gap_minutes = session_gap_minutes
        self.min_session_duration_minutes = min_session_duration_minutes
        self.max_session_duration_hours = max_session_duration_hours
        self.min_session_occurrences = min_session_occurrences
        self.routine_window_days = routine_window_days
        self.aggregate_client = aggregate_client  # Story AI5.6
        
        logger.info(f"SessionDetector initialized: gap={session_gap_minutes}min, min_duration={min_session_duration_minutes}min")
    
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect session patterns in events.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state columns
            
        Returns:
            List of session pattern dictionaries
        """
        start_time = datetime.utcnow()
        
        if not self._validate_events_dataframe(events_df):
            return []
        
        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)
        
        # Detect different types of session patterns
        patterns = []
        
        # 1. User session identification
        session_patterns = self._detect_user_sessions(events_df)
        patterns.extend(session_patterns)
        
        # 2. Routine pattern detection
        routine_patterns = self._detect_routine_patterns(events_df)
        patterns.extend(routine_patterns)
        
        # 3. Session clustering
        session_cluster_patterns = self._detect_session_clusters(events_df)
        patterns.extend(session_cluster_patterns)
        
        # 4. Temporal session patterns
        temporal_session_patterns = self._detect_temporal_session_patterns(events_df)
        patterns.extend(temporal_session_patterns)
        
        # Cluster similar session patterns using ML
        if self.enable_ml and len(patterns) > 2:
            patterns = self._cluster_session_patterns(patterns)
        
        # Story AI5.6: Store weekly aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_weekly_aggregates(patterns, events_df)
        
        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats['total_patterns'] += len(patterns)
        self.detection_stats['processing_time'] += processing_time
        
        logger.info(f"Detected {len(patterns)} session patterns in {processing_time:.2f}s")
        return patterns
    
    def _detect_user_sessions(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect user activity sessions.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of user session patterns
        """
        patterns = []
        
        # Identify sessions based on activity gaps
        sessions = self._identify_sessions(events_df)
        
        for session in sessions:
            if len(session['events']) < self.min_occurrences:
                continue
            
            # Analyze session characteristics
            session_confidence = self._calculate_session_confidence(session)
            
            if session_confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type='user_session',
                    pattern_id=self._generate_pattern_id('session'),
                    confidence=session_confidence,
                    occurrences=len(session['events']),
                    devices=list(session['devices']),
                    metadata={
                        'session_duration_minutes': session['duration_minutes'],
                        'session_start': session['start_time'].isoformat(),
                        'session_end': session['end_time'].isoformat(),
                        'device_count': len(session['devices']),
                        'activity_intensity': session['activity_intensity'],
                        'session_type': session['session_type'],
                        'rooms_involved': list(session['rooms']),
                        'state_distribution': session['state_distribution']
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_routine_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect routine patterns (morning, evening, etc.).
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of routine patterns
        """
        patterns = []
        
        # Group events by time periods
        time_periods = self._group_events_by_time_periods(events_df)
        
        for period, period_events in time_periods.items():
            if len(period_events) < self.min_session_occurrences:
                continue
            
            # Analyze routine characteristics
            routine_confidence = self._calculate_routine_confidence(period_events, period)
            
            if routine_confidence >= self.min_confidence:
                # Get devices and rooms involved
                devices = list(period_events['entity_id'].unique())
                rooms = list(period_events.get('area', pd.Series(['unknown'])).unique())
                
                pattern = self._create_pattern_dict(
                    pattern_type='routine',
                    pattern_id=self._generate_pattern_id('routine'),
                    confidence=routine_confidence,
                    occurrences=len(period_events),
                    devices=devices,
                    metadata={
                        'routine_period': period,
                        'routine_duration_hours': self._calculate_routine_duration(period_events),
                        'device_count': len(devices),
                        'room_count': len(rooms),
                        'activity_frequency': self._calculate_activity_frequency(period_events),
                        'routine_consistency': self._calculate_routine_consistency(period_events),
                        'most_active_device': period_events['entity_id'].value_counts().index[0],
                        'first_occurrence': period_events['time'].min().isoformat(),
                        'last_occurrence': period_events['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_session_clusters(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect session clusters using ML clustering.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of session cluster patterns
        """
        patterns = []
        
        # Extract session features
        session_features = self._extract_session_features(events_df)
        
        if len(session_features) < 3:
            return patterns
        
        try:
            from sklearn.cluster import DBSCAN
            
            # Cluster sessions
            clustering = DBSCAN(eps=0.5, min_samples=2)
            cluster_labels = clustering.fit_predict(session_features)
            
            # Analyze each cluster
            for cluster_id in set(cluster_labels):
                if cluster_id == -1:  # Skip noise
                    continue
                
                cluster_sessions = session_features[cluster_labels == cluster_id]
                
                if len(cluster_sessions) < self.min_session_occurrences:
                    continue
                
                cluster_confidence = self._calculate_cluster_confidence(cluster_sessions, cluster_id)
                
                if cluster_confidence >= self.min_confidence:
                    pattern = self._create_pattern_dict(
                        pattern_type='session_cluster',
                        pattern_id=self._generate_pattern_id('session_cluster'),
                        confidence=cluster_confidence,
                        occurrences=len(cluster_sessions),
                        devices=[],  # Will be filled from session data
                        metadata={
                            'cluster_id': cluster_id,
                            'cluster_size': len(cluster_sessions),
                            'cluster_characteristics': self._describe_cluster_characteristics(cluster_sessions),
                            'session_diversity': self._calculate_session_diversity(cluster_sessions)
                        }
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            logger.warning(f"Session clustering failed: {e}")
        
        return patterns
    
    def _detect_temporal_session_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect temporal patterns in sessions.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of temporal session patterns
        """
        patterns = []
        
        # Analyze temporal patterns
        temporal_analysis = self._analyze_temporal_patterns(events_df)
        
        for pattern_type, pattern_data in temporal_analysis.items():
            if pattern_data['occurrences'] < self.min_session_occurrences:
                continue
            
            pattern_confidence = self._calculate_temporal_pattern_confidence(pattern_data)
            
            if pattern_confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type=f'temporal_{pattern_type}',
                    pattern_id=self._generate_pattern_id(f'temporal_{pattern_type}'),
                    confidence=pattern_confidence,
                    occurrences=pattern_data['occurrences'],
                    devices=pattern_data['devices'],
                    metadata={
                        'temporal_pattern': pattern_type,
                        'pattern_frequency': pattern_data['frequency'],
                        'pattern_consistency': pattern_data['consistency'],
                        'time_distribution': pattern_data['time_distribution'],
                        'duration_analysis': pattern_data['duration_analysis'],
                        'first_occurrence': pattern_data['first_occurrence'].isoformat(),
                        'last_occurrence': pattern_data['last_occurrence'].isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _identify_sessions(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Identify user activity sessions.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of session dictionaries
        """
        sessions = []
        session_gap = pd.Timedelta(minutes=self.session_gap_minutes)
        
        # Sort events by time
        events_sorted = events_df.sort_values('time').reset_index(drop=True)
        
        current_session = []
        session_start = None
        
        for i, (_, event) in enumerate(events_sorted.iterrows()):
            if session_start is None:
                session_start = event['time']
                current_session = [event]
            else:
                # Check if event is within session gap
                time_since_last = event['time'] - events_sorted.iloc[i-1]['time']
                
                if time_since_last <= session_gap:
                    current_session.append(event)
                else:
                    # End current session and start new one
                    if current_session:
                        session = self._create_session_dict(current_session, session_start)
                        if self._is_valid_session(session):
                            sessions.append(session)
                    
                    session_start = event['time']
                    current_session = [event]
        
        # Add final session
        if current_session:
            session = self._create_session_dict(current_session, session_start)
            if self._is_valid_session(session):
                sessions.append(session)
        
        return sessions
    
    def _create_session_dict(self, session_events: List[pd.Series], start_time: datetime) -> Dict:
        """
        Create session dictionary from events.
        
        Args:
            session_events: List of events in session
            start_time: Session start time
            
        Returns:
            Session dictionary
        """
        end_time = session_events[-1]['time']
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        devices = list(set(event['entity_id'] for event in session_events))
        rooms = list(set(event.get('area', 'unknown') for event in session_events))
        states = [event['state'] for event in session_events]
        
        # Calculate activity intensity
        activity_intensity = len(session_events) / max(duration_minutes / 60, 0.1)  # Events per hour
        
        # Determine session type
        session_type = self._classify_session_type(start_time, duration_minutes, activity_intensity)
        
        # Calculate state distribution
        state_distribution = dict(pd.Series(states).value_counts())
        
        return {
            'events': session_events,
            'start_time': start_time,
            'end_time': end_time,
            'duration_minutes': duration_minutes,
            'devices': devices,
            'rooms': rooms,
            'activity_intensity': activity_intensity,
            'session_type': session_type,
            'state_distribution': state_distribution
        }
    
    def _is_valid_session(self, session: Dict) -> bool:
        """
        Check if session meets validity criteria.
        
        Args:
            session: Session dictionary
            
        Returns:
            True if session is valid
        """
        duration_minutes = session['duration_minutes']
        return (
            duration_minutes >= self.min_session_duration_minutes and
            duration_minutes <= self.max_session_duration_hours * 60
        )
    
    def _classify_session_type(self, start_time: datetime, duration_minutes: float, activity_intensity: float) -> str:
        """
        Classify session type based on characteristics.
        
        Args:
            start_time: Session start time
            duration_minutes: Session duration
            activity_intensity: Activity intensity
            
        Returns:
            Session type string
        """
        hour = start_time.hour
        
        if hour < 6:
            return 'night'
        elif hour < 12:
            return 'morning'
        elif hour < 18:
            return 'afternoon'
        else:
            return 'evening'
    
    def _group_events_by_time_periods(self, events_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Group events by time periods for routine detection.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Dictionary of time periods and their events
        """
        periods = {}
        
        # Define time periods
        time_periods = {
            'morning': (6, 12),
            'afternoon': (12, 18),
            'evening': (18, 22),
            'night': (22, 6)
        }
        
        for period_name, (start_hour, end_hour) in time_periods.items():
            if start_hour < end_hour:
                # Same day period
                period_events = events_df[
                    (events_df['time'].dt.hour >= start_hour) & 
                    (events_df['time'].dt.hour < end_hour)
                ]
            else:
                # Overnight period
                period_events = events_df[
                    (events_df['time'].dt.hour >= start_hour) | 
                    (events_df['time'].dt.hour < end_hour)
                ]
            
            if len(period_events) > 0:
                periods[period_name] = period_events
        
        return periods
    
    def _calculate_session_confidence(self, session: Dict) -> float:
        """
        Calculate confidence for session patterns.
        
        Args:
            session: Session dictionary
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from session length
        base_confidence = min(len(session['events']) / 10.0, 1.0)
        
        # Duration bonus (optimal duration range)
        duration_minutes = session['duration_minutes']
        duration_bonus = 0.0
        if 15 <= duration_minutes <= 120:  # 15 minutes to 2 hours
            duration_bonus = 0.2
        elif 5 <= duration_minutes <= 240:  # 5 minutes to 4 hours
            duration_bonus = 0.1
        
        # Activity intensity bonus
        intensity = session['activity_intensity']
        intensity_bonus = min(intensity / 10.0, 0.2)  # Max 20% bonus
        
        # Device diversity bonus
        device_diversity = len(session['devices']) / max(len(session['events']), 1)
        diversity_bonus = min(device_diversity * 0.3, 0.3)  # Max 30% bonus
        
        total_confidence = base_confidence + duration_bonus + intensity_bonus + diversity_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_routine_confidence(self, period_events: pd.DataFrame, period: str) -> float:
        """
        Calculate confidence for routine patterns.
        
        Args:
            period_events: Events in time period
            period: Time period name
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from occurrences
        base_confidence = min(len(period_events) / 15.0, 1.0)
        
        # Consistency bonus
        consistency = self._calculate_routine_consistency(period_events)
        consistency_bonus = consistency * 0.3
        
        # Frequency bonus
        frequency = self._calculate_activity_frequency(period_events)
        frequency_bonus = min(frequency * 0.2, 0.2)
        
        total_confidence = base_confidence + consistency_bonus + frequency_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_routine_consistency(self, period_events: pd.DataFrame) -> float:
        """
        Calculate routine consistency.
        
        Args:
            period_events: Events in time period
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        if len(period_events) < 2:
            return 0.0
        
        # Calculate time consistency
        times = period_events['time'].dt.time
        time_diffs = []
        
        for i in range(len(times) - 1):
            diff = (times.iloc[i+1] - times.iloc[i]).total_seconds()
            time_diffs.append(diff)
        
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
    
    def _calculate_activity_frequency(self, period_events: pd.DataFrame) -> float:
        """
        Calculate activity frequency.
        
        Args:
            period_events: Events in time period
            
        Returns:
            Frequency score
        """
        if len(period_events) == 0:
            return 0.0
        
        # Calculate events per day
        unique_days = period_events['time'].dt.date.nunique()
        if unique_days == 0:
            return 0.0
        
        return len(period_events) / unique_days
    
    def _calculate_routine_duration(self, period_events: pd.DataFrame) -> float:
        """
        Calculate routine duration in hours.
        
        Args:
            period_events: Events in time period
            
        Returns:
            Duration in hours
        """
        if len(period_events) == 0:
            return 0.0
        
        start_time = period_events['time'].min()
        end_time = period_events['time'].max()
        
        return (end_time - start_time).total_seconds() / 3600
    
    def _extract_session_features(self, events_df: pd.DataFrame) -> np.ndarray:
        """
        Extract features for session clustering.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Feature matrix for clustering
        """
        features = []
        
        # Group events by day and extract daily features
        events_df['date'] = events_df['time'].dt.date
        
        for date, day_events in events_df.groupby('date'):
            # Extract daily session features
            feature_vector = [
                len(day_events),  # Total events
                day_events['entity_id'].nunique(),  # Unique devices
                day_events['time'].dt.hour.nunique(),  # Active hours
                day_events['time'].dt.hour.min(),  # First activity hour
                day_events['time'].dt.hour.max(),  # Last activity hour
                day_events['time'].dt.hour.max() - day_events['time'].dt.hour.min(),  # Activity span
                day_events.get('area', pd.Series(['unknown'])).nunique()  # Unique rooms
            ]
            features.append(feature_vector)
        
        return np.array(features) if features else np.array([])
    
    def _calculate_cluster_confidence(self, cluster_sessions: np.ndarray, cluster_id: int) -> float:
        """
        Calculate confidence for session clusters.
        
        Args:
            cluster_sessions: Sessions in cluster
            cluster_id: Cluster identifier
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        occurrences = len(cluster_sessions)
        base_confidence = min(occurrences / 10.0, 1.0)
        
        # Cluster cohesion bonus
        if len(cluster_sessions) > 1:
            # Calculate variance in features
            feature_variance = np.var(cluster_sessions, axis=0)
            avg_variance = np.mean(feature_variance)
            cohesion_bonus = max(0.0, 1.0 - avg_variance) * 0.2
            base_confidence += cohesion_bonus
        
        return min(base_confidence, 1.0)
    
    def _describe_cluster_characteristics(self, cluster_sessions: np.ndarray) -> Dict[str, Any]:
        """
        Describe cluster characteristics.
        
        Args:
            cluster_sessions: Sessions in cluster
            
        Returns:
            Cluster characteristics
        """
        return {
            'session_count': len(cluster_sessions),
            'avg_events_per_session': np.mean(cluster_sessions[:, 0]) if len(cluster_sessions) > 0 else 0,
            'avg_devices_per_session': np.mean(cluster_sessions[:, 1]) if len(cluster_sessions) > 0 else 0,
            'avg_active_hours': np.mean(cluster_sessions[:, 2]) if len(cluster_sessions) > 0 else 0,
            'avg_activity_span': np.mean(cluster_sessions[:, 5]) if len(cluster_sessions) > 0 else 0
        }
    
    def _calculate_session_diversity(self, cluster_sessions: np.ndarray) -> float:
        """
        Calculate session diversity within cluster.
        
        Args:
            cluster_sessions: Sessions in cluster
            
        Returns:
            Diversity score (0.0 to 1.0)
        """
        if len(cluster_sessions) < 2:
            return 0.0
        
        # Calculate coefficient of variation for each feature
        cv_scores = []
        for i in range(cluster_sessions.shape[1]):
            feature_values = cluster_sessions[:, i]
            if np.mean(feature_values) > 0:
                cv = np.std(feature_values) / np.mean(feature_values)
                cv_scores.append(cv)
        
        # Higher CV = more diversity
        avg_cv = np.mean(cv_scores) if cv_scores else 0.0
        diversity = min(avg_cv, 1.0)
        
        return diversity
    
    def _analyze_temporal_patterns(self, events_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Analyze temporal patterns in events.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Dictionary of temporal patterns
        """
        patterns = {}
        
        # Analyze hourly patterns
        hourly_counts = events_df['time'].dt.hour.value_counts()
        if len(hourly_counts) > 0:
            peak_hour = hourly_counts.index[0]
            patterns['hourly_peak'] = {
                'occurrences': len(events_df),
                'frequency': hourly_counts.iloc[0],
                'consistency': self._calculate_hourly_consistency(events_df),
                'time_distribution': hourly_counts.to_dict(),
                'devices': list(events_df['entity_id'].unique()),
                'first_occurrence': events_df['time'].min(),
                'last_occurrence': events_df['time'].max(),
                'duration_analysis': self._analyze_duration_patterns(events_df)
            }
        
        return patterns
    
    def _calculate_hourly_consistency(self, events_df: pd.DataFrame) -> float:
        """
        Calculate hourly consistency.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        if len(events_df) < 2:
            return 0.0
        
        # Calculate consistency of hourly distribution
        hourly_counts = events_df['time'].dt.hour.value_counts()
        
        if len(hourly_counts) < 2:
            return 1.0
        
        # Calculate coefficient of variation
        mean_count = hourly_counts.mean()
        std_count = hourly_counts.std()
        
        if mean_count == 0:
            return 0.0
        
        cv = std_count / mean_count
        consistency = max(0.0, 1.0 - cv)
        
        return min(consistency, 1.0)
    
    def _analyze_duration_patterns(self, events_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze duration patterns in events.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Duration analysis
        """
        if len(events_df) < 2:
            return {'avg_duration': 0, 'duration_consistency': 0}
        
        # Calculate time differences
        time_diffs = events_df['time'].diff().dt.total_seconds().dropna()
        
        if len(time_diffs) == 0:
            return {'avg_duration': 0, 'duration_consistency': 0}
        
        avg_duration = time_diffs.mean()
        duration_consistency = 1.0 - (time_diffs.std() / time_diffs.mean()) if time_diffs.mean() > 0 else 0.0
        
        return {
            'avg_duration': avg_duration,
            'duration_consistency': max(0.0, duration_consistency)
        }
    
    def _calculate_temporal_pattern_confidence(self, pattern_data: Dict[str, Any]) -> float:
        """
        Calculate confidence for temporal patterns.
        
        Args:
            pattern_data: Temporal pattern data
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from occurrences
        base_confidence = min(pattern_data['occurrences'] / 20.0, 1.0)
        
        # Consistency bonus
        consistency = pattern_data.get('consistency', 0.0)
        consistency_bonus = consistency * 0.3
        
        # Frequency bonus
        frequency = pattern_data.get('frequency', 0)
        frequency_bonus = min(frequency / 50.0, 0.2)
        
        total_confidence = base_confidence + consistency_bonus + frequency_bonus
        
        return min(total_confidence, 1.0)
    
    def _cluster_session_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """
        Cluster similar session patterns using ML.
        
        Args:
            patterns: List of session patterns
            
        Returns:
            Clustered patterns with cluster information
        """
        if len(patterns) < 3:
            return patterns
        
        try:
            # Extract features for clustering
            features = self._extract_session_pattern_features(patterns)
            
            # Cluster patterns
            patterns = self._cluster_patterns(patterns, features)
            
            logger.info(f"Clustered {len(patterns)} session patterns")
            
        except Exception as e:
            logger.warning(f"Session pattern clustering failed: {e}")
        
        return patterns
    
    def _extract_session_pattern_features(self, patterns: List[Dict]) -> np.ndarray:
        """
        Extract features for session pattern clustering.
        
        Args:
            patterns: List of session patterns
            
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
                metadata.get('session_duration_minutes', 0),
                metadata.get('activity_intensity', 0),
                metadata.get('device_count', 0),
                metadata.get('routine_consistency', 0),
                metadata.get('activity_frequency', 0)
            ]
            
            # Add pattern type encoding
            pattern_type = pattern['pattern_type']
            type_encoding = {
                'user_session': 0,
                'routine': 1,
                'session_cluster': 2,
                'temporal_hourly_peak': 3
            }.get(pattern_type, 0)
            feature_vector.append(type_encoding)
            
            features.append(feature_vector)
        
        return np.array(features)

    def _store_weekly_aggregates(self, patterns: List[Dict], events_df: pd.DataFrame) -> None:
        """
        Store weekly aggregates to InfluxDB.
        
        Story AI5.6: Incremental pattern processing with weekly aggregate storage.
        
        Args:
            patterns: List of detected patterns
            events_df: Original events DataFrame
        """
        try:
            # Get week identifier from events
            if events_df.empty or 'time' not in events_df.columns:
                logger.warning("Cannot determine week from events for aggregate storage")
                return
            
            # Use ISO week format (YYYY-WW)
            first_date = pd.to_datetime(events_df['time'].min())
            week_str = first_date.strftime('%Y-W%V')
            
            logger.info(f"Storing weekly aggregates for {week_str}")
            
            for pattern in patterns:
                session_type = pattern.get('metadata', {}).get('session_type', 'general')
                avg_duration = pattern.get('metadata', {}).get('session_duration_minutes', 0) * 60  # Convert to seconds
                session_count = pattern.get('occurrences', 0)
                devices_used = pattern.get('devices', [])
                
                # Calculate typical start times from pattern metadata
                start_time_str = pattern.get('metadata', {}).get('session_start', '')
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        typical_start_times = [start_time.hour]
                    except:
                        typical_start_times = []
                else:
                    typical_start_times = []
                
                confidence = pattern.get('confidence', 0.0)
                
                # Store aggregate
                try:
                    self.aggregate_client.write_session_weekly(
                        week=week_str,
                        session_type=session_type,
                        avg_session_duration=avg_duration,
                        session_count=session_count,
                        typical_start_times=typical_start_times,
                        devices_used=devices_used,
                        confidence=confidence
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {session_type}: {e}", exc_info=True)
            
            logger.info(f"✅ Stored {len(patterns)} weekly aggregates to InfluxDB")
            
        except Exception as e:
            logger.error(f"Error storing weekly aggregates: {e}", exc_info=True)
