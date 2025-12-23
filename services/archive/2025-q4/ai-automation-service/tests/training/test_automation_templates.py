"""
Unit tests for blueprint automation templates.

Tests for Story AI11.6: Blueprint Automation Templates
"""

import pytest
from src.training.automation_templates import BLUEPRINT_TEMPLATES, BlueprintTemplate
from src.training.synthetic_automation_generator import SyntheticAutomationGenerator


class TestBlueprintTemplates:
    """Test blueprint template definitions."""
    
    def test_templates_defined(self):
        """Test that all 5 templates are defined."""
        assert len(BLUEPRINT_TEMPLATES) == 5
        
        expected_templates = [
            'motion_activated_light',
            'climate_comfort',
            'security_alert',
            'energy_optimization',
            'voice_routine'
        ]
        
        for template_id in expected_templates:
            assert template_id in BLUEPRINT_TEMPLATES
    
    def test_template_structure(self):
        """Test that each template has required fields."""
        for template_id, template in BLUEPRINT_TEMPLATES.items():
            assert isinstance(template, BlueprintTemplate)
            assert template.template_id == template_id
            assert template.name
            assert template.description
            assert template.trigger_type
            assert template.action_type
            assert isinstance(template.required_device_types, list)
            assert len(template.required_device_types) > 0
            assert isinstance(template.optional_device_types, list)
            assert isinstance(template.metadata, dict)
    
    def test_motion_activated_light_template(self):
        """Test motion-activated light template."""
        template = BLUEPRINT_TEMPLATES['motion_activated_light']
        
        assert template.name == 'Motion-Activated Light'
        assert 'motion' in template.description.lower()
        assert 'binary_sensor.motion' in template.required_device_types
        assert 'light' in template.required_device_types
        assert template.metadata['common_pattern'] is True
        assert 'typical_delay_minutes' in template.metadata
    
    def test_climate_comfort_template(self):
        """Test climate comfort template."""
        template = BLUEPRINT_TEMPLATES['climate_comfort']
        
        assert template.name == 'Climate Comfort Automation'
        assert 'climate' in template.description.lower() or 'temperature' in template.description.lower()
        assert 'sensor.temperature' in template.required_device_types
        assert 'climate' in template.required_device_types
        assert 'typical_temperature_range' in template.metadata
    
    def test_security_alert_template(self):
        """Test security alert template."""
        template = BLUEPRINT_TEMPLATES['security_alert']
        
        assert template.name == 'Security Alert Automation'
        assert 'security' in template.description.lower() or 'alert' in template.description.lower()
        assert 'binary_sensor.door' in template.required_device_types or 'binary_sensor.window' in template.required_device_types
        assert 'alarm_control_panel' in template.required_device_types
        assert 'alert_types' in template.metadata
    
    def test_energy_optimization_template(self):
        """Test energy optimization template."""
        template = BLUEPRINT_TEMPLATES['energy_optimization']
        
        assert template.name == 'Energy Optimization Automation'
        assert 'energy' in template.description.lower()
        assert 'sensor.energy' in template.required_device_types
        assert 'switch' in template.required_device_types
        assert 'optimization_factors' in template.metadata
    
    def test_voice_routine_template(self):
        """Test voice routine template."""
        template = BLUEPRINT_TEMPLATES['voice_routine']
        
        assert template.name == 'Voice Routine Automation'
        assert 'voice' in template.description.lower()
        assert 'light' in template.required_device_types or 'switch' in template.required_device_types
        assert 'voice_platforms' in template.metadata


