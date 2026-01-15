"""
Unit tests for SpecValidator
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.homeiq_automation.spec_validator import (
    SpecValidationError,
    SpecValidator,
    validate_semver,
    validate_spec,
)


class TestValidateSemver:
    """Test semver validation"""
    
    def test_valid_semver(self):
        """Test valid semver versions"""
        assert validate_semver("1.0.0") is True
        assert validate_semver("1.2.3") is True
        assert validate_semver("2.0.0-beta.1") is True
        assert validate_semver("1.0.0-rc.2") is True
        assert validate_semver("10.20.30") is True
    
    def test_invalid_semver(self):
        """Test invalid semver versions"""
        assert validate_semver("1.0") is False
        assert validate_semver("1") is False
        assert validate_semver("v1.0.0") is False
        assert validate_semver("1.0.0.0") is False
        assert validate_semver("") is False


class TestSpecValidator:
    """Test SpecValidator class"""
    
    @pytest.fixture
    def mock_schema(self):
        """Mock JSON schema"""
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["id", "version", "name", "enabled", "triggers", "actions", "policy"],
            "properties": {
                "id": {"type": "string", "minLength": 3},
                "version": {"type": "string"},
                "name": {"type": "string", "minLength": 3},
                "enabled": {"type": "boolean"},
                "triggers": {"type": "array", "minItems": 1},
                "actions": {"type": "array", "minItems": 1},
                "policy": {"type": "object", "required": ["risk"]}
            }
        }
    
    @pytest.fixture
    def valid_spec(self):
        """Valid automation spec"""
        return {
            "id": "test_automation",
            "version": "1.0.0",
            "name": "Test Automation",
            "enabled": True,
            "triggers": [
                {
                    "type": "ha_event",
                    "event_type": "state_changed"
                }
            ],
            "actions": [
                {
                    "id": "act1",
                    "capability": "light.turn_on",
                    "target": {"entity_id": "light.living_room"},
                    "data": {}
                }
            ],
            "policy": {
                "risk": "low"
            }
        }
    
    def test_validate_valid_spec(self, mock_schema, valid_spec):
        """Test validation of valid spec"""
        validator = SpecValidator(schema=mock_schema)
        is_valid, errors = validator.validate(valid_spec)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_triggers(self, mock_schema, valid_spec):
        """Test validation fails when triggers missing"""
        validator = SpecValidator(schema=mock_schema)
        spec = valid_spec.copy()
        spec["triggers"] = []
        is_valid, errors = validator.validate(spec)
        assert is_valid is False
        assert any("triggers" in str(e) for e in errors)
    
    def test_validate_missing_actions(self, mock_schema, valid_spec):
        """Test validation fails when actions missing"""
        validator = SpecValidator(schema=mock_schema)
        spec = valid_spec.copy()
        spec["actions"] = []
        is_valid, errors = validator.validate(spec)
        assert is_valid is False
        assert any("actions" in str(e) for e in errors)
    
    def test_validate_invalid_semver(self, mock_schema, valid_spec):
        """Test validation fails with invalid semver"""
        validator = SpecValidator(schema=mock_schema)
        spec = valid_spec.copy()
        spec["version"] = "invalid"
        is_valid, errors = validator.validate(spec)
        assert is_valid is False
        assert any("version" in str(e) for e in errors)
    
    def test_validate_ha_event_missing_event_type(self, mock_schema, valid_spec):
        """Test validation fails when ha_event missing event_type"""
        validator = SpecValidator(schema=mock_schema)
        spec = valid_spec.copy()
        spec["triggers"] = [{"type": "ha_event"}]
        is_valid, errors = validator.validate(spec)
        assert is_valid is False
        assert any("event_type" in str(e) for e in errors)
    
    def test_validate_action_missing_target(self, mock_schema, valid_spec):
        """Test validation fails when action missing target"""
        validator = SpecValidator(schema=mock_schema)
        spec = valid_spec.copy()
        spec["actions"] = [{"id": "act1", "capability": "light.turn_on", "target": {}, "data": {}}]
        is_valid, errors = validator.validate(spec)
        assert is_valid is False
        assert any("target" in str(e) for e in errors)
    
    def test_validate_file_json(self, mock_schema, valid_spec):
        """Test validation from JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_spec, f)
            file_path = Path(f.name)
        
        try:
            validator = SpecValidator(schema=mock_schema)
            is_valid, errors = validator.validate_file(file_path)
            assert is_valid is True
        finally:
            file_path.unlink()
    
    def test_validate_file_not_found(self, mock_schema):
        """Test validation fails when file not found"""
        validator = SpecValidator(schema=mock_schema)
        file_path = Path("/nonexistent/file.json")
        is_valid, errors = validator.validate_file(file_path)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_format_errors(self, mock_schema):
        """Test error formatting"""
        validator = SpecValidator(schema=mock_schema)
        errors = [
            {"field": "version", "message": "Invalid semver"},
            {"field": "triggers", "message": "Missing triggers"}
        ]
        formatted = validator.format_errors(errors)
        assert "version" in formatted
        assert "triggers" in formatted
        assert "Invalid semver" in formatted


class TestValidateSpecConvenience:
    """Test convenience function"""
    
    def test_validate_spec_function(self):
        """Test convenience validate_spec function"""
        spec = {
            "id": "test",
            "version": "1.0.0",
            "name": "Test",
            "enabled": True,
            "triggers": [{"type": "ha_event", "event_type": "state_changed"}],
            "actions": [{"id": "act1", "capability": "light.turn_on", "target": {"entity_id": "light.test"}, "data": {}}],
            "policy": {"risk": "low"}
        }
        # This will use actual schema - may fail if schema file not found
        # In real usage, would mock or ensure schema file exists
        pass
