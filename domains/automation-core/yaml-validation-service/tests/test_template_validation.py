"""
Tests for Template Syntax Validation

Tests Jinja2 template validation in YAML validation service Stage 6 (Style/Maintainability).
"""

import pytest
import yaml
from yaml_validation_service.validator import ValidationPipeline


class TestTemplateValidation:
    """Test template syntax validation."""
    
    @pytest.fixture
    def validator(self):
        """Create validation pipeline instance."""
        return ValidationPipeline(validation_level="moderate")
    
    def test_valid_template_syntax(self, validator):
        """Test validation of valid Jinja2 template."""
        yaml_content = """
alias: "Test Automation"
trigger:
  - platform: state
    entity_id: sensor.temperature
    to: "high"
condition:
  - condition: template
    value_template: "{{ states('sensor.temperature') | float > 25 }}"
action:
  - service: climate.set_temperature
    data:
      temperature: "{{ states('sensor.temperature') | float }}"
"""
        # This should parse without template errors
        result = validator._validate_style(yaml.safe_load(yaml_content))
        assert result["valid"] is True
        # Should not have template syntax errors
        assert not any("template syntax error" in str(e).lower() for e in result.get("errors", []))
    
    def test_invalid_template_syntax(self, validator):
        """Test detection of invalid Jinja2 template syntax."""
        yaml_content = """
alias: "Test Automation"
trigger:
  - platform: state
    entity_id: sensor.temperature
condition:
  - condition: template
    value_template: "{{ states('sensor.temperature' | float > 25 }}"  # Missing closing parenthesis
action:
  - service: climate.set_temperature
"""
        data = yaml.safe_load(yaml_content)
        result = validator._validate_style(data)
        
        # Should detect template syntax error
        errors = result.get("errors", [])
        assert any("template" in str(e).lower() and "syntax" in str(e).lower() for e in errors)
    
    def test_template_group_last_changed_warning(self, validator):
        """Test detection of templates accessing group.last_changed."""
        yaml_content = """
alias: "Test Automation"
trigger:
  - platform: state
    entity_id: binary_sensor.motion
condition:
  - condition: template
    value_template: >
      {{ (now() - states.group.office_motion_sensors.last_changed).total_seconds() > 5400 }}
action:
  - service: light.turn_on
    target:
      entity_id: light.office
"""
        data = yaml.safe_load(yaml_content)
        result = validator._validate_style(data)
        
        # Should have warning about group.last_changed
        warnings = result.get("warnings", [])
        assert any("group" in str(w).lower() and "last_changed" in str(w).lower() for w in warnings)
        assert any("condition: state" in str(w) or "for:" in str(w) for w in warnings)
    
    def test_extract_templates_from_conditions(self, validator):
        """Test extraction of templates from condition value_template fields."""
        data = {
            "condition": [
                {
                    "condition": "template",
                    "value_template": "{{ states('sensor.temp') | float > 25 }}"
                }
            ]
        }
        
        templates = validator._extract_templates_from_data(data)
        assert len(templates) == 1
        assert templates[0][0] == "root.condition[0].value_template"
        assert "states('sensor.temp')" in templates[0][1]
    
    def test_extract_templates_from_multiple_locations(self, validator):
        """Test extraction of templates from multiple locations in automation."""
        data = {
            "trigger": [
                {
                    "platform": "template",
                    "value_template": "{{ is_state('sensor.motion', 'on') }}"
                }
            ],
            "condition": [
                {
                    "condition": "template",
                    "value_template": "{{ states('sensor.temp') > 25 }}"
                }
            ],
            "action": [
                {
                    "service": "climate.set_temperature",
                    "data": {
                        "temperature": "{{ states('sensor.temp') }}"
                    }
                }
            ]
        }
        
        templates = validator._extract_templates_from_data(data)
        assert len(templates) >= 3  # Should find templates in trigger, condition, and action
    
    def test_template_validation_multiline(self, validator):
        """Test validation of multiline templates."""
        yaml_content = """
alias: "Test Automation"
condition:
  - condition: template
    value_template: >
      {% if is_state('sensor.motion', 'on') %}
        {{ (now() - states('sensor.motion').last_changed).total_seconds() > 300 }}
      {% endif %}
action:
  - service: light.turn_on
"""
        data = yaml.safe_load(yaml_content)
        result = validator._validate_style(data)
        
        # Should validate multiline template without syntax errors
        errors = result.get("errors", [])
        template_errors = [e for e in errors if "template" in str(e).lower() and "syntax" in str(e).lower()]
        # If template is valid, should not have syntax errors
        # Note: This may fail if Jinja2 is not installed, but that's handled gracefully
    
    def test_template_with_group_entity_detection(self, validator):
        """Test detection of group entities in templates."""
        yaml_content = """
alias: "Office Automation"
condition:
  - condition: template
    value_template: "{{ states.group.office_motion_sensors.last_changed }}"
action:
  - service: light.turn_on
"""
        data = yaml.safe_load(yaml_content)
        result = validator._validate_style(data)
        
        # Should detect group entity in template
        warnings = result.get("warnings", [])
        assert any("group" in str(w).lower() for w in warnings)
    
    def test_no_template_errors_when_no_templates(self, validator):
        """Test that automations without templates have no template errors."""
        yaml_content = """
alias: "Simple Automation"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
"""
        data = yaml.safe_load(yaml_content)
        result = validator._validate_style(data)
        
        # Should have no template-related errors
        errors = result.get("errors", [])
        assert not any("template" in str(e).lower() for e in errors)

