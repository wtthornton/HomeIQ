"""
Tests for Tool Service

Tests tool execution, routing, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.tool_service import ToolService
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
def tool_service(mock_ha_client, mock_data_api_client):
    """Create tool service with mocked clients"""
    return ToolService(mock_ha_client, mock_data_api_client)


@pytest.mark.asyncio
async def test_execute_tool_preview_automation(tool_service):
    """Test preview_automation_from_prompt tool execution"""
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
    result = await tool_service.execute_tool(
        "preview_automation_from_prompt",
        {
            "user_prompt": "Turn off kitchen light when it turns on",
            "automation_yaml": valid_yaml,
            "alias": "Test Automation"
        }
    )
    
    assert result["success"] is True
    assert result["preview"] is True


@pytest.mark.asyncio
async def test_execute_tool_unknown_tool(tool_service):
    """Test execution of unknown tool"""
    result = await tool_service.execute_tool("unknown_tool", {})
    
    assert "error" in result
    assert "available_tools" in result
    assert "unknown_tool" in result["error"]


@pytest.mark.asyncio
async def test_execute_tool_validation_error(tool_service):
    """Test tool execution with validation error (missing required fields)"""
    result = await tool_service.execute_tool(
        "preview_automation_from_prompt",
        {
            "user_prompt": "",  # Empty prompt should fail validation
            "automation_yaml": "alias: test",
            "alias": "test"
        }
    )
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_execute_tool_call_openai_format(tool_service):
    """Test tool call execution in OpenAI format"""
    import json
    
    valid_yaml = """alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""
    arguments = {
        "user_prompt": "Turn off kitchen light",
        "automation_yaml": valid_yaml,
        "alias": "Test Automation"
    }
    
    tool_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "preview_automation_from_prompt",
            "arguments": json.dumps(arguments)
        }
    }
    
    result = await tool_service.execute_tool_call(tool_call)
    
    assert result["success"] is True
    assert result["tool_call_id"] == "call_123"
    assert "preview" in result


@pytest.mark.asyncio
async def test_get_available_tools(tool_service):
    """Test getting list of available tools"""
    tools = tool_service.get_available_tools()
    
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert "preview_automation_from_prompt" in tools
    assert "create_automation_from_prompt" in tools
    assert "suggest_automation_enhancements" in tools
