"""
Tests for ai_automation_validation_strategy.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.validation.ai_automation_validation_strategy import AIAutomationValidationStrategy
from src.clients.ai_automation_client import AIAutomationClient


@pytest.fixture
def mock_ai_automation_client():
    """Mock AI Automation Service client"""
    client = MagicMock(spec=AIAutomationClient)
    client.validate_yaml = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": []
    })
    return client


class TestAIAutomationValidationStrategy:
    """Test AIAutomationValidationStrategy class."""

    def test___init__(self, mock_ai_automation_client):
        """Test __init__ method."""
        strategy = AIAutomationValidationStrategy(mock_ai_automation_client)
        assert strategy.ai_automation_client == mock_ai_automation_client

    def test_name(self, mock_ai_automation_client):
        """Test name property."""
        strategy = AIAutomationValidationStrategy(mock_ai_automation_client)
        assert strategy.name == "AI Automation Service"

    @pytest.mark.asyncio
    async def test_validate_success(self, mock_ai_automation_client):
        """Test validate with successful validation."""
        strategy = AIAutomationValidationStrategy(mock_ai_automation_client)
        
        yaml_str = "alias: test\ntrigger:\n  - platform: state"
        result = await strategy.validate(yaml_str)
        
        assert result.valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_with_errors(self, mock_ai_automation_client):
        """Test validate with validation errors."""
        mock_ai_automation_client.validate_yaml.return_value = {
            "valid": False,
            "errors": [{"message": "Missing required field: trigger"}],
            "warnings": []
        }
        
        strategy = AIAutomationValidationStrategy(mock_ai_automation_client)
        result = await strategy.validate("alias: test")
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "Missing required field" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_no_client(self):
        """Test validate without client raises error."""
        strategy = AIAutomationValidationStrategy(None)
        
        with pytest.raises(ValueError, match="AI Automation Service client not available"):
            await strategy.validate("alias: test")
    def test_name(self):
        """Test name method."""
        # TODO: Implement test
        pass