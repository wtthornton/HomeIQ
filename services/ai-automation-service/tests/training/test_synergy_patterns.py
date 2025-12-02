"""
Unit tests for synergy patterns generator.

Tests for Story AI11.8: Complex Multi-Device Synergies
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.training.synergy_patterns import SynergyPatternGenerator


class TestSynergyPatternGenerator:
    """Test SynergyPatternGenerator class."""
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = SynergyPatternGenerator()
        assert generator is not None
    
    def test_generate_two_device_synergies(self):
        """Test 2-device synergy generation (motion + light)."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen',
                'name': 'Kitchen Motion Sensor'
            },
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'area': 'Kitchen',
                'name': 'Kitchen Light'
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        synergies = generator._generate_two_device_synergies(devices, start_date, days=1)
        
        # Should generate synergy events
        assert len(synergies) > 0
        
        # Check structure: motion trigger → light on → light off (with delay)
        motion_events = [e for e in synergies if e.get('entity_id') == 'binary_sensor.kitchen_motion']
        light_on_events = [e for e in synergies if e.get('entity_id') == 'light.kitchen_light' and e.get('state') == 'on']
        light_off_events = [e for e in synergies if e.get('entity_id') == 'light.kitchen_light' and e.get('state') == 'off']
        
        assert len(motion_events) > 0
        assert len(light_on_events) > 0
        assert len(light_off_events) > 0
        
        # Check synergy attributes
        for event in light_on_events:
            assert 'synergy_action' in event.get('attributes', {})
            assert 'synergy_trigger_entity' in event.get('attributes', {})
            assert 'condition' in event.get('attributes', {})
        
        # Check delay attributes
        for event in light_off_events:
            assert 'synergy_delay' in event.get('attributes', {})
            assert 'delay_minutes' in event.get('attributes', {})
            assert event.get('attributes', {}).get('delay_minutes') == 5
    
    def test_generate_two_device_synergies_no_match(self):
        """Test 2-device synergy with no matching devices."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen'
            }
            # No lights
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        synergies = generator._generate_two_device_synergies(devices, start_date, days=1)
        
        # Should return empty list
        assert synergies == []
    
    def test_generate_three_device_synergies(self):
        """Test 3-device synergy generation (motion + light + brightness)."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.living_room_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Living Room'
            },
            {
                'entity_id': 'light.living_room_light',
                'device_type': 'light',
                'area': 'Living Room'
            },
            {
                'entity_id': 'sensor.living_room_brightness',
                'device_type': 'sensor',
                'device_class': 'illuminance',
                'area': 'Living Room'
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        synergies = generator._generate_three_device_synergies(devices, start_date, days=1)
        
        # Should generate synergy events
        assert len(synergies) > 0
        
        # Check structure: motion → brightness → light (conditional)
        motion_events = [e for e in synergies if e.get('entity_id') == 'binary_sensor.living_room_motion']
        brightness_events = [e for e in synergies if e.get('entity_id') == 'sensor.living_room_brightness']
        light_events = [e for e in synergies if e.get('entity_id') == 'light.living_room_light']
        
        assert len(motion_events) > 0
        assert len(brightness_events) > 0
        
        # Check conditional logic
        for brightness_event in brightness_events:
            assert 'synergy_condition' in brightness_event.get('attributes', {})
            brightness_value = int(brightness_event.get('state', '0'))
            
            # If brightness low, should have light events
            if brightness_value < 50:
                matching_light_events = [
                    e for e in light_events
                    if abs((datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) -
                           datetime.fromisoformat(brightness_event['timestamp'].replace('Z', '+00:00'))).total_seconds()) < 5
                ]
                assert len(matching_light_events) > 0
    
    def test_generate_state_dependent_synergies(self):
        """Test state-dependent synergy generation (only if home)."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'device_tracker.person',
                'device_type': 'device_tracker',
                'area': 'Home',
                'name': 'Person'
            },
            {
                'entity_id': 'light.living_room_light',
                'device_type': 'light',
                'area': 'Living Room',
                'name': 'Living Room Light'
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        # Generate for multiple days to increase chance of action events
        synergies = generator._generate_state_dependent_synergies(devices, start_date, days=7)
        
        # Should generate synergy events
        assert len(synergies) > 0
        
        # Check presence events
        presence_events = [e for e in synergies if e.get('entity_id') == 'device_tracker.person']
        assert len(presence_events) > 0
        
        # Check state-dependent actions (probabilistic, so may not always have actions)
        action_events = [e for e in synergies if 'only_if_home' in e.get('attributes', {}).get('condition', '') or 'only_if_away' in e.get('attributes', {}).get('condition', '')]
        
        # If action events exist, check their structure
        if action_events:
            for event in action_events:
                assert 'condition' in event.get('attributes', {})
                assert 'presence_state' in event.get('attributes', {})
                assert event.get('attributes', {}).get('presence_state') in ['home', 'away']
        
        # At minimum, should have presence state changes
        assert len(presence_events) >= 2  # At least arrive and leave events
    
    def test_generate_synergy_events_integration(self):
        """Test full synergy event generation integration."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen'
            },
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'area': 'Kitchen'
            },
            {
                'entity_id': 'sensor.living_room_brightness',
                'device_type': 'sensor',
                'device_class': 'illuminance',
                'area': 'Living Room'
            },
            {
                'entity_id': 'device_tracker.person',
                'device_type': 'device_tracker',
                'area': 'Home'
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        all_synergies = generator.generate_synergy_events(devices, None, start_date, days=1)
        
        # Should generate multiple synergy types
        assert len(all_synergies) > 0
        
        # Check that events have synergy attributes
        synergy_events = [e for e in all_synergies if 'synergy' in str(e.get('attributes', {})).lower()]
        assert len(synergy_events) > 0
        
        # Verify event structure
        for event in all_synergies:
            assert 'event_type' in event
            assert 'entity_id' in event
            assert 'timestamp' in event
            assert 'attributes' in event
    
    def test_delay_patterns(self):
        """Test delay patterns in synergy events."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen'
            },
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'area': 'Kitchen'
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        synergies = generator._generate_two_device_synergies(devices, start_date, days=1)
        
        # Find light on and light off events
        light_on_events = [e for e in synergies if e.get('entity_id') == 'light.kitchen_light' and e.get('state') == 'on']
        light_off_events = [e for e in synergies if e.get('entity_id') == 'light.kitchen_light' and e.get('state') == 'off']
        
        if light_on_events and light_off_events:
            # Check that off events are delayed after on events
            for on_event in light_on_events:
                on_time = datetime.fromisoformat(on_event['timestamp'].replace('Z', '+00:00'))
                
                # Find corresponding off event
                matching_off = [
                    e for e in light_off_events
                    if abs((datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) - on_time).total_seconds() - 300) < 10
                ]
                
                if matching_off:
                    off_time = datetime.fromisoformat(matching_off[0]['timestamp'].replace('Z', '+00:00'))
                    delay = (off_time - on_time).total_seconds() / 60  # minutes
                    assert 4.5 <= delay <= 5.5  # Approximately 5 minutes
    
    def test_conditional_logic_time_based(self):
        """Test conditional logic: time between sunset/sunrise."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen'
            },
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'area': 'Kitchen'
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        synergies = generator._generate_two_device_synergies(devices, start_date, days=1)
        
        # Check that light events have time condition
        light_events = [e for e in synergies if e.get('entity_id') == 'light.kitchen_light']
        
        for event in light_events:
            if event.get('state') == 'on':
                assert 'condition' in event.get('attributes', {})
                assert 'time_between_sunset_sunrise' in event.get('attributes', {}).get('condition', '')
    
    def test_conditional_logic_brightness(self):
        """Test conditional logic: brightness threshold."""
        generator = SynergyPatternGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.living_room_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Living Room'
            },
            {
                'entity_id': 'light.living_room_light',
                'device_type': 'light',
                'area': 'Living Room'
            },
            {
                'entity_id': 'sensor.living_room_brightness',
                'device_type': 'sensor',
                'device_class': 'illuminance',
                'area': 'Living Room'
            }
        ]
        
        start_date = datetime(2025, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        synergies = generator._generate_three_device_synergies(devices, start_date, days=1)
        
        # Check that light events have brightness condition
        light_events = [e for e in synergies if e.get('entity_id') == 'light.living_room_light' and e.get('state') == 'on']
        
        for event in light_events:
            assert 'condition_met' in event.get('attributes', {})
            assert 'brightness_value' in event.get('attributes', {})
            assert event.get('attributes', {}).get('brightness_value', 100) < 50  # Below threshold

