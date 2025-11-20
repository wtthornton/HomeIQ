"""
Seasonal Pattern Detector

Detects seasonal behavior changes using temporal analysis and ML clustering.
Identifies patterns that change with seasons, weather, and time of year.
"""

import logging
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class SeasonalDetector(MLPatternDetector):
    """
    Detects seasonal behavior patterns.
    
    Analyzes patterns based on:
    - Seasonal behavior changes
    - Weather-based patterns
    - Daylight hour adjustments
    - Holiday season patterns
    """

    def __init__(
        self,
        min_seasonal_occurrences: int = 10,
        seasonal_window_days: int = 30,
        weather_integration: bool = True,
        aggregate_client=None,  # Story AI5.8: Monthly aggregation
        **kwargs
    ):
        """
        Initialize seasonal detector.
        
        Args:
            min_seasonal_occurrences: Minimum occurrences for valid seasonal patterns
            seasonal_window_days: Window for seasonal analysis
            weather_integration: Whether to integrate weather data
            aggregate_client: PatternAggregateClient for storing monthly aggregates (Story AI5.8)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.min_seasonal_occurrences = min_seasonal_occurrences
        self.seasonal_window_days = seasonal_window_days
        self.weather_integration = weather_integration
        self.aggregate_client = aggregate_client  # Story AI5.8

        logger.info(f"SeasonalDetector initialized: min_occurrences={min_seasonal_occurrences}, window={seasonal_window_days}days")

    def detect_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect seasonal patterns in events.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state columns
            
        Returns:
            List of seasonal pattern dictionaries
        """
        start_time = datetime.utcnow()

        if not self._validate_events_dataframe(events_df):
            return []

        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)

        # Add seasonal features
        events_df = self._add_seasonal_features(events_df)

        # Detect different types of seasonal patterns
        patterns = []

        # 1. Seasonal behavior changes
        seasonal_change_patterns = self._detect_seasonal_changes(events_df)
        patterns.extend(seasonal_change_patterns)

        # 2. Weather-based patterns
        if self.weather_integration:
            weather_patterns = self._detect_weather_patterns(events_df)
            patterns.extend(weather_patterns)

        # 3. Daylight patterns
        daylight_patterns = self._detect_daylight_patterns(events_df)
        patterns.extend(daylight_patterns)

        # 4. Seasonal clustering
        seasonal_cluster_patterns = self._detect_seasonal_clusters(events_df)
        patterns.extend(seasonal_cluster_patterns)

        # Cluster similar seasonal patterns using ML
        if self.enable_ml and len(patterns) > 2:
            patterns = self._cluster_seasonal_patterns(patterns)

        # Story AI5.8: Store monthly aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_monthly_aggregates(patterns, events_df)

        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats['total_patterns'] += len(patterns)
        self.detection_stats['processing_time'] += processing_time

        logger.info(f"Detected {len(patterns)} seasonal patterns in {processing_time:.2f}s")
        return patterns

    def _add_seasonal_features(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add seasonal features to events DataFrame.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            DataFrame with seasonal features
        """
        df = events_df.copy()

        # Basic seasonal features
        df['month'] = df['time'].dt.month
        df['dayofyear'] = df['time'].dt.dayofyear
        df['quarter'] = df['time'].dt.quarter

        # Season classification
        df['season'] = df['month'].map({
            12: 'winter', 1: 'winter', 2: 'winter',
            3: 'spring', 4: 'spring', 5: 'spring',
            6: 'summer', 7: 'summer', 8: 'summer',
            9: 'fall', 10: 'fall', 11: 'fall'
        })

        # Daylight approximation
        df['daylight_hours'] = df['time'].dt.hour.map(self._calculate_daylight_hours)
        df['is_daylight'] = (df['time'].dt.hour >= 6) & (df['time'].dt.hour <= 18)

        # Weather features (if available)
        if 'temperature' not in df.columns:
            df['temperature'] = 20.0  # Default temperature
        if 'humidity' not in df.columns:
            df['humidity'] = 50.0  # Default humidity

        # Temperature categories
        df['temp_category'] = pd.cut(
            df['temperature'],
            bins=[-np.inf, 0, 15, 25, np.inf],
            labels=['cold', 'cool', 'warm', 'hot']
        )

        return df

    def _calculate_daylight_hours(self, hour: int) -> int:
        """
        Calculate approximate daylight hours for a given hour.
        
        Args:
            hour: Hour of day (0-23)
            
        Returns:
            Daylight hours (0-12)
        """
        # Simple approximation - could be enhanced with actual sunrise/sunset data
        if 6 <= hour <= 18:
            return min(12, hour - 6)
        else:
            return 0

    def _detect_seasonal_changes(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect seasonal behavior changes.
        
        Args:
            events_df: Events DataFrame with seasonal features
            
        Returns:
            List of seasonal change patterns
        """
        patterns = []

        # Group by season and analyze changes
        for season, season_events in events_df.groupby('season'):
            if len(season_events) < self.min_seasonal_occurrences:
                continue

            # Analyze seasonal characteristics
            seasonal_analysis = self._analyze_seasonal_characteristics(season_events, season)

            # Calculate confidence
            confidence = self._calculate_seasonal_confidence(seasonal_analysis)

            if confidence >= self.min_confidence:
                devices = list(season_events['entity_id'].unique())

                pattern = self._create_pattern_dict(
                    pattern_type=f'seasonal_{season}',
                    pattern_id=self._generate_pattern_id(f'season_{season}'),
                    confidence=confidence,
                    occurrences=len(season_events),
                    devices=devices,
                    metadata={
                        'season': season,
                        'event_count': len(season_events),
                        'device_count': len(devices),
                        'avg_events_per_day': seasonal_analysis['avg_events_per_day'],
                        'peak_hour': seasonal_analysis['peak_hour'],
                        'activity_intensity': seasonal_analysis['activity_intensity'],
                        'daylight_usage': seasonal_analysis['daylight_usage'],
                        'temperature_correlation': seasonal_analysis['temperature_correlation'],
                        'first_occurrence': season_events['time'].min().isoformat(),
                        'last_occurrence': season_events['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)

        return patterns

    def _detect_weather_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect weather-based patterns.
        
        Args:
            events_df: Events DataFrame with weather features
            
        Returns:
            List of weather patterns
        """
        patterns = []

        # Group by temperature category
        for temp_category, temp_events in events_df.groupby('temp_category'):
            if len(temp_events) < self.min_seasonal_occurrences:
                continue

            # Analyze weather characteristics
            weather_analysis = self._analyze_weather_characteristics(temp_events, temp_category)

            # Calculate confidence
            confidence = self._calculate_weather_confidence(weather_analysis)

            if confidence >= self.min_confidence:
                devices = list(temp_events['entity_id'].unique())

                pattern = self._create_pattern_dict(
                    pattern_type=f'weather_{temp_category}',
                    pattern_id=self._generate_pattern_id(f'weather_{temp_category}'),
                    confidence=confidence,
                    occurrences=len(temp_events),
                    devices=devices,
                    metadata={
                        'temperature_category': temp_category,
                        'event_count': len(temp_events),
                        'device_count': len(devices),
                        'avg_temperature': weather_analysis['avg_temperature'],
                        'temperature_variance': weather_analysis['temperature_variance'],
                        'activity_intensity': weather_analysis['activity_intensity'],
                        'weather_sensitivity': weather_analysis['weather_sensitivity'],
                        'first_occurrence': temp_events['time'].min().isoformat(),
                        'last_occurrence': temp_events['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)

        return patterns

    def _detect_daylight_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect daylight-based patterns.
        
        Args:
            events_df: Events DataFrame with daylight features
            
        Returns:
            List of daylight patterns
        """
        patterns = []

        # Group by daylight usage
        for is_daylight, daylight_events in events_df.groupby('is_daylight'):
            if len(daylight_events) < self.min_seasonal_occurrences:
                continue

            # Analyze daylight characteristics
            daylight_analysis = self._analyze_daylight_characteristics(daylight_events, is_daylight)

            # Calculate confidence
            confidence = self._calculate_daylight_confidence(daylight_analysis)

            if confidence >= self.min_confidence:
                devices = list(daylight_events['entity_id'].unique())
                pattern_type = 'daylight' if is_daylight else 'nighttime'

                pattern = self._create_pattern_dict(
                    pattern_type=f'daylight_{pattern_type}',
                    pattern_id=self._generate_pattern_id(f'daylight_{pattern_type}'),
                    confidence=confidence,
                    occurrences=len(daylight_events),
                    devices=devices,
                    metadata={
                        'daylight_type': pattern_type,
                        'event_count': len(daylight_events),
                        'device_count': len(devices),
                        'avg_daylight_hours': daylight_analysis['avg_daylight_hours'],
                        'activity_intensity': daylight_analysis['activity_intensity'],
                        'seasonal_variation': daylight_analysis['seasonal_variation'],
                        'first_occurrence': daylight_events['time'].min().isoformat(),
                        'last_occurrence': daylight_events['time'].max().isoformat()
                    }
                )
                patterns.append(pattern)

        return patterns

    def _detect_seasonal_clusters(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect seasonal clusters using ML clustering.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            List of seasonal cluster patterns
        """
        patterns = []

        # Extract seasonal features for clustering
        seasonal_features = self._extract_seasonal_features(events_df)

        if len(seasonal_features) < 3:
            return patterns

        try:
            from sklearn.cluster import KMeans

            # Determine optimal number of clusters
            n_clusters = min(4, len(seasonal_features) // 2)
            if n_clusters < 2:
                return patterns

            # Cluster seasonal patterns
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(seasonal_features)

            # Analyze each cluster
            for cluster_id in range(n_clusters):
                cluster_events = seasonal_features[cluster_labels == cluster_id]

                if len(cluster_events) < self.min_seasonal_occurrences:
                    continue

                cluster_confidence = self._calculate_cluster_confidence(
                    cluster_events, cluster_id, kmeans
                )

                if cluster_confidence >= self.min_confidence:
                    pattern = self._create_pattern_dict(
                        pattern_type='seasonal_cluster',
                        pattern_id=self._generate_pattern_id('seasonal_cluster'),
                        confidence=cluster_confidence,
                        occurrences=len(cluster_events),
                        devices=[],  # Will be filled from cluster data
                        metadata={
                            'cluster_id': cluster_id,
                            'cluster_size': len(cluster_events),
                            'cluster_characteristics': self._describe_seasonal_cluster(
                                cluster_events, cluster_id
                            ),
                            'cluster_centroid': kmeans.cluster_centers_[cluster_id].tolist()
                        }
                    )
                    patterns.append(pattern)

        except Exception as e:
            logger.warning(f"Seasonal clustering failed: {e}")

        return patterns

    def _analyze_seasonal_characteristics(self, season_events: pd.DataFrame, season: str) -> dict[str, Any]:
        """
        Analyze seasonal characteristics.
        
        Args:
            season_events: Events for season
            season: Season name
            
        Returns:
            Seasonal analysis
        """
        # Basic statistics
        event_count = len(season_events)
        device_count = season_events['entity_id'].nunique()

        # Daily statistics
        daily_events = season_events.groupby(season_events['time'].dt.date).size()
        avg_events_per_day = daily_events.mean()

        # Time analysis
        hourly_counts = season_events['time'].dt.hour.value_counts()
        peak_hour = hourly_counts.index[0] if len(hourly_counts) > 0 else 0

        # Activity intensity
        time_span_hours = (season_events['time'].max() - season_events['time'].min()).total_seconds() / 3600
        activity_intensity = event_count / max(time_span_hours, 1)

        # Daylight usage
        daylight_usage = season_events['is_daylight'].mean()

        # Temperature correlation
        temperature_correlation = 0.0
        if 'temperature' in season_events.columns:
            try:
                correlation = season_events['temperature'].corr(season_events['time'].dt.hour)
                temperature_correlation = abs(correlation) if not pd.isna(correlation) else 0.0
            except Exception:
                pass

        return {
            'avg_events_per_day': avg_events_per_day,
            'peak_hour': peak_hour,
            'activity_intensity': activity_intensity,
            'daylight_usage': daylight_usage,
            'temperature_correlation': temperature_correlation
        }

    def _analyze_weather_characteristics(self, weather_events: pd.DataFrame, temp_category: str) -> dict[str, Any]:
        """
        Analyze weather characteristics.
        
        Args:
            weather_events: Events for temperature category
            temp_category: Temperature category
            
        Returns:
            Weather analysis
        """
        # Basic statistics
        event_count = len(weather_events)
        device_count = weather_events['entity_id'].nunique()

        # Temperature statistics
        avg_temperature = weather_events['temperature'].mean()
        temperature_variance = weather_events['temperature'].var()

        # Activity intensity
        time_span_hours = (weather_events['time'].max() - weather_events['time'].min()).total_seconds() / 3600
        activity_intensity = event_count / max(time_span_hours, 1)

        # Weather sensitivity (correlation between temperature and activity)
        weather_sensitivity = 0.0
        if len(weather_events) > 1:
            try:
                correlation = weather_events['temperature'].corr(pd.Series(range(len(weather_events))))
                weather_sensitivity = abs(correlation) if not pd.isna(correlation) else 0.0
            except Exception:
                pass

        return {
            'avg_temperature': avg_temperature,
            'temperature_variance': temperature_variance,
            'activity_intensity': activity_intensity,
            'weather_sensitivity': weather_sensitivity
        }

    def _analyze_daylight_characteristics(self, daylight_events: pd.DataFrame, is_daylight: bool) -> dict[str, Any]:
        """
        Analyze daylight characteristics.
        
        Args:
            daylight_events: Events for daylight period
            is_daylight: Whether this is daylight period
            
        Returns:
            Daylight analysis
        """
        # Basic statistics
        event_count = len(daylight_events)
        device_count = daylight_events['entity_id'].nunique()

        # Daylight hours
        avg_daylight_hours = daylight_events['daylight_hours'].mean()

        # Activity intensity
        time_span_hours = (daylight_events['time'].max() - daylight_events['time'].min()).total_seconds() / 3600
        activity_intensity = event_count / max(time_span_hours, 1)

        # Seasonal variation
        seasonal_variation = 0.0
        if 'season' in daylight_events.columns:
            seasonal_counts = daylight_events['season'].value_counts()
            seasonal_variation = len(seasonal_counts) / 4.0  # 4 seasons

        return {
            'avg_daylight_hours': avg_daylight_hours,
            'activity_intensity': activity_intensity,
            'seasonal_variation': seasonal_variation
        }

    def _extract_seasonal_features(self, events_df: pd.DataFrame) -> np.ndarray:
        """
        Extract seasonal features for clustering.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Feature matrix for clustering
        """
        features = []

        # Group by month and extract features
        for month, month_events in events_df.groupby('month'):
            # Extract monthly features
            feature_vector = [
                len(month_events),  # Event count
                month_events['entity_id'].nunique(),  # Device count
                month_events['time'].dt.hour.nunique(),  # Active hours
                month_events['is_daylight'].mean(),  # Daylight usage ratio
                month_events['temperature'].mean(),  # Average temperature
                month_events['temperature'].std(),  # Temperature variance
                month,  # Month
                month_events['daylight_hours'].mean()  # Average daylight hours
            ]
            features.append(feature_vector)

        return np.array(features) if features else np.array([])

    def _calculate_seasonal_confidence(self, seasonal_analysis: dict[str, Any]) -> float:
        """
        Calculate confidence for seasonal patterns.
        
        Args:
            seasonal_analysis: Seasonal analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from activity intensity
        base_confidence = min(seasonal_analysis['activity_intensity'] / 3.0, 1.0)

        # Daylight usage bonus
        daylight_bonus = seasonal_analysis['daylight_usage'] * 0.2

        # Temperature correlation bonus
        temp_bonus = seasonal_analysis['temperature_correlation'] * 0.1

        total_confidence = base_confidence + daylight_bonus + temp_bonus

        return min(total_confidence, 1.0)

    def _calculate_weather_confidence(self, weather_analysis: dict[str, Any]) -> float:
        """
        Calculate confidence for weather patterns.
        
        Args:
            weather_analysis: Weather analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from activity intensity
        base_confidence = min(weather_analysis['activity_intensity'] / 2.0, 1.0)

        # Weather sensitivity bonus
        sensitivity_bonus = weather_analysis['weather_sensitivity'] * 0.3

        total_confidence = base_confidence + sensitivity_bonus

        return min(total_confidence, 1.0)

    def _calculate_daylight_confidence(self, daylight_analysis: dict[str, Any]) -> float:
        """
        Calculate confidence for daylight patterns.
        
        Args:
            daylight_analysis: Daylight analysis results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from activity intensity
        base_confidence = min(daylight_analysis['activity_intensity'] / 2.0, 1.0)

        # Seasonal variation bonus
        variation_bonus = daylight_analysis['seasonal_variation'] * 0.2

        total_confidence = base_confidence + variation_bonus

        return min(total_confidence, 1.0)

    def _calculate_cluster_confidence(self, cluster_events: np.ndarray, cluster_id: int, kmeans_model) -> float:
        """
        Calculate confidence for seasonal clusters.
        
        Args:
            cluster_events: Events in cluster
            cluster_id: Cluster identifier
            kmeans_model: Fitted KMeans model
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        occurrences = len(cluster_events)
        base_confidence = min(occurrences / 8.0, 1.0)

        # Cluster cohesion bonus
        try:
            distances = kmeans_model.transform(cluster_events)
            avg_distance = np.mean(distances[:, cluster_id])
            cohesion_bonus = max(0.0, 1.0 - avg_distance) * 0.3
            base_confidence += cohesion_bonus
        except Exception:
            pass

        return min(base_confidence, 1.0)

    def _describe_seasonal_cluster(self, cluster_events: np.ndarray, cluster_id: int) -> dict[str, Any]:
        """
        Describe seasonal cluster characteristics.
        
        Args:
            cluster_events: Events in cluster
            cluster_id: Cluster identifier
            
        Returns:
            Cluster characteristics
        """
        return {
            'cluster_id': cluster_id,
            'event_count': len(cluster_events),
            'avg_events_per_month': np.mean(cluster_events[:, 0]) if len(cluster_events) > 0 else 0,
            'avg_devices_per_month': np.mean(cluster_events[:, 1]) if len(cluster_events) > 0 else 0,
            'avg_active_hours': np.mean(cluster_events[:, 2]) if len(cluster_events) > 0 else 0,
            'avg_daylight_usage': np.mean(cluster_events[:, 3]) if len(cluster_events) > 0 else 0,
            'avg_temperature': np.mean(cluster_events[:, 4]) if len(cluster_events) > 0 else 0,
            'avg_daylight_hours': np.mean(cluster_events[:, 7]) if len(cluster_events) > 0 else 0
        }

    def _cluster_seasonal_patterns(self, patterns: list[dict]) -> list[dict]:
        """
        Cluster similar seasonal patterns using ML.
        
        Args:
            patterns: List of seasonal patterns
            
        Returns:
            Clustered patterns with cluster information
        """
        if len(patterns) < 3:
            return patterns

        try:
            # Extract features for clustering
            features = self._extract_seasonal_pattern_features(patterns)

            # Cluster patterns
            patterns = self._cluster_patterns(patterns, features)

            logger.info(f"Clustered {len(patterns)} seasonal patterns")

        except Exception as e:
            logger.warning(f"Seasonal pattern clustering failed: {e}")

        return patterns

    def _extract_seasonal_pattern_features(self, patterns: list[dict]) -> np.ndarray:
        """
        Extract features for seasonal pattern clustering.
        
        Args:
            patterns: List of seasonal patterns
            
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
                metadata.get('daylight_usage', 0),
                metadata.get('temperature_correlation', 0),
                metadata.get('weather_sensitivity', 0)
            ]

            # Add pattern type encoding
            pattern_type = pattern['pattern_type']
            type_encoding = {
                'seasonal_winter': 0,
                'seasonal_spring': 1,
                'seasonal_summer': 2,
                'seasonal_fall': 3,
                'weather_cold': 4,
                'weather_cool': 5,
                'weather_warm': 6,
                'weather_hot': 7,
                'daylight_daylight': 8,
                'daylight_nighttime': 9,
                'seasonal_cluster': 10
            }.get(pattern_type, 0)
            feature_vector.append(type_encoding)

            features.append(feature_vector)

        return np.array(features)

    def _store_monthly_aggregates(self, patterns: list[dict], events_df: pd.DataFrame) -> None:
        """
        Store monthly aggregates to InfluxDB.
        
        Story AI5.8: Incremental pattern processing with monthly aggregate storage.
        
        Args:
            patterns: List of detected patterns
            events_df: Original events DataFrame
        """
        try:
            # Get month identifier from events
            if events_df.empty or 'time' not in events_df.columns:
                logger.warning("Cannot determine month from events for aggregate storage")
                return

            # Use YYYY-MM format
            first_date = pd.to_datetime(events_df['time'].min())
            month_str = first_date.strftime('%Y-%m')

            logger.info(f"Storing monthly aggregates for {month_str}")

            for pattern in patterns:
                # Extract season information
                metadata = pattern.get('metadata', {})
                season = metadata.get('season', 'unknown')

                # Seasonal patterns from metadata
                seasonal_patterns = metadata.get('seasonal_patterns', {})
                if not seasonal_patterns:
                    seasonal_patterns = {'trend': 'stable'}

                # Determine trend direction from confidence changes
                confidence = pattern.get('confidence', 0.0)
                if confidence > 0.8:
                    trend_direction = 'increasing'
                elif confidence < 0.5:
                    trend_direction = 'decreasing'
                else:
                    trend_direction = 'stable'

                # Store aggregate
                try:
                    self.aggregate_client.write_seasonal_monthly(
                        month=month_str,
                        season=season,
                        seasonal_patterns=seasonal_patterns,
                        trend_direction=trend_direction,
                        confidence=confidence
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {season}: {e}", exc_info=True)

            logger.info(f"✅ Stored {len(patterns)} monthly aggregates to InfluxDB")

        except Exception as e:
            logger.error(f"Error storing monthly aggregates: {e}", exc_info=True)
