"""
Integration tests for weather and carbon intensity generators.

Tests the integration between weather generator, carbon generator,
and their correlation with device events.
"""

import time
from datetime import datetime, timezone

import pytest

from src.training.synthetic_carbon_intensity_generator import SyntheticCarbonIntensityGenerator
from src.training.synthetic_weather_generator import SyntheticWeatherGenerator


class TestWeatherCarbonIntegration:
    """Integration tests for weather and carbon generators."""
    
    def test_weather_hvac_correlation_integration(self):
        """Test integration of weather generator with HVAC correlation."""
        weather_gen = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {'area': 'living_room'}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Generate weather data
        weather_data = weather_gen.generate_weather(home, start_date, 1)
        assert len(weather_data) == 24  # 24 hours
        
        # Create device events
        device_events = [
            {
                'entity_id': 'climate.living_room',
                'state': 'off',
                'timestamp': '2025-07-15T12:00:00+00:00',
                'attributes': {}
            }
        ]
        
        # Create devices
        devices = [
            {
                'entity_id': 'climate.living_room',
                'device_type': 'climate',
                'device_class': 'thermostat',
                'area': 'living_room'
            }
        ]
        
        # Correlate weather with HVAC
        correlated_events = weather_gen.correlate_with_hvac(
            weather_data,
            device_events,
            devices
        )
        
        # Should have correlated events
        assert len(correlated_events) > 0
        
        # Check for weather correlation attributes
        hvac_events = [e for e in correlated_events if e.get('entity_id') == 'climate.living_room']
        if hvac_events:
            # At least one event should have weather correlation
            assert any('weather_correlated' in e.get('attributes', {}) for e in hvac_events)
    
    def test_carbon_energy_device_correlation_integration(self):
        """Test integration of carbon generator with energy device correlation."""
        carbon_gen = SyntheticCarbonIntensityGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Generate carbon data
        carbon_data = carbon_gen.generate_carbon_intensity(home, start_date, 1)
        assert len(carbon_data) > 0  # Should have 15-minute intervals
        
        # Create device events
        device_events = [
            {
                'entity_id': 'climate.living_room',
                'state': 'cooling',
                'timestamp': '2025-07-15T12:00:00+00:00',
                'attributes': {}
            },
            {
                'entity_id': 'sensor.ev_battery',
                'state': 'charging',
                'timestamp': '2025-07-15T19:00:00+00:00',
                'attributes': {}
            }
        ]
        
        # Create devices
        devices = [
            {
                'entity_id': 'climate.living_room',
                'device_type': 'climate',
                'device_class': 'thermostat'
            },
            {
                'entity_id': 'sensor.ev_battery',
                'device_type': 'sensor',
                'device_class': 'battery'
            }
        ]
        
        # Correlate carbon with energy devices
        correlated_events = carbon_gen.correlate_with_energy_devices(
            carbon_data,
            device_events,
            devices
        )
        
        # Should have correlated events
        assert len(correlated_events) > 0
        
        # Check for carbon correlation attributes
        hvac_events = [e for e in correlated_events if e.get('entity_id') == 'climate.living_room']
        if hvac_events:
            assert any('carbon_correlated' in e.get('attributes', {}) for e in hvac_events)
            assert any('carbon_intensity' in e.get('attributes', {}) for e in hvac_events)
    
    def test_weather_and_carbon_together(self):
        """Test weather and carbon generators working together."""
        weather_gen = SyntheticWeatherGenerator()
        carbon_gen = SyntheticCarbonIntensityGenerator()
        
        home = {
            'home_type': 'single_family_house',
            'metadata': {'area': 'living_room'}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Generate both weather and carbon data
        weather_data = weather_gen.generate_weather(home, start_date, 1)
        carbon_data = carbon_gen.generate_carbon_intensity(home, start_date, 1)
        
        # Both should generate data
        assert len(weather_data) == 24
        assert len(carbon_data) > 0
        
        # Weather data should have temperature, condition, humidity, precipitation
        assert all('temperature' in w for w in weather_data)
        assert all('condition' in w for w in weather_data)
        
        # Carbon data should have intensity, renewable_percentage, forecast
        assert all('intensity' in c for c in carbon_data)
        assert all('renewable_percentage' in c for c in carbon_data)
        assert all('forecast' in c for c in carbon_data)
    
    def test_weather_carbon_device_correlation_full_flow(self):
        """Test full integration flow: weather + carbon + device correlation."""
        weather_gen = SyntheticWeatherGenerator()
        carbon_gen = SyntheticCarbonIntensityGenerator()
        
        home = {
            'home_type': 'single_family_house',
            'metadata': {'area': 'living_room'}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Generate weather and carbon data
        weather_data = weather_gen.generate_weather(home, start_date, 1)
        carbon_data = carbon_gen.generate_carbon_intensity(home, start_date, 1)
        
        # Create device events
        device_events = [
            {
                'entity_id': 'climate.living_room',
                'state': 'off',
                'timestamp': '2025-07-15T12:00:00+00:00',
                'attributes': {}
            },
            {
                'entity_id': 'sensor.ev_battery',
                'state': 'charging',
                'timestamp': '2025-07-15T19:00:00+00:00',
                'attributes': {}
            }
        ]
        
        devices = [
            {
                'entity_id': 'climate.living_room',
                'device_type': 'climate',
                'device_class': 'thermostat',
                'area': 'living_room'
            },
            {
                'entity_id': 'sensor.ev_battery',
                'device_type': 'sensor',
                'device_class': 'battery'
            }
        ]
        
        # Correlate weather with HVAC
        weather_correlated = weather_gen.correlate_with_hvac(
            weather_data,
            device_events,
            devices
        )
        
        # Correlate carbon with energy devices
        carbon_correlated = carbon_gen.correlate_with_energy_devices(
            carbon_data,
            weather_correlated,  # Use weather-correlated events as input
            devices
        )
        
        # Should have both weather and carbon correlations
        assert len(carbon_correlated) > 0
        
        # Check for both correlation types
        hvac_events = [e for e in carbon_correlated if e.get('entity_id') == 'climate.living_room']
        if hvac_events:
            # Should have either weather or carbon correlation (or both)
            has_weather = any('weather_correlated' in e.get('attributes', {}) for e in hvac_events)
            has_carbon = any('carbon_correlated' in e.get('attributes', {}) for e in hvac_events)
            assert has_weather or has_carbon


class TestWeatherCarbonPerformance:
    """Performance tests for weather and carbon generators."""
    
    def test_weather_generator_performance(self):
        """Test weather generator performance <200ms per home."""
        weather_gen = SyntheticWeatherGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Measure generation time
        start_time = time.perf_counter()
        weather_data = weather_gen.generate_weather(home, start_date, 1)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        # Should be <200ms
        assert elapsed_ms < 200, f"Weather generation took {elapsed_ms:.2f}ms, expected <200ms"
        assert len(weather_data) == 24
    
    def test_carbon_generator_performance(self):
        """Test carbon generator performance <200ms per home."""
        carbon_gen = SyntheticCarbonIntensityGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Measure generation time
        start_time = time.perf_counter()
        carbon_data = carbon_gen.generate_carbon_intensity(home, start_date, 1)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        # Should be <200ms
        assert elapsed_ms < 200, f"Carbon generation took {elapsed_ms:.2f}ms, expected <200ms"
        assert len(carbon_data) > 0
    
    def test_combined_generation_performance(self):
        """Test combined weather + carbon generation performance <200ms."""
        weather_gen = SyntheticWeatherGenerator()
        carbon_gen = SyntheticCarbonIntensityGenerator()
        
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Measure combined generation time
        start_time = time.perf_counter()
        weather_data = weather_gen.generate_weather(home, start_date, 1)
        carbon_data = carbon_gen.generate_carbon_intensity(home, start_date, 1)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        # Combined should be <200ms (both generators together)
        assert elapsed_ms < 200, f"Combined generation took {elapsed_ms:.2f}ms, expected <200ms"
        assert len(weather_data) == 24
        assert len(carbon_data) > 0
    
    def test_correlation_performance(self):
        """Test correlation performance <200ms."""
        weather_gen = SyntheticWeatherGenerator()
        carbon_gen = SyntheticCarbonIntensityGenerator()
        
        home = {
            'home_type': 'single_family_house',
            'metadata': {'area': 'living_room'}
        }
        start_date = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        
        # Generate data
        weather_data = weather_gen.generate_weather(home, start_date, 1)
        carbon_data = carbon_gen.generate_carbon_intensity(home, start_date, 1)
        
        device_events = [
            {
                'entity_id': 'climate.living_room',
                'state': 'off',
                'timestamp': '2025-07-15T12:00:00+00:00',
                'attributes': {}
            }
        ]
        
        devices = [
            {
                'entity_id': 'climate.living_room',
                'device_type': 'climate',
                'device_class': 'thermostat',
                'area': 'living_room'
            }
        ]
        
        # Measure correlation time
        start_time = time.perf_counter()
        weather_correlated = weather_gen.correlate_with_hvac(
            weather_data,
            device_events,
            devices
        )
        carbon_correlated = carbon_gen.correlate_with_energy_devices(
            carbon_data,
            weather_correlated,
            devices
        )
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        # Correlation should be <200ms
        assert elapsed_ms < 200, f"Correlation took {elapsed_ms:.2f}ms, expected <200ms"
        assert len(carbon_correlated) > 0

