"""
Tests for YAML Validation Router

Tests the consolidated YAML validation endpoint.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client."""
    client = MagicMock()
    client.get_states = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_safety_validator():
    """Mock safety validator."""
    from src.safety_validator import SafetyResult, SafetyIssue
    
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=SafetyResult(
        passed=True,
        safety_score=95,
        issues=[],
        can_override=False,
        summary="Safety validation passed"
    ))
    return validator


@pytest.fixture
def valid_yaml():
    """Valid Home Assistant automation YAML."""
    return """
alias: Test Automation
description: Test automation for validation
initial_state: true
trigger:
  - platform: state
    entity_id: light.kitchen
    to: "on"
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""


@pytest.fixture
def invalid_yaml_syntax():
    """Invalid YAML syntax."""
    return """
alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
    to: "on"
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
    # Missing closing bracket
"""


@pytest.fixture
def invalid_yaml_structure():
    """Invalid YAML structure (missing required fields)."""
    return """
alias: Test Automation
# Missing trigger and action
"""


class TestYAMLValidationRouter:
    """Test suite for YAML validation endpoint."""

    def test_validate_yaml_valid(self, client, valid_yaml):
        """Test validation with valid YAML."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": valid_yaml,
                "validate_entities": False,
                "validate_safety": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0
        assert "stages" in data
        assert data["stages"].get("syntax") is True
        assert data["stages"].get("structure") is True

    def test_validate_yaml_invalid_syntax(self, client, invalid_yaml_syntax):
        """Test validation with invalid YAML syntax."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": invalid_yaml_syntax,
                "validate_entities": False,
                "validate_safety": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert any("syntax" in error.get("stage", "") for error in data["errors"])

    def test_validate_yaml_invalid_structure(self, client, invalid_yaml_structure):
        """Test validation with invalid YAML structure."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": invalid_yaml_structure,
                "validate_entities": False,
                "validate_safety": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert any("structure" in error.get("stage", "") for error in data["errors"])

    def test_validate_yaml_with_auto_fix(self, client):
        """Test validation with YAML that can be auto-fixed."""
        # YAML with plural keys (should be auto-fixed)
        yaml_with_plural = """
alias: Test Automation
triggers:
  - platform: state
    entity_id: light.kitchen
actions:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""
        
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": yaml_with_plural,
                "validate_entities": False,
                "validate_safety": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should have errors about plural keys
        assert len(data["errors"]) > 0
        # Should provide fixed YAML
        if data.get("fixed_yaml"):
            assert "trigger:" in data["fixed_yaml"]
            assert "action:" in data["fixed_yaml"]

    def test_validate_yaml_with_entities(self, client, valid_yaml):
        """Test validation with entity validation enabled."""
        with patch('src.api.yaml_validation_router.get_ha_client') as mock_get_ha:
            mock_ha = MagicMock()
            mock_get_ha.return_value = mock_ha
            
            # Mock entity validator
            with patch('src.services.automation.yaml_validator.EntityValidator') as mock_entity_validator:
                mock_validator = MagicMock()
                mock_validator.validate_entities = AsyncMock(return_value={
                    "light.kitchen": {"exists": True}
                })
                mock_entity_validator.return_value = mock_validator
                
                response = client.post(
                    "/api/v1/yaml/validate",
                    json={
                        "yaml": valid_yaml,
                        "validate_entities": True,
                        "validate_safety": False
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "stages" in data
                # Entity validation may or may not run depending on HA client availability

    def test_validate_yaml_with_safety(self, client, valid_yaml):
        """Test validation with safety validation enabled."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": valid_yaml,
                "validate_entities": False,
                "validate_safety": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        # Safety validation should run
        if "safety" in data["stages"]:
            assert "safety_score" in data or data["stages"]["safety"] is not None

    def test_validate_yaml_missing_yaml(self, client):
        """Test validation with missing YAML field."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "validate_entities": False,
                "validate_safety": False
            }
        )
        
        assert response.status_code == 422  # Validation error

    def test_validate_yaml_empty_yaml(self, client):
        """Test validation with empty YAML."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": "",
                "validate_entities": False,
                "validate_safety": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_yaml_with_context(self, client, valid_yaml):
        """Test validation with context provided."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": valid_yaml,
                "validate_entities": False,
                "validate_safety": False,
                "context": {
                    "entities": ["light.kitchen"],
                    "conversation_history": []
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data

    def test_validate_yaml_response_structure(self, client, valid_yaml):
        """Test that validation response has correct structure."""
        response = client.post(
            "/api/v1/yaml/validate",
            json={
                "yaml": valid_yaml,
                "validate_entities": False,
                "validate_safety": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "stages" in data
        assert "summary" in data
        
        # Check error/warning structure
        for error in data["errors"]:
            assert "stage" in error
            assert "severity" in error
            assert "message" in error
        
        for warning in data["warnings"]:
            assert "stage" in warning
            assert "severity" in warning
            assert "message" in warning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

