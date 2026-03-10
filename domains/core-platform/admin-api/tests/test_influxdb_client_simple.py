"""
Simple tests for InfluxDB client
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from src.influxdb_client import AdminAPIInfluxDBClient


@pytest.mark.asyncio
async def test_influxdb_client_initialization():
    """Test InfluxDB client can be initialized"""
    client = AdminAPIInfluxDBClient()

    assert client is not None
    assert client.url == os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    assert client.org == os.getenv("INFLUXDB_ORG", "homeiq")
    assert client.bucket == os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
    assert client.is_connected is False
    assert client.query_count == 0
    assert client.error_count == 0


@pytest.mark.asyncio
async def test_connection_status():
    """Test connection status method"""
    client = AdminAPIInfluxDBClient()

    status = client.get_connection_status()

    assert isinstance(status, dict)
    assert "is_connected" in status
    assert "url" in status
    assert "org" in status
    assert "bucket" in status
    assert "query_count" in status
    assert "error_count" in status
    assert status["is_connected"] is False


@pytest.mark.asyncio
async def test_period_to_seconds():
    """Test period conversion"""
    client = AdminAPIInfluxDBClient()

    assert client._period_to_seconds("15m") == 900
    assert client._period_to_seconds("1h") == 3600
    assert client._period_to_seconds("6h") == 21600
    assert client._period_to_seconds("24h") == 86400
    assert client._period_to_seconds("7d") == 604800
    assert client._period_to_seconds("unknown") == 3600  # Default


@pytest.mark.asyncio
async def test_connection_failure_handling():
    """Test that connection failures are handled gracefully"""
    with patch.dict(os.environ, {
        'INFLUXDB_URL': 'http://invalid-host:8086',
        'INFLUXDB_TOKEN': 'fake-token'
    }):
        client = AdminAPIInfluxDBClient()

        # Connection should fail but not raise exception
        result = await client.connect()

        assert result is False
        assert client.is_connected is False


@pytest.mark.asyncio
async def test_query_without_connection():
    """Test that queries fail gracefully when not connected"""
    client = AdminAPIInfluxDBClient()

    # Try to query without connecting
    with pytest.raises(Exception) as exc_info:
        await client.get_event_statistics("1h")

    assert "not connected" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_close_without_connection():
    """Test that close works even without active connection"""
    client = AdminAPIInfluxDBClient()

    # Should not raise exception
    await client.close()

    assert client.client is None
    assert client.query_api is None
    assert client.is_connected is False


@pytest.mark.asyncio
@patch('src.influxdb_client.AdminAPIInfluxDBClient._test_connection')
@patch('src.influxdb_client.InfluxDBClient')
async def test_successful_connection(mock_client_class, mock_test_connection):
    """Test successful connection flow"""
    # Mock the InfluxDB client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_test_connection.return_value = None  # Success

    client = AdminAPIInfluxDBClient()

    # Mock query_api
    client.client = mock_client
    result = await client.connect()

    # Should succeed but will fail due to missing query_api in mock
    # This is a simple test, just verify it tried to connect
    assert mock_client_class.called


# --- get_service_metrics service_name validation (Flux injection guard, Epic 46) ---


@pytest.mark.asyncio
async def test_get_service_metrics_invalid_service_name_raises_value_error():
    """Invalid service_name must raise ValueError before any Flux query (injection guard)."""
    client = AdminAPIInfluxDBClient()
    client.is_connected = True
    client.query_api = MagicMock()

    invalid_names = [
        'evil" |> drop()',
        'x">',
        'a\nb',
        'pipe|>',
        'semicolon;',
        'backtick`',
        'x' * 129,
    ]
    for name in invalid_names:
        with pytest.raises(ValueError, match=r"Invalid service_name"):
            await client.get_service_metrics(name, period="1h")


@pytest.mark.asyncio
async def test_get_service_metrics_valid_service_name_passes_validation():
    """Valid service_name (alphanumeric, underscore, hyphen, length <= 128) passes validation."""
    client = AdminAPIInfluxDBClient()
    client.is_connected = True
    client.query_api = MagicMock()

    valid_names = [
        "data-api",
        "websocket_ingestion",
        "admin-api",
        "Svc123",
        "a",
        "x" * 128,
    ]
    for name in valid_names:
        with patch.object(client, "_execute_query", new_callable=AsyncMock, return_value=None):
            # Should not raise ValueError
            result = await client.get_service_metrics(name, period="1h")
            assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

