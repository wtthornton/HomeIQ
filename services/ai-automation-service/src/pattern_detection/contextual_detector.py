"""
Contextual Pattern Detector

Detects context-aware patterns using weather, presence, and time data.
Uses ML clustering to identify contextual behavior patterns.
"""

import logging
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class ContextualDetector(MLPatternDetector):
    """
    Detects context-aware behavior patterns.
    
    Analyzes patterns based on:
    - Weather conditions (temperature, humidity, weather state)
    - Presence detection (home/away status)
    - Time context (sunrise/sunset, day/night)
    - Environmental factors
    """

    def __init__(
        self,
        weather_weight: float = 0.3,
        presence_weight: float = 0.4,
        time_weight: float = 0.3,
        context_window_hours: int = 24,
        min_context_occurrences: int = 5,
        aggregate_client=None,  # Story AI5.8: Monthly aggregation
        **kwargs
    ):
        """
        Initialize contextual detector.
        
        Args:
            weather_weight: Weight for weather features in clustering
            presence_weight: Weight for presence features in clustering
            time_weight: Weight for time features in clustering
            context_window_hours: Time window for context analysis
            min_context_occurrences: Minimum occurrences for valid context pattern
            aggregate_client: PatternAggregateClient for storing monthly aggregates (Story AI5.8)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.weather_weight = weather_weight
        self.presence_weight = presence_weight
        self.time_weight = time_weight
        self.context_window_hours = context_window_hours
        self.min_context_occurrences = min_context_occurrences
        self.aggregate_client = aggregate_client  # Story AI5.8

        # Context feature weights
        self.feature_weights = {
            'weather': weather_weight,
            'presence': presence_weight,
            'time': time_weight
        }

        logger.info(f"ContextualDetector initialized: weather={weather_weight}, presence={presence_weight}, time={time_weight}")

    def detect_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect contextual patterns in events.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state, and context columns
            
        Returns:
            List of contextual pattern dictionaries
        """
        start_time = datetime.utcnow()

        if not self._validate_events_dataframe(events_df):
            return []

        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)

        # Extract contextual features
        try:
            context_features = self._extract_contextual_features(events_df)
            if context_features.empty:
                logger.info("No contextual features found after extraction")
                return []
        except Exception as e:
            logger.warning(f"Failed to extract contextual features: {e}, using time-only features")
            # Fallback to time-only features
            context_features = self._add_time_features(events_df.copy())
            if context_features.empty:
                return []

        # Group events by context patterns
        context_groups = self._group_by_context(context_features)
        if not context_groups:
            logger.info("No contextual groups found")
            return []

        # Detect patterns within each context group
        patterns = []
        for context_key, context_events in context_groups.items():
            if len(context_events) < self.min_context_occurrences:
                continue

            context_patterns = self._detect_context_patterns(context_key, context_events)
            patterns.extend(context_patterns)

        # Cluster similar contextual patterns using ML
        if self.enable_ml and len(patterns) > 2:
            patterns = self._cluster_contextual_patterns(patterns)

        # Story AI5.8: Store monthly aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_monthly_aggregates(patterns, events_df)

        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats['total_patterns'] += len(patterns)
        self.detection_stats['processing_time'] += processing_time

        logger.info(f"Detected {len(patterns)} contextual patterns in {processing_time:.2f}s")
        return patterns

    def _extract_contextual_features(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract contextual features from events.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            DataFrame with contextual features
        """
        features_df = events_df.copy()

        # Time-based features
        features_df = self._add_time_features(features_df)

        # Weather features (if available)
        features_df = self._add_weather_features(features_df)

        # Presence features (if available)
        features_df = self._add_presence_features(features_df)

        # Environmental features
        features_df = self._add_environmental_features(features_df)

        return features_df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based contextual features."""
        df['hour'] = df['time'].dt.hour
        df['dayofweek'] = df['time'].dt.dayofweek
        df['dayofyear'] = df['time'].dt.dayofyear
        df['month'] = df['time'].dt.month
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        df['is_workday'] = (df['dayofweek'] < 5).astype(int)

        # Time of day categories
        df['time_of_day'] = pd.cut(
            df['hour'],
            bins=[0, 6, 12, 18, 24],
            labels=['night', 'morning', 'afternoon', 'evening'],
            include_lowest=True
        )

        # Season approximation
        df['season'] = pd.cut(
            df['month'],
            bins=[0, 3, 6, 9, 12],
            labels=['winter', 'spring', 'summer', 'fall'],
            include_lowest=True
        )

        return df

    def _add_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add weather-based contextual features (graceful fallback if missing)."""
        # Weather features (optional - don't fail if missing)
        weather_columns = ['temperature', 'humidity', 'pressure', 'weather_state', 'wind_speed']
        weather_available = False

        for col in weather_columns:
            if col in df.columns:
                weather_available = True
                break

        if not weather_available:
            # No weather data available - use time-based approximations
            logger.debug("No weather data available, using time-based approximations")
            # Use time of day to estimate temperature (rough approximation)
            df['temperature'] = df['hour'].apply(lambda h: 15 + 10 * np.sin((h - 6) * np.pi / 12) if 6 <= h <= 18 else 10)
            df['humidity'] = 50.0  # Default
            df['weather_state'] = 'unknown'
        else:
            # Fill missing weather columns with defaults
            for col in weather_columns:
                if col not in df.columns:
                    if col == 'temperature':
                        df[col] = 20.0
                    elif col == 'humidity':
                        df[col] = 50.0
                    elif col == 'pressure':
                        df[col] = 1013.25
                    elif col == 'weather_state':
                        df[col] = 'unknown'
                    elif col == 'wind_speed':
                        df[col] = 0.0

        # Weather categories (only if we have temperature/humidity)
        if 'temperature' in df.columns:
            try:
                df['temp_category'] = pd.cut(
                    df['temperature'],
                    bins=[-np.inf, 0, 15, 25, np.inf],
                    labels=['cold', 'cool', 'warm', 'hot']
                )
            except Exception:
                df['temp_category'] = 'unknown'

        if 'humidity' in df.columns:
            try:
                df['humidity_category'] = pd.cut(
                    df['humidity'],
                    bins=[0, 30, 60, 80, 100],
                    labels=['dry', 'normal', 'humid', 'very_humid']
                )
            except Exception:
                df['humidity_category'] = 'unknown'

        return df

    def _add_presence_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add presence-based contextual features."""
        # Presence features (if available)
        if 'presence_detected' not in df.columns:
            # Create dummy presence data for testing
            df['presence_detected'] = 1  # Assume presence by default

        if 'home_mode' not in df.columns:
            df['home_mode'] = 'home'  # Default home mode

        # Presence categories
        df['presence_category'] = df['presence_detected'].map({0: 'away', 1: 'home'})

        return df

    def _add_environmental_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add environmental contextual features."""
        # Light level approximation based on time
        df['is_daylight'] = ((df['hour'] >= 6) & (df['hour'] <= 18)).astype(int)

        # Activity level based on time
        df['activity_level'] = pd.cut(
            df['hour'],
            bins=[0, 6, 9, 17, 20, 24],
            labels=['sleep', 'morning', 'work', 'evening', 'night'],
            include_lowest=True
        )

        return df

    def _group_by_context(self, features_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """
        Group events by contextual patterns.
        
        Args:
            features_df: DataFrame with contextual features
            
        Returns:
            Dictionary of context groups
        """
        context_groups = defaultdict(list)

        # Create context signature for each event
        for idx, event in features_df.iterrows():
            context_key = self._create_context_key(event)
            context_groups[context_key].append(idx)

        # Convert to DataFrames
        context_dfs = {}
        for context_key, indices in context_groups.items():
            if len(indices) >= self.min_context_occurrences:
                context_dfs[context_key] = features_df.iloc[indices].copy()

        return context_dfs

    def _create_context_key(self, event: pd.Series) -> str:
        """
        Create context signature for an event.
        
        Args:
            event: Event series with contextual features
            
        Returns:
            Context signature string
        """
        # Key contextual features
        time_of_day = event.get('time_of_day', 'unknown')
        season = event.get('season', 'unknown')
        temp_category = event.get('temp_category', 'unknown')
        presence_category = event.get('presence_category', 'unknown')
        activity_level = event.get('activity_level', 'unknown')

        # Create context signature
        context_parts = [
            f"time:{time_of_day}",
            f"season:{season}",
            f"temp:{temp_category}",
            f"presence:{presence_category}",
            f"activity:{activity_level}"
        ]

        return "|".join(context_parts)

    def _detect_context_patterns(self, context_key: str, context_events: pd.DataFrame) -> list[dict]:
        """
        Detect patterns within a context group.
        
        Args:
            context_key: Context signature
            context_events: Events in this context
            
        Returns:
            List of contextual patterns
        """
        patterns = []

        # Group by device to find device-specific patterns
        for entity_id, device_events in context_events.groupby('entity_id'):
            if len(device_events) < self.min_occurrences:
                continue

            # Analyze device behavior in this context
            pattern = self._analyze_device_context_pattern(
                entity_id, device_events, context_key
            )

            if pattern and pattern['confidence'] >= self.min_confidence:
                patterns.append(pattern)

        # Group by area to find area-specific patterns
        if 'area' in context_events.columns:
            for area, area_events in context_events.groupby('area'):
                if len(area_events) < self.min_occurrences:
                    continue

                pattern = self._analyze_area_context_pattern(
                    area, area_events, context_key
                )

                if pattern and pattern['confidence'] >= self.min_confidence:
                    patterns.append(pattern)

        return patterns

    def _analyze_device_context_pattern(
        self,
        entity_id: str,
        device_events: pd.DataFrame,
        context_key: str
    ) -> dict | None:
        """
        Analyze device behavior in specific context.
        
        Args:
            entity_id: Device entity ID
            device_events: Device events in context
            context_key: Context signature
            
        Returns:
            Context pattern dictionary or None
        """
        # Calculate context-specific metrics
        occurrences = len(device_events)
        time_span = (device_events['time'].max() - device_events['time'].min()).total_seconds()

        # State distribution
        state_counts = device_events['state'].value_counts()
        most_common_state = state_counts.index[0]
        state_consistency = state_counts.iloc[0] / occurrences

        # Time consistency
        time_consistency = self._calculate_time_consistency(device_events)

        # Calculate confidence
        confidence = self._calculate_context_confidence(
            occurrences, state_consistency, time_consistency
        )

        if confidence < self.min_confidence:
            return None

        # Create pattern
        pattern = self._create_pattern_dict(
            pattern_type='contextual',
            pattern_id=self._generate_pattern_id('ctx'),
            confidence=confidence,
            occurrences=occurrences,
            devices=[entity_id],
            metadata={
                'context_key': context_key,
                'context_parsed': self._parse_context_key(context_key),
                'most_common_state': most_common_state,
                'state_consistency': state_consistency,
                'time_consistency': time_consistency,
                'time_span_hours': time_span / 3600,
                'first_occurrence': device_events['time'].min().isoformat(),
                'last_occurrence': device_events['time'].max().isoformat()
            }
        )

        return pattern

    def _analyze_area_context_pattern(
        self,
        area: str,
        area_events: pd.DataFrame,
        context_key: str
    ) -> dict | None:
        """
        Analyze area behavior in specific context.
        
        Args:
            area: Area name
            area_events: Area events in context
            context_key: Context signature
            
        Returns:
            Context pattern dictionary or None
        """
        # Calculate area-specific metrics
        occurrences = len(area_events)
        unique_devices = area_events['entity_id'].nunique()

        # Device activity distribution
        device_counts = area_events['entity_id'].value_counts()
        device_diversity = len(device_counts) / unique_devices if unique_devices > 0 else 0

        # Time consistency
        time_consistency = self._calculate_time_consistency(area_events)

        # Calculate confidence
        confidence = self._calculate_context_confidence(
            occurrences, device_diversity, time_consistency
        )

        if confidence < self.min_confidence:
            return None

        # Create pattern
        pattern = self._create_pattern_dict(
            pattern_type='contextual_area',
            pattern_id=self._generate_pattern_id('ctx_area'),
            confidence=confidence,
            occurrences=occurrences,
            devices=list(area_events['entity_id'].unique()),
            metadata={
                'context_key': context_key,
                'context_parsed': self._parse_context_key(context_key),
                'area': area,
                'device_diversity': device_diversity,
                'unique_devices': unique_devices,
                'time_consistency': time_consistency,
                'first_occurrence': area_events['time'].min().isoformat(),
                'last_occurrence': area_events['time'].max().isoformat()
            }
        )

        return pattern

    def _calculate_time_consistency(self, events: pd.DataFrame) -> float:
        """
        Calculate time consistency for events.
        
        Args:
            events: Events DataFrame
            
        Returns:
            Time consistency score (0.0 to 1.0)
        """
        if len(events) < 2:
            return 0.0

        # Calculate time differences
        time_diffs = events['time'].diff().dt.total_seconds().dropna()

        if len(time_diffs) == 0:
            return 0.0

        # Calculate coefficient of variation (lower = more consistent)
        mean_diff = time_diffs.mean()
        std_diff = time_diffs.std()

        if mean_diff == 0:
            return 0.0

        cv = std_diff / mean_diff
        consistency = max(0.0, 1.0 - cv)  # Higher consistency = lower CV

        return min(consistency, 1.0)

    def _calculate_context_confidence(
        self,
        occurrences: int,
        consistency: float,
        time_consistency: float
    ) -> float:
        """
        Calculate confidence for contextual pattern.
        
        Args:
            occurrences: Number of occurrences
            consistency: State or device consistency
            time_consistency: Time consistency score
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from occurrences
        base_confidence = min(occurrences / 15.0, 1.0)  # Max at 15 occurrences

        # Consistency bonus
        consistency_bonus = consistency * 0.3  # Max 30% bonus

        # Time consistency bonus
        time_bonus = time_consistency * 0.2  # Max 20% bonus

        total_confidence = base_confidence + consistency_bonus + time_bonus

        return min(total_confidence, 1.0)

    def _parse_context_key(self, context_key: str) -> dict[str, str]:
        """
        Parse context key into components.
        
        Args:
            context_key: Context signature string
            
        Returns:
            Dictionary of context components
        """
        context = {}
        for part in context_key.split('|'):
            if ':' in part:
                key, value = part.split(':', 1)
                context[key] = value

        return context

    def _cluster_contextual_patterns(self, patterns: list[dict]) -> list[dict]:
        """
        Cluster similar contextual patterns using ML.
        
        Args:
            patterns: List of contextual patterns
            
        Returns:
            Clustered patterns with cluster information
        """
        if len(patterns) < 3:
            return patterns

        try:
            # Extract features for clustering
            features = self._extract_contextual_pattern_features(patterns)

            # Cluster patterns
            patterns = self._cluster_patterns(patterns, features)

            logger.info(f"Clustered {len(patterns)} contextual patterns")

        except Exception as e:
            logger.warning(f"Contextual pattern clustering failed: {e}")

        return patterns

    def _extract_contextual_pattern_features(self, patterns: list[dict]) -> np.ndarray:
        """
        Extract features for contextual pattern clustering.
        
        Args:
            patterns: List of contextual patterns
            
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
                metadata.get('state_consistency', 0.0),
                metadata.get('time_consistency', 0.0),
                metadata.get('device_diversity', 0.0),
                metadata.get('unique_devices', 0),
                len(pattern['devices'])
            ]

            # Add context features
            context_parsed = metadata.get('context_parsed', {})

            # Time of day encoding
            time_of_day = context_parsed.get('time', 'unknown')
            time_encoding = {
                'night': 0, 'morning': 1, 'afternoon': 2, 'evening': 3
            }.get(time_of_day, 0)
            feature_vector.append(time_encoding)

            # Season encoding
            season = context_parsed.get('season', 'unknown')
            season_encoding = {
                'winter': 0, 'spring': 1, 'summer': 2, 'fall': 3
            }.get(season, 0)
            feature_vector.append(season_encoding)

            # Temperature category encoding
            temp_category = context_parsed.get('temp', 'unknown')
            temp_encoding = {
                'cold': 0, 'cool': 1, 'warm': 2, 'hot': 3
            }.get(temp_category, 0)
            feature_vector.append(temp_encoding)

            # Presence encoding
            presence = context_parsed.get('presence', 'unknown')
            presence_encoding = 1 if presence == 'home' else 0
            feature_vector.append(presence_encoding)

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
                # Extract context information
                metadata = pattern.get('metadata', {})
                weather_context = metadata.get('weather_context', 'unknown')

                # Device activity from pattern
                devices = pattern.get('devices', [])
                device_activity = dict.fromkeys(devices, 1)

                # Correlation score from confidence
                correlation_score = pattern.get('confidence', 0.0)
                occurrences = pattern.get('occurrences', 0)
                confidence = correlation_score

                # Store aggregate
                try:
                    self.aggregate_client.write_contextual_monthly(
                        month=month_str,
                        weather_context=weather_context,
                        device_activity=device_activity,
                        correlation_score=correlation_score,
                        occurrences=occurrences,
                        confidence=confidence
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {weather_context}: {e}", exc_info=True)

            logger.info(f"✅ Stored {len(patterns)} monthly aggregates to InfluxDB")

        except Exception as e:
            logger.error(f"Error storing monthly aggregates: {e}", exc_info=True)
