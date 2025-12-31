"""
Tests for basic_validation_strategy.py
"""

import pytest
from unittest.mock import MagicMock

from src.services.validation.basic_validation_strategy import BasicValidationStrategy


@pytest.fixture
def mock_tool_handler():
    """Mock tool handler"""
    handler = MagicMock()
    handler._extract_entities_from_yaml = MagicMock(return_value=["light.office"])
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

    @pytest.mark.asyncio
    async def test_validate_valid_yaml(self, mock_tool_handler):
        """Test validate with valid YAML."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        yaml_str = "alias: test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on"
        result = await strategy.validate(yaml_str)
        
        assert result.valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_missing_trigger(self, mock_tool_handler):
        """Test validate with missing trigger field."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        yaml_str = "alias: test\naction:\n  - service: light.turn_on"
        result = await strategy.validate(yaml_str)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("trigger" in error.lower() for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_missing_action(self, mock_tool_handler):
        """Test validate with missing action field."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        yaml_str = "alias: test\ntrigger:\n  - platform: state"
        result = await strategy.validate(yaml_str)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("action" in error.lower() for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_invalid_yaml_syntax(self, mock_tool_handler):
        """Test validate with invalid YAML syntax."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        yaml_str = "alias: test\ninvalid: ["
        result = await strategy.validate(yaml_str)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("syntax" in error.lower() for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_not_dict(self, mock_tool_handler):
        """Test validate with YAML that's not a dictionary."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        yaml_str = "not a dict"
        result = await strategy.validate(yaml_str)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("dictionary" in error.lower() for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_warnings(self, mock_tool_handler):
        """Test validate generates warnings for missing recommended fields."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        yaml_str = "trigger:\n  - platform: state\naction:\n  - service: light.turn_on"
        result = await strategy.validate(yaml_str)
        
        # Should have warnings for missing alias, description, initial_state
        assert len(result.warnings) > 0
    def test_name(self):
        """Test name method."""
        # TODO: Implement test
        pass