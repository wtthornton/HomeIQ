"""
Tests for YAML Normalizer (Epic 51, Story 51.3)
"""

import pytest
from yaml_validation_service.normalizer import YAMLNormalizer


class TestYAMLNormalizer:
    """Test YAML normalization and auto-correction."""
    
    def test_plural_to_singular_keys(self):
        """Test converting plural keys to singular."""
        normalizer = YAMLNormalizer()
        
        yaml_content = """
triggers:
  - platform: time
    at: "07:00:00"
actions:
  - service: light.turn_on
"""
        
        normalized = normalizer.normalize(yaml_content)
        
        assert "trigger:" in normalized
        assert "action:" in normalized
        assert "triggers:" not in normalized
        assert "actions:" not in normalized
    
    def test_field_name_corrections(self):
        """Test correcting field names in actions."""
        normalizer = YAMLNormalizer()
        
        yaml_content = """
trigger:
  - platform: state
    entity_id: light.living_room
action:
  - action: light.turn_on  # Wrong field name
    target:
      entity_id: light.living_room
"""
        
        normalized = normalizer.normalize(yaml_content)
        
        assert "service: light.turn_on" in normalized
        assert "action: light.turn_on" not in normalized
    
    def test_error_handling_format(self):
        """Test converting continue_on_error to error format."""
        normalizer = YAMLNormalizer()
        
        yaml_content = """
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    continue_on_error: true
"""
        
        normalized = normalizer.normalize(yaml_content)
        
        assert "error: continue" in normalized or "error:" in normalized
        assert "continue_on_error: true" not in normalized
    
    def test_idempotent_normalization(self):
        """Test that normalization is idempotent."""
        normalizer = YAMLNormalizer()
        
        yaml_content = """
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
"""
        
        normalized_once = normalizer.normalize(yaml_content)
        normalized_twice = normalizer.normalize(normalized_once)
        
        assert normalized_once == normalized_twice
