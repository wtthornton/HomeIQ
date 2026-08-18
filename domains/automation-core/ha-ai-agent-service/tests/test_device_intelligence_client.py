"""Tests for Device Intelligence Client"""

from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from src.clients.device_intelligence_client import DeviceIntelligenceClient


@pytest.fixture
def device_intelligence_client():
    """Create DeviceIntelligenceClient instance"""
    return DeviceIntelligenceClient(base_url="http://test-device-intel:8028", enabled=True)


@pytest.mark.asyncio
async def test_get_device_capabilities_success(device_intelligence_client):
    """Test successfully fetching device capabilities"""
    mock_capabilities = [
        {"capability_name": "brightness", "capability_type": "numeric", "properties": {"min": 0, "max": 255}}
    ]

    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_response = Mock()
        mock_response.json.return_value = mock_capabilities
        mock_response.raise_for_status = Mock()
        mock_response.status_code = 200
        mock_call.return_value = mock_response

        capabilities = await device_intelligence_client.get_device_capabilities("device1")

        assert len(capabilities) == 1
        assert capabilities[0]["capability_name"] == "brightness"
        mock_call.assert_called_once_with("GET", "/api/devices/device1/capabilities", headers={})


@pytest.mark.asyncio
async def test_get_device_capabilities_404(device_intelligence_client):
    """Test handling 404 for device not found"""
    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", request=Mock(), response=Mock())
        mock_response.status_code = 404
        mock_call.return_value = mock_response

        capabilities = await device_intelligence_client.get_device_capabilities("device1")

        # Should return empty list for 404
        assert capabilities == []


@pytest.mark.asyncio
async def test_get_device_capabilities_non_list_response(device_intelligence_client):
    """Test handling non-list response"""
    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid format"}
        mock_response.raise_for_status = MagicMock()
        mock_call.return_value = mock_response

        capabilities = await device_intelligence_client.get_device_capabilities("device1")

        # Should return empty list for non-list response
        assert capabilities == []


@pytest.mark.asyncio
async def test_get_devices_success(device_intelligence_client):
    """Test successfully fetching devices"""
    mock_devices = [
        {"device_id": "device1", "manufacturer": "Philips", "model": "Hue"},
        {"device_id": "device2", "manufacturer": "WLED", "model": "Strip"},
    ]

    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_response = Mock()
        mock_response.json.return_value = mock_devices
        mock_response.raise_for_status = Mock()
        mock_response.status_code = 200
        mock_call.return_value = mock_response

        devices = await device_intelligence_client.get_devices(limit=100)

        assert len(devices) == 2
        assert devices[0]["device_id"] == "device1"
        # Verify params were passed
        call_args = mock_call.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["limit"] == 100


@pytest.mark.asyncio
async def test_get_devices_dict_response(device_intelligence_client):
    """Test handling dict response with 'devices' key"""
    mock_response_data = {"devices": [{"device_id": "device1", "manufacturer": "Philips"}]}

    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        mock_response.status_code = 200
        mock_call.return_value = mock_response

        devices = await device_intelligence_client.get_devices()

        assert len(devices) == 1
        assert devices[0]["device_id"] == "device1"


@pytest.mark.asyncio
async def test_get_devices_http_error(device_intelligence_client):
    """Test handling HTTP errors"""
    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_response = Mock()
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=mock_error_response
        )
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_call.return_value = mock_response

        with pytest.raises(Exception, match="Device Intelligence API returned"):
            await device_intelligence_client.get_devices()


@pytest.mark.asyncio
async def test_get_devices_connection_error(device_intelligence_client):
    """Test handling connection errors"""
    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_call.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(Exception, match="Error fetching devices from Device Intelligence"):
            await device_intelligence_client.get_devices()


@pytest.mark.asyncio
async def test_get_devices_timeout(device_intelligence_client):
    """Test handling timeout errors"""
    with patch.object(device_intelligence_client._cross_client, "call") as mock_call:
        mock_call.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(Exception, match="timed out"):
            await device_intelligence_client.get_devices()


@pytest.mark.asyncio
async def test_close(device_intelligence_client):
    """Test closing client"""
    # close() is a no-op: CrossGroupClient opens a client per request, so
    # there is no persistent transport to close. Assert it stays awaitable
    # and side-effect free.
    await device_intelligence_client.close()

    assert device_intelligence_client._cross_client is not None
