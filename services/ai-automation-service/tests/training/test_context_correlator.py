"""
Unit tests for context correlator.

Tests for Story AI11.7: Context-Aware Event Generation
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.training.context_correlator import ContextCorrelator


class TestContextCorrelator:
    """Test ContextCorrelator class."""
    
    def test_correlator_initialization(self):
        """Test correlator initialization."""
        correlator = ContextCorrelator()
        assert correlator is not None
        assert correlator.HEATING_THRESHOLD == 18.0
        assert correlator.COOLING_THRESHOLD == 25.0
    
    def test_apply_weather_patterns_rain(self):
        """Test weather-driven pattern: rain → close windows."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'cover.living_room_window',
                'device_type': 'cover',
                'name': 'Living Room Window',
                'area': 'Living Room'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'cover.living_room_window',
                'state': 'open',
                'timestamp': '2025-12-02T14:00:00+00:00',
                'attributes': {'device_type': 'cover'}
            }
        ]
        
        weather_data = [
            {
                'timestamp': '2025-12-02T14:00:00+00:00',
                'temperature': 15.0,
                'condition': 'rain',
                'humidity': 80.0
            }
        ]
        
        result = correlator._apply_weather_patterns(events, devices, weather_data)
        
        # Should have added close event
        close_events = [e for e in result if e.get('state') == 'closed' and 'weather_rain' in e.get('attributes', {}).get('context', '')]
        assert len(close_events) > 0
    
    def test_apply_weather_patterns_cold(self):
        """Test weather-driven pattern: frost → heating."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'climate.living_room_thermostat',
                'device_type': 'climate',
                'name': 'Living Room Thermostat',
                'area': 'Living Room'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'climate.living_room_thermostat',
                'state': 'idle',
                'timestamp': '2025-12-02T08:00:00+00:00',
                'attributes': {'device_type': 'climate'}
            }
        ]
        
        weather_data = [
            {
                'timestamp': '2025-12-02T08:00:00+00:00',
                'temperature': 10.0,  # Below heating threshold
                'condition': 'clear',
                'humidity': 60.0
            }
        ]
        
        result = correlator._apply_weather_patterns(events, devices, weather_data)
        
        # Should have added heating event
        heat_events = [e for e in result if e.get('state') == 'heat' and 'weather_cold' in e.get('attributes', {}).get('context', '')]
        assert len(heat_events) > 0
    
    def test_apply_weather_patterns_hot(self):
        """Test weather-driven pattern: hot → cooling."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'climate.living_room_thermostat',
                'device_type': 'climate',
                'name': 'Living Room Thermostat',
                'area': 'Living Room'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'climate.living_room_thermostat',
                'state': 'idle',
                'timestamp': '2025-12-02T14:00:00+00:00',
                'attributes': {'device_type': 'climate'}
            }
        ]
        
        weather_data = [
            {
                'timestamp': '2025-12-02T14:00:00+00:00',
                'temperature': 30.0,  # Above cooling threshold
                'condition': 'clear',
                'humidity': 50.0
            }
        ]
        
        result = correlator._apply_weather_patterns(events, devices, weather_data)
        
        # Should have added cooling event
        cool_events = [e for e in result if e.get('state') == 'cool' and 'weather_hot' in e.get('attributes', {}).get('context', '')]
        assert len(cool_events) > 0
    
    def test_apply_energy_patterns_low_carbon(self):
        """Test energy-aware pattern: low carbon → EV charging."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'switch.ev_charger',
                'device_type': 'switch',
                'name': 'EV Charger',
                'area': 'Garage'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'switch.ev_charger',
                'state': 'off',
                'timestamp': '2025-12-02T12:00:00+00:00',
                'attributes': {'device_type': 'switch'}
            }
        ]
        
        carbon_data = [
            {
                'timestamp': '2025-12-02T12:00:00+00:00',
                'carbon_intensity': 150.0,  # Below low threshold
                'renewable_percentage': 80.0
            }
        ]
        
        result = correlator._apply_energy_patterns(events, devices, carbon_data)
        
        # May have added energy event (probabilistic)
        energy_events = [e for e in result if 'energy_low_carbon' in e.get('attributes', {}).get('context', '')]
        # Note: This is probabilistic, so we just check the method runs without error
    
    def test_apply_energy_patterns_high_carbon(self):
        """Test energy-aware pattern: high carbon → reduce usage."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'switch.living_room_outlet',
                'device_type': 'switch',
                'name': 'Living Room Outlet',
                'area': 'Living Room'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'switch.living_room_outlet',
                'state': 'on',
                'timestamp': '2025-12-02T18:00:00+00:00',
                'attributes': {'device_type': 'switch'}
            }
        ]
        
        carbon_data = [
            {
                'timestamp': '2025-12-02T18:00:00+00:00',
                'carbon_intensity': 500.0,  # Above high threshold
                'renewable_percentage': 20.0
            }
        ]
        
        result = correlator._apply_energy_patterns(events, devices, carbon_data)
        
        # May have added reduce events (probabilistic)
        # Just verify method runs without error
    
    def test_apply_brightness_patterns_sunset(self):
        """Test brightness-aware pattern: sunset → lights on."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'name': 'Kitchen Light',
                'area': 'Kitchen'
            }
        ]
        
        events = []
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        result = correlator._apply_brightness_patterns(events, devices, start_date)
        
        # Should have added sunset events
        sunset_events = [e for e in result if 'brightness_sunset' in e.get('attributes', {}).get('context', '')]
        assert len(sunset_events) > 0
        
        # Check sunset events have correct structure
        for event in sunset_events:
            assert event['state'] == 'on'
            assert event['entity_id'] == 'light.kitchen_light'
            assert 'brightness_pct' in event.get('attributes', {})
    
    def test_apply_brightness_patterns_sunrise(self):
        """Test brightness-aware pattern: sunrise → lights off."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'light.bedroom_light',
                'device_type': 'light',
                'name': 'Bedroom Light',
                'area': 'Bedroom'
            }
        ]
        
        events = []
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        result = correlator._apply_brightness_patterns(events, devices, start_date)
        
        # Should have added sunrise events
        sunrise_events = [e for e in result if 'brightness_sunrise' in e.get('attributes', {}).get('context', '')]
        assert len(sunrise_events) > 0
        
        # Check sunrise events have correct structure
        for event in sunrise_events:
            assert event['state'] == 'off'
            assert event['entity_id'] == 'light.bedroom_light'
    
    def test_apply_presence_patterns(self):
        """Test presence-aware patterns."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'device_tracker.person',
                'device_type': 'device_tracker',
                'name': 'Person',
                'area': 'Home'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'light.living_room_light',
                'state': 'on',
                'timestamp': '2025-12-02T14:00:00+00:00',
                'attributes': {'device_type': 'light'}
            }
        ]
        
        result = correlator._apply_presence_patterns(events, devices)
        
        # Should have added presence context
        for event in result:
            assert 'presence' in event.get('attributes', {})
            assert event['attributes']['presence'] in ['home', 'away']
    
    def test_apply_seasonal_adjustments_winter(self):
        """Test seasonal adjustments: winter."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'climate.living_room_thermostat',
                'device_type': 'climate',
                'name': 'Living Room Thermostat',
                'area': 'Living Room'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'climate.living_room_thermostat',
                'state': 'heat',
                'timestamp': '2025-12-02T14:00:00+00:00',
                'attributes': {'device_type': 'climate'}
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)  # December = winter
        
        result = correlator._apply_seasonal_adjustments(events, devices, start_date)
        
        # Should have added seasonal context
        for event in result:
            if event.get('attributes', {}).get('device_type') == 'climate':
                assert 'season' in event.get('attributes', {})
                assert event['attributes']['season'] == 'winter'
                assert 'seasonal_adjustment' in event.get('attributes', {})
    
    def test_apply_seasonal_adjustments_summer(self):
        """Test seasonal adjustments: summer."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'climate.living_room_thermostat',
                'device_type': 'climate',
                'name': 'Living Room Thermostat',
                'area': 'Living Room'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'climate.living_room_thermostat',
                'state': 'cool',
                'timestamp': '2025-07-02T14:00:00+00:00',
                'attributes': {'device_type': 'climate'}
            }
        ]
        
        start_date = datetime(2025, 7, 2, 12, 0, 0, tzinfo=timezone.utc)  # July = summer
        
        result = correlator._apply_seasonal_adjustments(events, devices, start_date)
        
        # Should have added seasonal context
        for event in result:
            if event.get('attributes', {}).get('device_type') == 'climate':
                assert 'season' in event.get('attributes', {})
                assert event['attributes']['season'] == 'summer'
                assert event['attributes']['seasonal_adjustment'] == 'cooling_priority'
    
    def test_apply_context_patterns_integration(self):
        """Test full context pattern application integration."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'name': 'Kitchen Light',
                'area': 'Kitchen'
            },
            {
                'entity_id': 'climate.living_room_thermostat',
                'device_type': 'climate',
                'name': 'Living Room Thermostat',
                'area': 'Living Room'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'light.kitchen_light',
                'state': 'off',
                'timestamp': '2025-12-02T14:00:00+00:00',
                'attributes': {'device_type': 'light'}
            }
        ]
        
        weather_data = [
            {
                'timestamp': '2025-12-02T14:00:00+00:00',
                'temperature': 20.0,
                'condition': 'clear',
                'humidity': 60.0
            }
        ]
        
        carbon_data = [
            {
                'timestamp': '2025-12-02T14:00:00+00:00',
                'carbon_intensity': 250.0,
                'renewable_percentage': 50.0
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        result = correlator.apply_context_patterns(
            events, devices, weather_data, carbon_data, start_date
        )
        
        # Should have applied multiple context patterns
        assert len(result) >= len(events)  # Should have added context events
        
        # Check that events have context attributes
        context_events = [e for e in result if 'context' in e.get('attributes', {}) or 'presence' in e.get('attributes', {}) or 'season' in e.get('attributes', {})]
        assert len(context_events) > 0
    
    def test_apply_context_patterns_no_external_data(self):
        """Test context pattern application without external data."""
        correlator = ContextCorrelator()
        
        devices = [
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'name': 'Kitchen Light',
                'area': 'Kitchen'
            }
        ]
        
        events = [
            {
                'event_type': 'state_changed',
                'entity_id': 'light.kitchen_light',
                'state': 'off',
                'timestamp': '2025-12-02T14:00:00+00:00',
                'attributes': {'device_type': 'light'}
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        result = correlator.apply_context_patterns(
            events, devices, None, None, start_date
        )
        
        # Should still apply brightness and presence patterns
        assert len(result) >= len(events)
    
    def test_temperature_thresholds(self):
        """Test temperature threshold constants."""
        correlator = ContextCorrelator()
        
        assert correlator.HEATING_THRESHOLD == 18.0
        assert correlator.COOLING_THRESHOLD == 25.0
        assert correlator.LOW_CARBON_THRESHOLD == 200.0
        assert correlator.HIGH_CARBON_THRESHOLD == 400.0

