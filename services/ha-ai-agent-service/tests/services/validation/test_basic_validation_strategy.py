"""
Tests for basic_validation_strategy.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.validation.basic_validation_strategy import BasicValidationStrategy


@pytest.fixture
def mock_tool_handler():
    """Mock HAToolHandler for testing."""
    handler = MagicMock()
    handler.data_api_client = MagicMock()
    handler.data_api_client.fetch_entities = AsyncMock(return_value=[
        {"entity_id": "light.office_led", "friendly_name": "Office LED"},
        {"entity_id": "light.office_go", "friendly_name": "Office Go"},
        {"entity_id": "switch.office_fan", "friendly_name": "Office Fan"},
    ])
    handler._extract_entities_from_yaml = MagicMock(return_value=["light.office_led"])
    handler._is_group_entity = MagicMock(return_value=False)
    return handler


class TestBasicValidationStrategy:
    """Test BasicValidationStrategy class."""

    def test___init__(self, mock_tool_handler):
        """Test __init__ method."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        assert strategy.tool_handler == mock_tool_handler

    def test_name(self, mock_tool_handler):
        """Test name property."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        assert strategy.name == "Basic Validation"

    def test__build_entity_error_message(self, mock_tool_handler):
        """Test _build_entity_error_message method."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        valid_entities = {"light.office_go", "switch.office_fan"}
        
        # Test with similar entities (suggestions)
        error_msg = strategy._build_entity_error_message("light.office_led", valid_entities)
        assert "Invalid entity ID" in error_msg
        assert "light.office_led" in error_msg
        
        # Test without similar entities
        error_msg_no_match = strategy._build_entity_error_message("sensor.unknown", valid_entities)
        assert "Invalid entity ID" in error_msg_no_match
        assert "sensor.unknown" in error_msg_no_match

    @pytest.mark.asyncio
    async def test__validate_entities_with_invalid_entities(self, mock_tool_handler):
        """Test _validate_entities with invalid entities."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        mock_tool_handler._extract_entities_from_yaml.return_value = ["light.invalid_entity"]
        
        errors, warnings = await strategy._validate_entities(["light.invalid_entity"])
        assert len(errors) > 0
        assert any("Invalid entity ID" in err for err in errors)

    @pytest.mark.asyncio
    async def test__validate_entities_with_valid_entities(self, mock_tool_handler):
        """Test _validate_entities with valid entities."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        errors, warnings = await strategy._validate_entities(["light.office_led"])
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test__validate_entities_no_data_api_client(self):
        """Test _validate_entities when Data API client is not available."""
        handler = MagicMock()
        handler.data_api_client = None
        strategy = BasicValidationStrategy(handler)
        
        errors, warnings = await strategy._validate_entities(["light.office_led"])
        assert len(errors) == 0
        assert len(warnings) == 0
