"""Tests for blueprint parser."""

import pytest
from src.indexer.blueprint_parser import BlueprintParser


class TestBlueprintParser:
    """Tests for BlueprintParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BlueprintParser()
    
    def test_parse_yaml_valid(self, sample_blueprint_yaml):
        """Test parsing valid YAML."""
        result = self.parser.parse_yaml(sample_blueprint_yaml)
        
        assert result is not None
        assert "blueprint" in result
        assert result["blueprint"]["name"] == "Motion-Activated Light"
    
    def test_parse_yaml_invalid(self):
        """Test parsing invalid YAML."""
        invalid_yaml = "this: is: invalid: yaml: :"
        result = self.parser.parse_yaml(invalid_yaml)
        
        assert result is None
    
    def test_is_blueprint(self, sample_blueprint_yaml):
        """Test blueprint detection."""
        data = self.parser.parse_yaml(sample_blueprint_yaml)
        
        assert self.parser.is_blueprint(data) is True
        assert self.parser.is_blueprint({"automation": {}}) is False
        assert self.parser.is_blueprint({}) is False
    
    def test_parse_blueprint_extracts_metadata(self, sample_blueprint_yaml):
        """Test that blueprint parsing extracts all metadata."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
            source_type="test",
            stars=50,
            author="test_author",
        )
        
        assert blueprint is not None
        assert blueprint.name == "Motion-Activated Light"
        assert blueprint.description == "Turn on a light when motion is detected"
        assert blueprint.domain == "automation"
        assert blueprint.source_url == "https://example.com/blueprint.yaml"
        assert blueprint.source_type == "test"
        assert blueprint.author == "test_author"
        assert blueprint.stars == 50
    
    def test_parse_blueprint_extracts_domains(self, sample_blueprint_yaml):
        """Test that required domains are extracted correctly."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert "binary_sensor" in blueprint.required_domains
        assert "light" in blueprint.required_domains
    
    def test_parse_blueprint_extracts_device_classes(self, sample_blueprint_yaml):
        """Test that device classes are extracted correctly."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert "motion" in blueprint.required_device_classes
    
    def test_parse_blueprint_extracts_inputs(self, sample_blueprint_yaml):
        """Test that inputs are extracted correctly."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert "motion_sensor" in blueprint.inputs
        assert "target_light" in blueprint.inputs
        assert "no_motion_wait" in blueprint.inputs
        
        # Check input details
        motion_input = blueprint.inputs["motion_sensor"]
        assert motion_input["domain"] == "binary_sensor"
        assert motion_input["device_class"] == "motion"
        assert motion_input["selector_type"] == "entity"
    
    def test_parse_blueprint_extracts_trigger_platforms(self, sample_blueprint_yaml):
        """Test that trigger platforms are extracted."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert "state" in blueprint.trigger_platforms
    
    def test_parse_blueprint_extracts_action_services(self, sample_blueprint_yaml):
        """Test that action services are extracted."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert "light.turn_on" in blueprint.action_services
        assert "light.turn_off" in blueprint.action_services
    
    def test_classify_use_case_comfort(self, sample_blueprint_yaml):
        """Test use case classification for comfort blueprint."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert blueprint.use_case == "comfort"  # Contains "light"
    
    def test_classify_use_case_security(self, sample_security_blueprint_yaml):
        """Test use case classification for security blueprint."""
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_security_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert blueprint.use_case == "security"  # Contains "door", "alert"
    
    def test_calculate_complexity_low(self):
        """Test complexity calculation for simple blueprint."""
        simple_yaml = '''
blueprint:
  name: Simple
  domain: automation
trigger:
  - platform: state
action:
  - service: light.turn_on
'''
        blueprint = self.parser.parse_blueprint(
            yaml_content=simple_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert blueprint.complexity == "low"
    
    def test_calculate_complexity_high(self):
        """Test complexity calculation for complex blueprint."""
        complex_yaml = '''
blueprint:
  name: Complex
  domain: automation
trigger:
  - platform: state
  - platform: time
  - platform: event
  - platform: numeric_state
condition:
  - condition: state
  - condition: time
action:
  - service: light.turn_on
  - service: notify.mobile
  - service: climate.set_temperature
  - delay: 60
'''
        blueprint = self.parser.parse_blueprint(
            yaml_content=complex_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        assert blueprint is not None
        assert blueprint.complexity == "high"
    
    def test_quality_score_calculation(self, sample_blueprint_yaml):
        """Test quality score calculation."""
        # Blueprint with description, inputs, and stars
        blueprint = self.parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/blueprint.yaml",
            stars=100,
        )
        
        assert blueprint is not None
        assert blueprint.quality_score > 0.5  # Should be higher than default
        assert blueprint.quality_score <= 1.0
    
    def test_parse_non_blueprint_yaml(self):
        """Test parsing YAML that is not a blueprint."""
        automation_yaml = '''
automation:
  - alias: "Test Automation"
    trigger:
      - platform: state
    action:
      - service: light.turn_on
'''
        blueprint = self.parser.parse_blueprint(
            yaml_content=automation_yaml,
            source_url="https://example.com/automation.yaml",
        )
        
        assert blueprint is None
    
    def test_parse_malformed_blueprint(self):
        """Test parsing malformed blueprint."""
        malformed_yaml = '''
blueprint:
  name: Incomplete
  # Missing domain
trigger: invalid_structure
'''
        blueprint = self.parser.parse_blueprint(
            yaml_content=malformed_yaml,
            source_url="https://example.com/blueprint.yaml",
        )
        
        # Should still parse but with defaults
        assert blueprint is not None
        assert blueprint.domain == "automation"  # Default