class TestSyntheticAutomationGenerator:
    """Test SyntheticAutomationGenerator."""
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = SyntheticAutomationGenerator()
        assert generator is not None
    
    def test_group_devices_by_type(self):
        """Test device grouping by type."""
        generator = SyntheticAutomationGenerator()
        
        devices = [
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'area': 'Kitchen'
            },
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen'
            },
            {
                'entity_id': 'sensor.living_room_temperature',
                'device_type': 'sensor',
                'device_class': 'temperature',
                'area': 'Living Room'
            }
        ]
        
        grouped = generator._group_devices_by_type(devices)
        
        assert 'light' in grouped
        assert 'binary_sensor.motion' in grouped
        assert 'sensor.temperature' in grouped
        assert len(grouped['light']) == 1
        assert len(grouped['binary_sensor.motion']) == 1
    
    def test_can_generate_template(self):
        """Test template generation feasibility check."""
        generator = SyntheticAutomationGenerator()
        template = BLUEPRINT_TEMPLATES['motion_activated_light']
        
        # Test with required devices
        devices_by_type = {
            'binary_sensor.motion': [{'entity_id': 'binary_sensor.motion_1'}],
            'light': [{'entity_id': 'light.light_1'}]
        }
        assert generator._can_generate_template(template, devices_by_type) is True
        
        # Test without required devices
        devices_by_type_missing = {
            'binary_sensor.motion': [{'entity_id': 'binary_sensor.motion_1'}]
        }
        assert generator._can_generate_template(template, devices_by_type_missing) is False
    
    def test_generate_motion_light_automation(self):
        """Test motion-activated light automation generation."""
        generator = SyntheticAutomationGenerator()
        template = BLUEPRINT_TEMPLATES['motion_activated_light']
        
        required_devices = {
            'binary_sensor.motion': {
                'entity_id': 'binary_sensor.kitchen_motion',
                'area': 'Kitchen',
                'friendly_name': 'Kitchen Motion'
            },
            'light': {
                'entity_id': 'light.kitchen_light',
                'area': 'Kitchen',
                'friendly_name': 'Kitchen Light'
            }
        }
        
        automation = generator._generate_motion_light_automation(
            template, required_devices, None
        )
        
        assert automation is not None
        assert automation['template_id'] == 'motion_activated_light'
        assert automation['automation_id'].startswith('automation.')
        assert 'Motion Light' in automation['name']
        assert automation['trigger']['entity_id'] == 'binary_sensor.kitchen_motion'
        assert automation['action']['entity_id'] == 'light.kitchen_light'
        assert 'delay' in automation
        assert len(automation['devices_involved']) == 2
    
    def test_generate_climate_automation(self):
        """Test climate comfort automation generation."""
        generator = SyntheticAutomationGenerator()
        template = BLUEPRINT_TEMPLATES['climate_comfort']
        
        required_devices = {
            'sensor.temperature': {
                'entity_id': 'sensor.living_room_temperature',
                'area': 'Living Room',
                'friendly_name': 'Living Room Temperature'
            },
            'climate': {
                'entity_id': 'climate.living_room_thermostat',
                'area': 'Living Room',
                'friendly_name': 'Living Room Thermostat'
            }
        }
        
        automation = generator._generate_climate_automation(
            template, required_devices, None
        )
        
        assert automation is not None
        assert automation['template_id'] == 'climate_comfort'
        assert 'Climate Control' in automation['name']
        assert automation['trigger']['entity_id'] == 'sensor.living_room_temperature'
        assert automation['action']['entity_id'] == 'climate.living_room_thermostat'
        assert 'condition' in automation
        assert len(automation['devices_involved']) == 2
    
    def test_generate_security_automation(self):
        """Test security alert automation generation."""
        generator = SyntheticAutomationGenerator()
        template = BLUEPRINT_TEMPLATES['security_alert']
        
        required_devices = {
            'binary_sensor.door': {
                'entity_id': 'binary_sensor.front_door',
                'area': 'Front Door',
                'friendly_name': 'Front Door'
            },
            'alarm_control_panel': {
                'entity_id': 'alarm_control_panel.security',
                'area': 'Home',
                'friendly_name': 'Security Alarm'
            }
        }
        
        automation = generator._generate_security_automation(
            template, required_devices, None
        )
        
        assert automation is not None
        assert automation['template_id'] == 'security_alert'
        assert 'Security Alert' in automation['name']
        assert automation['trigger']['entity_id'] == 'binary_sensor.front_door'
        assert 'condition' in automation
        assert automation['action']['service'] == 'notify.mobile_app'
        assert len(automation['devices_involved']) == 2
    
    def test_generate_energy_automation(self):
        """Test energy optimization automation generation."""
        generator = SyntheticAutomationGenerator()
        template = BLUEPRINT_TEMPLATES['energy_optimization']
        
        required_devices = {
            'sensor.energy': {
                'entity_id': 'sensor.living_room_energy',
                'area': 'Living Room',
                'friendly_name': 'Living Room Energy'
            },
            'switch': {
                'entity_id': 'switch.living_room_outlet',
                'area': 'Living Room',
                'friendly_name': 'Living Room Outlet'
            }
        }
        
        automation = generator._generate_energy_automation(
            template, required_devices, None
        )
        
        assert automation is not None
        assert automation['template_id'] == 'energy_optimization'
        assert 'Energy Optimization' in automation['name']
        assert automation['trigger']['platform'] == 'time'
        assert automation['action']['entity_id'] == 'switch.living_room_outlet'
        assert len(automation['devices_involved']) == 2
    
    def test_generate_voice_routine_automation(self):
        """Test voice routine automation generation."""
        generator = SyntheticAutomationGenerator()
        template = BLUEPRINT_TEMPLATES['voice_routine']
        
        required_devices = {
            'light': {
                'entity_id': 'light.bedroom_light',
                'area': 'Bedroom',
                'friendly_name': 'Bedroom Light'
            }
        }
        
        automation = generator._generate_voice_routine_automation(
            template, required_devices, None
        )
        
        assert automation is not None
        assert automation['template_id'] == 'voice_routine'
        assert 'Voice Routine' in automation['name']
        assert automation['trigger']['platform'] == 'event'
        assert automation['trigger']['event_type'] == 'voice_command'
        assert 'voice_platform' in automation
        assert automation['action']['entity_id'] == 'light.bedroom_light'
    
    def test_generate_automations_integration(self):
        """Test full automation generation integration."""
        generator = SyntheticAutomationGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen',
                'friendly_name': 'Kitchen Motion Sensor'
            },
            {
                'entity_id': 'light.kitchen_light',
                'device_type': 'light',
                'area': 'Kitchen',
                'friendly_name': 'Kitchen Light'
            },
            {
                'entity_id': 'sensor.living_room_temperature',
                'device_type': 'sensor',
                'device_class': 'temperature',
                'area': 'Living Room',
                'friendly_name': 'Living Room Temperature'
            },
            {
                'entity_id': 'climate.living_room_thermostat',
                'device_type': 'climate',
                'area': 'Living Room',
                'friendly_name': 'Living Room Thermostat'
            }
        ]
        
        automations = generator.generate_automations(devices)
        
        # Should generate at least motion_light and climate automations
        assert len(automations) > 0
        
        # Check automation structure
        for automation in automations:
            assert 'automation_id' in automation
            assert 'template_id' in automation
            assert 'name' in automation
            assert 'trigger' in automation
            assert 'action' in automation
            assert 'devices_involved' in automation
            assert automation['template_id'] in BLUEPRINT_TEMPLATES
        
        # Verify motion light automation was generated
        motion_automations = [a for a in automations if a['template_id'] == 'motion_activated_light']
        assert len(motion_automations) > 0
        
        # Verify climate automation was generated
        climate_automations = [a for a in automations if a['template_id'] == 'climate_comfort']
        assert len(climate_automations) > 0
    
    def test_generate_automations_no_devices(self):
        """Test automation generation with no devices."""
        generator = SyntheticAutomationGenerator()
        
        automations = generator.generate_automations([])
        
        assert automations == []
    
    def test_generate_automations_partial_devices(self):
        """Test automation generation with partial device requirements."""
        generator = SyntheticAutomationGenerator()
        
        # Only motion sensor, no light
        devices = [
            {
                'entity_id': 'binary_sensor.kitchen_motion',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Kitchen'
            }
        ]
        
        automations = generator.generate_automations(devices)
        
        # Should not generate motion_light (missing light)
        motion_automations = [a for a in automations if a['template_id'] == 'motion_activated_light']
        assert len(motion_automations) == 0

