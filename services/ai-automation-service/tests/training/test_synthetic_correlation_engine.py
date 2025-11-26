"""
Unit tests for SyntheticCorrelationEngine.

Tests correlation validation rules, weather-HVAC correlation, and energy correlation.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.training.synthetic_correlation_engine import (
    SyntheticCorrelationEngine
)


class TestSyntheticCorrelationEngine:
    """Test suite for SyntheticCorrelationEngine."""
    
    def test_initialization(self):
        """Test correlation engine initialization."""
        engine = SyntheticCorrelationEngine()
        assert engine is not None
        assert engine.AC_THRESHOLD == 25.0
        assert engine.HEAT_THRESHOLD == 18.0
        assert engine.LOW_CARBON_THRESHOLD == 200.0
        assert engine.HIGH_CARBON_THRESHOLD == 500.0
    
    def test_validate_weather_hvac_correlation_high_temp_ac_on(self):
        """Test weather-HVAC correlation: high temp → AC on."""
        engine = SyntheticCorrelationEngine()
        
        # High temperature weather
        weather_data = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'temperature': 30.0,
                'condition': 'sunny'
            }
        ]
        
        # AC on event
        hvac_events = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'cool',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_weather_hvac_correlation(
            weather_data=weather_data,
            hvac_events=hvac_events
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
        assert len(result['violations']) == 0
    
    def test_validate_weather_hvac_correlation_high_temp_ac_off(self):
        """Test weather-HVAC correlation: high temp but AC off (violation)."""
        engine = SyntheticCorrelationEngine()
        
        # High temperature weather
        weather_data = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'temperature': 30.0,
                'condition': 'sunny'
            }
        ]
        
        # AC off event (violation)
        hvac_events = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'off',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_weather_hvac_correlation(
            weather_data=weather_data,
            hvac_events=hvac_events
        )
        
        assert result['valid'] is False
        assert len(result['violations']) > 0
        assert 'High temp' in result['violations'][0]
    
    def test_validate_weather_hvac_correlation_low_temp_heat_on(self):
        """Test weather-HVAC correlation: low temp → heat on."""
        engine = SyntheticCorrelationEngine()
        
        # Low temperature weather
        weather_data = [
            {
                'timestamp': '2025-01-15T12:00:00+00:00',
                'temperature': 10.0,
                'condition': 'cold'
            }
        ]
        
        # Heat on event
        hvac_events = [
            {
                'timestamp': '2025-01-15T12:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'heat',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_weather_hvac_correlation(
            weather_data=weather_data,
            hvac_events=hvac_events
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
        assert len(result['violations']) == 0
    
    def test_validate_weather_hvac_correlation_moderate_temp(self):
        """Test weather-HVAC correlation: moderate temp (acceptable)."""
        engine = SyntheticCorrelationEngine()
        
        # Moderate temperature weather
        weather_data = [
            {
                'timestamp': '2025-04-15T12:00:00+00:00',
                'temperature': 20.0,  # Between 18 and 25
                'condition': 'mild'
            }
        ]
        
        # HVAC can be off (acceptable)
        hvac_events = [
            {
                'timestamp': '2025-04-15T12:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'off',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_weather_hvac_correlation(
            weather_data=weather_data,
            hvac_events=hvac_events
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
    
    def test_validate_energy_correlation_low_carbon_ev_charging(self):
        """Test energy correlation: low carbon → EV charging preferred."""
        engine = SyntheticCorrelationEngine()
        
        # Low carbon intensity
        carbon_data = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'intensity': 150.0,  # Low carbon
                'renewable_percentage': 0.6
            }
        ]
        
        # Low pricing
        pricing_data = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'price_per_kwh': 0.15,
                'pricing_tier': 'off-peak',
                'region': 'california_tou'
            }
        ]
        
        # EV charging event
        energy_events = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'sensor.ev_charging',
                'state': 'charging',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_energy_correlation(
            carbon_data=carbon_data,
            pricing_data=pricing_data,
            energy_events=energy_events
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
    
    def test_validate_energy_correlation_high_price_delay_devices(self):
        """Test energy correlation: high price → delay high-energy devices."""
        engine = SyntheticCorrelationEngine()
        
        # High carbon intensity
        carbon_data = [
            {
                'timestamp': '2025-06-15T18:00:00+00:00',
                'intensity': 400.0,
                'renewable_percentage': 0.2
            }
        ]
        
        # High pricing (peak tier)
        pricing_data = [
            {
                'timestamp': '2025-06-15T18:00:00+00:00',
                'price_per_kwh': 0.50,  # High price
                'pricing_tier': 'peak',
                'region': 'california_tou'
            }
        ]
        
        # No high-energy devices active (good)
        energy_events = []
        
        result = engine.validate_energy_correlation(
            carbon_data=carbon_data,
            pricing_data=pricing_data,
            energy_events=energy_events
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
    
    def test_validate_energy_correlation_solar_peak(self):
        """Test energy correlation: solar peak (low carbon + low price)."""
        engine = SyntheticCorrelationEngine()
        
        # Low carbon intensity (solar peak)
        carbon_data = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'intensity': 150.0,  # Low carbon
                'renewable_percentage': 0.7
            }
        ]
        
        # Low pricing
        pricing_data = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'price_per_kwh': 0.10,  # Low price
                'pricing_tier': 'off-peak',
                'region': 'california_tou'
            }
        ]
        
        # Renewable device active
        energy_events = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'sensor.solar_generation',
                'state': 'active',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_energy_correlation(
            carbon_data=carbon_data,
            pricing_data=pricing_data,
            energy_events=energy_events
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
    
    def test_validate_all_correlations(self):
        """Test validate_all_correlations method."""
        engine = SyntheticCorrelationEngine()
        
        # External data
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
            'calendar': []
        }
        
        # Devices
        devices = [
            {
                'entity_id': 'climate.thermostat',
                'device_type': 'climate',
                'device_class': 'thermostat'
            }
        ]
        
        # Device events
        device_events = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'cool',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_all_correlations(
            external_data=external_data,
            device_events=device_events,
            devices=devices
        )
        
        assert 'weather_hvac' in result
        assert 'energy' in result
        assert 'overall_valid' in result
        assert 'overall_score' in result
        assert isinstance(result['overall_score'], float)
        assert 0.0 <= result['overall_score'] <= 1.0
    
    def test_validate_calendar_presence_correlation_away_security_on(self):
        """Test calendar-presence correlation: away → security on, lights off."""
        engine = SyntheticCorrelationEngine()
        
        # Away calendar event
        calendar_data = [
            {
                'timestamp': '2025-06-15T10:00:00+00:00',
                'event_type': 'away',
                'summary': 'Vacation',
                'start': '2025-06-15T10:00:00+00:00',
                'end': '2025-06-20T10:00:00+00:00'
            }
        ]
        
        # Devices
        devices = [
            {
                'entity_id': 'alarm_control_panel.home',
                'device_type': 'alarm_control_panel',
                'device_class': 'security'
            },
            {
                'entity_id': 'light.living_room',
                'device_type': 'light',
                'device_class': 'light'
            }
        ]
        
        # Security on, lights off (correct)
        device_events = [
            {
                'timestamp': '2025-06-15T10:00:00+00:00',
                'entity_id': 'alarm_control_panel.home',
                'state': 'armed',
                'event_type': 'state_changed'
            },
            {
                'timestamp': '2025-06-15T10:00:00+00:00',
                'entity_id': 'light.living_room',
                'state': 'off',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_calendar_presence_correlation(
            calendar_data=calendar_data,
            device_events=device_events,
            devices=devices
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
        assert len(result['violations']) == 0
    
    def test_validate_calendar_presence_correlation_away_lights_on_violation(self):
        """Test calendar-presence correlation: away but lights on (violation)."""
        engine = SyntheticCorrelationEngine()
        
        # Away calendar event
        calendar_data = [
            {
                'timestamp': '2025-06-15T10:00:00+00:00',
                'event_type': 'away',
                'summary': 'Vacation',
                'start': '2025-06-15T10:00:00+00:00',
                'end': '2025-06-20T10:00:00+00:00'
            }
        ]
        
        # Devices
        devices = [
            {
                'entity_id': 'light.living_room',
                'device_type': 'light',
                'device_class': 'light'
            }
        ]
        
        # Lights on (violation)
        device_events = [
            {
                'timestamp': '2025-06-15T10:00:00+00:00',
                'entity_id': 'light.living_room',
                'state': 'on',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_calendar_presence_correlation(
            calendar_data=calendar_data,
            device_events=device_events,
            devices=devices
        )
        
        assert result['valid'] is False
        assert len(result['violations']) > 0
        assert 'lights' in result['violations'][0].lower()
    
    def test_validate_calendar_presence_correlation_home_comfort_lights(self):
        """Test calendar-presence correlation: home → comfort settings, lights on."""
        engine = SyntheticCorrelationEngine()
        
        # Home calendar event
        calendar_data = [
            {
                'timestamp': '2025-06-15T18:00:00+00:00',
                'event_type': 'home',
                'summary': 'Home',
                'start': '2025-06-15T18:00:00+00:00',
                'end': '2025-06-15T22:00:00+00:00'
            }
        ]
        
        # Devices
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
        
        # Comfort active, lights on (correct)
        device_events = [
            {
                'timestamp': '2025-06-15T18:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'heat',
                'event_type': 'state_changed'
            },
            {
                'timestamp': '2025-06-15T18:00:00+00:00',
                'entity_id': 'light.living_room',
                'state': 'on',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_calendar_presence_correlation(
            calendar_data=calendar_data,
            device_events=device_events,
            devices=devices
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
    
    def test_validate_calendar_presence_correlation_work_reduced_activity(self):
        """Test calendar-presence correlation: work → reduced device activity."""
        engine = SyntheticCorrelationEngine()
        
        # Work calendar event
        calendar_data = [
            {
                'timestamp': '2025-06-15T09:00:00+00:00',
                'event_type': 'work',
                'summary': 'Work',
                'start': '2025-06-15T09:00:00+00:00',
                'end': '2025-06-15T17:00:00+00:00'
            }
        ]
        
        # Devices
        devices = [
            {
                'entity_id': 'light.living_room',
                'device_type': 'light',
                'device_class': 'light'
            },
            {
                'entity_id': 'switch.coffee_maker',
                'device_type': 'switch',
                'device_class': 'switch'
            }
        ]
        
        # Minimal device activity (correct)
        device_events = [
            {
                'timestamp': '2025-06-15T09:00:00+00:00',
                'entity_id': 'light.living_room',
                'state': 'off',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_calendar_presence_correlation(
            calendar_data=calendar_data,
            device_events=device_events,
            devices=devices
        )
        
        assert result['valid'] is True
        assert result['correlation_score'] >= 0.9
    
    def test_validate_all_correlations_with_calendar(self):
        """Test validate_all_correlations with calendar data."""
        engine = SyntheticCorrelationEngine()
        
        # External data with calendar
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
        
        # Devices
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
        
        # Device events
        device_events = [
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'climate.thermostat',
                'state': 'cool',
                'event_type': 'state_changed'
            },
            {
                'timestamp': '2025-06-15T12:00:00+00:00',
                'entity_id': 'light.living_room',
                'state': 'on',
                'event_type': 'state_changed'
            }
        ]
        
        result = engine.validate_all_correlations(
            external_data=external_data,
            device_events=device_events,
            devices=devices
        )
        
        assert 'weather_hvac' in result
        assert 'energy' in result
        assert 'calendar_presence' in result
        assert 'overall_valid' in result
        assert 'overall_score' in result
        assert isinstance(result['overall_score'], float)
        assert 0.0 <= result['overall_score'] <= 1.0

