"""Tests for Data API Client"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx  # noqa: F401 - used in test side_effect values
import pytest
from src.clients.data_api_client import DataAPIClient


@pytest.fixture
def data_api_client():
    """Create DataAPIClient instance"""
    return DataAPIClient(base_url="http://test-data-api:8006")


def _mock_response(json_data, status_code=200):
    """Helper to create a mock httpx.Response."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_fetch_entities_success(data_api_client):
    """Test successfully fetching entities"""
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office"},
        {"entity_id": "sensor.temp_1", "domain": "sensor", "area_id": "kitchen"},
    ]

    with patch.object(data_api_client._cross_client, "call", new_callable=AsyncMock, return_value=_mock_response(mock_entities)):
        entities = await data_api_client.fetch_entities()

        assert len(entities) == 2
        assert entities[0]["entity_id"] == "light.office_1"


@pytest.mark.asyncio
async def test_fetch_entities_with_filters(data_api_client):
    """Test fetching entities with filters"""
    mock_entities = [{"entity_id": "light.office_1", "domain": "light"}]

    with patch.object(data_api_client._cross_client, "call", new_callable=AsyncMock, return_value=_mock_response(mock_entities)) as mock_call:
        await data_api_client.fetch_entities(
            domain="light",
            area_id="office",
            limit=100
        )

        # Verify params were passed
        call_kwargs = mock_call.call_args[1]
        assert call_kwargs["params"]["domain"] == "light"
        assert call_kwargs["params"]["area_id"] == "office"


@pytest.mark.asyncio
async def test_fetch_entities_dict_response(data_api_client):
    """Test handling dict response with 'entities' key"""
    mock_response_data = {
        "entities": [
            {"entity_id": "light.office_1", "domain": "light"}
        ]
    }

    with patch.object(data_api_client._cross_client, "call", new_callable=AsyncMock, return_value=_mock_response(mock_response_data)):
        entities = await data_api_client.fetch_entities()

        assert len(entities) == 1
        assert entities[0]["entity_id"] == "light.office_1"


@pytest.mark.asyncio
async def test_fetch_entities_http_error(data_api_client):
    """Test handling HTTP errors"""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Error", request=MagicMock(), response=mock_resp
    )

    with (
        patch.object(data_api_client._cross_client, "call", new_callable=AsyncMock, return_value=mock_resp),
        pytest.raises(Exception, match="Data API returned"),
    ):
        await data_api_client.fetch_entities()


@pytest.mark.asyncio
async def test_fetch_entities_connection_error(data_api_client):
    """Test handling connection errors"""
    with (
        patch.object(data_api_client._cross_client, "call", new_callable=AsyncMock, side_effect=httpx.ConnectError("Connection failed")),
        pytest.raises(Exception, match="Error fetching entities"),
    ):
        await data_api_client.fetch_entities()


@pytest.mark.asyncio
async def test_fetch_entities_timeout(data_api_client):
    """Test handling timeout errors"""
    with (
        patch.object(data_api_client._cross_client, "call", new_callable=AsyncMock, side_effect=httpx.TimeoutException("Request timed out")),
        pytest.raises(Exception, match="Error fetching entities"),
    ):
        await data_api_client.fetch_entities()


@pytest.mark.asyncio
async def test_close(data_api_client):
    """Test closing client (no-op with CrossGroupClient)"""
    await data_api_client.close()  # Should not raise
