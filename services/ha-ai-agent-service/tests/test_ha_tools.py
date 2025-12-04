"""
Tests for Home Assistant Tool Handlers

Tests individual tool implementations.
"""

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock

from src.tools.ha_tools import HAToolHandler
from src.clients.ha_client import HomeAssistantClient
from src.clients.data_api_client import DataAPIClient
from src.clients.ai_automation_client import AIAutomationClient


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    client = MagicMock(spec=HomeAssistantClient)
    client.get_states = AsyncMock(return_value=[
        {
            "entity_id": "light.kitchen",
            "state": "on",
            "attributes": {"brightness": 255}
        }
    ])
    client._get_session = AsyncMock()
    return client


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = MagicMock(spec=DataAPIClient)
    client.fetch_entities = AsyncMock(return_value=[
        {
            "entity_id": "light.kitchen",
            "friendly_name": "Kitchen Light",
            "domain": "light",
            "area_id": "kitchen"
        }
    ])
    return client


@pytest.fixture
def mock_ai_automation_client():
    """Mock AI Automation Service client"""
    client = MagicMock(spec=AIAutomationClient)
    client.validate_yaml = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": [],
        "stages": {"syntax": True, "structure": True},
        "fixed_yaml": None,
        "summary": "✅ All validation checks passed"
    })
    return client


@pytest.fixture
def tool_handler(mock_ha_client, mock_data_api_client):
    """Create tool handler with mocked clients (no AI automation client)"""
    return HAToolHandler(mock_ha_client, mock_data_api_client)


@pytest.fixture
def tool_handler_with_validation(mock_ha_client, mock_data_api_client, mock_ai_automation_client):
    """Create tool handler with AI automation client for consolidated validation"""
    return HAToolHandler(mock_ha_client, mock_data_api_client, mock_ai_automation_client)


@pytest.mark.asyncio
async def test_get_entity_state_success(tool_handler, mock_ha_client):
    """Test successful entity state retrieval"""
    result = await tool_handler.get_entity_state({"entity_id": "light.kitchen"})
    
    assert result["success"] is True
    assert result["entity_id"] == "light.kitchen"
    assert result["state"] == "on"


@pytest.mark.asyncio
async def test_get_entity_state_not_found(tool_handler, mock_ha_client):
    """Test entity state retrieval for non-existent entity"""
    result = await tool_handler.get_entity_state({"entity_id": "light.nonexistent"})
    
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_entity_state_invalid_format(tool_handler):
    """Test entity state retrieval with invalid entity ID format"""
    result = await tool_handler.get_entity_state({"entity_id": "invalid-format"})
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_test_automation_yaml_valid(tool_handler):
    """Test automation YAML validation with valid YAML (fallback to basic validation)"""
    valid_yaml = """
alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
    to: "on"
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""
    result = await tool_handler.test_automation_yaml({"automation_yaml": valid_yaml})
    
    assert result["success"] is True
    assert result["valid"] is True
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_validate_yaml_with_consolidated_validation(tool_handler_with_validation, mock_ai_automation_client):
    """Test YAML validation using consolidated validation endpoint"""
    valid_yaml = """
alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
    to: "on"
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""
    
    result = await tool_handler_with_validation._validate_yaml(valid_yaml)
    
    # Should use consolidated validation
    mock_ai_automation_client.validate_yaml.assert_called_once()
    assert result["valid"] is True
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_validate_yaml_with_fixed_yaml(tool_handler_with_validation, mock_ai_automation_client):
    """Test YAML validation that returns fixed YAML"""
    yaml_with_issues = """
alias: Test Automation
triggers:
  - platform: state
    entity_id: light.kitchen
actions:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""
    
    # Mock validation response with fixed YAML
    mock_ai_automation_client.validate_yaml.return_value = {
        "valid": True,
        "errors": [],
        "warnings": ["Fixed plural keys"],
        "stages": {"syntax": True, "structure": True},
        "fixed_yaml": "alias: Test Automation\ntrigger:\n  - platform: state\n    entity_id: light.kitchen\naction:\n  - service: light.turn_off\n    target:\n      entity_id: light.kitchen",
        "summary": "Validation passed with fixes"
    }
    
    result = await tool_handler_with_validation._validate_yaml(yaml_with_issues)
    
    assert result["valid"] is True
    assert "fixed_yaml" in result
    assert result["fixed_yaml"] is not None


@pytest.mark.asyncio
async def test_validate_yaml_fallback_to_basic(tool_handler):
    """Test YAML validation falls back to basic validation when AI automation client unavailable"""
    valid_yaml = """
alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
    to: "on"
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""
    
    result = await tool_handler._validate_yaml(valid_yaml)
    
    # Should use basic validation (no AI automation client)
    assert result["valid"] is True
    assert "errors" in result
    assert "warnings" in result


@pytest.mark.asyncio
async def test_validate_yaml_consolidated_validation_error(tool_handler_with_validation, mock_ai_automation_client):
    """Test YAML validation when consolidated validation fails, falls back to basic"""
    valid_yaml = """
alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""
    
    # Mock validation error
    mock_ai_automation_client.validate_yaml.side_effect = Exception("Service unavailable")
    
    result = await tool_handler_with_validation._validate_yaml(valid_yaml)
    
    # Should fall back to basic validation
    assert "valid" in result
    assert "errors" in result


@pytest.mark.asyncio
async def test_test_automation_yaml_invalid(tool_handler):
    """Test automation YAML validation with invalid YAML"""
    invalid_yaml = """
alias: Test Automation
trigger: []
action: []
"""
    result = await tool_handler.test_automation_yaml({"automation_yaml": invalid_yaml})
    
    assert result["success"] is True
    assert result["valid"] is False
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_test_automation_yaml_missing_fields(tool_handler):
    """Test automation YAML validation with missing required fields"""
    incomplete_yaml = """
alias: Test Automation
"""
    result = await tool_handler.test_automation_yaml({"automation_yaml": incomplete_yaml})
    
    assert result["success"] is True
    assert result["valid"] is False
    assert any("trigger" in error.lower() or "action" in error.lower() for error in result["errors"])


@pytest.mark.asyncio
async def test_get_entities_with_search(tool_handler, mock_data_api_client):
    """Test entity search with search term"""
    result = await tool_handler.get_entities({"search_term": "kitchen"})
    
    assert result["success"] is True
    assert result["count"] > 0
    assert "entities" in result


@pytest.mark.asyncio
async def test_get_entities_by_domain(tool_handler, mock_data_api_client):
    """Test entity search by domain"""
    result = await tool_handler.get_entities({"domain": "light"})
    
    assert result["success"] is True
    assert "entities" in result

