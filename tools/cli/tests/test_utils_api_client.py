"""Tests for API client utilities."""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from src.utils.api_client import APIClient
from src.utils.config import CLIConfig

class TestAPIClient:
    """Test APIClient class."""
    
    def test_init(self):
        """Test API client initialization."""
        config = CLIConfig(
            api_url="http://test:8000",
            api_token="test-token",
            timeout=60
        )
        
        client = APIClient(config)
        
        assert client.config == config
        assert client.client.base_url == "http://test:8000"
        assert client.client.timeout == 60
        assert "Authorization" in client.client.headers
        assert client.client.headers["Authorization"] == "Bearer test-token"
    
    def test_init_no_token(self):
        """Test API client initialization without token."""
        config = CLIConfig(api_url="http://test:8000")
        
        client = APIClient(config)
        
        assert "Authorization" not in client.client.headers
    
    def test_get_headers(self):
        """Test getting HTTP headers."""
        config = CLIConfig(
            api_url="http://test:8000",
            api_token="test-token"
        )
        
        client = APIClient(config)
        headers = client._get_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "homeiq-cli/1.0.0"
        assert headers["Authorization"] == "Bearer test-token"
    
    def test_get_headers_no_token(self):
        """Test getting HTTP headers without token."""
        config = CLIConfig(api_url="http://test:8000")
        
        client = APIClient(config)
        headers = client._get_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "homeiq-cli/1.0.0"
        assert "Authorization" not in headers
    
    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test successful API request."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        
        client.client.request = AsyncMock(return_value=mock_response)
        
        result = await client._make_request("GET", "/test")
        
        assert result == {"status": "success"}
        client.client.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_make_request_with_params(self):
        """Test API request with parameters."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        
        client.client.request = AsyncMock(return_value=mock_response)
        
        params = {"limit": 10, "offset": 0}
        data = {"key": "value"}
        
        await client._make_request("POST", "/test", params=params, data=data)
        
        call_args = client.client.request.call_args
        assert call_args[1]["params"] == params
        assert call_args[1]["json"] == data
    
    @pytest.mark.asyncio
    async def test_get_health(self):
        """Test get health endpoint."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"overall_status": "healthy"}
        mock_response.raise_for_status.return_value = None
        
        client.client.request = AsyncMock(return_value=mock_response)
        
        result = await client.get_health()
        
        assert result == {"overall_status": "healthy"}
        client.client.request.assert_called_once_with(
            method="GET",
            url="/api/v1/health",
            params=None,
            json=None
        )
    
    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test get statistics endpoint."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"total_events": 1000}
        mock_response.raise_for_status.return_value = None
        
        client.client.request = AsyncMock(return_value=mock_response)
        
        result = await client.get_statistics()
        
        assert result == {"total_events": 1000}
        client.client.request.assert_called_once_with(
            method="GET",
            url="/api/v1/stats",
            params=None,
            json=None
        )
    
    @pytest.mark.asyncio
    async def test_get_recent_events(self):
        """Test get recent events endpoint."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"events": []}
        mock_response.raise_for_status.return_value = None
        
        client.client.request = AsyncMock(return_value=mock_response)
        
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        result = await client.get_recent_events(
            limit=50,
            entity_id="sensor.temperature",
            event_type="state_changed",
            start_time=start_time,
            end_time=end_time
        )
        
        assert result == {"events": []}
        
        call_args = client.client.request.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 50
        assert params["entity_id"] == "sensor.temperature"
        assert params["event_type"] == "state_changed"
        assert params["start_time"] == "2024-01-01T12:00:00"
        assert params["end_time"] == "2024-01-01T13:00:00"
    
    @pytest.mark.asyncio
    async def test_export_events(self):
        """Test export events endpoint."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.content = b'{"events": []}'
        mock_response.raise_for_status.return_value = None
        
        client.client.get = AsyncMock(return_value=mock_response)
        
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)
        
        result = await client.export_events(
            format="json",
            entity_id="sensor.temperature",
            start_time=start_time,
            end_time=end_time
        )
        
        assert result == b'{"events": []}'
        
        call_args = client.client.get.call_args
        assert call_args[0][0] == "/api/v1/events/export"
        params = call_args[1]["params"]
        assert params["format"] == "json"
        assert params["entity_id"] == "sensor.temperature"
        assert params["start_time"] == "2024-01-01T12:00:00"
        assert params["end_time"] == "2024-01-01T13:00:00"
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status.return_value = None
        
        client.client.request = AsyncMock(return_value=mock_response)
        
        result = await client.test_connection()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test failed connection test."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client to raise an exception
        client.client.request = AsyncMock(side_effect=Exception("Connection failed"))
        
        result = await client.test_connection()
        
        assert result is False
    
    def test_format_output_table(self):
        """Test formatting output as table."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        data = {"key1": "value1", "key2": "value2"}
        
        # Mock console to capture output
        with patch.object(client.console, 'print') as mock_print:
            client.format_output(data, "table")
            mock_print.assert_called_once()
    
    def test_format_output_json(self):
        """Test formatting output as JSON."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        data = {"key1": "value1", "key2": "value2"}
        
        # Mock console to capture output
        with patch.object(client.console, 'print') as mock_print:
            client.format_output(data, "json")
            mock_print.assert_called_once()
    
    def test_format_output_yaml(self):
        """Test formatting output as YAML."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        data = {"key1": "value1", "key2": "value2"}
        
        # Mock console to capture output
        with patch.object(client.console, 'print') as mock_print:
            client.format_output(data, "yaml")
            mock_print.assert_called_once()
    
    def test_format_table_events(self):
        """Test formatting events table."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        data = {
            "events": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "entity_id": "sensor.temperature",
                    "event_type": "state_changed",
                    "state": "20.5"
                }
            ]
        }
        
        # Mock console to capture output
        with patch.object(client.console, 'print') as mock_print:
            client._format_table(data)
            mock_print.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing the API client."""
        config = CLIConfig(api_url="http://test:8000")
        client = APIClient(config)
        
        # Mock the HTTP client
        client.client.aclose = AsyncMock()
        
        await client.close()
        
        client.client.aclose.assert_called_once()
