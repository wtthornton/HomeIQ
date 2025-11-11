"""
Multi-Factor Pattern Detector

Detects patterns considering multiple contextual factors:
- Time (time of day, day of week, season)
- Presence (home/away, room occupancy)
- Weather (temperature, humidity, conditions)
- Device state (other devices' states)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class MultiFactorPatternDetector(MLPatternDetector):
    """
    Detects patterns using multiple contextual factors.
    
    Combines time, presence, weather, and device state to find
    more accurate and context-aware patterns.
    """
    
    def __init__(
        self,
        time_factors: List[str] = ['time_of_day', 'day_of_week', 'season'],
        presence_factors: List[str] = ['presence', 'room_occupancy'],
        weather_factors: List[str] = ['temperature', 'humidity', 'conditions'],
        min_pattern_occurrences: int = 10,
        min_confidence: float = 0.7,
        aggregate_client=None,
        **kwargs
    ):
        """
        Initialize multi-factor pattern detector.
        
        Args:
            time_factors: List of time-based factors to consider
            presence_factors: List of presence-based factors to consider
            weather_factors: List of weather-based factors to consider
            min_pattern_occurrences: Minimum occurrences for valid pattern
            min_confidence: Minimum confidence threshold
            aggregate_client: PatternAggregateClient for storing aggregates
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.time_factors = time_factors
        self.presence_factors = presence_factors
        self.weather_factors = weather_factors
        self.min_pattern_occurrences = min_pattern_occurrences
        self.min_confidence = min_confidence
        self.aggregate_client = aggregate_client
        
        logger.info(
            f"MultiFactorPatternDetector initialized: "
            f"time={time_factors}, presence={presence_factors}, weather={weather_factors}"
        )
    
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect patterns using multiple contextual factors.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state, and context columns
            
        Returns:
            List of multi-factor pattern dictionaries
        """
        if not self._validate_events_dataframe(events_df):
            return []
        
        # Optimize DataFrame
        events_df = self._optimize_dataframe(events_df)
        
        # Extract all contextual factors
        enriched_df = self._enrich_with_factors(events_df)
        
        if enriched_df.empty:
            logger.warning("No enriched data available for multi-factor detection")
            return []
        
        # Group by device and detect patterns
        patterns = []
        for device_id, device_events in enriched_df.groupby('entity_id'):
            device_patterns = self._detect_device_patterns(device_id, device_events)
            patterns.extend(device_patterns)
        
        logger.info(f"✅ Detected {len(patterns)} multi-factor patterns")
        return patterns
    
    def _enrich_with_factors(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """Enrich events with all contextual factors."""
        df = events_df.copy()
        
        # Time factors
        if 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
            df['month'] = df['timestamp'].dt.month
            df['season'] = df['month'].apply(self._get_season)
        
        # Presence factors (if available)
        if 'presence' in df.columns:
            df['is_home'] = df['presence'].apply(lambda x: x in ['home', 'not_away', 'present'])
        else:
            # Try to infer from device_tracker or person entities
            df['is_home'] = None
        
        # Weather factors (if available)
        if 'temperature' not in df.columns:
            df['temperature'] = None
        if 'humidity' not in df.columns:
            df['humidity'] = None
        if 'weather_state' not in df.columns:
            df['weather_state'] = None
        
        return df
    
    def _get_season(self, month: int) -> str:
        """Get season from month."""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'
    
    def _detect_device_patterns(self, device_id: str, device_events: pd.DataFrame) -> List[Dict]:
        """Detect patterns for a single device using multiple factors."""
        patterns = []
        
        if len(device_events) < self.min_pattern_occurrences:
            return patterns
        
        # Group by factor combinations
        factor_groups = self._group_by_factors(device_events)
        
        for factor_combo, group_events in factor_groups.items():
            if len(group_events) < self.min_pattern_occurrences:
                continue
            
            # Calculate confidence based on factor consistency
            confidence = self._calculate_multi_factor_confidence(
                device_events, group_events, factor_combo
            )
            
            if confidence >= self.min_confidence:
                pattern = self._create_pattern(
                    device_id, group_events, factor_combo, confidence
                )
                patterns.append(pattern)
        
        return patterns
    
    def _group_by_factors(self, events: pd.DataFrame) -> Dict[Tuple, pd.DataFrame]:
        """Group events by factor combinations."""
        groups = defaultdict(list)
        
        for _, event in events.iterrows():
            # Build factor key
            factor_key = []
            
            # Time factors
            if 'time_of_day' in self.time_factors:
                hour = event.get('hour', 0)
                if 6 <= hour < 12:
                    factor_key.append('morning')
                elif 12 <= hour < 17:
                    factor_key.append('afternoon')
                elif 17 <= hour < 21:
                    factor_key.append('evening')
                else:
                    factor_key.append('night')
            
            if 'day_of_week' in self.time_factors:
                dow = event.get('day_of_week', 0)
                if dow < 5:  # Monday-Friday
                    factor_key.append('weekday')
                else:
                    factor_key.append('weekend')
            
            if 'season' in self.time_factors:
                season = event.get('season', 'unknown')
                factor_key.append(season)
            
            # Presence factors
            if 'presence' in self.presence_factors:
                is_home = event.get('is_home')
                if is_home is not None:
                    factor_key.append('home' if is_home else 'away')
            
            # Weather factors
            if 'temperature' in self.weather_factors:
                temp = event.get('temperature')
                if temp is not None and pd.notna(temp):
                    if temp < 50:
                        factor_key.append('cold')
                    elif temp < 70:
                        factor_key.append('cool')
                    elif temp < 80:
                        factor_key.append('warm')
                    else:
                        factor_key.append('hot')
            
            if 'humidity' in self.weather_factors:
                humidity = event.get('humidity')
                if humidity is not None and pd.notna(humidity):
                    if humidity < 40:
                        factor_key.append('dry')
                    elif humidity < 60:
                        factor_key.append('normal')
                    else:
                        factor_key.append('humid')
            
            factor_key_tuple = tuple(factor_key)
            groups[factor_key_tuple].append(event)
        
        # Convert to DataFrames
        return {
            key: pd.DataFrame(values) 
            for key, values in groups.items()
            if len(values) >= self.min_pattern_occurrences
        }
    
    def _calculate_multi_factor_confidence(
        self,
        all_events: pd.DataFrame,
        pattern_events: pd.DataFrame,
        factor_combo: Tuple
    ) -> float:
        """Calculate confidence for multi-factor pattern."""
        # Base confidence: ratio of pattern events to all events
        base_confidence = len(pattern_events) / len(all_events)
        
        # Boost for high occurrence count
        occurrence_boost = min(0.1, (len(pattern_events) - self.min_pattern_occurrences) / 100.0)
        
        # Boost for more factors (more specific = higher confidence)
        factor_boost = len(factor_combo) * 0.02
        
        confidence = base_confidence + occurrence_boost + factor_boost
        return min(0.95, confidence)
    
    def _create_pattern(
        self,
        device_id: str,
        events: pd.DataFrame,
        factor_combo: Tuple,
        confidence: float
    ) -> Dict:
        """Create pattern dictionary from detected pattern."""
        # Calculate average time if available
        avg_hour = None
        if 'hour' in events.columns:
            avg_hour = events['hour'].mean()
        
        pattern = {
            'pattern_type': 'multi_factor',
            'device_id': device_id,
            'occurrences': int(len(events)),
            'total_events': int(len(events)),
            'confidence': float(confidence),
            'metadata': {
                'factors': list(factor_combo),
                'factor_count': len(factor_combo),
                'avg_hour': float(avg_hour) if avg_hour is not None else None,
                'time_factors': self.time_factors,
                'presence_factors': self.presence_factors,
                'weather_factors': self.weather_factors
            }
        }
        
        return pattern







