"""
Day Type Pattern Detector

Detects weekday vs weekend patterns using temporal analysis and ML clustering.
Identifies different behavior patterns between workdays and weekends.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class DayTypeDetector(MLPatternDetector):
    """
    Detects day type patterns (weekday vs weekend).
    
    Analyzes patterns based on:
    - Weekday vs weekend behavior differences
    - Holiday pattern detection
    - Work schedule analysis
    - Lifestyle pattern recognition
    """
    
    def __init__(
        self,
        min_day_type_occurrences: int = 5,
        holiday_detection: bool = True,
        work_hours: Tuple[int, int] = (9, 17),
        **kwargs
    ):
        """
        Initialize day type detector.
        
        Args:
            min_day_type_occurrences: Minimum occurrences for valid day type patterns
            holiday_detection: Whether to detect holiday patterns
            work_hours: Work hours tuple (start, end)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.min_day_type_occurrences = min_day_type_occurrences
        self.holiday_detection = holiday_detection
        self.work_hours = work_hours
        
        logger.info(f"DayTypeDetector initialized: min_occurrences={min_day_type_occurrences}, work_hours={work_hours}")
    
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect day type patterns in events.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state columns
            
        Returns:
            List of day type pattern dictionaries
        """
        start_time = datetime.utcnow()
        
        if not self._validate_events_dataframe(events_df):
            return []
        
        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)
        
        # Add day type features
        events_df = self._add_day_type_features(events_df)
        
        # Detect different types of day patterns
        patterns = []
        
        # 1. Weekday vs weekend patterns
        weekday_weekend_patterns = self._detect_weekday_weekend_patterns(events_df)
        patterns.extend(weekday_weekend_patterns)
        
        # 2. Work vs non-work patterns
        work_patterns = self._detect_work_patterns(events_df)
        patterns.extend(work_patterns)
        
        # 3. Holiday patterns (if enabled)
        if self.holiday_detection:
            holiday_patterns = self._detect_holiday_patterns(events_df)
            patterns.extend(holiday_patterns)
        
        # 4. Day type clustering
        day_type_cluster_patterns = self._detect_day_type_clusters(events_df)
        patterns.extend(day_type_cluster_patterns)
        
        # Cluster similar day type patterns using ML
        if self.enable_ml and len(patterns) > 2:
            patterns = self._cluster_day_type_patterns(patterns)
        
        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats['total_patterns'] += len(patterns)
        self.detection_stats['processing_time'] += processing_time
        
        logger.info(f"Detected {len(patterns)} day type patterns in {processing_time:.2f}s")
        return patterns
    
    def _add_day_type_features(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add day type features to events DataFrame.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            DataFrame with day type features
        """
        df = events_df.copy()
        
        # Basic day type features
        df['dayofweek'] = df['time'].dt.dayofweek
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        df['is_weekday'] = (df['dayofweek'] < 5).astype(int)
        
        # Work hours
        df['is_work_hours'] = (
            (df['time'].dt.hour >= self.work_hours[0]) & 
            (df['time'].dt.hour < self.work_hours[1]) &
            (df['is_weekday'] == 1)
        ).astype(int)
        
        # Day type categories
        df['day_type'] = df['dayofweek'].map({
            0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday',
            5: 'saturday', 6: 'sunday'
        })
        
        # Work vs non-work
        df['work_status'] = df.apply(self._classify_work_status, axis=1)
        
        return df
    
    def _classify_work_status(self, row: pd.Series) -> str:
        """
        Classify work status for an event.
        
        Args:
            row: Event row
            
        Returns:
            Work status string
        """
        if row['is_weekend']:
            return 'weekend'
        elif row['is_work_hours']:
            return 'work_hours'
        else:
            return 'non_work_hours'
    
    def _detect_weekday_weekend_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect weekday vs weekend patterns.
        
        Args:
            events_df: Events DataFrame with day type features
            
        Returns:
            List of weekday/weekend patterns
        """
        patterns = []
        
        # Group by day type
        for day_type, day_events in events_df.groupby('is_weekend'):
            if len(day_events) < self.min_day_type_occurrences:
                continue
            
            # Analyze day type characteristics
            day_type_analysis = self._analyze_day_type_characteristics(day_events, day_type)
            
            # Calculate confidence
            confidence = self._calculate_day_type_confidence(day_type_analysis)
            
            if confidence >= self.min_confidence:
                pattern_type = 'weekend' if day_type else 'weekday'
                devices = list(day_events['entity_id'].unique())
                
                pattern = self._create_pattern_dict(
                    pattern_type=f'day_type_{pattern_type}',
                    pattern_id=self._generate_pattern_id(f'day_{pattern_type}'),
                    confidence=confidence,
                    occurrences=len(day_events),
                    devices=devices,
                    metadata={
                        'day_type': pattern_type,
                        'event_count': len(day_events),
                        'device_count': len(devices),
                        'avg_events_per_day': day_type_analysis['avg_events_per_day'],
                        'peak_hour': day_type_analysis['peak_hour'],
                        'activity_intensity': day_type_analysis['activity_intensity'],
                        'device_diversity': day_type_analysis['device_diversity'],
                        'time_distribution': day_type_analysis['time_distribution'],
                        'first_occurrence': day_events['time'].min().isoformat(),
                        'last_occurrence': day_events['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_work_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect work vs non-work patterns.
        
        Args:
            events_df: Events DataFrame with work features
            
        Returns:
            List of work patterns
        """
        patterns = []
        
        # Group by work status
        for work_status, work_events in events_df.groupby('work_status'):
            if len(work_events) < self.min_day_type_occurrences:
                continue
            
            # Analyze work pattern characteristics
            work_analysis = self._analyze_work_characteristics(work_events, work_status)
            
            # Calculate confidence
            confidence = self._calculate_work_confidence(work_analysis)
            
            if confidence >= self.min_confidence:
                devices = list(work_events['entity_id'].unique())
                
                pattern = self._create_pattern_dict(
                    pattern_type=f'work_{work_status}',
                    pattern_id=self._generate_pattern_id(f'work_{work_status}'),
                    confidence=confidence,
                    occurrences=len(work_events),
                    devices=devices,
                    metadata={
                        'work_status': work_status,
                        'event_count': len(work_events),
                        'device_count': len(devices),
                        'avg_events_per_day': work_analysis['avg_events_per_day'],
                        'peak_hour': work_analysis['peak_hour'],
                        'activity_intensity': work_analysis['activity_intensity'],
                        'work_efficiency': work_analysis['work_efficiency'],
                        'time_distribution': work_analysis['time_distribution'],
                        'first_occurrence': work_events['time'].min().isoformat(),
                        'last_occurrence': work_events['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_holiday_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect holiday patterns.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of holiday patterns
        """
        patterns = []
        
        # Simple holiday detection based on unusual activity patterns
        # This is a basic implementation - could be enhanced with actual holiday data
        
        # Group by date and analyze daily patterns
        events_df['date'] = events_df['time'].dt.date
        daily_stats = events_df.groupby('date').agg({
            'entity_id': 'count',
            'time': ['min', 'max']
        }).reset_index()
        
        daily_stats.columns = ['date', 'event_count', 'first_event', 'last_event']
        daily_stats['dayofweek'] = pd.to_datetime(daily_stats['date']).dt.dayofweek
        daily_stats['is_weekend'] = daily_stats['dayofweek'].isin([5, 6])
        
        # Find unusual activity days (potential holidays)
        for is_weekend in [True, False]:
            subset = daily_stats[daily_stats['is_weekend'] == is_weekend]
            
            if len(subset) < 3:
                continue
            
            # Calculate activity statistics
            mean_activity = subset['event_count'].mean()
            std_activity = subset['event_count'].std()
            
            # Find unusual days (2+ standard deviations from mean)
            threshold = mean_activity + 2 * std_activity
            unusual_days = subset[subset['event_count'] > threshold]
            
            if len(unusual_days) >= 2:  # Need at least 2 unusual days
                # Analyze unusual day patterns
                unusual_events = events_df[events_df['date'].isin(unusual_days['date'])]
                
                if len(unusual_events) >= self.min_day_type_occurrences:
                    holiday_analysis = self._analyze_holiday_characteristics(unusual_events, is_weekend)
                    
                    confidence = self._calculate_holiday_confidence(holiday_analysis)
                    
                    if confidence >= self.min_confidence:
                        pattern_type = 'holiday_weekend' if is_weekend else 'holiday_weekday'
                        devices = list(unusual_events['entity_id'].unique())
                        
                        pattern = self._create_pattern_dict(
                            pattern_type=pattern_type,
                            pattern_id=self._generate_pattern_id(pattern_type),
                            confidence=confidence,
                            occurrences=len(unusual_events),
                            devices=devices,
                            metadata={
                                'pattern_type': pattern_type,
                                'unusual_days': len(unusual_days),
                                'avg_activity_increase': holiday_analysis['activity_increase'],
                                'device_count': len(devices),
                                'peak_hour': holiday_analysis['peak_hour'],
                                'activity_intensity': holiday_analysis['activity_intensity'],
                                'first_occurrence': unusual_events['time'].min().isoformat(),
                                'last_occurrence': unusual_events['time'].max().isoformat()
                            }
                        )
                        patterns.append(pattern)
        
        return patterns
    
    def _detect_day_type_clusters(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect day type clusters using ML clustering.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of day type cluster patterns
        """
        patterns = []
        
        # Extract day type features for clustering
        day_features = self._extract_day_type_features(events_df)
        
        if len(day_features) < 3:
            return patterns
        
        try:
            from sklearn.cluster import KMeans
            
            # Determine optimal number of clusters
            n_clusters = min(4, len(day_features) // 2)
            if n_clusters < 2:
                return patterns
            
            # Cluster day types
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(day_features)
            
            # Analyze each cluster
            for cluster_id in range(n_clusters):
                cluster_days = day_features[cluster_labels == cluster_id]
                
                if len(cluster_days) < self.min_day_type_occurrences:
                    continue
                
                cluster_confidence = self._calculate_cluster_confidence(
                    cluster_days, cluster_id, kmeans
                )
                
                if cluster_confidence >= self.min_confidence:
                    pattern = self._create_pattern_dict(
                        pattern_type='day_type_cluster',
                        pattern_id=self._generate_pattern_id('day_cluster'),
                        confidence=cluster_confidence,
                        occurrences=len(cluster_days),
                        devices=[],  # Will be filled from cluster data
                        metadata={
                            'cluster_id': cluster_id,
                            'cluster_size': len(cluster_days),
                            'cluster_characteristics': self._describe_day_type_cluster(
                                cluster_days, cluster_id
                            ),
                            'cluster_centroid': kmeans.cluster_centers_[cluster_id].tolist()
                        }
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            logger.warning(f"Day type clustering failed: {e}")
        
        return patterns
    
    def _analyze_day_type_characteristics(self, day_events: pd.DataFrame, is_weekend: bool) -> Dict[str, Any]:
        """
        Analyze day type characteristics.
        
        Args:
            day_events: Events for day type
            is_weekend: Whether this is weekend data
            
        Returns:
            Day type analysis
        """
        # Basic statistics
        event_count = len(day_events)
        device_count = day_events['entity_id'].nunique()
        
        # Daily statistics
        daily_events = day_events.groupby(day_events['time'].dt.date).size()
        avg_events_per_day = daily_events.mean()
        
        # Time analysis
        hourly_counts = day_events['time'].dt.hour.value_counts()
        peak_hour = hourly_counts.index[0] if len(hourly_counts) > 0 else 0
        
        # Activity intensity (events per hour)
        time_span_hours = (day_events['time'].max() - day_events['time'].min()).total_seconds() / 3600
        activity_intensity = event_count / max(time_span_hours, 1)
        
        # Device diversity
        device_diversity = device_count / max(event_count, 1)
        
        # Time distribution
        time_distribution = hourly_counts.to_dict()
        
        return {
            'avg_events_per_day': avg_events_per_day,
            'peak_hour': peak_hour,
            'activity_intensity': activity_intensity,
            'device_diversity': device_diversity,
            'time_distribution': time_distribution
        }
    
    def _analyze_work_characteristics(self, work_events: pd.DataFrame, work_status: str) -> Dict[str, Any]:
        """
        Analyze work pattern characteristics.
        
        Args:
            work_events: Events for work status
            work_status: Work status string
            
        Returns:
            Work analysis
        """
        # Basic statistics
        event_count = len(work_events)
        device_count = work_events['entity_id'].nunique()
        
        # Daily statistics
        daily_events = work_events.groupby(work_events['time'].dt.date).size()
        avg_events_per_day = daily_events.mean()
        
        # Time analysis
        hourly_counts = work_events['time'].dt.hour.value_counts()
        peak_hour = hourly_counts.index[0] if len(hourly_counts) > 0 else 0
        
        # Activity intensity
        time_span_hours = (work_events['time'].max() - work_events['time'].min()).total_seconds() / 3600
        activity_intensity = event_count / max(time_span_hours, 1)
        
        # Work efficiency (based on activity during work hours)
        work_efficiency = 1.0
        if work_status == 'work_hours':
            # Higher efficiency = more activity during work hours
            work_efficiency = min(activity_intensity / 10.0, 1.0)
        elif work_status == 'non_work_hours':
            # Lower activity during non-work hours = higher efficiency
            work_efficiency = max(0.0, 1.0 - activity_intensity / 5.0)
        
        # Time distribution
        time_distribution = hourly_counts.to_dict()
        
        return {
            'avg_events_per_day': avg_events_per_day,
            'peak_hour': peak_hour,
            'activity_intensity': activity_intensity,
            'work_efficiency': work_efficiency,
            'time_distribution': time_distribution
        }
    
    def _analyze_holiday_characteristics(self, holiday_events: pd.DataFrame, is_weekend: bool) -> Dict[str, Any]:
        """
        Analyze holiday pattern characteristics.
        
        Args:
            holiday_events: Events for holiday periods
            is_weekend: Whether this is weekend holiday data
            
        Returns:
            Holiday analysis
        """
        # Basic statistics
        event_count = len(holiday_events)
        device_count = holiday_events['entity_id'].nunique()
        
        # Activity increase calculation
        # This would need baseline data for proper calculation
        activity_increase = 1.5  # Placeholder - would calculate from baseline
        
        # Time analysis
        hourly_counts = holiday_events['time'].dt.hour.value_counts()
        peak_hour = hourly_counts.index[0] if len(hourly_counts) > 0 else 0
        
        # Activity intensity
        time_span_hours = (holiday_events['time'].max() - holiday_events['time'].min()).total_seconds() / 3600
        activity_intensity = event_count / max(time_span_hours, 1)
        
        return {
            'activity_increase': activity_increase,
            'peak_hour': peak_hour,
            'activity_intensity': activity_intensity
        }
    
    def _extract_day_type_features(self, events_df: pd.DataFrame) -> np.ndarray:
        """
        Extract day type features for clustering.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Feature matrix for clustering
        """
        features = []
        
        # Group by date and extract daily features
        events_df['date'] = events_df['time'].dt.date
        
        for date, day_events in events_df.groupby('date'):
            # Extract daily features
            feature_vector = [
                len(day_events),  # Event count
                day_events['entity_id'].nunique(),  # Device count
                day_events['time'].dt.hour.nunique(),  # Active hours
                day_events['time'].dt.hour.min(),  # First activity hour
                day_events['time'].dt.hour.max(),  # Last activity hour
                day_events['time'].dt.hour.max() - day_events['time'].dt.hour.min(),  # Activity span
                day_events['is_weekend'].iloc[0],  # Is weekend
                day_events['is_work_hours'].sum()  # Work hours events
            ]
            features.append(feature_vector)
        
        return np.array(features) if features else np.array([])
    
    def _calculate_day_type_confidence(self, day_type_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence for day type patterns.
        
        Args:
            day_type_analysis: Day type analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from activity intensity
        base_confidence = min(day_type_analysis['activity_intensity'] / 5.0, 1.0)
        
        # Device diversity bonus
        diversity_bonus = day_type_analysis['device_diversity'] * 0.2
        
        # Consistency bonus (based on peak hour consistency)
        peak_hour = day_type_analysis['peak_hour']
        consistency_bonus = 0.1 if peak_hour in [7, 8, 9, 18, 19, 20] else 0.0  # Common activity hours
        
        total_confidence = base_confidence + diversity_bonus + consistency_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_work_confidence(self, work_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence for work patterns.
        
        Args:
            work_analysis: Work analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from activity intensity
        base_confidence = min(work_analysis['activity_intensity'] / 3.0, 1.0)
        
        # Work efficiency bonus
        efficiency_bonus = work_analysis['work_efficiency'] * 0.3
        
        total_confidence = base_confidence + efficiency_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_holiday_confidence(self, holiday_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence for holiday patterns.
        
        Args:
            holiday_analysis: Holiday analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from activity increase
        base_confidence = min(holiday_analysis['activity_increase'] / 2.0, 1.0)
        
        # Activity intensity bonus
        intensity_bonus = min(holiday_analysis['activity_intensity'] / 10.0, 0.3)
        
        total_confidence = base_confidence + intensity_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_cluster_confidence(self, cluster_days: np.ndarray, cluster_id: int, kmeans_model) -> float:
        """
        Calculate confidence for day type clusters.
        
        Args:
            cluster_days: Days in cluster
            cluster_id: Cluster identifier
            kmeans_model: Fitted KMeans model
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        occurrences = len(cluster_days)
        base_confidence = min(occurrences / 10.0, 1.0)
        
        # Cluster cohesion bonus
        try:
            distances = kmeans_model.transform(cluster_days)
            avg_distance = np.mean(distances[:, cluster_id])
            cohesion_bonus = max(0.0, 1.0 - avg_distance) * 0.3
            base_confidence += cohesion_bonus
        except Exception:
            pass
        
        return min(base_confidence, 1.0)
    
    def _describe_day_type_cluster(self, cluster_days: np.ndarray, cluster_id: int) -> Dict[str, Any]:
        """
        Describe day type cluster characteristics.
        
        Args:
            cluster_days: Days in cluster
            cluster_id: Cluster identifier
            
        Returns:
            Cluster characteristics
        """
        return {
            'cluster_id': cluster_id,
            'day_count': len(cluster_days),
            'avg_events_per_day': np.mean(cluster_days[:, 0]) if len(cluster_days) > 0 else 0,
            'avg_devices_per_day': np.mean(cluster_days[:, 1]) if len(cluster_days) > 0 else 0,
            'avg_active_hours': np.mean(cluster_days[:, 2]) if len(cluster_days) > 0 else 0,
            'avg_activity_span': np.mean(cluster_days[:, 5]) if len(cluster_days) > 0 else 0,
            'weekend_ratio': np.mean(cluster_days[:, 6]) if len(cluster_days) > 0 else 0,
            'work_hours_ratio': np.mean(cluster_days[:, 7]) if len(cluster_days) > 0 else 0
        }
    
    def _cluster_day_type_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """
        Cluster similar day type patterns using ML.
        
        Args:
            patterns: List of day type patterns
            
        Returns:
            Clustered patterns with cluster information
        """
        if len(patterns) < 3:
            return patterns
        
        try:
            # Extract features for clustering
            features = self._extract_day_type_pattern_features(patterns)
            
            # Cluster patterns
            patterns = self._cluster_patterns(patterns, features)
            
            logger.info(f"Clustered {len(patterns)} day type patterns")
            
        except Exception as e:
            logger.warning(f"Day type pattern clustering failed: {e}")
        
        return patterns
    
    def _extract_day_type_pattern_features(self, patterns: List[Dict]) -> np.ndarray:
        """
        Extract features for day type pattern clustering.
        
        Args:
            patterns: List of day type patterns
            
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
                metadata.get('event_count', 0),
                metadata.get('device_count', 0),
                metadata.get('avg_events_per_day', 0),
                metadata.get('peak_hour', 0),
                metadata.get('activity_intensity', 0),
                metadata.get('device_diversity', 0),
                metadata.get('work_efficiency', 0)
            ]
            
            # Add pattern type encoding
            pattern_type = pattern['pattern_type']
            type_encoding = {
                'day_type_weekday': 0,
                'day_type_weekend': 1,
                'work_work_hours': 2,
                'work_non_work_hours': 3,
                'work_weekend': 4,
                'holiday_weekday': 5,
                'holiday_weekend': 6,
                'day_type_cluster': 7
            }.get(pattern_type, 0)
            feature_vector.append(type_encoding)
            
            features.append(feature_vector)
        
        return np.array(features)
