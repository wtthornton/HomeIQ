"""Tests for Data API Client"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from src.clients.data_api_client import DataAPIClient


@pytest.fixture
def data_api_client():
    """Create DataAPIClient instance"""
    return DataAPIClient(base_url="http://test-data-api:8006")


@pytest.mark.asyncio
async def test_fetch_entities_success(data_api_client):
    """Test successfully fetching entities"""
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office"},
        {"entity_id": "sensor.temp_1", "domain": "sensor", "area_id": "kitchen"},
    ]

    with patch.object(data_api_client.client, "get") as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_entities
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        entities = await data_api_client.fetch_entities()

        assert len(entities) == 2
        assert entities[0]["entity_id"] == "light.office_1"
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_entities_with_filters(data_api_client):
    """Test fetching entities with filters"""
    mock_entities = [{"entity_id": "light.office_1", "domain": "light"}]

    with patch.object(data_api_client.client, "get") as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_entities
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        entities = await data_api_client.fetch_entities(
            domain="light",
            area_id="office",
            limit=100
        )

        # Verify params were passed
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["domain"] == "light"
        assert call_args.kwargs["params"]["area_id"] == "office"


@pytest.mark.asyncio
async def test_fetch_entities_dict_response(data_api_client):
    """Test handling dict response with 'entities' key"""
    mock_response_data = {
        "entities": [
            {"entity_id": "light.office_1", "domain": "light"}
        ]
    }

    with patch.object(data_api_client.client, "get") as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        entities = await data_api_client.fetch_entities()

        assert len(entities) == 1
        assert entities[0]["entity_id"] == "light.office_1"


@pytest.mark.asyncio
async def test_fetch_entities_http_error(data_api_client):
    """Test handling HTTP errors"""
    with patch.object(data_api_client.client, "get") as mock_get:
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=AsyncMock(), response=AsyncMock()
        )
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Data API returned"):
            await data_api_client.fetch_entities()


@pytest.mark.asyncio
async def test_fetch_entities_connection_error(data_api_client):
    """Test handling connection errors"""
    with patch.object(data_api_client.client, "get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(Exception, match="Could not connect"):
            await data_api_client.fetch_entities()


@pytest.mark.asyncio
async def test_fetch_entities_timeout(data_api_client):
    """Test handling timeout errors"""
    with patch.object(data_api_client.client, "get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(Exception, match="timed out"):
            await data_api_client.fetch_entities()


@pytest.mark.asyncio
async def test_close(data_api_client):
    """Test closing client"""
    data_api_client.client.aclose = AsyncMock()

    await data_api_client.close()

    data_api_client.client.aclose.assert_called_once()

