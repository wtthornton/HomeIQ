"""
Tests for tag determination utilities
"""

import pytest

from src.services.automation.tag_determination import (
    determine_automation_tags,
    add_tags_to_automation
)


class TestTagDetermination:
    """Tests for tag determination"""

    def test_ai_generated_tag_always_present(self):
        """Test that ai-generated tag is always added"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "ai-generated" in tags
    
    def test_time_based_tag(self):
        """Test time-based tag for time triggers"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "time-based" in tags
    
    def test_presence_tag(self):
        """Test presence tag for motion sensors"""
        yaml_data = {
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.motion_sensor", "to": "on"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "presence" in tags
    
    def test_security_tag_from_lock(self):
        """Test security tag for lock actions"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "22:00:00"}
            ],
            "action": [
                {"service": "lock.lock", "entity_id": "lock.front_door"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "security" in tags
    
    def test_security_tag_from_alarm(self):
        """Test security tag for alarm actions"""
        yaml_data = {
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.door", "to": "on"}
            ],
            "action": [
                {"service": "alarm_control_panel.trigger", "entity_id": "alarm.home"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "security" in tags
    
    def test_energy_tag_from_lights(self):
        """Test energy tag for light actions"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "energy" in tags
        assert "lighting" in tags
    
    def test_climate_tag(self):
        """Test climate tag for climate actions"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "climate.set_temperature", "entity_id": "climate.thermostat"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "climate" in tags
        assert "comfort" in tags
    
    def test_convenience_tag_from_notify(self):
        """Test convenience tag for notifications"""
        yaml_data = {
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.door", "to": "on"}
            ],
            "action": [
                {"service": "notify.mobile_app", "data": {"message": "Door opened"}}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "convenience" in tags
    
    def test_tags_from_description(self):
        """Test tag determination from description"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "22:00:00"}
            ],
            "action": [
                {"service": "light.turn_off", "entity_id": "light.all"}
            ],
            "description": "Energy saving automation to turn off all lights at night"
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "energy" in tags
    
    def test_multiple_tags(self):
        """Test automation with multiple tags"""
        yaml_data = {
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.motion_sensor", "to": "on"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"},
                {"service": "notify.mobile_app", "data": {"message": "Motion detected"}}
            ],
            "description": "Turn on kitchen light and notify when motion detected"
        }
        
        tags = determine_automation_tags(yaml_data)
        assert "ai-generated" in tags
        assert "presence" in tags
        assert "energy" in tags
        assert "lighting" in tags
        assert "convenience" in tags
    
    def test_add_tags_to_automation(self):
        """Test adding tags to automation YAML"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ]
        }
        
        enhanced = add_tags_to_automation(yaml_data)
        
        assert "tags" in enhanced
        assert isinstance(enhanced["tags"], list)
        assert "ai-generated" in enhanced["tags"]
    
    def test_preserve_existing_tags(self):
        """Test that existing tags are preserved"""
        yaml_data = {
            "trigger": [
                {"platform": "time", "at": "07:00:00"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"}
            ],
            "tags": ["custom-tag", "user-defined"]
        }
        
        enhanced = add_tags_to_automation(yaml_data)
        
        # Should preserve existing tags
        assert enhanced["tags"] == ["custom-tag", "user-defined"]
    
    def test_default_convenience_tag(self):
        """Test that convenience is default category if no specific category detected"""
        yaml_data = {
            "trigger": [
                {"platform": "event", "event_type": "custom_event"}
            ],
            "action": [
                {"service": "script.run", "entity_id": "script.custom"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        # Should have ai-generated and at least one category
        assert "ai-generated" in tags
        assert "convenience" in tags or len(tags) > 1
    
    def test_tags_sorted(self):
        """Test that tags are returned sorted"""
        yaml_data = {
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
            ],
            "action": [
                {"service": "light.turn_on", "entity_id": "light.kitchen"},
                {"service": "climate.set_temperature", "entity_id": "climate.thermostat"}
            ]
        }
        
        tags = determine_automation_tags(yaml_data)
        # Should be sorted alphabetically
        assert tags == sorted(tags)

