"""
End-to-end validation tests for external data integration and correlation.

Tests:
- Full pipeline integration
- All correlations working together
- Data realism validation
- Performance targets
"""

import pytest
import time
from datetime import datetime, timezone, timedelta

from src.training.synthetic_external_data_generator import SyntheticExternalDataGenerator
from src.training.synthetic_correlation_engine import SyntheticCorrelationEngine
from src.training.synthetic_home_generator import SyntheticHomeGenerator
from src.training.synthetic_area_generator import SyntheticAreaGenerator
from src.training.synthetic_device_generator import SyntheticDeviceGenerator
from src.training.synthetic_event_generator import SyntheticEventGenerator


class TestExternalDataIntegration:
    """End-to-end validation tests for external data integration."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self):
        """Test full pipeline: home → external data → correlation validation."""
        # Generate a synthetic home
        home_generator = SyntheticHomeGenerator()
        homes = home_generator.generate_homes(target_count=1, home_types=['single_family_house'])
        assert len(homes) > 0
        home = homes[0]
        
        # Generate areas and devices
        area_generator = SyntheticAreaGenerator()
        device_generator = SyntheticDeviceGenerator()
        event_generator = SyntheticEventGenerator()
        
        areas = area_generator.generate_areas(home)
        devices = device_generator.generate_devices(home, areas)
        events = await event_generator.generate_events(devices, days=7)
        
        # Generate external data
        external_data_generator = SyntheticExternalDataGenerator()
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        external_data = await external_data_generator.generate_external_data(
            home=home,
            start_date=start_date,
            days=7,
            enable_weather=True,
            enable_carbon=True,
            enable_pricing=True,
            enable_calendar=True
        )
        
        # Verify all data types present
        assert 'weather' in external_data
        assert 'carbon_intensity' in external_data
        assert 'pricing' in external_data
        assert 'calendar' in external_data
        
        # Verify data is not empty
        assert len(external_data['weather']) > 0
        assert len(external_data['carbon_intensity']) > 0
        assert len(external_data['pricing']) > 0
        assert len(external_data['calendar']) > 0
        
        # Validate correlations
        correlation_engine = SyntheticCorrelationEngine()
        correlation_results = correlation_engine.validate_all_correlations(
            external_data=external_data,
            device_events=events,
            devices=devices
        )
        
        # Verify correlation results
        assert 'weather_hvac' in correlation_results
        assert 'energy' in correlation_results
        assert 'calendar_presence' in correlation_results
        assert 'overall_valid' in correlation_results
        assert 'overall_score' in correlation_results
        
        # Overall score should be reasonable (>0.5)
        assert correlation_results['overall_score'] >= 0.5
    
    def test_data_realism_weather_temperature(self):
        """Test weather data realism: temperature ranges."""
        external_data_generator = SyntheticExternalDataGenerator()
        home = {'home_type': 'single_family_house', 'location': {'latitude': 37.7749, 'longitude': -122.4194}}
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Generate weather data
        weather_data = external_data_generator.weather_gen.generate_weather(
            home=home,
            start_date=start_date,
            days=30
        )
        
        # Validate temperature ranges (San Francisco: -5°C to 40°C)
        for weather_point in weather_data:
            temperature = weather_point.get('temperature', 0.0)
            assert -10.0 <= temperature <= 50.0, f"Temperature {temperature}°C out of realistic range"
        
        # Validate temperature variation (should have some variation)
        temperatures = [w.get('temperature', 0.0) for w in weather_data]
        temp_range = max(temperatures) - min(temperatures)
        assert temp_range >= 5.0, "Temperature should have reasonable variation"
    
    def test_data_realism_carbon_intensity(self):
        """Test carbon intensity data realism: intensity ranges."""
        external_data_generator = SyntheticExternalDataGenerator()
        home = {'home_type': 'single_family_house', 'location': {'latitude': 37.7749, 'longitude': -122.4194}}
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Generate carbon intensity data
        carbon_data = external_data_generator.carbon_gen.generate_carbon_intensity(
            home=home,
            start_date=start_date,
            days=30
        )
        
        # Validate intensity ranges (typical: 50-800 gCO2/kWh)
        for carbon_point in carbon_data:
            intensity = carbon_point.get('intensity', 0.0)
            assert 0.0 <= intensity <= 1000.0, f"Carbon intensity {intensity} out of realistic range"
        
        # Validate renewable percentage (0-100% or 0-1.0 fraction)
        for carbon_point in carbon_data:
            renewable = carbon_point.get('renewable_percentage', 0.0)
            # Accept both percentage (0-100) and fraction (0-1.0) formats
            assert 0.0 <= renewable <= 100.0, f"Renewable percentage {renewable} out of range"
    
    def test_data_realism_pricing(self):
        """Test pricing data realism: price ranges and tiers."""
        external_data_generator = SyntheticExternalDataGenerator()
        home = {'home_type': 'single_family_house', 'location': {'latitude': 37.7749, 'longitude': -122.4194}}
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Generate pricing data
        pricing_data = external_data_generator.pricing_gen.generate_pricing(
            home=home,
            start_date=start_date,
            days=30
        )
        
        # Validate price ranges (typical: $0.05-$0.50 per kWh)
        for pricing_point in pricing_data:
            price = pricing_point.get('price_per_kwh', 0.0)
            assert 0.0 <= price <= 1.0, f"Price {price} out of realistic range"
        
        # Validate pricing tiers
        valid_tiers = {'off-peak', 'mid-peak', 'peak'}
        for pricing_point in pricing_data:
            tier = pricing_point.get('pricing_tier', '')
            assert tier in valid_tiers, f"Invalid pricing tier: {tier}"
    
    def test_data_realism_calendar(self):
        """Test calendar data realism: event types and dates."""
        external_data_generator = SyntheticExternalDataGenerator()
        home = {'home_type': 'single_family_house'}
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Generate calendar data
        calendar_data = external_data_generator.calendar_gen.generate_calendar(
            home=home,
            start_date=start_date,
            days=30
        )
        
        # Validate event types
        valid_types = {'home', 'away', 'work', 'vacation', 'event', 'routine', 'commute'}
        for calendar_event in calendar_data:
            event_type = calendar_event.get('event_type', '')
            assert event_type in valid_types or event_type == '', f"Invalid event type: {event_type}"
        
        # Validate timestamps are within range (start/end or timestamp)
        for calendar_event in calendar_data:
            start = calendar_event.get('start') or calendar_event.get('timestamp', '')
            end = calendar_event.get('end', '')
            # Some events may only have timestamp, which is acceptable
            assert start or calendar_event.get('timestamp'), "Calendar event missing start/timestamp time"
    
    @pytest.mark.asyncio
    async def test_performance_target(self):
        """Test performance: <500ms per home for external data generation (7 days)."""
        external_data_generator = SyntheticExternalDataGenerator()
        home = {'home_type': 'single_family_house', 'location': {'latitude': 37.7749, 'longitude': -122.4194}}
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Measure generation time (7 days is more realistic for performance testing)
        start_time = time.time()
        external_data = await external_data_generator.generate_external_data(
            home=home,
            start_date=start_date,
            days=7,
            enable_weather=True,
            enable_carbon=True,
            enable_pricing=True,
            enable_calendar=True
        )
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Verify performance target (<500ms for 7 days)
        assert elapsed_time < 500.0, f"Generation took {elapsed_time:.2f}ms, target is <500ms for 7 days"
        
        # Verify data was generated
        assert len(external_data.get('weather', [])) > 0
        assert len(external_data.get('carbon_intensity', [])) > 0
        assert len(external_data.get('pricing', [])) > 0
        assert len(external_data.get('calendar', [])) > 0
    
    @pytest.mark.asyncio
    async def test_correlation_validation_performance(self):
        """Test correlation validation performance: <100ms per home."""
        correlation_engine = SyntheticCorrelationEngine()
        
        # Generate test data
        external_data = {
            'weather': [
                {
                    'timestamp': '2025-06-15T12:00:00+00:00',
                    'temperature': 28.0,
                    'condition': 'sunny'
                }
            ],
            'carbon_intensity': [
                {
                    'timestamp': '2025-06-15T12:00:00+00:00',
                    'intensity': 200.0,
                    'renewable_percentage': 0.5
                }
            ],
            'pricing': [
                {
                    'timestamp': '2025-06-15T12:00:00+00:00',
                    'price_per_kwh': 0.20,
                    'pricing_tier': 'mid-peak',
                    'region': 'california_tou'
                }
            ],
            'calendar': [
                {
                    'timestamp': '2025-06-15T12:00:00+00:00',
                    'event_type': 'home',
                    'summary': 'Home',
                    'start': '2025-06-15T12:00:00+00:00',
                    'end': '2025-06-15T18:00:00+00:00'
                }
            ]
        }
        
        devices = [
            {
                'entity_id': 'climate.thermostat',
                'device_type': 'climate',
                'device_class': 'thermostat'
            },
            {
                'entity_id': 'light.living_room',
                'device_type': 'light',
                'device_class': 'light'
            }
        ]
        
        device_events = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'cool',
                'event_type': 'state_changed'
            }
        ]
        
        # Measure validation time
        start_time = time.time()
        results = correlation_engine.validate_all_correlations(
            external_data=external_data,
            device_events=device_events,
            devices=devices
        )
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Verify performance target (<100ms)
        assert elapsed_time < 100.0, f"Validation took {elapsed_time:.2f}ms, target is <100ms"
        
        # Verify results
        assert 'overall_score' in results
        assert 0.0 <= results['overall_score'] <= 1.0

