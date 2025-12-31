"""
Tests for yaml_validation_strategy.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.validation.yaml_validation_strategy import YAMLValidationStrategy
from src.clients.yaml_validation_client import YAMLValidationClient


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


class TestYAMLValidationStrategy:
    """Test YAMLValidationStrategy class."""

    def test___init__(self, mock_yaml_validation_client):
        """Test __init__ method."""
        strategy = YAMLValidationStrategy(mock_yaml_validation_client)
        assert strategy.yaml_validation_client == mock_yaml_validation_client

    def test_name(self, mock_yaml_validation_client):
        """Test name property."""
        strategy = YAMLValidationStrategy(mock_yaml_validation_client)
        assert strategy.name == "YAML Validation Service"

    @pytest.mark.asyncio
    async def test_validate_success(self, mock_yaml_validation_client):
        """Test validate with successful validation."""
        strategy = YAMLValidationStrategy(mock_yaml_validation_client)
        
        yaml_str = "alias: test\ntrigger:\n  - platform: state"
        result = await strategy.validate(yaml_str)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_validate_with_errors(self, mock_yaml_validation_client):
        """Test validate with validation errors."""
        mock_yaml_validation_client.validate_yaml.return_value = {
            "valid": False,
            "errors": ["Missing required field: trigger"],
            "warnings": [],
            "score": 50.0
        }
        
        strategy = YAMLValidationStrategy(mock_yaml_validation_client)
        result = await strategy.validate("alias: test")
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.score == 50.0

    @pytest.mark.asyncio
    async def test_validate_with_fixed_yaml(self, mock_yaml_validation_client):
        """Test validate with fixed YAML returned."""
        mock_yaml_validation_client.validate_yaml.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "score": 100.0,
            "fixed_yaml": "alias: test\ntrigger:\n  - platform: state",
            "fixes_applied": ["Added missing trigger field"]
        }
        
        strategy = YAMLValidationStrategy(mock_yaml_validation_client)
        result = await strategy.validate("alias: test")
        
        assert result.valid is True
        assert result.fixed_yaml is not None
        assert result.fixes_applied is not None

    @pytest.mark.asyncio
    async def test_validate_no_client(self):
        """Test validate without client raises error."""
        strategy = YAMLValidationStrategy(None)
        
        with pytest.raises(ValueError, match="YAML Validation Service client not available"):
            await strategy.validate("alias: test")
    def test_name(self):
        """Test name method."""
        # TODO: Implement test
        pass