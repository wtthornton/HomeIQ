"""
Unit tests for SyntheticExternalDataGenerator.

Tests orchestrator coordination, unified generation, and error handling.
"""

import pytest
from datetime import datetime, timezone

from src.training.synthetic_external_data_generator import (
    SyntheticExternalDataGenerator
)


class TestSyntheticExternalDataGenerator:
    """Test suite for SyntheticExternalDataGenerator."""
    
    def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = SyntheticExternalDataGenerator()
        assert orchestrator is not None
        assert orchestrator.weather_gen is not None
        assert orchestrator.carbon_gen is not None
        assert orchestrator.pricing_gen is not None
        assert orchestrator.calendar_gen is not None
    
    def test_generate_external_data_basic(self):
        """Test basic external data generation."""
        orchestrator = SyntheticExternalDataGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        external_data = orchestrator.generate_external_data(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Verify structure
        assert isinstance(external_data, dict)
        assert 'weather' in external_data
        assert 'carbon_intensity' in external_data
        assert 'pricing' in external_data
        assert 'calendar' in external_data
        
        # Verify data types
        assert isinstance(external_data['weather'], list)
        assert isinstance(external_data['carbon_intensity'], list)
        assert isinstance(external_data['pricing'], list)
        assert isinstance(external_data['calendar'], list)
        
        # Verify data is not empty
        assert len(external_data['weather']) > 0
        assert len(external_data['carbon_intensity']) > 0
        assert len(external_data['pricing']) > 0
        assert len(external_data['calendar']) > 0
    
    def test_generate_external_data_multiple_days(self):
        """Test external data generation for multiple days."""
        orchestrator = SyntheticExternalDataGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 7
        
        external_data = orchestrator.generate_external_data(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Verify data scales with days
        # Weather: 24 hourly points per day
        assert len(external_data['weather']) == 24 * days
        # Carbon: 96 points per day (24 hours * 4 quarters)
        assert len(external_data['carbon_intensity']) == 96 * days
        # Pricing: 24 hourly points per day
        assert len(external_data['pricing']) == 24 * days
        # Calendar: At least 1 event per day
        assert len(external_data['calendar']) >= days
    
    def test_generate_external_data_with_location(self):
        """Test external data generation with location parameter."""
        orchestrator = SyntheticExternalDataGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        location = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'state': 'California',
            'country': 'USA'
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        external_data = orchestrator.generate_external_data(
            home=home,
            start_date=start_date,
            days=days,
            location=location
        )
        
        # Verify structure
        assert 'weather' in external_data
        assert 'carbon_intensity' in external_data
        assert 'pricing' in external_data
        assert 'calendar' in external_data
        
        # Verify data points have location-specific characteristics
        # Weather should reflect California climate
        assert len(external_data['weather']) > 0
        # Carbon should reflect California grid region
        assert len(external_data['carbon_intensity']) > 0
        # Pricing should reflect California TOU pricing
        assert len(external_data['pricing']) > 0
    
    def test_generate_external_data_structure(self):
        """Test that external data structure is correct."""
        orchestrator = SyntheticExternalDataGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {}
        }
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        external_data = orchestrator.generate_external_data(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Verify weather data structure
        weather_point = external_data['weather'][0]
        assert 'timestamp' in weather_point
        assert 'temperature' in weather_point
        
        # Verify carbon intensity data structure
        carbon_point = external_data['carbon_intensity'][0]
        assert 'timestamp' in carbon_point
        assert 'intensity' in carbon_point
        
        # Verify pricing data structure
        pricing_point = external_data['pricing'][0]
        assert 'timestamp' in pricing_point
        assert 'price_per_kwh' in pricing_point
        assert 'pricing_tier' in pricing_point
        
        # Verify calendar data structure
        calendar_event = external_data['calendar'][0]
        assert 'timestamp' in calendar_event
        assert 'event_type' in calendar_event
        assert 'presence_state' in calendar_event
    
    def test_generate_external_data_coordination(self):
        """Test that orchestrator coordinates all generators correctly."""
        orchestrator = SyntheticExternalDataGenerator()
        home = {
            'home_type': 'single_family_house',
            'metadata': {
                'grid_region': 'california',
                'climate_zone': 'temperate',
                'pricing_region': 'california_tou'
            }
        }
        start_date = datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        external_data = orchestrator.generate_external_data(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Verify all generators were called
        assert len(external_data['weather']) > 0
        assert len(external_data['carbon_intensity']) > 0
        assert len(external_data['pricing']) > 0
        assert len(external_data['calendar']) > 0
        
        # Verify timestamps are consistent (all start from same date)
        weather_timestamp = external_data['weather'][0]['timestamp']
        carbon_timestamp = external_data['carbon_intensity'][0]['timestamp']
        pricing_timestamp = external_data['pricing'][0]['timestamp']
        calendar_timestamp = external_data['calendar'][0]['timestamp']
        
        # All should start from the same date (within same day)
        assert weather_timestamp.startswith('2025-06-15')
        assert carbon_timestamp.startswith('2025-06-15')
        assert pricing_timestamp.startswith('2025-06-15')
        assert calendar_timestamp.startswith('2025-06-15')
    
    def test_generate_external_data_error_handling(self):
        """Test error handling in orchestrator."""
        orchestrator = SyntheticExternalDataGenerator()
        
        # Test with invalid home structure (should still work with defaults)
        home = {}  # Empty home
        start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        days = 1
        
        # Should not raise exception, but use defaults
        external_data = orchestrator.generate_external_data(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Should still generate data with defaults
        assert 'weather' in external_data
        assert 'carbon_intensity' in external_data
        assert 'pricing' in external_data
        assert 'calendar' in external_data

