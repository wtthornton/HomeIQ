"""
Unit tests for event type diversification in SyntheticEventGenerator.

Tests for Story AI11.5: Event Type Diversification
- Event type distribution
- All 7 event types (state_changed, automation_triggered, script_started, scene_activated, voice_command, webhook_triggered, api_call)
"""

import pytest
import random
from datetime import datetime, timezone
from collections import Counter
from src.training.synthetic_event_generator import SyntheticEventGenerator


class TestEventTypeDistribution:
    """Test event type distribution."""
    
    def test_event_type_distribution_defined(self):
        """Test that event type distribution is defined."""
        generator = SyntheticEventGenerator()
        
        assert hasattr(generator, 'EVENT_TYPE_DISTRIBUTION')
        assert isinstance(generator.EVENT_TYPE_DISTRIBUTION, dict)
        assert len(generator.EVENT_TYPE_DISTRIBUTION) == 7
    
    def test_event_type_distribution_sum(self):
        """Test that event type distribution probabilities sum to 1.0."""
        generator = SyntheticEventGenerator()
        
        total = sum(generator.EVENT_TYPE_DISTRIBUTION.values())
        assert abs(total - 1.0) < 0.01, f"Distribution sum is {total}, expected 1.0"
    
    def test_event_type_distribution_values(self):
        """Test that all distribution values are between 0 and 1."""
        generator = SyntheticEventGenerator()
        
        for event_type, probability in generator.EVENT_TYPE_DISTRIBUTION.items():
            assert 0.0 <= probability <= 1.0, \
                f"Event type '{event_type}' has invalid probability: {probability}"
    
    def test_event_type_distribution_targets(self):
        """Test that distribution matches target percentages."""
        generator = SyntheticEventGenerator()
        
        expected = {
            'state_changed': 0.60,
            'automation_triggered': 0.15,
            'script_started': 0.08,
            'scene_activated': 0.05,
            'voice_command': 0.05,
            'webhook_triggered': 0.04,
            'api_call': 0.03
        }
        
        for event_type, expected_prob in expected.items():
            actual_prob = generator.EVENT_TYPE_DISTRIBUTION.get(event_type)
            assert actual_prob == expected_prob, \
                f"Event type '{event_type}' has probability {actual_prob}, expected {expected_prob}"


class TestEventTypeSelection:
    """Test event type selection logic."""
    
    def test_select_event_type(self):
        """Test that event type selection works."""
        generator = SyntheticEventGenerator()
        
        # Test multiple selections
        event_types = [generator._select_event_type() for _ in range(100)]
        
        # Should return valid event types
        for event_type in event_types:
            assert event_type in generator.EVENT_TYPE_DISTRIBUTION
    
    def test_select_event_type_distribution(self):
        """Test that event type selection follows distribution (statistical test)."""
        generator = SyntheticEventGenerator()
        
        # Generate many events to test distribution
        random.seed(42)
        event_types = [generator._select_event_type() for _ in range(10000)]
        counts = Counter(event_types)
        
        # Check that distribution is approximately correct (within 5% tolerance)
        for event_type, expected_prob in generator.EVENT_TYPE_DISTRIBUTION.items():
            actual_prob = counts[event_type] / len(event_types)
            tolerance = 0.05  # 5% tolerance
            
            assert abs(actual_prob - expected_prob) <= tolerance, \
                f"Event type '{event_type}' has probability {actual_prob:.3f}, " \
                f"expected {expected_prob:.3f} (tolerance: {tolerance})"


class TestStateChangedEvent:
    """Test state_changed event generation."""
    
    def test_generate_state_changed_event(self):
        """Test state_changed event generation."""
        generator = SyntheticEventGenerator()
        
        device = {
            'device_type': 'light',
            'device_class': None,
            'friendly_name': 'Kitchen Light',
            'name': 'Kitchen Light'
        }
        
        event_time = datetime.now(timezone.utc)
        event = generator._generate_state_changed_event(
            entity_id='light.kitchen_light',
            device_type='light',
            area='Kitchen',
            device=device,
            event_time=event_time
        )
        
        assert event['event_type'] == 'state_changed'
        assert event['entity_id'] == 'light.kitchen_light'
        assert 'state' in event
        assert event['state'] in ['on', 'off']
        assert event['timestamp'] == event_time.isoformat()
        assert 'attributes' in event
        assert event['attributes']['device_type'] == 'light'
        assert event['attributes']['area'] == 'Kitchen'


