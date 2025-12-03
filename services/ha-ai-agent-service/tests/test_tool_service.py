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
def tool_service(mock_ha_client, mock_data_api_client):
    """Create tool service with mocked clients"""
    return ToolService(mock_ha_client, mock_data_api_client)


@pytest.mark.asyncio
async def test_execute_tool_get_entity_state(tool_service, mock_ha_client):
    """Test get_entity_state tool execution"""
    result = await tool_service.execute_tool(
        "get_entity_state",
        {"entity_id": "light.kitchen"}
    )
    
    assert result["success"] is True
    assert result["entity_id"] == "light.kitchen"
    assert result["state"] == "on"


@pytest.mark.asyncio
async def test_execute_tool_unknown_tool(tool_service):
    """Test execution of unknown tool"""
    result = await tool_service.execute_tool("unknown_tool", {})
    
    assert "error" in result
    assert "available_tools" in result


@pytest.mark.asyncio
async def test_execute_tool_validation_error(tool_service):
    """Test tool execution with validation error"""
    result = await tool_service.execute_tool(
        "get_entity_state",
        {}  # Missing entity_id
    )
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_execute_tool_call_openai_format(tool_service, mock_ha_client):
    """Test tool call execution in OpenAI format"""
    tool_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "get_entity_state",
            "arguments": '{"entity_id": "light.kitchen"}'
        }
    }
    
    result = await tool_service.execute_tool_call(tool_call)
    
    assert result["success"] is True
    assert result["tool_call_id"] == "call_123"
    assert result["entity_id"] == "light.kitchen"


@pytest.mark.asyncio
async def test_get_available_tools(tool_service):
    """Test getting list of available tools"""
    tools = tool_service.get_available_tools()
    
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert "get_entity_state" in tools
    assert "create_automation" in tools

