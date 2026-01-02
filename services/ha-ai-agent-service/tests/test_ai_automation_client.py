"""
Tests for AI Automation Service Client

Tests the HTTP client for calling the consolidated YAML validation endpoint.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import httpx

from src.clients.ai_automation_client import AIAutomationClient


class MockResponse:
    """Mock httpx.Response-like object."""
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data
        # Ensure json is a bound method, not a property
        self.json = lambda: json_data
    
    def raise_for_status(self):
        """Synchronous raise_for_status method."""
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("Error", request=MagicMock(), response=self)
    
    def __getattr__(self, name):
        """Prevent MagicMock from interfering."""
        if name == 'json':
            return lambda: self._json_data
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


@pytest.fixture
def client():
    """Create AI Automation Service client."""
    return AIAutomationClient(base_url="http://test-service:8000")


@pytest.fixture
def valid_yaml():
    """Valid Home Assistant automation YAML."""
    return """
alias: Test Automation
trigger:
  - platform: state
    entity_id: light.kitchen
action:
  - service: light.turn_off
    target:
      entity_id: light.kitchen
"""


@pytest.fixture
def validation_response():
    """Mock validation response."""
    return {
        "valid": True,
        "errors": [],
        "warnings": [],
        "stages": {
            "syntax": True,
            "structure": True,
            "entities": True,
            "safety": True
        },
        "entity_results": [],
        "safety_score": 95,
        "fixed_yaml": None,
        "summary": "✅ All validation checks passed"
    }


class TestAIAutomationClient:
    """Test suite for AI Automation Service client."""

    @pytest.mark.asyncio
    async def test_validate_yaml_success(self, client, valid_yaml, validation_response):
        """Test successful YAML validation."""
        with patch.object(client.client, 'post') as mock_post:
            mock_response = MockResponse(200, validation_response)
            # httpx.AsyncClient.post() returns Response directly when awaited
            mock_post.return_value = mock_response
            
            result = await client.validate_yaml(valid_yaml)
            
            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert "stages" in result
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_yaml_with_options(self, client, valid_yaml, validation_response):
        """Test YAML validation with custom options."""
        with patch.object(client.client, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response = MockResponse(200, validation_response)
            mock_response.raise_for_status = MagicMock()
            # httpx.AsyncClient.post() returns Response directly when awaited
            mock_post.return_value = mock_response
            
            result = await client.validate_yaml(
                valid_yaml,
                validate_entities=False,
                validate_safety=False
            )
            
            assert result["valid"] is True
            # Check that request was made with correct options
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://test-service:8000/api/v1/yaml/validate"
            payload = call_args[1]["json"]
            assert payload["validate_entities"] is False
            assert payload["validate_safety"] is False

    @pytest.mark.asyncio
    async def test_validate_yaml_with_context(self, client, valid_yaml, validation_response):
        """Test YAML validation with context."""
        with patch.object(client.client, 'post') as mock_post:
            mock_response = MockResponse(200, validation_response)
            # httpx.AsyncClient.post() returns Response directly when awaited
            mock_post.return_value = mock_response
            
            context = {
                "entities": ["light.kitchen"],
                "conversation_history": []
            }
            
            result = await client.validate_yaml(valid_yaml, context=context)
            
            assert result["valid"] is True
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["context"] == context

    @pytest.mark.asyncio
    async def test_validate_yaml_invalid_response(self, client, valid_yaml):
        """Test YAML validation with invalid response."""
        with patch.object(client.client, 'post') as mock_post:
            mock_response = MockResponse(200, {
                "valid": False,
                "errors": [{"stage": "syntax", "severity": "error", "message": "Invalid YAML"}],
                "warnings": [],
                "stages": {"syntax": False},
                "summary": "Validation failed"
            })
            # httpx.AsyncClient.post() returns Response directly when awaited
            mock_post.return_value = mock_response
            
            result = await client.validate_yaml(valid_yaml)
            
            assert result["valid"] is False
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_yaml_http_error(self, client, valid_yaml):
        """Test YAML validation with HTTP error."""
        with patch.object(client.client, 'post') as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=MagicMock(status_code=500)
            )
            
            with pytest.raises(Exception) as exc_info:
                await client.validate_yaml(valid_yaml)
            
            assert "AI Automation Service" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_yaml_connection_error(self, client, valid_yaml):
        """Test YAML validation with connection error."""
        with patch.object(client.client, 'post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(Exception) as exc_info:
                await client.validate_yaml(valid_yaml)
            
            assert "Could not connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_yaml_timeout(self, client, valid_yaml):
        """Test YAML validation with timeout."""
        with patch.object(client.client, 'post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            
            with pytest.raises(Exception) as exc_info:
                await client.validate_yaml(valid_yaml)
            
            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_yaml_with_fixed_yaml(self, client, valid_yaml):
        """Test YAML validation that returns fixed YAML."""
        validation_response_with_fix = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stages": {"syntax": True, "structure": True},
            "fixed_yaml": "alias: Test Automation\nfixed: true",
            "summary": "Validation passed with fixes"
        }
        
        with patch.object(client.client, 'post') as mock_post:
            mock_response = MockResponse(200, validation_response_with_fix)
            # httpx.AsyncClient.post() returns Response directly when awaited
            mock_post.return_value = mock_response
            
            result = await client.validate_yaml(valid_yaml)
            
            assert result["valid"] is True
            assert result["fixed_yaml"] is not None
            assert "fixed: true" in result["fixed_yaml"]

    @pytest.mark.asyncio
    async def test_close_client(self, client):
        """Test closing the client."""
        with patch.object(client.client, 'aclose') as mock_close:
            await client.close()
            mock_close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

