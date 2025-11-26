"""
Correlation Feature Extractor

Epic 36, Story 36.4: External Data Feature Extraction
Extracts features including external data (weather, carbon, electricity, air quality)
for correlation analysis.

Single-home NUC optimized:
- Memory: <5MB (in-memory feature computation)
- Feature extraction: <5ms per pair
- Caches external data queries
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from shared.logging_config import get_logger

logger = get_logger(__name__)


class CorrelationFeatureExtractor:
    """
    Extracts features for correlation analysis including external data.
    
    Features include:
    - Device metadata (domain, area, device_id)
    - Usage statistics (frequency, patterns)
    - External data (weather, carbon, electricity, air quality)
    - Temporal features (time of day, day of week)
    - Spatial features (area, room)
    """
    
    def __init__(self, data_api_client: Optional[object] = None):
        """
        Initialize feature extractor.
        
        Args:
            data_api_client: Optional data API client for external data queries
        """
        self.data_api_client = data_api_client
        
        # External data cache (timestamp -> data)
        self.weather_cache: dict[datetime, dict] = {}
        self.carbon_cache: dict[datetime, dict] = {}
        self.electricity_cache: dict[datetime, dict] = {}
        self.air_quality_cache: dict[datetime, dict] = {}
        
        # Cache TTL (1 hour)
        self.cache_ttl = timedelta(hours=1)
        
        logger.info("CorrelationFeatureExtractor initialized")
    
    def extract_pair_features(
        self,
        entity1: dict,
        entity2: dict,
        usage_stats: Optional[dict] = None,
        timestamp: Optional[datetime] = None
    ) -> dict:
        """
        Extract features for a device pair.
        
        Args:
            entity1: Entity 1 metadata
            entity2: Entity 2 metadata
            usage_stats: Optional usage statistics
            timestamp: Optional timestamp for external data
        
        Returns:
            Dict with feature values
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        features = {}
        
        # Basic device features
        features.update(self._extract_device_features(entity1, entity2))
        
        # Usage features
        if usage_stats:
            features.update(self._extract_usage_features(entity1, entity2, usage_stats))
        
        # External data features
        features.update(self._extract_external_features(timestamp))
        
        # Temporal features
        features.update(self._extract_temporal_features(timestamp))
        
        # Spatial features
        features.update(self._extract_spatial_features(entity1, entity2))
        
        return features
    
    def _extract_device_features(self, entity1: dict, entity2: dict) -> dict:
        """Extract device metadata features"""
        domain1 = entity1.get('domain', 'other')
        domain2 = entity2.get('domain', 'other')
        area1 = entity1.get('area_id')
        area2 = entity2.get('area_id')
        device1 = entity1.get('device_id')
        device2 = entity2.get('device_id')
        
        return {
            'entity1_domain': domain1,
            'entity2_domain': domain2,
            'same_domain': domain1 == domain2,
            'same_area': area1 is not None and area2 is not None and area1 == area2,
            'same_device': device1 is not None and device2 is not None and device1 == device2,
            'domain_complementary': self._are_domains_complementary(domain1, domain2)
        }
    
    def _extract_usage_features(
        self,
        entity1: dict,
        entity2: dict,
        usage_stats: dict
    ) -> dict:
        """Extract usage statistics features"""
        entity1_id = entity1.get('entity_id', '')
        entity2_id = entity2.get('entity_id', '')
        
        stats1 = usage_stats.get(entity1_id, {})
        stats2 = usage_stats.get(entity2_id, {})
        
        freq1 = stats1.get('frequency', 0.5)
        freq2 = stats2.get('frequency', 0.5)
        
        # Time overlap (if available)
        time_overlap = 0.0
        if 'active_hours' in stats1 and 'active_hours' in stats2:
            hours1 = set(stats1['active_hours'])
            hours2 = set(stats2['active_hours'])
            if hours1 and hours2:
                overlap = len(hours1 & hours2)
                union = len(hours1 | hours2)
                time_overlap = overlap / union if union > 0 else 0.0
        
        return {
            'usage_frequency_1': freq1,
            'usage_frequency_2': freq2,
            'usage_frequency_diff': abs(freq1 - freq2),
            'usage_frequency_sum': freq1 + freq2,
            'time_overlap': time_overlap
        }
    
    def _extract_external_features(self, timestamp: datetime) -> dict:
        """Extract external data features (weather, carbon, electricity, air quality)"""
        features = {}
        
        # Weather features
        weather = self._get_weather_data(timestamp)
        if weather:
            features.update({
                'temperature': weather.get('temperature', 20.0),
                'humidity': weather.get('humidity', 50.0),
                'condition': weather.get('condition', 'unknown')
            })
        
        # Carbon intensity features
        carbon = self._get_carbon_data(timestamp)
        if carbon:
            features.update({
                'carbon_intensity': carbon.get('intensity', 0.0),
                'carbon_index': carbon.get('index', 'moderate')
            })
        
        # Electricity pricing features
        electricity = self._get_electricity_data(timestamp)
        if electricity:
            features.update({
                'electricity_price': electricity.get('price', 0.0),
                'price_tier': electricity.get('tier', 'standard')
            })
        
        # Air quality features
        air_quality = self._get_air_quality_data(timestamp)
        if air_quality:
            features.update({
                'air_quality_index': air_quality.get('aqi', 50),
                'pm25': air_quality.get('pm25', 0.0),
                'pm10': air_quality.get('pm10', 0.0)
            })
        
        return features
    
    def _extract_temporal_features(self, timestamp: datetime) -> dict:
        """Extract temporal features"""
        return {
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),  # 0 = Monday, 6 = Sunday
            'is_weekend': timestamp.weekday() >= 5,
            'is_night': timestamp.hour < 6 or timestamp.hour >= 22,
            'is_day': 6 <= timestamp.hour < 18,
            'is_evening': 18 <= timestamp.hour < 22
        }
    
    def _extract_spatial_features(self, entity1: dict, entity2: dict) -> dict:
        """Extract spatial features"""
        area1 = entity1.get('area_id')
        area2 = entity2.get('area_id')
        
        same_area = area1 is not None and area2 is not None and area1 == area2
        
        # Spatial distance (0.0 = same room, 1.0 = far apart)
        if same_area:
            spatial_distance = 0.0
        elif area1 is None or area2 is None:
            spatial_distance = 0.5  # Unknown
        else:
            spatial_distance = 1.0  # Different areas
        
        return {
            'same_area': same_area,
            'spatial_distance': spatial_distance,
            'area1': area1,
            'area2': area2
        }
    
    def _are_domains_complementary(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are complementary (likely to be correlated)"""
        complementary_pairs = [
            ('binary_sensor', 'light'),  # Motion sensor -> light
            ('binary_sensor', 'switch'),  # Door sensor -> switch
            ('binary_sensor', 'lock'),  # Door sensor -> lock
            ('sensor', 'climate'),  # Temperature sensor -> climate
            ('light', 'switch'),  # Light -> switch
        ]
        
        pair = tuple(sorted([domain1, domain2]))
        return pair in [tuple(sorted(p)) for p in complementary_pairs]
    
    def _get_weather_data(self, timestamp: datetime) -> Optional[dict]:
        """Get weather data (cached)"""
        # Check cache
        cache_key = timestamp.replace(minute=0, second=0, microsecond=0)  # Hourly cache
        if cache_key in self.weather_cache:
            return self.weather_cache[cache_key]
        
        # Query data API if available
        if self.data_api_client:
            try:
                # Query weather domain from InfluxDB
                # This would be implemented based on data-api client
                # For now, return None (external data integration in Epic 33-35)
                pass
            except Exception as e:
                logger.debug("Failed to fetch weather data: %s", e)
        
        return None
    
    def _get_carbon_data(self, timestamp: datetime) -> Optional[dict]:
        """Get carbon intensity data (cached)"""
        cache_key = timestamp.replace(minute=0, second=0, microsecond=0)
        if cache_key in self.carbon_cache:
            return self.carbon_cache[cache_key]
        
        # Query data API if available
        if self.data_api_client:
            try:
                # Query carbon intensity service
                pass
            except Exception as e:
                logger.debug("Failed to fetch carbon data: %s", e)
        
        return None
    
    def _get_electricity_data(self, timestamp: datetime) -> Optional[dict]:
        """Get electricity pricing data (cached)"""
        cache_key = timestamp.replace(minute=0, second=0, microsecond=0)
        if cache_key in self.electricity_cache:
            return self.electricity_cache[cache_key]
        
        # Query data API if available
        if self.data_api_client:
            try:
                # Query electricity pricing service
                pass
            except Exception as e:
                logger.debug("Failed to fetch electricity data: %s", e)
        
        return None
    
    def _get_air_quality_data(self, timestamp: datetime) -> Optional[dict]:
        """Get air quality data (cached)"""
        cache_key = timestamp.replace(minute=0, second=0, microsecond=0)
        if cache_key in self.air_quality_cache:
            return self.air_quality_cache[cache_key]
        
        # Query data API if available
        if self.data_api_client:
            try:
                # Query air quality service
                pass
            except Exception as e:
                logger.debug("Failed to fetch air quality data: %s", e)
        
        return None

