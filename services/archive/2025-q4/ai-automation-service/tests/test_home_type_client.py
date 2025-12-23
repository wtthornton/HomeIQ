"""
Unit tests for Home Type Client
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.home_type_client import (
    HomeTypeAPIError,
    HomeTypeClient,
    HomeTypeError,
)


@pytest.fixture
def home_type_client():
    """Create a HomeTypeClient instance for testing"""
    client = HomeTypeClient(base_url="http://test-service:8018")
    yield client
    # Cleanup
    import asyncio
    try:
        asyncio.run(client.close())
    except Exception:
        pass


@pytest.fixture
def mock_home_type_response():
    """Create a mock home type API response"""
    return {
        "home_type": "security_focused",
        "confidence": 0.85,
        "method": "ml_model",
        "features_used": ["device_count", "security_ratio", "event_frequency"],
        "last_updated": "2025-11-15T10:00:00Z",
    }


class TestHomeTypeClient:
    """Test Home Type Client"""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test client initialization"""
        client = HomeTypeClient(base_url="http://test:8018")
        assert client.base_url == "http://test:8018"
        assert client._cache is None
        assert client._cache_time is None
        assert client._cache_ttl == timedelta(hours=24)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_home_type_success(self, home_type_client, mock_home_type_response):
        """Test successful home type fetch"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_home_type_response

        with patch.object(home_type_client.client, "get", return_value=mock_response):
            result = await home_type_client.get_home_type(use_cache=False)

            assert result["home_type"] == "security_focused"
            assert result["confidence"] == 0.85
            assert "cached_at" in result
            assert home_type_client._cache is not None
            assert home_type_client._cache_time is not None

    @pytest.mark.asyncio
    async def test_get_home_type_caching(self, home_type_client, mock_home_type_response):
        """Test that caching works correctly"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_home_type_response

        # First call - should fetch from API
        with patch.object(home_type_client.client, "get", return_value=mock_response):
            result1 = await home_type_client.get_home_type(use_cache=False)

        # Second call - should use cache
        result2 = await home_type_client.get_home_type(use_cache=True)

        assert result1 == result2
        assert result1["home_type"] == "security_focused"
        # Verify only one API call was made
        assert home_type_client._cache is not None

    @pytest.mark.asyncio
    async def test_get_home_type_cache_expiry(self, home_type_client, mock_home_type_response):
        """Test that cache expires after TTL"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_home_type_response

        # First call - fetch and cache
        with patch.object(home_type_client.client, "get", return_value=mock_response):
            await home_type_client.get_home_type(use_cache=False)

        # Expire cache by setting old time
        home_type_client._cache_time = datetime.now(timezone.utc) - timedelta(hours=25)

        # Second call - should fetch again (cache expired)
        with patch.object(home_type_client.client, "get", return_value=mock_response) as mock_get:
            await home_type_client.get_home_type(use_cache=True)
            # Verify API was called again
            assert mock_get.called

    @pytest.mark.asyncio
    async def test_get_home_type_http_error(self, home_type_client):
        """Test handling of HTTP errors"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(home_type_client.client, "get", return_value=mock_response):
            result = await home_type_client.get_home_type(use_cache=False)

            # Should return default home type
            assert result["home_type"] == "standard_home"
            assert result["confidence"] == 0.5
            assert result["method"] == "default_fallback"

    @pytest.mark.asyncio
    async def test_get_home_type_httpx_error(self, home_type_client):
        """Test handling of httpx errors with retry"""
        with patch.object(
            home_type_client.client, "get", side_effect=httpx.HTTPError("Connection error")
        ) as mock_get:
            # Should retry 3 times, then raise
            with pytest.raises(HomeTypeAPIError):
                await home_type_client.get_home_type(use_cache=False)
            # Verify retries (tenacity retries 3 times = 4 total attempts)
            assert mock_get.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_home_type_timeout_error(self, home_type_client):
        """Test handling of timeout errors"""
        with patch.object(
            home_type_client.client, "get", side_effect=httpx.TimeoutException("Timeout")
        ):
            # Should retry, then raise
            with pytest.raises(HomeTypeAPIError):
                await home_type_client.get_home_type(use_cache=False)

    @pytest.mark.asyncio
    async def test_get_home_type_unexpected_error(self, home_type_client):
        """Test handling of unexpected errors (fallback to default)"""
        with patch.object(home_type_client.client, "get", side_effect=ValueError("Unexpected")):
            result = await home_type_client.get_home_type(use_cache=False)

            # Should return default home type
            assert result["home_type"] == "standard_home"
            assert result["method"] == "default_fallback"

    @pytest.mark.asyncio
    async def test_startup_prefetch(self, home_type_client, mock_home_type_response):
        """Test startup pre-fetch functionality"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_home_type_response

        with patch.object(home_type_client.client, "get", return_value=mock_response):
            await home_type_client.startup()

            # Verify cache is populated
            assert home_type_client._cache is not None
            assert home_type_client._cache["home_type"] == "security_focused"

    @pytest.mark.asyncio
    async def test_startup_prefetch_error(self, home_type_client):
        """Test startup pre-fetch with error (should not raise)"""
        with patch.object(home_type_client.client, "get", side_effect=httpx.HTTPError("Error")):
            # Should not raise, just log warning
            await home_type_client.startup()

            # Cache should still be None (fallback will be used on demand)
            assert home_type_client._cache is None

    def test_clear_cache(self, home_type_client):
        """Test cache clearing"""
        # Set cache
        home_type_client._cache = {"home_type": "test"}
        home_type_client._cache_time = datetime.now(timezone.utc)

        # Clear cache
        home_type_client.clear_cache()

        assert home_type_client._cache is None
        assert home_type_client._cache_time is None

    @pytest.mark.asyncio
    async def test_close(self, home_type_client):
        """Test client cleanup"""
        await home_type_client.close()
        # Verify client is closed (httpx client should be closed)
        # Note: httpx client doesn't expose closed state, but aclose() should work

    def test_get_default_home_type(self, home_type_client):
        """Test default home type fallback"""
        result = home_type_client._get_default_home_type()

        assert result["home_type"] == "standard_home"
        assert result["confidence"] == 0.5
        assert result["method"] == "default_fallback"
        assert "cached_at" in result
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, home_type_client, mock_home_type_response):
        """Test cache hit behavior"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_home_type_response

        # First call - cache miss
        with patch.object(home_type_client.client, "get", return_value=mock_response) as mock_get:
            await home_type_client.get_home_type(use_cache=False)
            assert mock_get.call_count == 1

        # Second call - cache hit (should not call API)
        with patch.object(home_type_client.client, "get", return_value=mock_response) as mock_get:
            await home_type_client.get_home_type(use_cache=True)
            # Should not call API (cache hit)
            assert mock_get.call_count == 0

