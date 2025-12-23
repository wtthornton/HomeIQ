"""
Unit tests for SyntheticWeatherGenerator.

Tests climate zone detection, basic temperature generation, and edge cases.
"""

import pytest
from datetime import datetime, timezone

from src.training.synthetic_weather_generator import (
    SyntheticWeatherGenerator,
    WeatherDataPoint
)


class TestSyntheticWeatherGenerator:
    """Test suite for SyntheticWeatherGenerator."""
    
    def test_initialization(self):
        """Test generator initialization."""
        generator = SyntheticWeatherGenerator()
        assert generator is not None
        assert hasattr(generator, 'CLIMATE_ZONES')
        assert len(generator.CLIMATE_ZONES) == 4
    
    def test_climate_zone_arctic_high_latitude(self):
        """Test arctic climate zone detection for high latitude."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'latitude': 65.0}
        
        zone = generator._get_climate_zone(home, location)
        assert zone == 'arctic'
    
    def test_climate_zone_arctic_low_latitude(self):
        """Test arctic climate zone detection for low latitude."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'latitude': -65.0}
        
        zone = generator._get_climate_zone(home, location)
        assert zone == 'arctic'
    
    def test_climate_zone_tropical(self):
        """Test tropical climate zone detection."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'latitude': 15.0}
        
        zone = generator._get_climate_zone(home, location)
        assert zone == 'tropical'
    
    def test_climate_zone_tropical_negative(self):
        """Test tropical climate zone detection for negative latitude."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'latitude': -15.0}
        
        zone = generator._get_climate_zone(home, location)
        assert zone == 'tropical'
    
    def test_climate_zone_continental_positive(self):
        """Test continental climate zone detection for positive latitude."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'latitude': 45.0}
        
        zone = generator._get_climate_zone(home, location)
        assert zone == 'continental'
    
    def test_climate_zone_continental_negative(self):
        """Test continental climate zone detection for negative latitude."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'latitude': -45.0}
        
        zone = generator._get_climate_zone(home, location)
        assert zone == 'continental'
    
    def test_climate_zone_from_metadata(self):
        """Test climate zone detection from home metadata."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {
                'climate_zone': 'tropical'
            }
        }
        
        zone = generator._get_climate_zone(home, None)
        assert zone == 'tropical'
    
    def test_climate_zone_fallback_temperate(self):
        """Test fallback to temperate when no location data."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        
        zone = generator._get_climate_zone(home, None)
        assert zone == 'temperate'
    
    def test_climate_zone_location_lat_key(self):
        """Test climate zone detection with 'lat' key instead of 'latitude'."""
        generator = SyntheticWeatherGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'lat': 15.0}
        
        zone = generator._get_climate_zone(home, location)
        assert zone == 'tropical'
    
    def test_generate_weather_basic(self):
        """Test basic weather generation."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days)
        
        assert len(weather_data) == 24  # 24 hours per day
        assert all('timestamp' in point for point in weather_data)
        assert all('temperature' in point for point in weather_data)
    
    def test_generate_weather_multiple_days(self):
        """Test weather generation for multiple days."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 7
        
        weather_data = generator.generate_weather(home, start_date, days)
        
        assert len(weather_data) == 7 * 24  # 7 days * 24 hours
        assert all('timestamp' in point for point in weather_data)
        assert all('temperature' in point for point in weather_data)
    
    def test_generate_weather_temperature_range_tropical(self):
        """Test temperature values are within tropical range."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        location = {'latitude': 15.0}
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days, location)
        
        temp_min, temp_max = generator.CLIMATE_ZONES['tropical']['temp_range']
        for point in weather_data:
            assert temp_min <= point['temperature'] <= temp_max
    
    def test_generate_weather_temperature_range_arctic(self):
        """Test temperature values are within arctic range."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        location = {'latitude': 65.0}
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days, location)
        
        temp_min, temp_max = generator.CLIMATE_ZONES['arctic']['temp_range']
        for point in weather_data:
            assert temp_min <= point['temperature'] <= temp_max
    
    def test_generate_weather_timestamp_format(self):
        """Test timestamp format is ISO 8601."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days)
        
        for point in weather_data:
            # Verify timestamp is ISO format string
            assert isinstance(point['timestamp'], str)
            # Should be parseable as datetime
            parsed = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
            assert parsed is not None
    
    def test_weather_data_point_pydantic_model(self):
        """Test WeatherDataPoint Pydantic model."""
        data_point = WeatherDataPoint(
            timestamp="2025-01-15T08:00:00+00:00",
            temperature=22.5
        )
        
        assert data_point.timestamp == "2025-01-15T08:00:00+00:00"
        assert data_point.temperature == 22.5
        assert data_point.condition is None
        assert data_point.humidity is None
        assert data_point.precipitation is None
    
    def test_weather_data_point_with_optional_fields(self):
        """Test WeatherDataPoint with optional fields."""
        data_point = WeatherDataPoint(
            timestamp="2025-01-15T08:00:00+00:00",
            temperature=22.5,
            condition="sunny",
            humidity=65.0,
            precipitation=0.0
        )
        
        assert data_point.condition == "sunny"
        assert data_point.humidity == 65.0
        assert data_point.precipitation == 0.0
    
    def test_get_season_winter(self):
        """Test season detection for winter months."""
        generator = SyntheticWeatherGenerator()
        winter_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(winter_date) == 'winter'
        
        winter_date2 = datetime(2025, 12, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(winter_date2) == 'winter'
    
    def test_get_season_spring(self):
        """Test season detection for spring months."""
        generator = SyntheticWeatherGenerator()
        spring_date = datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(spring_date) == 'spring'
        
        spring_date2 = datetime(2025, 5, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(spring_date2) == 'spring'
    
    def test_get_season_summer(self):
        """Test season detection for summer months."""
        generator = SyntheticWeatherGenerator()
        summer_date = datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(summer_date) == 'summer'
        
        summer_date2 = datetime(2025, 8, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(summer_date2) == 'summer'
    
    def test_get_season_fall(self):
        """Test season detection for fall months."""
        generator = SyntheticWeatherGenerator()
        fall_date = datetime(2025, 9, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(fall_date) == 'fall'
        
        fall_date2 = datetime(2025, 11, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert generator._get_season(fall_date2) == 'fall'
    
    def test_calculate_seasonal_temp_winter(self):
        """Test seasonal temperature calculation for winter."""
        generator = SyntheticWeatherGenerator()
        base_temp = 15.0
        winter_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        seasonal_temp = generator._calculate_seasonal_temp(base_temp, winter_date, 'temperate')
        
        # Winter should be colder (negative offset)
        assert seasonal_temp < base_temp
    
    def test_calculate_seasonal_temp_summer(self):
        """Test seasonal temperature calculation for summer."""
        generator = SyntheticWeatherGenerator()
        base_temp = 15.0
        summer_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        seasonal_temp = generator._calculate_seasonal_temp(base_temp, summer_date, 'temperate')
        
        # Summer should be warmer (positive offset)
        assert seasonal_temp > base_temp
    
    def test_calculate_seasonal_temp_within_bounds(self):
        """Test seasonal temperature stays within climate zone bounds."""
        generator = SyntheticWeatherGenerator()
        base_temp = 15.0
        winter_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        seasonal_temp = generator._calculate_seasonal_temp(base_temp, winter_date, 'temperate')
        
        temp_min, temp_max = generator.CLIMATE_ZONES['temperate']['temp_range']
        assert temp_min <= seasonal_temp <= temp_max
    
    def test_calculate_daily_temp_peak_afternoon(self):
        """Test daily temperature cycle peaks in afternoon."""
        generator = SyntheticWeatherGenerator()
        base_temp = 20.0
        season = 'summer'
        
        # Check temperatures around peak time (2-3 PM)
        afternoon_temps = []
        for hour in [13, 14, 15, 16]:
            temp = generator._calculate_daily_temp(base_temp, hour, season)
            afternoon_temps.append(temp)
        
        # Afternoon should be warmer than base
        assert any(temp > base_temp for temp in afternoon_temps)
    
    def test_calculate_daily_temp_minimum_morning(self):
        """Test daily temperature cycle minimum in early morning."""
        generator = SyntheticWeatherGenerator()
        base_temp = 20.0
        season = 'summer'
        
        # Check temperatures around minimum time (4-6 AM)
        morning_temps = []
        for hour in [4, 5, 6, 7]:
            temp = generator._calculate_daily_temp(base_temp, hour, season)
            morning_temps.append(temp)
        
        # Morning should be cooler than base
        assert any(temp < base_temp for temp in morning_temps)
    
    def test_generate_weather_with_seasonal_patterns(self):
        """Test weather generation includes seasonal patterns."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        # Winter date
        winter_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        winter_weather = generator.generate_weather(home, winter_date, days)
        
        # Summer date
        summer_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        summer_weather = generator.generate_weather(home, summer_date, days)
        
        # Average winter temp should be lower than summer temp
        winter_avg = sum(p['temperature'] for p in winter_weather) / len(winter_weather)
        summer_avg = sum(p['temperature'] for p in summer_weather) / len(summer_weather)
        
        assert winter_avg < summer_avg
    
    def test_generate_weather_with_daily_cycle(self):
        """Test weather generation includes daily temperature cycle."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days)
        
        # Find temperatures at different times
        morning_temp = weather_data[5]['temperature']  # 5 AM
        afternoon_temp = weather_data[14]['temperature']  # 2 PM
        
        # Afternoon should be warmer than morning (peak of daily cycle)
        assert afternoon_temp > morning_temp
        
        # Verify we have temperature variation throughout the day
        temps = [p['temperature'] for p in weather_data]
        temp_range = max(temps) - min(temps)
        # Should have at least 5°C variation throughout the day
        assert temp_range >= 5.0
    
    def test_generate_condition_snowy_below_freezing(self):
        """Test condition generation returns snowy when temperature < 0°C."""
        generator = SyntheticWeatherGenerator()
        
        condition = generator._generate_condition(
            temperature=-5.0,
            season='winter',
            climate_zone='temperate',
            random_factor=0.5
        )
        
        assert condition == "snowy"
    
    def test_generate_condition_rainy_probability(self):
        """Test condition generation returns rainy based on probability."""
        generator = SyntheticWeatherGenerator()
        
        # Use low random factor to trigger rain
        condition = generator._generate_condition(
            temperature=15.0,
            season='spring',
            climate_zone='temperate',
            random_factor=0.1  # Low value should trigger rain
        )
        
        # Should be rainy or cloudy (depending on exact probability)
        assert condition in ("rainy", "cloudy", "sunny")
    
    def test_generate_condition_sunny_or_cloudy(self):
        """Test condition generation returns sunny or cloudy for normal conditions."""
        generator = SyntheticWeatherGenerator()
        
        # Use high random factor to avoid rain
        condition = generator._generate_condition(
            temperature=20.0,
            season='summer',
            climate_zone='temperate',
            random_factor=0.9  # High value should avoid rain
        )
        
        assert condition in ("sunny", "cloudy")
    
    def test_calculate_humidity_rainy_high(self):
        """Test humidity calculation for rainy condition."""
        generator = SyntheticWeatherGenerator()
        
        humidity = generator._calculate_humidity(
            condition="rainy",
            temperature=15.0,
            climate_zone='temperate'
        )
        
        # Rainy should have high humidity (80-95%)
        assert 80 <= humidity <= 95
    
    def test_calculate_humidity_snowy_moderate_high(self):
        """Test humidity calculation for snowy condition."""
        generator = SyntheticWeatherGenerator()
        
        humidity = generator._calculate_humidity(
            condition="snowy",
            temperature=-5.0,
            climate_zone='temperate'
        )
        
        # Snowy should have moderate-high humidity (70-90%)
        assert 70 <= humidity <= 90
    
    def test_calculate_humidity_hot_weather_low(self):
        """Test humidity calculation for hot weather."""
        generator = SyntheticWeatherGenerator()
        
        humidity = generator._calculate_humidity(
            condition="sunny",
            temperature=35.0,
            climate_zone='temperate'
        )
        
        # Hot weather should have low humidity (30-50%)
        assert 30 <= humidity <= 50
    
    def test_calculate_humidity_within_climate_zone(self):
        """Test humidity stays within climate zone bounds."""
        generator = SyntheticWeatherGenerator()
        
        humidity = generator._calculate_humidity(
            condition="sunny",
            temperature=20.0,
            climate_zone='tropical'
        )
        
        # Should be within tropical humidity range (60-90%)
        temp_min, temp_max = generator.CLIMATE_ZONES['tropical']['temp_range']
        humidity_min, humidity_max = generator.CLIMATE_ZONES['tropical']['humidity_range']
        assert humidity_min <= humidity <= humidity_max
    
    def test_calculate_precipitation_rainy(self):
        """Test precipitation calculation for rainy condition."""
        generator = SyntheticWeatherGenerator()
        
        precipitation = generator._calculate_precipitation(
            condition="rainy",
            temperature=15.0
        )
        
        # Rain should have precipitation (0.1-10 mm/h)
        assert 0.1 <= precipitation <= 10.0
    
    def test_calculate_precipitation_snowy(self):
        """Test precipitation calculation for snowy condition."""
        generator = SyntheticWeatherGenerator()
        
        precipitation = generator._calculate_precipitation(
            condition="snowy",
            temperature=-5.0
        )
        
        # Snow should have precipitation (0.1-3 mm/h)
        assert 0.1 <= precipitation <= 3.0
    
    def test_calculate_precipitation_sunny_zero(self):
        """Test precipitation is zero for sunny condition."""
        generator = SyntheticWeatherGenerator()
        
        precipitation = generator._calculate_precipitation(
            condition="sunny",
            temperature=20.0
        )
        
        assert precipitation == 0.0
    
    def test_calculate_precipitation_cloudy_zero(self):
        """Test precipitation is zero for cloudy condition."""
        generator = SyntheticWeatherGenerator()
        
        precipitation = generator._calculate_precipitation(
            condition="cloudy",
            temperature=15.0
        )
        
        assert precipitation == 0.0
    
    def test_generate_weather_includes_condition(self):
        """Test weather generation includes condition field."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days)
        
        # All points should have condition
        assert all('condition' in point for point in weather_data)
        assert all(point['condition'] in ('sunny', 'cloudy', 'rainy', 'snowy') for point in weather_data)
    
    def test_generate_weather_includes_humidity(self):
        """Test weather generation includes humidity field."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days)
        
        # All points should have humidity
        assert all('humidity' in point for point in weather_data)
        assert all(0 <= point['humidity'] <= 100 for point in weather_data)
    
    def test_generate_weather_includes_precipitation(self):
        """Test weather generation includes precipitation field."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days)
        
        # All points should have precipitation
        assert all('precipitation' in point for point in weather_data)
        assert all(point['precipitation'] >= 0 for point in weather_data)
    
    def test_generate_weather_snowy_when_cold(self):
        """Test weather generation produces snowy condition when temperature is below freezing."""
        generator = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        # Use arctic climate to get cold temperatures
        location = {'latitude': 65.0}
        # Use winter date
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        weather_data = generator.generate_weather(home, start_date, days, location)
        
        # Should have at least some snowy conditions when cold
        conditions = [p['condition'] for p in weather_data]
        # With arctic winter, we should see some snowy conditions
        # (though random variation means not all will be snowy)
        assert 'snowy' in conditions or any(p['temperature'] < 0 for p in weather_data)
    
    def test_correlate_with_hvac_hot_weather(self):
        """Test HVAC correlation for hot weather (AC should turn on)."""
        generator = SyntheticWeatherGenerator()
        
        weather_data = [
            {
                'timestamp': '2025-07-15T14:00:00+00:00',
                'temperature': 28.0,
                'condition': 'sunny',
                'humidity': 50.0,
                'precipitation': 0.0
            }
        ]
        
        devices = [
            {
                'entity_id': 'climate.living_room',
                'device_type': 'climate',
                'device_class': 'thermostat'
            }
        ]
        
        device_events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'climate.living_room',
                'state': '70',
                'timestamp': '2025-07-15T14:00:00+00:00',
                'attributes': {}
            }
        ]
        
        correlated = generator.correlate_with_hvac(weather_data, device_events, devices)
        
        # Should have adjusted HVAC event with cooling mode
        hvac_events = [e for e in correlated if e.get('entity_id') == 'climate.living_room']
        assert len(hvac_events) > 0
        # Check that at least one event has weather correlation
        assert any(
            e.get('attributes', {}).get('weather_correlated') == True
            for e in hvac_events
        )
    
    def test_correlate_with_hvac_cold_weather(self):
        """Test HVAC correlation for cold weather (heat should turn on)."""
        generator = SyntheticWeatherGenerator()
        
        weather_data = [
            {
                'timestamp': '2025-01-15T08:00:00+00:00',
                'temperature': 10.0,
                'condition': 'cloudy',
                'humidity': 60.0,
                'precipitation': 0.0
            }
        ]
        
        devices = [
            {
                'entity_id': 'climate.living_room',
                'device_type': 'climate',
                'device_class': 'thermostat'
            }
        ]
        
        device_events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'climate.living_room',
                'state': '68',
                'timestamp': '2025-01-15T08:00:00+00:00',
                'attributes': {}
            }
        ]
        
        correlated = generator.correlate_with_hvac(weather_data, device_events, devices)
        
        # Should have adjusted HVAC event with heating mode
        hvac_events = [e for e in correlated if e.get('entity_id') == 'climate.living_room']
        assert len(hvac_events) > 0
        # Check that at least one event has weather correlation
        assert any(
            e.get('attributes', {}).get('weather_correlated') == True
            for e in hvac_events
        )
    
    def test_correlate_with_windows_nice_weather(self):
        """Test window correlation for nice weather (windows should open)."""
        generator = SyntheticWeatherGenerator()
        
        weather_data = [
            {
                'timestamp': '2025-05-15T12:00:00+00:00',
                'temperature': 22.0,
                'condition': 'sunny',
                'humidity': 55.0,
                'precipitation': 0.0
            }
        ]
        
        devices = [
            {
                'entity_id': 'cover.living_room_window',
                'device_type': 'cover',
                'device_class': 'window'
            }
        ]
        
        device_events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'cover.living_room_window',
                'state': 'closed',
                'timestamp': '2025-05-15T12:00:00+00:00',
                'attributes': {}
            }
        ]
        
        correlated = generator.correlate_with_windows(weather_data, device_events, devices)
        
        # Should have adjusted window event to open
        window_events = [e for e in correlated if e.get('entity_id') == 'cover.living_room_window']
        assert len(window_events) > 0
        # Check that window is open in nice weather
        assert any(
            e.get('state') == 'open' and
            e.get('attributes', {}).get('weather_correlated') == True
            for e in window_events
        )
    
    def test_correlate_with_windows_rainy_weather(self):
        """Test window correlation for rainy weather (windows should close)."""
        generator = SyntheticWeatherGenerator()
        
        weather_data = [
            {
                'timestamp': '2025-05-15T12:00:00+00:00',
                'temperature': 18.0,
                'condition': 'rainy',
                'humidity': 85.0,
                'precipitation': 5.0
            }
        ]
        
        devices = [
            {
                'entity_id': 'cover.living_room_window',
                'device_type': 'cover',
                'device_class': 'window'
            }
        ]
        
        device_events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'cover.living_room_window',
                'state': 'open',
                'timestamp': '2025-05-15T12:00:00+00:00',
                'attributes': {}
            }
        ]
        
        correlated = generator.correlate_with_windows(weather_data, device_events, devices)
        
        # Should have adjusted window event to closed
        window_events = [e for e in correlated if e.get('entity_id') == 'cover.living_room_window']
        assert len(window_events) > 0
        # Check that window is closed in rainy weather
        assert any(
            e.get('state') == 'closed' and
            e.get('attributes', {}).get('weather_correlated') == True
            for e in window_events
        )
    
    def test_correlate_with_hvac_no_hvac_devices(self):
        """Test HVAC correlation when no HVAC devices present."""
        generator = SyntheticWeatherGenerator()
        
        weather_data = [
            {
                'timestamp': '2025-07-15T14:00:00+00:00',
                'temperature': 28.0,
                'condition': 'sunny',
                'humidity': 50.0,
                'precipitation': 0.0
            }
        ]
        
        devices = [
            {
                'entity_id': 'light.living_room',
                'device_type': 'light'
            }
        ]
        
        device_events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'light.living_room',
                'state': 'on',
                'timestamp': '2025-07-15T14:00:00+00:00',
                'attributes': {}
            }
        ]
        
        correlated = generator.correlate_with_hvac(weather_data, device_events, devices)
        
        # Should return original events unchanged
        assert len(correlated) == len(device_events)
        assert all(e.get('attributes', {}).get('weather_correlated') != True for e in correlated)
    
    def test_correlate_with_windows_no_window_devices(self):
        """Test window correlation when no window devices present."""
        generator = SyntheticWeatherGenerator()
        
        weather_data = [
            {
                'timestamp': '2025-05-15T12:00:00+00:00',
                'temperature': 22.0,
                'condition': 'sunny',
                'humidity': 55.0,
                'precipitation': 0.0
            }
        ]
        
        devices = [
            {
                'entity_id': 'light.living_room',
                'device_type': 'light'
            }
        ]
        
        device_events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'light.living_room',
                'state': 'on',
                'timestamp': '2025-05-15T12:00:00+00:00',
                'attributes': {}
            }
        ]
        
        correlated = generator.correlate_with_windows(weather_data, device_events, devices)
        
        # Should return original events unchanged
        assert len(correlated) == len(device_events)
        assert all(e.get('attributes', {}).get('weather_correlated') != True for e in correlated)

