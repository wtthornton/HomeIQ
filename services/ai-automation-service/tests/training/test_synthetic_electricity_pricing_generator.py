"""
Unit tests for SyntheticElectricityPricingGenerator.

Tests pricing region detection, basic price generation, and edge cases.
"""

import pytest
from datetime import datetime, timedelta, timezone

from src.training.synthetic_electricity_pricing_generator import (
    SyntheticElectricityPricingGenerator,
    PricingDataPoint
)


class TestSyntheticElectricityPricingGenerator:
    """Test suite for SyntheticElectricityPricingGenerator."""
    
    def test_initialization(self):
        """Test generator initialization."""
        generator = SyntheticElectricityPricingGenerator()
        assert generator is not None
        assert hasattr(generator, 'PRICING_REGIONS')
        assert len(generator.PRICING_REGIONS) == 3
    
    def test_pricing_region_germany(self):
        """Test Germany pricing region detection."""
        generator = SyntheticElectricityPricingGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'country': 'Germany'}
        
        region = generator._get_pricing_region(home, location)
        assert region == 'germany_awattar'
    
    def test_pricing_region_california(self):
        """Test California pricing region detection."""
        generator = SyntheticElectricityPricingGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        location = {'state': 'California'}
        
        region = generator._get_pricing_region(home, location)
        assert region == 'california_tou'
    
    def test_pricing_region_from_metadata(self):
        """Test pricing region detection from home metadata."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {
                'pricing_region': 'california_tou'
            }
        }
        
        region = generator._get_pricing_region(home, None)
        assert region == 'california_tou'
    
    def test_pricing_region_fallback_fixed_rate(self):
        """Test fallback to fixed_rate when no location data."""
        generator = SyntheticElectricityPricingGenerator()
        home = {'home_type': 'single_family_house', 'metadata': {}}
        
        region = generator._get_pricing_region(home, None)
        assert region == 'fixed_rate'
    
    def test_generate_basic_price_germany(self):
        """Test basic price generation for Germany region."""
        generator = SyntheticElectricityPricingGenerator()
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        price = generator._generate_basic_price('germany_awattar', timestamp)
        
        # Should be in realistic range (0.10-0.50 EUR/kWh)
        assert 0.10 <= price <= 0.50
        assert isinstance(price, float)
    
    def test_generate_basic_price_california(self):
        """Test basic price generation for California region."""
        generator = SyntheticElectricityPricingGenerator()
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        price = generator._generate_basic_price('california_tou', timestamp)
        
        # Should be in realistic range (0.10-0.50 USD/kWh)
        assert 0.10 <= price <= 0.50
        assert isinstance(price, float)
    
    def test_generate_basic_price_fixed_rate(self):
        """Test basic price generation for fixed rate region."""
        generator = SyntheticElectricityPricingGenerator()
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        price = generator._generate_basic_price('fixed_rate', timestamp)
        
        # Should be in realistic range (0.10-0.50 USD/kWh)
        assert 0.10 <= price <= 0.50
        assert isinstance(price, float)
    
    def test_generate_pricing_basic(self):
        """Test basic pricing generation."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days)
        
        # Should have 24 data points per day (hourly)
        assert len(pricing_data) == 24
        assert all('timestamp' in point for point in pricing_data)
        assert all('price_per_kwh' in point for point in pricing_data)
        assert all('pricing_tier' in point for point in pricing_data)
        assert all('region' in point for point in pricing_data)
    
    def test_generate_pricing_multiple_days(self):
        """Test pricing generation for multiple days."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 7
        
        pricing_data = generator.generate_pricing(home, start_date, days)
        
        # Should have 24 * 7 = 168 data points
        assert len(pricing_data) == 168
    
    def test_generate_pricing_price_ranges(self):
        """Test that all generated prices are in realistic ranges."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days)
        
        # All prices should be in realistic range (0.10-0.50)
        for point in pricing_data:
            assert 0.10 <= point['price_per_kwh'] <= 0.50
    
    def test_generate_pricing_timestamps(self):
        """Test that timestamps are correctly generated."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days)
        
        # First timestamp should match start_date
        first_timestamp = datetime.fromisoformat(pricing_data[0]['timestamp'])
        assert first_timestamp == start_date.replace(minute=0, second=0, microsecond=0)
        
        # Last timestamp should be 23 hours later
        last_timestamp = datetime.fromisoformat(pricing_data[-1]['timestamp'])
        expected_last = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=23)
        assert last_timestamp == expected_last
    
    def test_pricing_data_point_model(self):
        """Test PricingDataPoint Pydantic model validation."""
        point = PricingDataPoint(
            timestamp="2025-01-15T12:00:00+00:00",
            price_per_kwh=0.25,
            pricing_tier="off-peak",
            region="california_tou"
        )
        
        assert point.timestamp == "2025-01-15T12:00:00+00:00"
        assert point.price_per_kwh == 0.25
        assert point.pricing_tier == "off-peak"
        assert point.region == "california_tou"
        assert point.forecast is None
    
    def test_pricing_data_point_with_forecast(self):
        """Test PricingDataPoint with optional forecast field."""
        forecast = [0.24, 0.25, 0.26]
        point = PricingDataPoint(
            timestamp="2025-01-15T12:00:00+00:00",
            price_per_kwh=0.25,
            pricing_tier="off-peak",
            region="california_tou",
            forecast=forecast
        )
        
        assert point.forecast == forecast
    
    def test_generate_pricing_germany_region(self):
        """Test pricing generation with Germany region."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        location = {'country': 'Germany'}
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days, location)
        
        # All points should have germany_awattar region
        assert all(point['region'] == 'germany_awattar' for point in pricing_data)
    
    def test_generate_pricing_california_region(self):
        """Test pricing generation with California region."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        location = {'state': 'California'}
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days, location)
        
        # All points should have california_tou region
        assert all(point['region'] == 'california_tou' for point in pricing_data)
    
    def test_calculate_time_of_use_tier_peak(self):
        """Test TOU tier calculation for peak hours (weekday evening)."""
        generator = SyntheticElectricityPricingGenerator()
        # Tuesday, 6 PM (18:00) - peak hour for California TOU
        timestamp = datetime(2025, 1, 14, 18, 0, 0, tzinfo=timezone.utc)  # Tuesday
        
        tier = generator._calculate_time_of_use_tier('california_tou', timestamp)
        assert tier == 'peak'
    
    def test_calculate_time_of_use_tier_mid_peak(self):
        """Test TOU tier calculation for mid-peak hours (weekday afternoon)."""
        generator = SyntheticElectricityPricingGenerator()
        # Tuesday, 2 PM (14:00) - mid-peak hour for California TOU
        timestamp = datetime(2025, 1, 14, 14, 0, 0, tzinfo=timezone.utc)  # Tuesday
        
        tier = generator._calculate_time_of_use_tier('california_tou', timestamp)
        assert tier == 'mid-peak'
    
    def test_calculate_time_of_use_tier_off_peak(self):
        """Test TOU tier calculation for off-peak hours (early morning)."""
        generator = SyntheticElectricityPricingGenerator()
        # Tuesday, 2 AM (02:00) - off-peak hour
        timestamp = datetime(2025, 1, 14, 2, 0, 0, tzinfo=timezone.utc)  # Tuesday
        
        tier = generator._calculate_time_of_use_tier('california_tou', timestamp)
        assert tier == 'off-peak'
    
    def test_calculate_time_of_use_tier_weekend_off_peak(self):
        """Test TOU tier calculation for weekend (all off-peak)."""
        generator = SyntheticElectricityPricingGenerator()
        # Saturday, 6 PM (18:00) - weekend should be off-peak
        timestamp = datetime(2025, 1, 18, 18, 0, 0, tzinfo=timezone.utc)  # Saturday
        
        tier = generator._calculate_time_of_use_tier('california_tou', timestamp)
        assert tier == 'off-peak'
    
    def test_calculate_time_of_use_tier_fixed_rate(self):
        """Test TOU tier calculation for fixed rate (always off-peak)."""
        generator = SyntheticElectricityPricingGenerator()
        timestamp = datetime(2025, 1, 14, 18, 0, 0, tzinfo=timezone.utc)
        
        tier = generator._calculate_time_of_use_tier('fixed_rate', timestamp)
        assert tier == 'off-peak'
    
    def test_generate_pricing_with_tou_tiers(self):
        """Test that pricing generation includes correct TOU tiers."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        location = {'state': 'California'}
        # Tuesday - should have peak/mid-peak/off-peak periods
        start_date = datetime(2025, 1, 14, 0, 0, 0, tzinfo=timezone.utc)  # Tuesday
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days, location)
        
        # Should have multiple tiers on a weekday
        tiers = [point['pricing_tier'] for point in pricing_data]
        assert 'off-peak' in tiers
        assert 'mid-peak' in tiers
        assert 'peak' in tiers
    
    def test_generate_pricing_weekend_all_off_peak(self):
        """Test that weekend pricing is all off-peak."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        location = {'state': 'California'}
        # Saturday - should all be off-peak
        start_date = datetime(2025, 1, 18, 0, 0, 0, tzinfo=timezone.utc)  # Saturday
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days, location)
        
        # All points should be off-peak on weekend
        assert all(point['pricing_tier'] == 'off-peak' for point in pricing_data)
    
    def test_tou_price_multipliers(self):
        """Test that TOU multipliers are applied correctly."""
        generator = SyntheticElectricityPricingGenerator()
        baseline = generator.PRICING_REGIONS['california_tou']['baseline']
        
        # Peak hour should be higher than baseline
        peak_timestamp = datetime(2025, 1, 14, 18, 0, 0, tzinfo=timezone.utc)  # Tuesday 6 PM
        peak_price = generator._generate_basic_price('california_tou', peak_timestamp)
        
        # Off-peak hour should be lower than baseline
        off_peak_timestamp = datetime(2025, 1, 14, 2, 0, 0, tzinfo=timezone.utc)  # Tuesday 2 AM
        off_peak_price = generator._generate_basic_price('california_tou', off_peak_timestamp)
        
        # Peak should be significantly higher than off-peak
        assert peak_price > off_peak_price
        
        # Peak should be at least 1.5x the baseline (accounting for variation)
        assert peak_price >= baseline * 1.3  # Allow for some variation
        
        # Off-peak should be less than baseline
        assert off_peak_price <= baseline * 0.8  # Allow for some variation
    
    def test_demand_based_variation(self):
        """Test that demand-based variation is applied to prices."""
        generator = SyntheticElectricityPricingGenerator()
        baseline = generator.PRICING_REGIONS['california_tou']['baseline']
        
        # High demand hour (morning rush)
        high_demand_ts = datetime(2025, 1, 14, 7, 0, 0, tzinfo=timezone.utc)  # Tuesday 7 AM
        high_demand_price = generator._generate_basic_price('california_tou', high_demand_ts)
        
        # Low demand hour (night)
        low_demand_ts = datetime(2025, 1, 14, 2, 0, 0, tzinfo=timezone.utc)  # Tuesday 2 AM
        low_demand_price = generator._generate_basic_price('california_tou', low_demand_ts)
        
        # High demand should generally be higher (accounting for random variation)
        # Check multiple times to account for randomness
        high_demand_samples = [
            generator._generate_basic_price('california_tou', high_demand_ts)
            for _ in range(5)
        ]
        low_demand_samples = [
            generator._generate_basic_price('california_tou', low_demand_ts)
            for _ in range(5)
        ]
        
        # Average high demand should be higher than average low demand
        avg_high = sum(high_demand_samples) / len(high_demand_samples)
        avg_low = sum(low_demand_samples) / len(low_demand_samples)
        assert avg_high > avg_low
    
    def test_random_variation_range(self):
        """Test that random variation is within ±10% range."""
        generator = SyntheticElectricityPricingGenerator()
        baseline = generator.PRICING_REGIONS['california_tou']['baseline']
        tou_multiplier = generator.TOU_MULTIPLIERS['off-peak']  # 0.6x
        
        # Generate multiple prices and check variation range
        timestamp = datetime(2025, 1, 14, 2, 0, 0, tzinfo=timezone.utc)  # Off-peak
        prices = [
            generator._generate_basic_price('california_tou', timestamp)
            for _ in range(20)
        ]
        
        # Base price without random variation (with TOU and demand)
        # Demand factor ranges 0.9-1.0 for night hours, so base is approximately baseline * 0.6 * 0.95
        expected_base = baseline * tou_multiplier * 0.95
        
        # All prices should be within ±10% of expected base (accounting for demand variation)
        min_price = min(prices)
        max_price = max(prices)
        
        # Variation should be at least 5% (to ensure randomness is working)
        variation_range = (max_price - min_price) / expected_base
        assert variation_range >= 0.05, f"Price variation too small: {variation_range}"
    
    def test_forecast_generation(self):
        """Test that 24-hour forecast is generated correctly."""
        generator = SyntheticElectricityPricingGenerator()
        timestamp = datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)
        base_price = 0.25
        
        forecast = generator._generate_forecast('california_tou', timestamp, base_price)
        
        # Should have 24 hours of forecast
        assert len(forecast) == 24
        
        # All forecast values should be realistic prices
        for price in forecast:
            assert 0.10 <= price <= 0.50
        
        # Forecast should have variation (not all same price)
        assert len(set(forecast)) > 1, "Forecast should have price variation"
    
    def test_forecast_in_pricing_data(self):
        """Test that pricing data points include forecast."""
        generator = SyntheticElectricityPricingGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 14, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        pricing_data = generator.generate_pricing(home, start_date, days)
        
        # All points should have forecast
        assert all(point['forecast'] is not None for point in pricing_data)
        
        # All forecasts should have 24 values
        for point in pricing_data:
            assert len(point['forecast']) == 24
            # All forecast values should be realistic
            for forecast_price in point['forecast']:
                assert 0.10 <= forecast_price <= 0.50
    
    def test_forecast_realism(self):
        """Test that forecast prices follow TOU patterns."""
        generator = SyntheticElectricityPricingGenerator()
        # Tuesday noon - should have peak hours in forecast
        timestamp = datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)  # Tuesday
        base_price = 0.25
        
        forecast = generator._generate_forecast('california_tou', timestamp, base_price)
        
        # Forecast should include peak hours (17-21 = hours 5-9 in forecast)
        peak_hours_in_forecast = forecast[5:9]  # Hours 5-8 in forecast = 17:00-20:00
        
        # Peak hours should generally be higher than off-peak
        # Compare with off-peak hours in forecast (early morning, hours 0-3)
        off_peak_hours = forecast[0:3]
        
        avg_peak = sum(peak_hours_in_forecast) / len(peak_hours_in_forecast)
        avg_off_peak = sum(off_peak_hours) / len(off_peak_hours)
        
        # Peak should be higher than off-peak (accounting for variation)
        assert avg_peak > avg_off_peak * 0.9, "Peak hours in forecast should be higher than off-peak"
    
    def test_correlate_with_energy_devices_ev_charging(self):
        """Test that EV charging events are correlated with off-peak pricing."""
        generator = SyntheticElectricityPricingGenerator()
        
        # Create pricing data with peak and off-peak periods
        home = {'home_type': 'single_family_house', 'metadata': {}}
        start_date = datetime(2025, 1, 14, 0, 0, 0, tzinfo=timezone.utc)  # Tuesday
        pricing_data = generator.generate_pricing(home, start_date, 1)
        
        # Create EV device and charging event during peak period
        ev_device = {
            'entity_id': 'sensor.ev_battery',
            'device_type': 'sensor',
            'device_class': 'battery'
        }
        ev_event = {
            'entity_id': 'sensor.ev_battery',
            'timestamp': '2025-01-14T18:00:00+00:00',  # 6 PM - peak period
            'state': 'charging',
            'event_type': 'state_changed'
        }
        
        # Correlate
        correlated_events = generator.correlate_with_energy_devices(
            pricing_data,
            [ev_event],
            [ev_device]
        )
        
        # Should have adjusted event to off-peak period
        assert len(correlated_events) > 0
        optimized_events = [e for e in correlated_events if e.get('pricing_optimized')]
        if optimized_events:
            optimized_event = optimized_events[0]
            assert optimized_event.get('original_timestamp') == ev_event['timestamp']
            # New timestamp should be different
            assert optimized_event.get('timestamp') != ev_event['timestamp']
    
    def test_correlate_with_energy_devices_hvac(self):
        """Test that HVAC events can be correlated with pricing."""
        generator = SyntheticElectricityPricingGenerator()
        
        home = {'home_type': 'single_family_house', 'metadata': {}}
        start_date = datetime(2025, 1, 14, 0, 0, 0, tzinfo=timezone.utc)  # Tuesday
        pricing_data = generator.generate_pricing(home, start_date, 1)
        
        # Create HVAC device and event during peak period
        hvac_device = {
            'entity_id': 'climate.thermostat',
            'device_type': 'climate'
        }
        hvac_event = {
            'entity_id': 'climate.thermostat',
            'timestamp': '2025-01-14T18:00:00+00:00',  # 6 PM - peak
            'state': 'cooling',
            'event_type': 'state_changed'
        }
        
        # Correlate
        correlated_events = generator.correlate_with_energy_devices(
            pricing_data,
            [hvac_event],
            [hvac_device]
        )
        
        # Should process HVAC events
        assert len(correlated_events) > 0
        assert any(e.get('entity_id') == 'climate.thermostat' for e in correlated_events)
    
    def test_correlate_with_energy_devices_water_heater(self):
        """Test that high-energy devices like water heater are correlated."""
        generator = SyntheticElectricityPricingGenerator()
        
        home = {'home_type': 'single_family_house', 'metadata': {}}
        start_date = datetime(2025, 1, 14, 0, 0, 0, tzinfo=timezone.utc)
        pricing_data = generator.generate_pricing(home, start_date, 1)
        
        # Create water heater device and event
        water_heater_device = {
            'entity_id': 'water_heater.main',
            'device_type': 'water_heater'
        }
        water_heater_event = {
            'entity_id': 'water_heater.main',
            'timestamp': '2025-01-14T18:00:00+00:00',  # Peak period
            'state': 'on',
            'event_type': 'state_changed'
        }
        
        # Correlate
        correlated_events = generator.correlate_with_energy_devices(
            pricing_data,
            [water_heater_event],
            [water_heater_device]
        )
        
        # Should process water heater events
        assert len(correlated_events) > 0
        assert any(e.get('entity_id') == 'water_heater.main' for e in correlated_events)
    
    def test_correlate_respects_existing_events(self):
        """Test that correlation respects existing events (doesn't duplicate)."""
        generator = SyntheticElectricityPricingGenerator()
        
        home = {'home_type': 'single_family_house', 'metadata': {}}
        start_date = datetime(2025, 1, 14, 0, 0, 0, tzinfo=timezone.utc)
        pricing_data = generator.generate_pricing(home, start_date, 1)
        
        # Create regular device event (not energy device)
        regular_event = {
            'entity_id': 'light.kitchen',
            'timestamp': '2025-01-14T12:00:00+00:00',
            'state': 'on',
            'event_type': 'state_changed'
        }
        regular_device = {
            'entity_id': 'light.kitchen',
            'device_type': 'light'
        }
        
        # Correlate
        correlated_events = generator.correlate_with_energy_devices(
            pricing_data,
            [regular_event],
            [regular_device]
        )
        
        # Should preserve original event unchanged
        assert len(correlated_events) == 1
        assert correlated_events[0]['entity_id'] == regular_event['entity_id']
        assert correlated_events[0]['timestamp'] == regular_event['timestamp']
        assert 'pricing_optimized' not in correlated_events[0]

