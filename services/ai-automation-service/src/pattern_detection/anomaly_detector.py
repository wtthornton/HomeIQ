"""
Anomaly Pattern Detector

Detects unusual behavior patterns using statistical analysis and ML-based anomaly detection.
Identifies outliers, unusual timing, and unexpected device behavior.

Story AI5.3: Converted to incremental processing with aggregate storage.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class AnomalyDetector(MLPatternDetector):
    """
    Detects anomaly patterns in device behavior.
    
    Analyzes patterns based on:
    - Statistical outliers
    - Unusual timing patterns
    - Unexpected device combinations
    - Behavioral deviations
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        min_anomaly_occurrences: int = 3,
        anomaly_window_hours: int = 24,
        enable_timing_analysis: bool = True,
        enable_behavioral_analysis: bool = True,
        enable_device_analysis: bool = True,
        aggregate_client=None,
        **kwargs
    ):
        """
        Initialize anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
            min_anomaly_occurrences: Minimum occurrences for valid anomalies
            anomaly_window_hours: Window for anomaly analysis
            enable_timing_analysis: Whether to analyze timing anomalies
            enable_behavioral_analysis: Whether to analyze behavioral anomalies
            enable_device_analysis: Whether to analyze device anomalies
            aggregate_client: PatternAggregateClient for storing daily aggregates (Story AI5.3)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.contamination = contamination
        self.min_anomaly_occurrences = min_anomaly_occurrences
        self.anomaly_window_hours = anomaly_window_hours
        self.enable_timing_analysis = enable_timing_analysis
        self.enable_behavioral_analysis = enable_behavioral_analysis
        self.enable_device_analysis = enable_device_analysis
        self.aggregate_client = aggregate_client
        
        logger.info(f"AnomalyDetector initialized: contamination={contamination}, min_occurrences={min_anomaly_occurrences}")
    
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect anomaly patterns in events.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state columns
            
        Returns:
            List of anomaly pattern dictionaries
        """
        start_time = datetime.utcnow()
        
        if not self._validate_events_dataframe(events_df):
            return []
        
        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)
        
        # Add anomaly features
        events_df = self._add_anomaly_features(events_df)
        
        # Detect different types of anomalies
        patterns = []
        
        # 1. Statistical outliers
        outlier_patterns = self._detect_statistical_outliers(events_df)
        patterns.extend(outlier_patterns)
        
        # 2. Timing anomalies
        if self.enable_timing_analysis:
            timing_patterns = self._detect_timing_anomalies(events_df)
            patterns.extend(timing_patterns)
        
        # 3. Behavioral anomalies
        if self.enable_behavioral_analysis:
            behavioral_patterns = self._detect_behavioral_anomalies(events_df)
            patterns.extend(behavioral_patterns)
        
        # 4. Device anomalies
        if self.enable_device_analysis:
            device_patterns = self._detect_device_anomalies(events_df)
            patterns.extend(device_patterns)
        
        # 5. ML-based anomaly detection
        if self.enable_ml and len(events_df) > 10:
            ml_patterns = self._detect_ml_anomalies(events_df)
            patterns.extend(ml_patterns)
        
        # Cluster similar anomalies using ML
        if self.enable_ml and len(patterns) > 2:
            patterns = self._cluster_anomaly_patterns(patterns)
        
        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats['total_patterns'] += len(patterns)
        self.detection_stats['processing_time'] += processing_time
        
        logger.info(f"Detected {len(patterns)} anomaly patterns in {processing_time:.2f}s")
        
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
                entity_id = pattern.get('entity_id', pattern.get('devices', ['unknown'])[0] if pattern.get('devices') else 'unknown')
                domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                
                # Calculate metrics
                occurrences = pattern.get('occurrences', 0)
                confidence = pattern.get('confidence', 0.0)
                anomaly_score = pattern.get('metadata', {}).get('anomaly_score', 0.0)
                
                # Store aggregate
                try:
                    self.aggregate_client.write_anomaly_daily(
                        date=date_str,
                        entity_id=entity_id,
                        domain=domain,
                        occurrences=occurrences,
                        confidence=confidence,
                        anomaly_score=anomaly_score
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {entity_id}: {e}", exc_info=True)
            
            logger.info(f"✅ Stored {len(patterns)} daily aggregates to InfluxDB")
            
        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
    
    def _add_anomaly_features(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add anomaly features to events DataFrame.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            DataFrame with anomaly features
        """
        df = events_df.copy()
        
        # Time-based features
        df['hour'] = df['time'].dt.hour
        df['dayofweek'] = df['time'].dt.dayofweek
        df['dayofyear'] = df['time'].dt.dayofyear
        df['is_weekend'] = df['dayofweek'].isin([5, 6])
        df['is_night'] = (df['hour'] >= 22) | (df['hour'] <= 6)
        df['is_work_hours'] = (df['hour'] >= 9) & (df['hour'] <= 17)
        
        # Event frequency features
        df['events_per_hour'] = df.groupby(df['time'].dt.floor('H'))['entity_id'].transform('count')
        df['events_per_day'] = df.groupby(df['time'].dt.date)['entity_id'].transform('count')
        
        # Device activity features
        df['device_activity_count'] = df.groupby('entity_id')['entity_id'].transform('count')
        df['device_daily_activity'] = df.groupby(['entity_id', df['time'].dt.date])['entity_id'].transform('count')
        
        # State change features
        df['state_changes'] = df.groupby('entity_id')['state'].transform(lambda x: (x != x.shift()).sum())
        df['unique_states'] = df.groupby('entity_id')['state'].transform('nunique')
        
        # Temporal features
        df['time_since_last_event'] = df.groupby('entity_id')['time'].diff().dt.total_seconds()
        df['time_since_last_event'] = df['time_since_last_event'].fillna(0)
        
        # Interaction features
        df['concurrent_events'] = df.groupby(df['time'].dt.floor('min'))['entity_id'].transform('count')
        df['device_interactions'] = df.groupby('entity_id')['concurrent_events'].transform('mean')
        
        return df
    
    def _detect_statistical_outliers(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect statistical outliers using Isolation Forest.
        
        Args:
            events_df: Events DataFrame with anomaly features
            
        Returns:
            List of statistical outlier patterns
        """
        patterns = []
        
        # Extract numerical features for outlier detection
        feature_columns = [
            'hour', 'dayofweek', 'events_per_hour', 'events_per_day',
            'device_activity_count', 'device_daily_activity', 'state_changes',
            'unique_states', 'time_since_last_event', 'concurrent_events'
        ]
        
        # Filter out non-numeric columns and handle missing values
        available_features = [col for col in feature_columns if col in events_df.columns]
        if not available_features:
            return patterns
        
        # Prepare features
        features = events_df[available_features].fillna(0)
        
        if len(features) < 10:
            return patterns
        
        try:
            # Use Isolation Forest for outlier detection
            isolation_forest = IsolationForest(
                contamination=self.contamination,
                random_state=42
            )
            
            outlier_labels = isolation_forest.fit_predict(features)
            outlier_scores = isolation_forest.decision_function(features)
            
            # Get outlier events
            outlier_events = events_df[outlier_labels == -1]
            
            if len(outlier_events) < self.min_anomaly_occurrences:
                return patterns
            
            # Group outliers by entity
            for entity_id, entity_outliers in outlier_events.groupby('entity_id'):
                if len(entity_outliers) < self.min_anomaly_occurrences:
                    continue
                
                # Calculate anomaly characteristics
                anomaly_analysis = self._analyze_anomaly_characteristics(entity_outliers, 'statistical_outlier')
                
                # Calculate confidence
                confidence = self._calculate_anomaly_confidence(anomaly_analysis, outlier_scores[outlier_labels == -1])
                
                if confidence >= self.min_confidence:
                    pattern = self._create_pattern_dict(
                        pattern_type='statistical_outlier',
                        pattern_id=self._generate_pattern_id('statistical_outlier'),
                        confidence=confidence,
                        occurrences=len(entity_outliers),
                        devices=[entity_id],
                        metadata={
                            'anomaly_type': 'statistical_outlier',
                            'outlier_count': len(entity_outliers),
                            'avg_outlier_score': np.mean(outlier_scores[outlier_labels == -1]),
                            'min_outlier_score': np.min(outlier_scores[outlier_labels == -1]),
                            'max_outlier_score': np.max(outlier_scores[outlier_labels == -1]),
                            'anomaly_characteristics': anomaly_analysis,
                            'first_occurrence': entity_outliers['time'].min().isoformat(),
                            'last_occurrence': entity_outliers['time'].max().isoformat()
                        }
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            logger.warning(f"Statistical outlier detection failed: {e}")
        
        return patterns
    
    def _detect_timing_anomalies(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect timing anomalies.
        
        Args:
            events_df: Events DataFrame with timing features
            
        Returns:
            List of timing anomaly patterns
        """
        patterns = []
        
        # Group by entity and analyze timing patterns
        for entity_id, entity_events in events_df.groupby('entity_id'):
            if len(entity_events) < 10:
                continue
            
            # Analyze timing patterns
            timing_analysis = self._analyze_timing_patterns(entity_events)
            
            # Detect timing anomalies
            timing_anomalies = self._identify_timing_anomalies(entity_events, timing_analysis)
            
            if len(timing_anomalies) < self.min_anomaly_occurrences:
                continue
            
            # Calculate confidence
            confidence = self._calculate_timing_anomaly_confidence(timing_anomalies, timing_analysis)
            
            if confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type='timing_anomaly',
                    pattern_id=self._generate_pattern_id('timing_anomaly'),
                    confidence=confidence,
                    occurrences=len(timing_anomalies),
                    devices=[entity_id],
                    metadata={
                        'anomaly_type': 'timing_anomaly',
                        'anomaly_count': len(timing_anomalies),
                        'timing_analysis': timing_analysis,
                        'anomaly_details': timing_anomalies.to_dict('records'),
                        'first_occurrence': timing_anomalies['time'].min().isoformat(),
                        'last_occurrence': timing_anomalies['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_behavioral_anomalies(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect behavioral anomalies.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of behavioral anomaly patterns
        """
        patterns = []
        
        # Group by entity and analyze behavioral patterns
        for entity_id, entity_events in events_df.groupby('entity_id'):
            if len(entity_events) < 10:
                continue
            
            # Analyze behavioral patterns
            behavioral_analysis = self._analyze_behavioral_patterns(entity_events)
            
            # Detect behavioral anomalies
            behavioral_anomalies = self._identify_behavioral_anomalies(entity_events, behavioral_analysis)
            
            if len(behavioral_anomalies) < self.min_anomaly_occurrences:
                continue
            
            # Calculate confidence
            confidence = self._calculate_behavioral_anomaly_confidence(behavioral_anomalies, behavioral_analysis)
            
            if confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type='behavioral_anomaly',
                    pattern_id=self._generate_pattern_id('behavioral_anomaly'),
                    confidence=confidence,
                    occurrences=len(behavioral_anomalies),
                    devices=[entity_id],
                    metadata={
                        'anomaly_type': 'behavioral_anomaly',
                        'anomaly_count': len(behavioral_anomalies),
                        'behavioral_analysis': behavioral_analysis,
                        'anomaly_details': behavioral_anomalies.to_dict('records'),
                        'first_occurrence': behavioral_anomalies['time'].min().isoformat(),
                        'last_occurrence': behavioral_anomalies['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_device_anomalies(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect device anomalies.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of device anomaly patterns
        """
        patterns = []
        
        # Analyze device interaction patterns
        device_interactions = self._analyze_device_interactions(events_df)
        
        # Detect unusual device combinations
        unusual_combinations = self._identify_unusual_device_combinations(device_interactions)
        
        for combination, anomaly_data in unusual_combinations.items():
            if anomaly_data['count'] < self.min_anomaly_occurrences:
                continue
            
            # Calculate confidence
            confidence = self._calculate_device_anomaly_confidence(anomaly_data)
            
            if confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type='device_anomaly',
                    pattern_id=self._generate_pattern_id('device_anomaly'),
                    confidence=confidence,
                    occurrences=anomaly_data['count'],
                    devices=anomaly_data['devices'],
                    metadata={
                        'anomaly_type': 'device_anomaly',
                        'anomaly_count': anomaly_data['count'],
                        'device_combination': combination,
                        'interaction_analysis': anomaly_data['analysis'],
                        'first_occurrence': anomaly_data['first_occurrence'],
                        'last_occurrence': anomaly_data['last_occurrence']
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_ml_anomalies(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect ML-based anomalies using advanced algorithms.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of ML anomaly patterns
        """
        patterns = []
        
        # Extract features for ML anomaly detection
        ml_features = self._extract_ml_anomaly_features(events_df)
        
        if len(ml_features) < 10:
            return patterns
        
        try:
            # Use DBSCAN for density-based anomaly detection
            dbscan = DBSCAN(eps=0.5, min_samples=3)
            cluster_labels = dbscan.fit_predict(ml_features)
            
            # Identify noise points as anomalies
            noise_points = events_df[cluster_labels == -1]
            
            if len(noise_points) < self.min_anomaly_occurrences:
                return patterns
            
            # Group anomalies by entity
            for entity_id, entity_anomalies in noise_points.groupby('entity_id'):
                if len(entity_anomalies) < self.min_anomaly_occurrences:
                    continue
                
                # Calculate ML anomaly characteristics
                ml_analysis = self._analyze_ml_anomaly_characteristics(entity_anomalies)
                
                # Calculate confidence
                confidence = self._calculate_ml_anomaly_confidence(ml_analysis)
                
                if confidence >= self.min_confidence:
                    pattern = self._create_pattern_dict(
                        pattern_type='ml_anomaly',
                        pattern_id=self._generate_pattern_id('ml_anomaly'),
                        confidence=confidence,
                        occurrences=len(entity_anomalies),
                        devices=[entity_id],
                        metadata={
                            'anomaly_type': 'ml_anomaly',
                            'anomaly_count': len(entity_anomalies),
                            'ml_analysis': ml_analysis,
                            'first_occurrence': entity_anomalies['time'].min().isoformat(),
                            'last_occurrence': entity_anomalies['time'].max().isoformat()
                        }
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            logger.warning(f"ML anomaly detection failed: {e}")
        
        return patterns
    
    def _analyze_anomaly_characteristics(self, anomaly_events: pd.DataFrame, anomaly_type: str) -> Dict[str, Any]:
        """
        Analyze anomaly characteristics.
        
        Args:
            anomaly_events: Anomaly events
            anomaly_type: Type of anomaly
            
        Returns:
            Anomaly analysis
        """
        # Basic statistics
        event_count = len(anomaly_events)
        device_count = anomaly_events['entity_id'].nunique()
        
        # Time analysis
        time_span_hours = (anomaly_events['time'].max() - anomaly_events['time'].min()).total_seconds() / 3600
        activity_intensity = event_count / max(time_span_hours, 1)
        
        # State analysis
        unique_states = anomaly_events['state'].nunique()
        state_distribution = anomaly_events['state'].value_counts().to_dict()
        
        # Timing analysis
        hourly_distribution = anomaly_events['time'].dt.hour.value_counts().to_dict()
        peak_hour = max(hourly_distribution, key=hourly_distribution.get) if hourly_distribution else 0
        
        # Weekend analysis
        weekend_events = anomaly_events[anomaly_events['is_weekend']]
        weekend_ratio = len(weekend_events) / max(event_count, 1)
        
        # Night analysis
        night_events = anomaly_events[anomaly_events['is_night']]
        night_ratio = len(night_events) / max(event_count, 1)
        
        return {
            'event_count': event_count,
            'device_count': device_count,
            'activity_intensity': activity_intensity,
            'unique_states': unique_states,
            'state_distribution': state_distribution,
            'peak_hour': peak_hour,
            'weekend_ratio': weekend_ratio,
            'night_ratio': night_ratio
        }
    
    def _analyze_timing_patterns(self, entity_events: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze timing patterns for an entity.
        
        Args:
            entity_events: Events for entity
            
        Returns:
            Timing analysis
        """
        # Hourly patterns
        hourly_counts = entity_events['time'].dt.hour.value_counts()
        peak_hours = hourly_counts.head(3).index.tolist()
        
        # Daily patterns
        daily_counts = entity_events['time'].dt.dayofweek.value_counts()
        peak_days = daily_counts.head(3).index.tolist()
        
        # Time between events
        time_diffs = entity_events['time'].diff().dt.total_seconds()
        avg_time_between = time_diffs.mean()
        std_time_between = time_diffs.std()
        
        # Weekend vs weekday
        weekend_events = entity_events[entity_events['is_weekend']]
        weekday_events = entity_events[~entity_events['is_weekend']]
        
        weekend_ratio = len(weekend_events) / max(len(entity_events), 1)
        weekday_ratio = len(weekday_events) / max(len(entity_events), 1)
        
        return {
            'peak_hours': peak_hours,
            'peak_days': peak_days,
            'avg_time_between': avg_time_between,
            'std_time_between': std_time_between,
            'weekend_ratio': weekend_ratio,
            'weekday_ratio': weekday_ratio
        }
    
    def _identify_timing_anomalies(self, entity_events: pd.DataFrame, timing_analysis: Dict[str, Any]) -> pd.DataFrame:
        """
        Identify timing anomalies based on analysis.
        
        Args:
            entity_events: Events for entity
            timing_analysis: Timing analysis results
            
        Returns:
            DataFrame of timing anomalies
        """
        anomalies = []
        
        # Identify events outside peak hours
        peak_hours = set(timing_analysis['peak_hours'])
        non_peak_events = entity_events[~entity_events['time'].dt.hour.isin(peak_hours)]
        
        if len(non_peak_events) > 0:
            anomalies.append(non_peak_events)
        
        # Identify events with unusual timing
        avg_time_between = timing_analysis['avg_time_between']
        std_time_between = timing_analysis['std_time_between']
        
        if not pd.isna(avg_time_between) and not pd.isna(std_time_between):
            time_diffs = entity_events['time'].diff().dt.total_seconds()
            unusual_timing = entity_events[
                (time_diffs < (avg_time_between - 2 * std_time_between)) |
                (time_diffs > (avg_time_between + 2 * std_time_between))
            ]
            
            if len(unusual_timing) > 0:
                anomalies.append(unusual_timing)
        
        # Combine all anomalies
        if anomalies:
            return pd.concat(anomalies).drop_duplicates()
        else:
            return pd.DataFrame()
    
    def _analyze_behavioral_patterns(self, entity_events: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze behavioral patterns for an entity.
        
        Args:
            entity_events: Events for entity
            
        Returns:
            Behavioral analysis
        """
        # State patterns
        state_counts = entity_events['state'].value_counts()
        most_common_state = state_counts.index[0] if len(state_counts) > 0 else 'unknown'
        state_diversity = len(state_counts)
        
        # State transitions
        state_transitions = entity_events['state'].ne(entity_events['state'].shift()).sum()
        transition_rate = state_transitions / max(len(entity_events), 1)
        
        # Activity patterns
        daily_activity = entity_events.groupby(entity_events['time'].dt.date).size()
        avg_daily_activity = daily_activity.mean()
        std_daily_activity = daily_activity.std()
        
        # Concurrent activity
        concurrent_events = entity_events['concurrent_events'].mean()
        max_concurrent = entity_events['concurrent_events'].max()
        
        return {
            'most_common_state': most_common_state,
            'state_diversity': state_diversity,
            'transition_rate': transition_rate,
            'avg_daily_activity': avg_daily_activity,
            'std_daily_activity': std_daily_activity,
            'concurrent_events': concurrent_events,
            'max_concurrent': max_concurrent
        }
    
    def _identify_behavioral_anomalies(self, entity_events: pd.DataFrame, behavioral_analysis: Dict[str, Any]) -> pd.DataFrame:
        """
        Identify behavioral anomalies based on analysis.
        
        Args:
            entity_events: Events for entity
            behavioral_analysis: Behavioral analysis results
            
        Returns:
            DataFrame of behavioral anomalies
        """
        anomalies = []
        
        # Identify unusual state patterns
        most_common_state = behavioral_analysis['most_common_state']
        unusual_states = entity_events[entity_events['state'] != most_common_state]
        
        if len(unusual_states) > 0:
            anomalies.append(unusual_states)
        
        # Identify unusual activity levels
        avg_daily_activity = behavioral_analysis['avg_daily_activity']
        std_daily_activity = behavioral_analysis['std_daily_activity']
        
        if not pd.isna(avg_daily_activity) and not pd.isna(std_daily_activity):
            daily_activity = entity_events.groupby(entity_events['time'].dt.date).size()
            unusual_activity = daily_activity[
                (daily_activity < (avg_daily_activity - 2 * std_daily_activity)) |
                (daily_activity > (avg_daily_activity + 2 * std_daily_activity))
            ]
            
            if len(unusual_activity) > 0:
                # Get events for unusual activity days
                unusual_days = unusual_activity.index
                unusual_events = entity_events[entity_events['time'].dt.date.isin(unusual_days)]
                anomalies.append(unusual_events)
        
        # Combine all anomalies
        if anomalies:
            return pd.concat(anomalies).drop_duplicates()
        else:
            return pd.DataFrame()
    
    def _analyze_device_interactions(self, events_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze device interactions.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Device interaction analysis
        """
        interactions = defaultdict(list)
        
        # Group events by time windows
        for time_window, window_events in events_df.groupby(events_df['time'].dt.floor('min')):
            devices = window_events['entity_id'].unique()
            
            # Record device combinations
            for i, device1 in enumerate(devices):
                for device2 in devices[i+1:]:
                    combination = tuple(sorted([device1, device2]))
                    interactions[combination].append(time_window)
        
        # Analyze interaction patterns
        interaction_analysis = {}
        for combination, timestamps in interactions.items():
            interaction_analysis[combination] = {
                'count': len(timestamps),
                'devices': list(combination),
                'first_occurrence': min(timestamps).isoformat(),
                'last_occurrence': max(timestamps).isoformat(),
                'frequency': len(timestamps) / max(len(events_df), 1)
            }
        
        return interaction_analysis
    
    def _identify_unusual_device_combinations(self, device_interactions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify unusual device combinations.
        
        Args:
            device_interactions: Device interaction analysis
            
        Returns:
            Dictionary of unusual combinations
        """
        unusual_combinations = {}
        
        # Calculate interaction frequencies
        frequencies = [data['frequency'] for data in device_interactions.values()]
        if not frequencies:
            return unusual_combinations
        
        # Identify low-frequency combinations as unusual
        threshold = np.percentile(frequencies, 10)  # Bottom 10% as unusual
        
        for combination, data in device_interactions.items():
            if data['frequency'] < threshold and data['count'] >= self.min_anomaly_occurrences:
                unusual_combinations[combination] = data
        
        return unusual_combinations
    
    def _extract_ml_anomaly_features(self, events_df: pd.DataFrame) -> np.ndarray:
        """
        Extract features for ML anomaly detection.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Feature matrix for ML anomaly detection
        """
        features = []
        
        # Group by entity and extract features
        for entity_id, entity_events in events_df.groupby('entity_id'):
            if len(entity_events) < 3:
                continue
            
            # Extract entity-level features
            feature_vector = [
                len(entity_events),  # Event count
                entity_events['state'].nunique(),  # State diversity
                entity_events['time'].dt.hour.nunique(),  # Active hours
                entity_events['is_weekend'].mean(),  # Weekend ratio
                entity_events['is_night'].mean(),  # Night ratio
                entity_events['concurrent_events'].mean(),  # Concurrent events
                entity_events['time_since_last_event'].mean(),  # Avg time between events
                entity_events['device_activity_count'].iloc[0],  # Total device activity
                entity_events['state_changes'].iloc[0],  # State changes
                entity_events['unique_states'].iloc[0]  # Unique states
            ]
            
            features.append(feature_vector)
        
        return np.array(features) if features else np.array([])
    
    def _analyze_ml_anomaly_characteristics(self, anomaly_events: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze ML anomaly characteristics.
        
        Args:
            anomaly_events: ML anomaly events
            
        Returns:
            ML anomaly analysis
        """
        # Basic statistics
        event_count = len(anomaly_events)
        device_count = anomaly_events['entity_id'].nunique()
        
        # Feature analysis
        feature_analysis = {
            'avg_concurrent_events': anomaly_events['concurrent_events'].mean(),
            'max_concurrent_events': anomaly_events['concurrent_events'].max(),
            'avg_time_between_events': anomaly_events['time_since_last_event'].mean(),
            'state_diversity': anomaly_events['state'].nunique(),
            'weekend_ratio': anomaly_events['is_weekend'].mean(),
            'night_ratio': anomaly_events['is_night'].mean()
        }
        
        return {
            'event_count': event_count,
            'device_count': device_count,
            'feature_analysis': feature_analysis
        }
    
    def _calculate_anomaly_confidence(self, anomaly_analysis: Dict[str, Any], outlier_scores: np.ndarray) -> float:
        """
        Calculate confidence for anomaly patterns.
        
        Args:
            anomaly_analysis: Anomaly analysis results
            outlier_scores: Outlier scores from ML model
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from outlier scores
        base_confidence = np.mean(np.abs(outlier_scores))
        
        # Activity intensity bonus
        activity_bonus = min(anomaly_analysis['activity_intensity'] / 5.0, 0.3)
        
        # State diversity bonus
        diversity_bonus = min(anomaly_analysis['unique_states'] / 5.0, 0.2)
        
        total_confidence = base_confidence + activity_bonus + diversity_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_timing_anomaly_confidence(self, timing_anomalies: pd.DataFrame, timing_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence for timing anomalies.
        
        Args:
            timing_anomalies: Timing anomaly events
            timing_analysis: Timing analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from anomaly count
        base_confidence = min(len(timing_anomalies) / 10.0, 1.0)
        
        # Weekend/night ratio bonus
        weekend_bonus = timing_analysis['weekend_ratio'] * 0.2
        night_bonus = timing_analysis['night_ratio'] * 0.2
        
        total_confidence = base_confidence + weekend_bonus + night_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_behavioral_anomaly_confidence(self, behavioral_anomalies: pd.DataFrame, behavioral_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence for behavioral anomalies.
        
        Args:
            behavioral_anomalies: Behavioral anomaly events
            behavioral_analysis: Behavioral analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from anomaly count
        base_confidence = min(len(behavioral_anomalies) / 10.0, 1.0)
        
        # State diversity bonus
        diversity_bonus = min(behavioral_analysis['state_diversity'] / 5.0, 0.3)
        
        # Transition rate bonus
        transition_bonus = min(behavioral_analysis['transition_rate'] / 2.0, 0.2)
        
        total_confidence = base_confidence + diversity_bonus + transition_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_device_anomaly_confidence(self, anomaly_data: Dict[str, Any]) -> float:
        """
        Calculate confidence for device anomalies.
        
        Args:
            anomaly_data: Device anomaly data
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from anomaly count
        base_confidence = min(anomaly_data['count'] / 10.0, 1.0)
        
        # Frequency bonus (lower frequency = more unusual)
        frequency_bonus = (1.0 - anomaly_data['analysis']['frequency']) * 0.3
        
        total_confidence = base_confidence + frequency_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_ml_anomaly_confidence(self, ml_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence for ML anomalies.
        
        Args:
            ml_analysis: ML anomaly analysis
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from event count
        base_confidence = min(ml_analysis['event_count'] / 10.0, 1.0)
        
        # Feature analysis bonus
        feature_analysis = ml_analysis['feature_analysis']
        feature_bonus = 0.0
        
        # Concurrent events bonus
        if feature_analysis['avg_concurrent_events'] > 2:
            feature_bonus += 0.2
        
        # State diversity bonus
        if feature_analysis['state_diversity'] > 3:
            feature_bonus += 0.2
        
        # Weekend/night ratio bonus
        if feature_analysis['weekend_ratio'] > 0.5 or feature_analysis['night_ratio'] > 0.5:
            feature_bonus += 0.1
        
        total_confidence = base_confidence + feature_bonus
        
        return min(total_confidence, 1.0)
    
    def _cluster_anomaly_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """
        Cluster similar anomaly patterns using ML.
        
        Args:
            patterns: List of anomaly patterns
            
        Returns:
            Clustered patterns with cluster information
        """
        if len(patterns) < 3:
            return patterns
        
        try:
            # Extract features for clustering
            features = self._extract_anomaly_pattern_features(patterns)
            
            # Cluster patterns
            patterns = self._cluster_patterns(patterns, features)
            
            logger.info(f"Clustered {len(patterns)} anomaly patterns")
            
        except Exception as e:
            logger.warning(f"Anomaly pattern clustering failed: {e}")
        
        return patterns
    
    def _extract_anomaly_pattern_features(self, patterns: List[Dict]) -> np.ndarray:
        """
        Extract features for anomaly pattern clustering.
        
        Args:
            patterns: List of anomaly patterns
            
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
                metadata.get('anomaly_count', 0),
                metadata.get('outlier_count', 0),
                metadata.get('avg_outlier_score', 0),
                metadata.get('anomaly_characteristics', {}).get('activity_intensity', 0),
                metadata.get('anomaly_characteristics', {}).get('unique_states', 0),
                metadata.get('anomaly_characteristics', {}).get('weekend_ratio', 0),
                metadata.get('anomaly_characteristics', {}).get('night_ratio', 0)
            ]
            
            # Add pattern type encoding
            pattern_type = pattern['pattern_type']
            type_encoding = {
                'statistical_outlier': 0,
                'timing_anomaly': 1,
                'behavioral_anomaly': 2,
                'device_anomaly': 3,
                'ml_anomaly': 4
            }.get(pattern_type, 0)
            feature_vector.append(type_encoding)
            
            features.append(feature_vector)
        
        return np.array(features)
