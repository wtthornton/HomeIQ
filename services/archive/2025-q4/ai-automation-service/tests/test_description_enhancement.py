"""
Tests for description enhancement utilities
"""

import pytest

from src.services.automation.description_enhancement import (
    enhance_automation_description,
    _describe_actions,
    _describe_triggers,
    _describe_conditions,
    _get_friendly_name
)


class TestDescriptionEnhancement:
    """Tests for description enhancement"""

    def test_enhance_simple_automation(self):
        """Test enhancing a simple automation description"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ],
            "description": ""
        }
        
        entity_names = {"light.kitchen": "Kitchen Light"}
        enhanced = enhance_automation_description(yaml_data, entity_names)
        
        # Should have enhanced description
        assert "description" in enhanced
        assert len(enhanced["description"]) > 20
        assert "Kitchen Light" in enhanced["description"] or "kitchen" in enhanced["description"].lower()
        assert "07:00:00" in enhanced["description"] or "time" in enhanced["description"].lower()
    
    def test_enhance_with_conditions(self):
        """Test enhancing description with conditions"""
        yaml_data = {
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
            ],
            "condition": [
                {"condition": "time", "after": "18:00:00", "before": "23:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.living_room"}
            ],
            "description": ""
        }
        
        entity_names = {
            "binary_sensor.motion": "Motion Sensor",
            "light.living_room": "Living Room Light"
        }
        enhanced = enhance_automation_description(yaml_data, entity_names)
        
        # Should include trigger, action, and condition
        desc = enhanced["description"]
        assert "motion" in desc.lower() or "Motion Sensor" in desc
        assert "living" in desc.lower() or "Living Room" in desc
        assert "18:00:00" in desc or "23:00:00" in desc or "between" in desc.lower()
    
    def test_preserve_comprehensive_description(self):
        """Test that comprehensive descriptions are preserved"""
        comprehensive_desc = "This is a very comprehensive description that includes all the details about when and why this automation runs and what it does in great detail."
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ],
            "description": comprehensive_desc
        }
        
        enhanced = enhance_automation_description(yaml_data, None)
        
        # Should preserve existing comprehensive description
        assert enhanced["description"] == comprehensive_desc
    
    def test_describe_actions_turn_on(self):
        """Test describing turn_on actions"""
        actions = [
            {"service": "light.turn_on", "entity_id": "light.kitchen"}
        ]
        entity_names = {"light.kitchen": "Kitchen Light"}
        
        desc = _describe_actions(actions, entity_names)
        assert "turn on" in desc.lower()
        assert "Kitchen Light" in desc or "kitchen" in desc.lower()
    
    def test_describe_actions_multiple(self):
        """Test describing multiple actions"""
        actions = [
            {"service": "light.turn_on", "entity_id": "light.kitchen"},
            {"service": "switch.turn_on", "entity_id": "switch.fan"},
            {"service": "climate.set_temperature", "entity_id": "climate.thermostat"}
        ]
        entity_names = {
            "light.kitchen": "Kitchen Light",
            "switch.fan": "Fan",
            "climate.thermostat": "Thermostat"
        }
        
        desc = _describe_actions(actions, entity_names)
        assert "turn on" in desc.lower()
        assert "and" in desc  # Multiple actions joined with "and"
    
    def test_describe_triggers_time(self):
        """Test describing time triggers"""
        triggers = [
            {"platform": "time", "at": "07:00:00"}
        ]
        
        desc = _describe_triggers(triggers, None)
        assert "time" in desc.lower()
        assert "07:00:00" in desc
    
    def test_describe_triggers_state(self):
        """Test describing state triggers"""
        triggers = [
            {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
        ]
        entity_names = {"binary_sensor.motion": "Motion Sensor"}
        
        desc = _describe_triggers(triggers, entity_names)
        assert "motion" in desc.lower() or "Motion Sensor" in desc
        assert "on" in desc.lower()
    
    def test_describe_triggers_sun(self):
        """Test describing sun triggers"""
        triggers = [
            {"platform": "sun", "event": "sunset"}
        ]
        
        desc = _describe_triggers(triggers, None)
        assert "sunset" in desc.lower()
    
    def test_describe_conditions_time(self):
        """Test describing time conditions"""
        conditions = [
            {"condition": "time", "after": "18:00:00", "before": "23:00:00"}
        ]
        
        desc = _describe_conditions(conditions, None)
        assert "18:00:00" in desc and "23:00:00" in desc
        assert "between" in desc.lower()
    
    def test_describe_conditions_state(self):
        """Test describing state conditions"""
        conditions = [
            {"condition": "state", "entity_id": "binary_sensor.presence", "state": "on"}
        ]
        entity_names = {"binary_sensor.presence": "Presence Sensor"}
        
        desc = _describe_conditions(conditions, entity_names)
        assert "presence" in desc.lower() or "Presence Sensor" in desc
        assert "on" in desc.lower()
    
    def test_get_friendly_name_with_mapping(self):
        """Test getting friendly name from mapping"""
        entity_names = {"light.kitchen": "Kitchen Light"}
        name = _get_friendly_name("light.kitchen", entity_names)
        assert name == "Kitchen Light"
    
    def test_get_friendly_name_without_mapping(self):
        """Test getting friendly name without mapping"""
        name = _get_friendly_name("light.kitchen_ceiling", None)
        # Should extract from entity ID
        assert "kitchen" in name.lower()
        assert "ceiling" in name.lower()
    
    def test_get_friendly_name_list(self):
        """Test getting friendly name for list of entities"""
        name = _get_friendly_name(["light.kitchen", "light.bedroom"], None)
        assert "2 devices" in name.lower()

