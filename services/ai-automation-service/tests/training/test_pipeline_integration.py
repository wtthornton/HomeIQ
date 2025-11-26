"""
Integration tests for weather and carbon generators in the synthetic home pipeline.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.training.synthetic_area_generator import SyntheticAreaGenerator
from src.training.synthetic_carbon_intensity_generator import SyntheticCarbonIntensityGenerator
from src.training.synthetic_device_generator import SyntheticDeviceGenerator
from src.training.synthetic_event_generator import SyntheticEventGenerator
from src.training.synthetic_home_generator import SyntheticHomeGenerator
from src.training.synthetic_weather_generator import SyntheticWeatherGenerator


class TestPipelineIntegration:
    """Test weather and carbon integration in the synthetic home pipeline."""
    
    def test_home_json_structure_with_external_data(self):
        """Test that home JSON structure includes external_data section."""
        home_generator = SyntheticHomeGenerator()
        area_generator = SyntheticAreaGenerator()
        device_generator = SyntheticDeviceGenerator()
        event_generator = SyntheticEventGenerator()
        weather_generator = SyntheticWeatherGenerator()
        carbon_generator = SyntheticCarbonIntensityGenerator()
        
        # Generate a single home
        homes = home_generator.generate_homes(target_count=1)
        assert len(homes) == 1
        
        home = homes[0]
        
        # Generate areas, devices, events
        areas = area_generator.generate_areas(home)
        devices = device_generator.generate_devices(home, areas)
        
        # Generate events (synchronous for test)
        import asyncio
        events = asyncio.run(event_generator.generate_events(devices, days=7))
        
        # Generate weather and carbon data
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        weather_data = weather_generator.generate_weather(home, start_date, 7)
        carbon_data = carbon_generator.generate_carbon_intensity(home, start_date, 7)
        
        # Correlate
        weather_correlated = weather_generator.correlate_with_hvac(
            weather_data,
            events,
            devices
        )
        final_events = carbon_generator.correlate_with_energy_devices(
            carbon_data,
            weather_correlated,
            devices
        )
        
        # Build complete home structure
        home['areas'] = areas
        home['devices'] = devices
        home['events'] = final_events
        home['external_data'] = {
            'weather': weather_data,
            'carbon_intensity': carbon_data
        }
        
        # Validate structure
        assert 'external_data' in home
        assert 'weather' in home['external_data']
        assert 'carbon_intensity' in home['external_data']
        
        # Validate weather data structure
        assert len(home['external_data']['weather']) > 0
        weather_point = home['external_data']['weather'][0]
        assert 'timestamp' in weather_point
        assert 'temperature' in weather_point
        assert 'condition' in weather_point
        
        # Validate carbon data structure
        assert len(home['external_data']['carbon_intensity']) > 0
        carbon_point = home['external_data']['carbon_intensity'][0]
        assert 'timestamp' in carbon_point
        assert 'intensity' in carbon_point
        assert 'renewable_percentage' in carbon_point
        assert 'forecast' in carbon_point
    
    def test_json_serialization(self):
        """Test that home with external_data can be serialized to JSON."""
        home_generator = SyntheticHomeGenerator()
        area_generator = SyntheticAreaGenerator()
        device_generator = SyntheticDeviceGenerator()
        event_generator = SyntheticEventGenerator()
        weather_generator = SyntheticWeatherGenerator()
        carbon_generator = SyntheticCarbonIntensityGenerator()
        
        # Generate a minimal home
        homes = home_generator.generate_homes(target_count=1)
        home = homes[0]
        
        # Generate minimal data
        areas = area_generator.generate_areas(home)
        devices = device_generator.generate_devices(home, areas)
        
        import asyncio
        events = asyncio.run(event_generator.generate_events(devices, days=1))
        
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        weather_data = weather_generator.generate_weather(home, start_date, 1)
        carbon_data = carbon_generator.generate_carbon_intensity(home, start_date, 1)
        
        # Build complete structure
        home['areas'] = areas
        home['devices'] = devices
        home['events'] = events
        home['external_data'] = {
            'weather': weather_data,
            'carbon_intensity': carbon_data
        }
        
        # Test JSON serialization
        json_str = json.dumps(home, indent=2, ensure_ascii=False)
        assert len(json_str) > 0
        
        # Test JSON deserialization
        parsed = json.loads(json_str)
        assert 'external_data' in parsed
        assert 'weather' in parsed['external_data']
        assert 'carbon_intensity' in parsed['external_data']
    
    def test_pipeline_doesnt_break_existing_functionality(self):
        """Test that adding external_data doesn't break existing pipeline."""
        home_generator = SyntheticHomeGenerator()
        area_generator = SyntheticAreaGenerator()
        device_generator = SyntheticDeviceGenerator()
        event_generator = SyntheticEventGenerator()
        
        # Generate home without external data (existing functionality)
        homes = home_generator.generate_homes(target_count=1)
        home = homes[0]
        
        areas = area_generator.generate_areas(home)
        devices = device_generator.generate_devices(home, areas)
        
        import asyncio
        events = asyncio.run(event_generator.generate_events(devices, days=1))
        
        # Existing structure should still work
        home['areas'] = areas
        home['devices'] = devices
        home['events'] = events
        
        # Validate existing fields
        assert 'home_type' in home
        assert 'areas' in home
        assert 'devices' in home
        assert 'events' in home
        
        # external_data is optional, so it's OK if it's not present
        # But if it is present, it should have the right structure
        if 'external_data' in home:
            assert 'weather' in home['external_data']
            assert 'carbon_intensity' in home['external_data']

