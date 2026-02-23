"""
Tests for YAML Renderer (Epic 51, Story 51.1)
"""

import pytest
import yaml
from yaml_validation_service.renderer import AutomationRenderer
from yaml_validation_service.schema import (
    ActionSpec,
    AutomationSpec,
    TriggerSpec,
)


class TestAutomationRenderer:
    """Test YAML rendering from AutomationSpec."""
    
    def test_basic_render(self):
        """Test rendering basic automation."""
        renderer = AutomationRenderer()
        
        spec = AutomationSpec(
            alias="Test Automation",
            description="Test description",
            trigger=[
                TriggerSpec(platform="time", at="07:00:00")
            ],
            action=[
                ActionSpec(service="light.turn_on", target={"area_id": "office"})
            ]
        )
        
        yaml_output = renderer.render(spec)
        
        # Parse to verify structure
        data = yaml.safe_load(yaml_output)
        
        assert data["alias"] == "Test Automation"
        assert "trigger:" in yaml_output  # Singular, not plural
        assert "action:" in yaml_output  # Singular, not plural
        assert len(data["trigger"]) == 1
        assert len(data["action"]) == 1
        assert data["trigger"][0]["platform"] == "time"
        assert data["action"][0]["service"] == "light.turn_on"
    
    def test_singular_keys_not_plural(self):
        """Test that rendered YAML uses singular keys."""
        renderer = AutomationRenderer()
        
        spec = AutomationSpec(
            alias="Test",
            trigger=[TriggerSpec(platform="time", at="07:00:00")],
            action=[ActionSpec(service="light.turn_on")]
        )
        
        yaml_output = renderer.render(spec)
        
        assert "trigger:" in yaml_output
        assert "action:" in yaml_output
        assert "triggers:" not in yaml_output
        assert "actions:" not in yaml_output
    
    def test_correct_field_names(self):
        """Test that rendered YAML uses correct field names."""
        renderer = AutomationRenderer()
        
        spec = AutomationSpec(
            alias="Test",
            trigger=[TriggerSpec(platform="state", entity_id="light.living_room")],
            action=[ActionSpec(service="light.turn_on")]
        )
        
        yaml_output = renderer.render(spec)
        data = yaml.safe_load(yaml_output)
        
        assert data["trigger"][0]["platform"] == "state"
        assert data["action"][0]["service"] == "light.turn_on"
        assert "action:" not in str(data["action"][0])  # Should be "service:", not "action:"
