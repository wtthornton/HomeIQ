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
from src.models.automation_models import ValidationResult


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
    client.ha_url = "http://localhost:8123"
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
    client.get_devices = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_ai_automation_client():
    """Mock AI Automation Service client"""
    client = MagicMock(spec=AIAutomationClient)
    # Note: AIAutomationValidationStrategy expects errors/warnings as lists of dicts with "message" keys
    client.validate_yaml = AsyncMock(return_value={
        "valid": True,
        "errors": [],  # List of dicts with "message" keys
        "warnings": [],  # List of dicts with "message" keys
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
async def test_preview_automation_valid_yaml(tool_handler):
    """Test preview automation with valid YAML (fallback to basic validation)"""
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
    arguments = {
        "user_prompt": "Turn off kitchen light when it turns on",
        "automation_yaml": valid_yaml,
        "alias": "Test Automation"
    }
    result = await tool_handler.preview_automation_from_prompt(arguments)
    
    assert result["success"] is True
    assert result["preview"] is True
    assert "validation" in result
    assert result["validation"]["valid"] is True


@pytest.mark.asyncio
async def test_preview_automation_invalid_yaml(tool_handler):
    """Test preview automation with invalid YAML"""
    invalid_yaml = """
alias: Test Automation
trigger: []
action: []
"""
    arguments = {
        "user_prompt": "Test automation",
        "automation_yaml": invalid_yaml,
        "alias": "Test Automation"
    }
    result = await tool_handler.preview_automation_from_prompt(arguments)
    
    assert result["success"] is True
    assert result["preview"] is True
    assert "validation" in result
    # Basic validation may still pass syntax check but fail structure check


@pytest.mark.asyncio
async def test_preview_automation_missing_fields(tool_handler):
    """Test preview automation with missing required fields"""
    incomplete_yaml = """
alias: Test Automation
"""
    arguments = {
        "user_prompt": "Test automation",
        "automation_yaml": incomplete_yaml,
        "alias": "Test Automation"
    }
    result = await tool_handler.preview_automation_from_prompt(arguments)
    
    assert result["success"] is True
    assert result["preview"] is True
    assert "validation" in result


@pytest.mark.asyncio
async def test_preview_automation_invalid_request(tool_handler):
    """Test preview automation with invalid request (empty prompt)"""
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
    arguments = {
        "user_prompt": "",  # Empty prompt
        "automation_yaml": valid_yaml,
        "alias": "Test Automation"
    }
    result = await tool_handler.preview_automation_from_prompt(arguments)
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_preview_automation_with_consolidated_validation(tool_handler_with_validation, mock_ai_automation_client):
    """Test preview automation using consolidated validation endpoint"""
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
    arguments = {
        "user_prompt": "Turn off kitchen light when it turns on",
        "automation_yaml": valid_yaml,
        "alias": "Test Automation"
    }
    
    result = await tool_handler_with_validation.preview_automation_from_prompt(arguments)
    
    # Should use consolidated validation through validation chain
    assert result["success"] is True
    assert result["preview"] is True
    assert "validation" in result
    assert result["validation"]["valid"] is True


@pytest.mark.asyncio
async def test_preview_automation_with_fixed_yaml(tool_handler_with_validation, mock_ai_automation_client):
    """Test preview automation that returns fixed YAML"""
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
    # Note: AIAutomationValidationStrategy expects errors/warnings as lists of dicts with "message" keys
    mock_ai_automation_client.validate_yaml.return_value = {
        "valid": True,
        "errors": [],  # List of dicts with "message" keys
        "warnings": [{"message": "Fixed plural keys"}],  # List of dicts with "message" keys
        "stages": {"syntax": True, "structure": True},
        "fixed_yaml": "alias: Test Automation\ntrigger:\n  - platform: state\n    entity_id: light.kitchen\naction:\n  - service: light.turn_off\n    target:\n      entity_id: light.kitchen",
        "summary": "Validation passed with fixes"
    }
    
    arguments = {
        "user_prompt": "Turn off kitchen light when it turns on",
        "automation_yaml": yaml_with_issues,
        "alias": "Test Automation"
    }
    
    result = await tool_handler_with_validation.preview_automation_from_prompt(arguments)
    
    assert result["success"] is True
    assert result["preview"] is True
    assert "validation" in result
    assert result["validation"]["valid"] is True
    # Check that fixed_yaml is in the validation result
    assert "fixed_yaml" in result["validation"]
    assert result["validation"]["fixed_yaml"] is not None


@pytest.mark.asyncio
async def test_preview_automation_fallback_to_basic(tool_handler):
    """Test preview automation falls back to basic validation when AI automation client unavailable"""
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
    arguments = {
        "user_prompt": "Turn off kitchen light when it turns on",
        "automation_yaml": valid_yaml,
        "alias": "Test Automation"
    }
    
    result = await tool_handler.preview_automation_from_prompt(arguments)
    
    # Should use basic validation (no AI automation client)
    assert result["success"] is True
    assert result["preview"] is True
    assert "validation" in result
    assert "errors" in result["validation"]
    assert "warnings" in result["validation"]


@pytest.mark.asyncio
async def test_preview_automation_consolidated_validation_error(tool_handler_with_validation, mock_ai_automation_client):
    """Test preview automation when consolidated validation fails, falls back to basic"""
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
    
    arguments = {
        "user_prompt": "Turn off kitchen light when it turns on",
        "automation_yaml": valid_yaml,
        "alias": "Test Automation"
    }
    
    result = await tool_handler_with_validation.preview_automation_from_prompt(arguments)
    
    # Should fall back to basic validation
    assert result["success"] is True
    assert result["preview"] is True
    assert "validation" in result
    assert "errors" in result["validation"]


@pytest.mark.asyncio
async def test_preview_automation_yaml_parsing_error(tool_handler):
    """Test preview automation with YAML parsing error"""
    invalid_yaml = """
alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
    to: "on"
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
invalid: [unclosed bracket
"""
    arguments = {
        "user_prompt": "Turn off kitchen light when it turns on",
        "automation_yaml": invalid_yaml,
        "alias": "Test Automation"
    }
    
    result = await tool_handler.preview_automation_from_prompt(arguments)
    
    assert result["success"] is False
    assert "error" in result
    assert "YAML" in result["error"] or "yaml" in result["error"].lower()


@pytest.mark.asyncio
async def test_preview_automation_missing_alias(tool_handler):
    """Test preview automation with missing alias"""
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
    arguments = {
        "user_prompt": "Turn off kitchen light when it turns on",
        "automation_yaml": valid_yaml,
        "alias": ""  # Empty alias
    }
    
    result = await tool_handler.preview_automation_from_prompt(arguments)
    
    assert result["success"] is False
    assert "error" in result
