"""
Tests for Validation Pipeline (Epic 51, Story 51.2, 51.7, 51.10)
"""

import pytest
from yaml_validation_service.validator import ValidationPipeline


class TestValidationPipeline:
    """Test multi-stage validation pipeline."""
    
    @pytest.fixture
    def validator(self):
        """Create validation pipeline instance."""
        return ValidationPipeline(validation_level="moderate")
    
    def test_syntax_validation_valid_yaml(self, validator):
        """Test syntax validation with valid YAML."""
        yaml_content = """
alias: "Test Automation"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
"""
        
        result = validator._validate_syntax(yaml_content)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_syntax_validation_invalid_yaml(self, validator):
        """Test syntax validation with invalid YAML."""
        yaml_content = """
alias: "Test Automation
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
"""

        result = validator._validate_syntax(yaml_content)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_schema_validation_required_fields(self, validator):
        """Test schema validation checks required fields."""
        data = {
            "alias": "Test",
            # Missing trigger and action
        }
        
        result = validator._validate_schema(data)
        assert result["valid"] is False
        assert any("trigger" in error.lower() for error in result["errors"])
        assert any("action" in error.lower() for error in result["errors"])
    
    def test_schema_validation_plural_keys(self, validator):
        """Test schema validation detects plural keys."""
        data = {
            "triggers": [{"platform": "time", "at": "07:00:00"}],
            "actions": [{"service": "light.turn_on"}]
        }
        
        result = validator._validate_schema(data)
        assert result["valid"] is False
        assert any("triggers" in error.lower() for error in result["errors"])
        assert any("actions" in error.lower() for error in result["errors"])
    
    def test_entity_extraction_known_locations(self, validator):
        """Test entity extraction only from known locations (Epic 51.7)."""
        data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "light.living_room"
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.kitchen"
                    }
                }
            ],
            "description": "Turn on light.living_room"  # Should NOT extract from description
        }
        
        entity_ids = validator._extract_entity_ids(data)
        
        assert "light.living_room" in entity_ids
        assert "light.kitchen" in entity_ids
        # Should NOT extract from description
        assert len(entity_ids) == 2
    
    def test_service_extraction_distinct_from_entities(self, validator):
        """Test service extraction distinguishes from entities (Epic 51.7)."""
        data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.living_room"
                    }
                }
            ]
        }
        
        services = validator._extract_services(data)
        entity_ids = validator._extract_entity_ids(data)
        
        assert "light.turn_on" in services
        assert "light.living_room" in entity_ids
        assert "light.turn_on" not in entity_ids
        assert "light.living_room" not in services
    
    def test_safety_validation_critical_devices(self, validator):
        """Test safety validation rejects blocked devices (Epic 93)."""
        data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "lock.front_door"
                }
            ],
            "action": [
                {
                    "service": "lock.unlock",
                    "target": {
                        "entity_id": "lock.front_door"
                    }
                }
            ]
        }

        result = validator._validate_safety(data)

        # Epic 93: lock/alarm entities are now hard-blocked (errors, not warnings)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("BLOCKED" in error for error in result["errors"])
        assert "safety_score" in result
        assert result["safety_score"] < 100.0
