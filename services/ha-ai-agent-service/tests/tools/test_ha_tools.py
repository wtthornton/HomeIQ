"""
Tests for ha_tools.py
"""

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock

from src.tools.ha_tools import HAToolHandler
from src.clients.ha_client import HomeAssistantClient
from src.clients.data_api_client import DataAPIClient
from src.clients.yaml_validation_client import YAMLValidationClient
from src.models.automation_models import AutomationPreviewRequest, ValidationResult


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    client = MagicMock(spec=HomeAssistantClient)
    client.get_states = AsyncMock(return_value=[])
    client._get_session = AsyncMock()
    return client


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = MagicMock(spec=DataAPIClient)
    client.get_entities = AsyncMock(return_value=[])
    client.get_areas = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_yaml_validation_client():
    """Mock YAML Validation Service client"""
    client = MagicMock(spec=YAMLValidationClient)
    client.validate_yaml = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": [],
        "score": 100.0
    })
    return client


@pytest.fixture
def tool_handler(mock_ha_client, mock_data_api_client, mock_yaml_validation_client):
    """Create tool handler with mocked clients"""
    return HAToolHandler(
        mock_ha_client,
        mock_data_api_client,
        yaml_validation_client=mock_yaml_validation_client
    )


class TestHAToolHandler:
    """Test HAToolHandler class."""

    def test___init__(self, mock_ha_client, mock_data_api_client):
        """Test __init__ method."""
        handler = HAToolHandler(mock_ha_client, mock_data_api_client)
        assert handler.ha_client == mock_ha_client
        assert handler.data_api_client == mock_data_api_client
        assert handler.entity_resolution_service is not None
        assert handler.business_rule_validator is not None
        assert handler.validation_chain is not None

    def test__is_group_entity(self, tool_handler):
        """Test _is_group_entity method."""
        assert tool_handler._is_group_entity("group.lights") is True
        assert tool_handler._is_group_entity("light.office") is False
        assert tool_handler._is_group_entity("switch.kitchen") is False
        assert tool_handler._is_group_entity("") is False

    def test__validate_preview_request_valid(self, tool_handler):
        """Test _validate_preview_request with valid request."""
        request = AutomationPreviewRequest(
            user_prompt="Turn on lights",
            automation_yaml="alias: test\ntrigger:\n  - platform: state",
            alias="test_automation"
        )
        result = tool_handler._validate_preview_request(request)
        assert result is None

    def test__validate_preview_request_invalid(self, tool_handler):
        """Test _validate_preview_request with invalid request."""
        request = AutomationPreviewRequest(
            user_prompt="",  # Empty prompt
            automation_yaml="alias: test",
            alias="test"
        )
        result = tool_handler._validate_preview_request(request)
        assert result is not None
        assert result["success"] is False
        assert "error" in result

    def test__parse_automation_yaml_valid(self, tool_handler):
        """Test _parse_automation_yaml with valid YAML."""
        request = AutomationPreviewRequest(
            user_prompt="test",
            automation_yaml="alias: test\ntrigger:\n  - platform: state",
            alias="test"
        )
        yaml_str = "alias: test\ntrigger:\n  - platform: state"
        result = tool_handler._parse_automation_yaml(yaml_str, request)
        assert isinstance(result, dict)
        assert result["alias"] == "test"
        assert "trigger" in result

    def test__parse_automation_yaml_invalid(self, tool_handler):
        """Test _parse_automation_yaml with invalid YAML."""
        request = AutomationPreviewRequest(
            user_prompt="test",
            automation_yaml="not a dict",
            alias="test"
        )
        yaml_str = "not a dict"
        with pytest.raises(ValueError, match="Automation YAML must be a dictionary"):
            tool_handler._parse_automation_yaml(yaml_str, request)

    def test__extract_automation_details(self, tool_handler):
        """Test _extract_automation_details method."""
        automation_dict = {
            "trigger": {
                "platform": "state",
                "entity_id": "light.office"
            },
            "action": {
                "service": "light.turn_on",
                "target": {
                    "area_id": "office"
                }
            }
        }
        result = tool_handler._extract_automation_details(automation_dict)
        assert "entities" in result
        assert "areas" in result
        assert "services" in result
        assert isinstance(result["entities"], list)
        assert isinstance(result["areas"], list)
        assert isinstance(result["services"], list)

    @pytest.mark.asyncio
    async def test_preview_automation_from_prompt_success(self, tool_handler, mock_yaml_validation_client):
        """Test preview_automation_from_prompt with valid input."""
        # Mock validation result
        mock_yaml_validation_client.validate_yaml.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "score": 100.0
        }

        arguments = {
            "user_prompt": "Turn on office lights",
            "automation_yaml": "alias: Office Lights\ntrigger:\n  - platform: state\n    entity_id: light.office\naction:\n  - service: light.turn_on\n    target:\n      area_id: office",
            "alias": "Office Lights"
        }

        result = await tool_handler.preview_automation_from_prompt(arguments)
        assert result["success"] is True
        assert "preview" in result
        assert result["preview"] is True

    @pytest.mark.asyncio
    async def test_preview_automation_from_prompt_invalid_request(self, tool_handler):
        """Test preview_automation_from_prompt with invalid request."""
        arguments = {
            "user_prompt": "",  # Empty prompt
            "automation_yaml": "alias: test",
            "alias": "test"
        }

        result = await tool_handler.preview_automation_from_prompt(arguments)
        assert result["success"] is False
        assert "error" in result