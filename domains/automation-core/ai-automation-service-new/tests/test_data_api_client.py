"""
Unit tests for Data API Client

Epic 39, Story 39.12: Query & Automation Service Testing

Context7/pytest best practices:
- Use a single default constant to avoid scattering literals.
- Use a fixture to provide the base URL so the value is resolved at test time (not import).
- Override via monkeypatch.setenv("DATA_API_URL", "...") in tests, or set env in CI.
  (Monkeypatching env vars is the recommended way to simulate different env conditions.)
"""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.data_api_client import DataAPIClient

# Default base URL for Data API in tests (local dev port). Single literal in one place.
DEFAULT_DATA_API_BASE_URL = "http://localhost:8006"


@pytest.fixture
def data_api_base_url() -> str:
    """Base URL for Data API. Resolved at test time so monkeypatch.setenv can override."""
    return os.environ.get("DATA_API_URL", DEFAULT_DATA_API_BASE_URL)


class TestDataAPIClient:
    """Test suite for Data API client."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_init_default_url(self, data_api_base_url):
        """Test client initialization with default URL."""
        with patch("src.clients.data_api_client.settings") as mock_settings:
            mock_settings.data_api_url = data_api_base_url
            client = DataAPIClient()
            assert client.base_url == data_api_base_url
            assert client.client is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_init_custom_url(self):
        """Test client initialization with custom URL."""
        client = DataAPIClient(base_url="http://custom:9000")
        assert client.base_url == "http://custom:9000"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_init_strips_trailing_slash(self, data_api_base_url):
        """Test that trailing slash is stripped from base URL."""
        client = DataAPIClient(base_url=f"{data_api_base_url}/")
        assert client.base_url == data_api_base_url

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_success(self, data_api_base_url):
        """Test successful event fetching."""
        client = DataAPIClient(base_url=data_api_base_url)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {"entity_id": "light.office", "state": "on", "timestamp": "2025-01-01T00:00:00Z"},
                {"entity_id": "light.office", "state": "off", "timestamp": "2025-01-01T01:00:00Z"},
            ]
        }

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            events = await client.fetch_events(entity_id="light.office", days=7)

            assert len(events) == 2
            assert events[0]["entity_id"] == "light.office"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_with_filters(self, data_api_base_url):
        """Test event fetching with multiple filters."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.fetch_events(
                entity_id="light.office",
                device_id="device123",
                event_type="state_changed",
                limit=100,
            )

            # Verify query parameters were included
            call_args = mock_get.call_args
            assert "entity_id" in str(call_args)
            assert "device_id" in str(call_args)
            assert "event_type" in str(call_args)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_time_range(self, data_api_base_url):
        """Test event fetching with custom time range."""
        client = DataAPIClient(base_url=data_api_base_url)

        start_time = datetime(2025, 1, 1, tzinfo=UTC)
        end_time = datetime(2025, 1, 2, tzinfo=UTC)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.fetch_events(start_time=start_time, end_time=end_time)

            # Client uses limit param; time range not yet supported by data-api (see client docstring)
            call_args = mock_get.call_args
            assert call_args is not None
            assert call_args.kwargs.get("params", {}).get("limit") == 10000

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_default_time_range(self, data_api_base_url):
        """Test event fetching with default time range (30 days)."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.fetch_events()

            # Should use default 30 days
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_http_error(self, data_api_base_url):
        """Test event fetching handles HTTP errors."""
        client = DataAPIClient(base_url=data_api_base_url)

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")

            with pytest.raises(httpx.HTTPError):
                await client.fetch_events()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_timeout(self, data_api_base_url):
        """Test event fetching handles timeout errors."""
        client = DataAPIClient(base_url=data_api_base_url)

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await client.fetch_events()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_close(self, data_api_base_url):
        """Test client cleanup."""
        client = DataAPIClient(base_url=data_api_base_url)

        with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager(self, data_api_base_url):
        """Test client as context manager."""
        with patch("src.clients.data_api_client.settings") as mock_settings:
            mock_settings.data_api_url = data_api_base_url

            async with DataAPIClient() as client:
                assert client.base_url == data_api_base_url
                # Context manager should handle cleanup

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_devices_success(self, data_api_base_url):
        """Test successful device fetching."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "devices": [
                {"device_id": "device1", "name": "Office Light"},
                {"device_id": "device2", "name": "Kitchen Light"},
            ]
        }

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            devices = await client.fetch_devices()

            assert len(devices) == 2
            assert devices[0]["device_id"] == "device1"
            mock_get.assert_called_once_with(
                f"{data_api_base_url}/api/devices", params={"limit": 1000}, headers={}
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_entities_success(self, data_api_base_url):
        """Test successful entity fetching."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [
                {"entity_id": "light.office", "state": "on"},
                {"entity_id": "light.kitchen", "state": "off"},
            ]
        }

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            entities = await client.fetch_entities()

            assert len(entities) == 2
            assert entities[0]["entity_id"] == "light.office"
            mock_get.assert_called_once_with(
                f"{data_api_base_url}/api/entities", params={"limit": 1000}, headers={}
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_entity_by_id_found(self, data_api_base_url):
        """Test getting entity by ID when found."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entity_id": "light.office", "state": "on"}

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            entity = await client.get_entity_by_id("light.office")

            assert entity is not None
            assert entity["entity_id"] == "light.office"
            mock_get.assert_called_once_with(
                f"{data_api_base_url}/api/entities/light.office", headers={}
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_entity_by_id_not_found(self, data_api_base_url):
        """Test getting entity by ID when not found."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            entity = await client.get_entity_by_id("light.nonexistent")

            assert entity is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_check_success(self, data_api_base_url):
        """Test health check when service is healthy."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            is_healthy = await client.health_check()

            assert is_healthy is True
            mock_get.assert_called_once_with(
                f"{data_api_base_url}/health", headers={}, timeout=5.0
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_check_failure(self, data_api_base_url):
        """Test health check when service is unhealthy."""
        client = DataAPIClient(base_url=data_api_base_url)

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            is_healthy = await client.health_check()

            assert is_healthy is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_check_exception(self, data_api_base_url):
        """Test health check handles exceptions gracefully."""
        client = DataAPIClient(base_url=data_api_base_url)

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection error")

            is_healthy = await client.health_check()

            assert is_healthy is False
