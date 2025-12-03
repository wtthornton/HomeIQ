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
def tool_handler(mock_ha_client, mock_data_api_client):
    """Create tool handler with mocked clients"""
    return HAToolHandler(mock_ha_client, mock_data_api_client)


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
    """Test automation YAML validation with valid YAML"""
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