class TestAutomationTriggerEvent:
    """Test automation_triggered event generation."""
    
    def test_generate_automation_trigger_event(self):
        """Test automation_triggered event generation."""
        generator = SyntheticEventGenerator()
        
        device = {
            'device_type': 'binary_sensor',
            'device_class': 'motion',
            'friendly_name': 'Motion Sensor'
        }
        
        event_time = datetime.now(timezone.utc)
        event = generator._generate_automation_trigger_event(
            entity_id='binary_sensor.kitchen_motion',
            device_type='binary_sensor',
            area='Kitchen',
            device=device,
            event_time=event_time
        )
        
        assert event['event_type'] == 'automation_triggered'
        assert event['entity_id'].startswith('automation.')
        assert event['timestamp'] == event_time.isoformat()
        assert 'attributes' in event
        assert event['attributes']['trigger_entity_id'] == 'binary_sensor.kitchen_motion'
        assert event['attributes']['trigger_device_type'] == 'binary_sensor'
        assert event['attributes']['area'] == 'Kitchen'
        assert 'trigger_state' in event['attributes']
        assert 'automation_name' in event['attributes']


class TestScriptCallEvent:
    """Test script_started event generation."""
    
    def test_generate_script_call_event(self):
        """Test script_started event generation."""
        generator = SyntheticEventGenerator()
        
        device = {
            'device_type': 'light',
            'friendly_name': 'Living Room Light'
        }
        
        event_time = datetime.now(timezone.utc)
        event = generator._generate_script_call_event(
            entity_id='light.living_room_light',
            device_type='light',
            area='Living Room',
            device=device,
            event_time=event_time
        )
        
        assert event['event_type'] == 'script_started'
        assert event['entity_id'].startswith('script.')
        assert event['timestamp'] == event_time.isoformat()
        assert 'attributes' in event
        assert 'script_name' in event['attributes']
        assert event['attributes']['trigger_entity_id'] == 'light.living_room_light'
        assert event['attributes']['area'] == 'Living Room'
        assert event['attributes']['device_type'] == 'light'


class TestSceneActivationEvent:
    """Test scene_activated event generation."""
    
    def test_generate_scene_activation_event(self):
        """Test scene_activated event generation."""
        generator = SyntheticEventGenerator()
        
        device = {
            'device_type': 'light',
            'friendly_name': 'Bedroom Light'
        }
        
        event_time = datetime.now(timezone.utc)
        event = generator._generate_scene_activation_event(
            entity_id='light.bedroom_light',
            device_type='light',
            area='Bedroom',
            device=device,
            event_time=event_time
        )
        
        assert event['event_type'] == 'scene_activated'
        assert event['entity_id'].startswith('scene.')
        assert event['timestamp'] == event_time.isoformat()
        assert 'attributes' in event
        assert 'scene_name' in event['attributes']
        assert 'scene_type' in event['attributes']
        assert event['attributes']['scene_type'] in generator.SCENE_TYPES
        assert event['attributes']['area'] == 'Bedroom'


class TestVoiceCommandEvent:
    """Test voice_command event generation."""
    
    def test_generate_voice_command_event(self):
        """Test voice_command event generation."""
        generator = SyntheticEventGenerator()
        
        device = {
            'device_type': 'light',
            'friendly_name': 'Kitchen Light'
        }
        
        event_time = datetime.now(timezone.utc)
        event = generator._generate_voice_command_event(
            entity_id='light.kitchen_light',
            device_type='light',
            area='Kitchen',
            device=device,
            event_time=event_time
        )
        
        assert event['event_type'] == 'voice_command'
        assert event['entity_id'] == 'light.kitchen_light'
        assert event['timestamp'] == event_time.isoformat()
        assert 'attributes' in event
        assert 'platform' in event['attributes']
        assert event['attributes']['platform'] in generator.VOICE_PLATFORMS
        assert 'command' in event['attributes']
        assert 'area' in event['attributes']
        assert 'user' in event['attributes']
        assert event['attributes']['user'].startswith('user_')


class TestWebhookTriggerEvent:
    """Test webhook_triggered event generation."""
    
    def test_generate_webhook_trigger_event(self):
        """Test webhook_triggered event generation."""
        generator = SyntheticEventGenerator()
        
        device = {
            'device_type': 'sensor',
            'friendly_name': 'Temperature Sensor'
        }
        
        event_time = datetime.now(timezone.utc)
        event = generator._generate_webhook_trigger_event(
            entity_id='sensor.temperature',
            device_type='sensor',
            area='Living Room',
            device=device,
            event_time=event_time
        )
        
        assert event['event_type'] == 'webhook_triggered'
        assert event['entity_id'].startswith('webhook.')
        assert event['timestamp'] == event_time.isoformat()
        assert 'attributes' in event
        assert 'webhook_source' in event['attributes']
        assert event['attributes']['webhook_source'] in generator.WEBHOOK_SOURCES
        assert 'webhook_id' in event['attributes']
        assert 'trigger_entity_id' in event['attributes']
        assert 'payload' in event['attributes']


