"""
Synthetic Weather Generator

Generate realistic weather data for synthetic homes based on location and climate zones.
NUC-optimized: Uses in-memory dictionaries, no external API calls.

Epic 39, Story 39.2: Synthetic Data Generation Migration
Migrated from ai-automation-service.
"""

import logging
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WeatherDataPoint(BaseModel):
    """Pydantic model for weather data point (2025 best practice)."""
    
    timestamp: str
    temperature: float
    condition: str | None = None
    humidity: float | None = None
    precipitation: float | None = None


class SyntheticWeatherGenerator:
    """
    Generate realistic weather data for synthetic homes.
    
    NUC-Optimized: Uses in-memory dictionaries, no external API calls.
    Performance target: <50ms per home for basic generation.
    """
    
    # Climate zones with temperature ranges and characteristics
    CLIMATE_ZONES: dict[str, dict[str, Any]] = {
        'tropical': {
            'temp_range': (20, 35),  # °C
            'humidity_range': (60, 90),
            'seasonal_variation': 5,  # Small seasonal variation
            'precipitation_freq': 0.3
        },
        'temperate': {
            'temp_range': (-5, 30),
            'humidity_range': (40, 80),
            'seasonal_variation': 15,
            'precipitation_freq': 0.25
        },
        'continental': {
            'temp_range': (-20, 35),
            'humidity_range': (30, 70),
            'seasonal_variation': 25,
            'precipitation_freq': 0.2
        },
        'arctic': {
            'temp_range': (-40, 15),
            'humidity_range': (50, 90),
            'seasonal_variation': 30,
            'precipitation_freq': 0.15
        }
    }
    
    def __init__(self):
        """Initialize weather generator (NUC-optimized, no heavy initialization)."""
        logger.debug("SyntheticWeatherGenerator initialized")
    
    def _get_climate_zone(
        self,
        home: dict[str, Any],
        location: dict[str, Any] | None = None
    ) -> str:
        """
        Determine climate zone from home location.
        
        Uses latitude-based heuristic:
        - Arctic: latitude > 60° or < -60°
        - Tropical: latitude between -30° and 30°
        - Continental: latitude between 30° and 60° or -30° and -60°
        - Temperate: default fallback
        
        Args:
            home: Home dictionary with metadata
            location: Optional location dict with lat/lon
        
        Returns:
            Climate zone identifier (tropical, temperate, continental, arctic)
        """
        # Try to get latitude from location parameter
        latitude = None
        if location and 'latitude' in location:
            latitude = location['latitude']
        elif location and 'lat' in location:
            latitude = location['lat']
        elif home.get('metadata', {}).get('location', {}).get('latitude'):
            latitude = home['metadata']['location']['latitude']
        elif home.get('metadata', {}).get('location', {}).get('lat'):
            latitude = home['metadata']['location']['lat']
        
        # Determine climate zone from latitude
        if latitude is not None:
            if latitude > 60 or latitude < -60:
                return 'arctic'
            elif -30 <= latitude <= 30:
                return 'tropical'
            elif (30 < latitude <= 60) or (-60 < latitude < -30):
                return 'continental'
            else:
                return 'temperate'
        
        # Fallback: check if climate zone is specified in metadata
        if home.get('metadata', {}).get('climate_zone'):
            climate_zone = home['metadata']['climate_zone']
            if climate_zone in self.CLIMATE_ZONES:
                return climate_zone
        
        # Default fallback to temperate
        logger.debug(f"No location data found for home, defaulting to temperate climate")
        return 'temperate'
    
    def _get_season(self, date: datetime) -> str:
        """
        Determine season from date.
        
        Args:
            date: Date to determine season for
        
        Returns:
            Season string: 'winter', 'spring', 'summer', 'fall'
        """
        month = date.month
        # Northern hemisphere seasons
        if month in (12, 1, 2):
            return 'winter'
        elif month in (3, 4, 5):
            return 'spring'
        elif month in (6, 7, 8):
            return 'summer'
        else:  # 9, 10, 11
            return 'fall'
    
    def _calculate_seasonal_temp(
        self,
        base_temp: float,
        date: datetime,
        climate_zone: str
    ) -> float:
        """
        Calculate seasonal temperature offset.
        
        Winter: -10°C, Summer: +10°C, Spring/Fall: 0°C
        Seasonal variation is scaled by climate zone's seasonal_variation parameter.
        
        Args:
            base_temp: Base temperature from climate zone
            date: Date for seasonal calculation
            climate_zone: Climate zone identifier
        
        Returns:
            Temperature with seasonal offset applied
        """
        season = self._get_season(date)
        climate_config = self.CLIMATE_ZONES[climate_zone]
        max_seasonal_variation = climate_config['seasonal_variation']
        
        # Seasonal offsets (scaled by climate zone variation)
        seasonal_offsets = {
            'winter': -max_seasonal_variation * 0.4,  # -10°C for zones with 25°C variation
            'spring': 0.0,
            'summer': max_seasonal_variation * 0.4,   # +10°C for zones with 25°C variation
            'fall': 0.0
        }
        
        offset = seasonal_offsets.get(season, 0.0)
        seasonal_temp = base_temp + offset
        
        # Ensure temperature stays within climate zone bounds
        temp_min, temp_max = climate_config['temp_range']
        seasonal_temp = max(temp_min, min(temp_max, seasonal_temp))
        
        return seasonal_temp
    
    def _calculate_daily_temp(
        self,
        base_temp: float,
        hour: int,
        season: str
    ) -> float:
        """
        Calculate daily temperature cycle using sinusoidal curve.
        
        Peak at 2-3 PM (14-15), minimum at 4-6 AM (4-6).
        Amplitude varies by season (stronger in summer).
        
        Args:
            base_temp: Base temperature (with seasonal offset)
            hour: Hour of day (0-23)
            season: Season string
        
        Returns:
            Temperature with daily cycle applied
        """
        # Daily cycle amplitude varies by season
        # Summer has stronger daily variation, winter has weaker
        amplitude_by_season = {
            'winter': 3.0,   # Smaller daily variation in winter
            'spring': 5.0,
            'summer': 7.0,   # Larger daily variation in summer
            'fall': 5.0
        }
        amplitude = amplitude_by_season.get(season, 5.0)
        
        # Peak temperature at 2:30 PM (14.5 hours)
        peak_hour = 14.5
        # Minimum temperature at 5:00 AM (5.0 hours)
        min_hour = 5.0
        
        # Calculate phase offset to align peak and minimum
        # Use sinusoidal function: sin((hour - peak_offset) * 2π / 24)
        # Shift so peak is at 14.5 and minimum is at 5.0
        phase_offset = (peak_hour - 6) * math.pi / 12  # Shift to align peak
        
        # Calculate daily variation using sinusoidal curve
        # Normalize hour to 0-24 range
        hour_normalized = hour % 24
        daily_variation = amplitude * math.sin((hour_normalized - 6) * math.pi / 12 - phase_offset)
        
        daily_temp = base_temp + daily_variation
        
        return daily_temp
    
    def _generate_condition(
        self,
        temperature: float,
        season: str,
        climate_zone: str,
        random_factor: float
    ) -> str:
        """
        Generate weather condition based on temperature, season, climate.
        
        Logic:
        - Snow if temp < 0°C
        - Rain probability from climate zone
        - Cloudy as default variation
        - Sunny when conditions favorable
        
        Args:
            temperature: Current temperature (°C)
            season: Season string
            climate_zone: Climate zone identifier
            random_factor: Random value (0.0-1.0) for probability
        
        Returns:
            Weather condition string (sunny, cloudy, rainy, snowy)
        """
        # Snow condition: temperature below freezing
        if temperature < 0:
            return "snowy"
        
        # Get precipitation frequency from climate zone
        climate_config = self.CLIMATE_ZONES[climate_zone]
        rain_prob = climate_config['precipitation_freq']
        
        # Adjust rain probability by season
        # Higher in spring/fall, lower in summer/winter (for temperate zones)
        if climate_zone == 'temperate':
            if season in ('spring', 'fall'):
                rain_prob *= 1.2  # 20% more likely in spring/fall
            elif season == 'summer':
                rain_prob *= 0.8  # 20% less likely in summer
        
        # Rain condition: based on precipitation frequency
        if random_factor < rain_prob:
            return "rainy"
        
        # Cloudy vs sunny based on random factor
        # 40% chance of cloudy, 60% chance of sunny
        if random_factor < 0.4:
            return "cloudy"
        else:
            return "sunny"
    
    def _calculate_humidity(
        self,
        condition: str,
        temperature: float,
        climate_zone: str
    ) -> float:
        """
        Calculate humidity based on condition and temperature.
        
        Args:
            condition: Weather condition string
            temperature: Current temperature (°C)
            climate_zone: Climate zone identifier
        
        Returns:
            Humidity percentage (0-100)
        """
        climate_config = self.CLIMATE_ZONES[climate_zone]
        humidity_min, humidity_max = climate_config['humidity_range']
        
        # Humidity correlation with condition
        if condition == "rainy":
            # High humidity when raining
            humidity = random.uniform(80, min(95, humidity_max))
        elif condition == "snowy":
            # Moderate-high humidity when snowing
            humidity = random.uniform(70, min(90, humidity_max))
        elif temperature > 30:
            # Low humidity in hot weather
            humidity = random.uniform(max(30, humidity_min), 50)
        elif temperature < 5:
            # Higher humidity in cold weather
            humidity = random.uniform(60, min(85, humidity_max))
        else:
            # Moderate humidity for normal conditions
            humidity = random.uniform(humidity_min, humidity_max)
        
        # Ensure humidity stays within climate zone bounds
        humidity = max(humidity_min, min(humidity_max, humidity))
        
        return round(humidity, 1)
    
    def _calculate_precipitation(
        self,
        condition: str,
        temperature: float
    ) -> float:
        """
        Calculate precipitation amount based on condition.
        
        Args:
            condition: Weather condition string
            temperature: Current temperature (°C)
        
        Returns:
            Precipitation amount in mm/h (0 for sunny/cloudy)
        """
        if condition == "rainy":
            # Rain: 0.1-10 mm/h based on intensity
            # Light rain: 0.1-2 mm/h, Moderate: 2-5 mm/h, Heavy: 5-10 mm/h
            intensity = random.random()
            if intensity < 0.5:
                # Light rain
                return round(random.uniform(0.1, 2.0), 1)
            elif intensity < 0.8:
                # Moderate rain
                return round(random.uniform(2.0, 5.0), 1)
            else:
                # Heavy rain
                return round(random.uniform(5.0, 10.0), 1)
        elif condition == "snowy":
            # Snow: 0.1-5 cm/h, convert to mm equivalent (1 cm = 10 mm)
            # But snow is less dense, so use 0.1-3 mm/h equivalent
            intensity = random.random()
            if intensity < 0.6:
                # Light snow
                return round(random.uniform(0.1, 1.0), 1)
            elif intensity < 0.9:
                # Moderate snow
                return round(random.uniform(1.0, 2.0), 1)
            else:
                # Heavy snow
                return round(random.uniform(2.0, 3.0), 1)
        else:
            # No precipitation for sunny/cloudy
            return 0.0
    
    def generate_weather(
        self,
        home: dict[str, Any],
        start_date: datetime,
        days: int,
        location: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate basic weather data for a home.
        
        Args:
            home: Home dictionary with metadata
            start_date: Start date for weather generation
            days: Number of days to generate
            location: Optional location data
        
        Returns:
            List of weather data dictionaries (hourly)
        """
        # Get climate zone for this home
        climate_zone = self._get_climate_zone(home, location)
        climate_config = self.CLIMATE_ZONES[climate_zone]
        
        # Calculate base temperature (midpoint of climate zone range)
        temp_min, temp_max = climate_config['temp_range']
        base_temp = (temp_min + temp_max) / 2.0
        
        # Generate hourly weather data
        weather_data = []
        current_date = start_date.replace(minute=0, second=0, microsecond=0)
        
        for day in range(days):
            for hour in range(24):
                # Calculate timestamp
                timestamp = current_date + timedelta(days=day, hours=hour)
                timestamp_str = timestamp.isoformat()
                
                # Get season for this date
                season = self._get_season(timestamp)
                
                # Calculate temperature with patterns:
                # 1. Base temperature (climate zone midpoint)
                # 2. Seasonal offset
                seasonal_temp = self._calculate_seasonal_temp(base_temp, timestamp, climate_zone)
                
                # 3. Daily cycle
                daily_temp = self._calculate_daily_temp(seasonal_temp, hour, season)
                
                # 4. Random variation (±3°C)
                random_variation = random.uniform(-3.0, 3.0)
                final_temp = daily_temp + random_variation
                
                # Ensure temperature stays within climate zone bounds
                final_temp = max(temp_min, min(temp_max, final_temp))
                
                # Generate weather condition
                random_factor = random.random()
                condition = self._generate_condition(
                    final_temp,
                    season,
                    climate_zone,
                    random_factor
                )
                
                # Calculate humidity based on condition and temperature
                humidity = self._calculate_humidity(
                    condition,
                    final_temp,
                    climate_zone
                )
                
                # Calculate precipitation based on condition
                precipitation = self._calculate_precipitation(
                    condition,
                    final_temp
                )
                
                # Create weather data point
                weather_point = {
                    'timestamp': timestamp_str,
                    'temperature': round(final_temp, 1),
                    'condition': condition,
                    'humidity': humidity,
                    'precipitation': precipitation
                }
                
                weather_data.append(weather_point)
        
        logger.debug(f"Generated {len(weather_data)} weather data points for {climate_zone} climate")
        return weather_data
    
    def correlate_with_hvac(
        self,
        weather_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        devices: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Correlate weather data with HVAC device events.
        
        Rules:
        - AC turns on when temperature > 25°C
        - Heat turns on when temperature < 18°C
        - HVAC intensity correlates with temperature extremes
        - Only adjusts events for climate/thermostat devices
        
        Args:
            weather_data: List of weather data points (hourly)
            device_events: List of existing device events
            devices: Optional list of devices (to identify HVAC devices)
        
        Returns:
            List of correlated/adjusted device events
        """
        # Find HVAC devices (climate type)
        hvac_devices = []
        if devices:
            hvac_devices = [
                d for d in devices
                if d.get('device_type') == 'climate'
                or d.get('device_class') in ('thermostat', 'temperature')
            ]
        
        # Create a map of weather by timestamp for quick lookup
        weather_by_timestamp = {w['timestamp']: w for w in weather_data}
        
        # Create a map of events by entity_id and timestamp
        events_by_entity = {}
        for event in device_events:
            entity_id = event.get('entity_id', '')
            if entity_id not in events_by_entity:
                events_by_entity[entity_id] = []
            events_by_entity[entity_id].append(event)
        
        correlated_events = []
        hvac_entity_ids = {d.get('entity_id') for d in hvac_devices if d.get('entity_id')}
        
        # Process each weather point and correlate with HVAC
        for weather_point in weather_data:
            timestamp = weather_point['timestamp']
            temperature = weather_point['temperature']
            
            # Find HVAC events near this timestamp (within 1 hour)
            for entity_id, events in events_by_entity.items():
                if entity_id not in hvac_entity_ids:
                    continue
                
                # Find closest event to this weather timestamp
                closest_event = None
                min_time_diff = float('inf')
                
                for event in events:
                    event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    weather_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_diff = abs((event_time - weather_time).total_seconds())
                    
                    if time_diff < min_time_diff and time_diff < 3600:  # Within 1 hour
                        min_time_diff = time_diff
                        closest_event = event
                
                if closest_event:
                    # Adjust HVAC state based on temperature
                    if temperature > 25:
                        # Hot weather - AC should be on or cooling
                        new_state = str(int(22 + (temperature - 25) * 0.5))  # Cooler target when hotter
                        if closest_event.get('state') != new_state:
                            adjusted_event = closest_event.copy()
                            adjusted_event['state'] = new_state
                            adjusted_event['attributes'] = adjusted_event.get('attributes', {}).copy()
                            adjusted_event['attributes']['hvac_mode'] = 'cool'
                            adjusted_event['attributes']['weather_correlated'] = True
                            correlated_events.append(adjusted_event)
                    elif temperature < 18:
                        # Cold weather - Heat should be on or heating
                        new_state = str(int(20 + (18 - temperature) * 0.3))  # Warmer target when colder
                        if closest_event.get('state') != new_state:
                            adjusted_event = closest_event.copy()
                            adjusted_event['state'] = new_state
                            adjusted_event['attributes'] = adjusted_event.get('attributes', {}).copy()
                            adjusted_event['attributes']['hvac_mode'] = 'heat'
                            adjusted_event['attributes']['weather_correlated'] = True
                            correlated_events.append(adjusted_event)
        
        # Add original events that weren't correlated
        for event in device_events:
            if not any(
                e.get('entity_id') == event.get('entity_id') and
                e.get('timestamp') == event.get('timestamp')
                for e in correlated_events
            ):
                correlated_events.append(event)
        
        # Sort by timestamp
        correlated_events.sort(key=lambda e: e.get('timestamp', ''))
        
        logger.debug(f"Correlated {len(correlated_events)} events with weather data")
        return correlated_events
    
    def correlate_with_windows(
        self,
        weather_data: list[dict[str, Any]],
        device_events: list[dict[str, Any]],
        devices: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Correlate weather data with window (cover) device events.
        
        Rules:
        - Windows open in nice weather (sunny, 18-25°C)
        - Windows closed in extreme weather (hot/cold, rainy)
        - Only adjusts events for cover devices with window device_class
        
        Args:
            weather_data: List of weather data points (hourly)
            device_events: List of existing device events
            devices: Optional list of devices (to identify window devices)
        
        Returns:
            List of correlated/adjusted device events
        """
        # Find window devices (cover type with window device_class)
        window_devices = []
        if devices:
            window_devices = [
                d for d in devices
                if d.get('device_type') == 'cover'
                and d.get('device_class') == 'window'
            ]
        
        # Create a map of events by entity_id
        events_by_entity = {}
        for event in device_events:
            entity_id = event.get('entity_id', '')
            if entity_id not in events_by_entity:
                events_by_entity[entity_id] = []
            events_by_entity[entity_id].append(event)
        
        correlated_events = []
        window_entity_ids = {d.get('entity_id') for d in window_devices if d.get('entity_id')}
        
        # Process each weather point and correlate with windows
        for weather_point in weather_data:
            timestamp = weather_point['timestamp']
            temperature = weather_point['temperature']
            condition = weather_point.get('condition', 'sunny')
            
            # Find window events near this timestamp (within 1 hour)
            for entity_id, events in events_by_entity.items():
                if entity_id not in window_entity_ids:
                    continue
                
                # Find closest event to this weather timestamp
                closest_event = None
                min_time_diff = float('inf')
                
                for event in events:
                    event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    weather_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_diff = abs((event_time - weather_time).total_seconds())
                    
                    if time_diff < min_time_diff and time_diff < 3600:  # Within 1 hour
                        min_time_diff = time_diff
                        closest_event = event
                
                if closest_event:
                    # Determine window state based on weather
                    if condition == 'sunny' and 18 <= temperature <= 25:
                        # Nice weather - windows should be open
                        new_state = 'open'
                    elif condition in ('rainy', 'snowy') or temperature < 10 or temperature > 30:
                        # Extreme weather - windows should be closed
                        new_state = 'closed'
                    else:
                        # Moderate weather - keep existing state or random
                        new_state = closest_event.get('state', 'closed')
                    
                    if closest_event.get('state') != new_state:
                        adjusted_event = closest_event.copy()
                        adjusted_event['state'] = new_state
                        adjusted_event['attributes'] = adjusted_event.get('attributes', {}).copy()
                        adjusted_event['attributes']['weather_correlated'] = True
                        correlated_events.append(adjusted_event)
        
        # Add original events that weren't correlated
        for event in device_events:
            if not any(
                e.get('entity_id') == event.get('entity_id') and
                e.get('timestamp') == event.get('timestamp')
                for e in correlated_events
            ):
                correlated_events.append(event)
        
        # Sort by timestamp
        correlated_events.sort(key=lambda e: e.get('timestamp', ''))
        
        logger.debug(f"Correlated {len(correlated_events)} window events with weather data")
        return correlated_events