class TestApiCallEvent:
    """Test api_call event generation."""
    
    def test_generate_api_call_event(self):
        """Test api_call event generation."""
        generator = SyntheticEventGenerator()
        
        device = {
            'device_type': 'sensor',
            'friendly_name': 'Weather Sensor'
        }
        
        event_time = datetime.now(timezone.utc)
        event = generator._generate_api_call_event(
            entity_id='sensor.weather',
            device_type='sensor',
            area='Outdoor',
            device=device,
            event_time=event_time
        )
        
        assert event['event_type'] == 'api_call'
        assert event['entity_id'].startswith('api.')
        assert event['timestamp'] == event_time.isoformat()
        assert 'attributes' in event
        assert 'service' in event['attributes']
        assert event['attributes']['service'] in generator.API_SERVICES
        assert 'endpoint' in event['attributes']
        assert 'method' in event['attributes']
        assert event['attributes']['method'] in ['GET', 'POST', 'PUT']
        assert 'status_code' in event['attributes']


class TestEventGenerationIntegration:
    """Test event generation integration."""
    
    def test_generate_events_with_diverse_types(self):
        """Test that generate_events produces diverse event types."""
        generator = SyntheticEventGenerator()
        
        devices = [
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'name': 'Kitchen Light',
                'friendly_name': 'Kitchen Light',
                'area': 'Kitchen',
                'category': 'lighting',
                'attributes': {}
            },
            {
                'entity_id': 'binary_sensor.living_room_motion',
                'device_type': 'binary_sensor',
                'name': 'Living Room Motion',
                'friendly_name': 'Living Room Motion',
                'area': 'Living Room',
                'category': 'security',
                'device_class': 'motion',
                'attributes': {}
            }
        ]
        
        # Generate events
        import asyncio
        events = asyncio.run(generator.generate_events(devices, days=1))
        
        # Check that we have events
        assert len(events) > 0
        
        # Check event types
        event_types = [e['event_type'] for e in events]
        unique_types = set(event_types)
        
        # Should have multiple event types (not just state_changed)
        assert len(unique_types) > 1, "Should have multiple event types"
        
        # Check that all event types are valid
        valid_types = set(generator.EVENT_TYPE_DISTRIBUTION.keys())
        assert unique_types.issubset(valid_types), \
            f"Invalid event types found: {unique_types - valid_types}"
    
    def test_event_type_distribution_in_generated_events(self):
        """Test that generated events follow distribution (statistical test)."""
        generator = SyntheticEventGenerator()
        
        devices = [
            {
                'entity_id': f'light.test_light_{i}',
                'device_type': 'light',
                'name': f'Test Light {i}',
                'friendly_name': f'Test Light {i}',
                'area': 'Test',
                'category': 'lighting',
                'attributes': {}
            }
            for i in range(10)
        ]
        
        # Generate many events
        import asyncio
        random.seed(42)
        events = asyncio.run(generator.generate_events(devices, days=7))
        
        # Count event types
        event_types = [e['event_type'] for e in events]
        counts = Counter(event_types)
        
        # Check distribution (within 10% tolerance for smaller sample)
        total = len(events)
        tolerance = 0.10  # 10% tolerance for smaller samples
        
        for event_type, expected_prob in generator.EVENT_TYPE_DISTRIBUTION.items():
            if event_type in counts:
                actual_prob = counts[event_type] / total
                assert abs(actual_prob - expected_prob) <= tolerance, \
                    f"Event type '{event_type}' has probability {actual_prob:.3f}, " \
                    f"expected {expected_prob:.3f} (tolerance: {tolerance})"
    
    def test_all_event_types_present(self):
        """Test that all event types can be generated."""
        generator = SyntheticEventGenerator()
        
        device = {
            'entity_id': 'light.test_light',
            'device_type': 'light',
            'name': 'Test Light',
            'friendly_name': 'Test Light',
            'area': 'Test',
            'category': 'lighting',
            'attributes': {}
        }
        
        # Generate many events to ensure all types appear
        import asyncio
        random.seed(42)
        events = asyncio.run(generator.generate_events([device], days=30))
        
        event_types = set(e['event_type'] for e in events)
        
        # Should have most event types (some may be rare)
        # At minimum, should have state_changed and a few others
        assert 'state_changed' in event_types
        assert len(event_types) >= 3, \
            f"Expected at least 3 event types, got {len(event_types)}: {event_types}"

