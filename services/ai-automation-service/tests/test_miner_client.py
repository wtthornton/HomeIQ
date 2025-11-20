"""
Unit Tests for MinerClient

Epic AI-4, Story AI4.2
"""
import pytest

pytest.skip(
    "Miner client module removed; skipping legacy AI automation tests",
    allow_module_level=True,
)

from unittest.mock import AsyncMock, patch

from src.miner.miner_client import MinerClient


@pytest.mark.asyncio
async def test_search_corpus_success():
    """Test successful Miner query"""
    client = MinerClient(base_url="http://test-miner:8019", timeout=0.1)

    mock_response = {
        'automations': [
            {
                'id': 1,
                'title': 'Test Automation',
                'devices': ['light'],
                'quality_score': 0.85
            }
        ],
        'count': 1
    }

    with patch('httpx.AsyncClient') as mock_httpx:
        mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=AsyncMock(
                raise_for_status=AsyncMock(),
                json=AsyncMock(return_value=mock_response)
            )
        )

        results = await client.search_corpus(device='light', min_quality=0.8)

        assert len(results) == 1
        assert results[0]['title'] == 'Test Automation'


@pytest.mark.asyncio
async def test_search_corpus_timeout():
    """Test Miner query timeout - graceful degradation"""
    client = MinerClient(timeout=0.001)  # 1ms timeout (will fail)

    with patch('httpx.AsyncClient') as mock_httpx:
        mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=TimeoutError("Timeout")
        )

        # Should return empty list on timeout
        results = await client.search_corpus(device='light')

        assert results == []


@pytest.mark.asyncio
async def test_search_corpus_http_error():
    """Test Miner query HTTP error - graceful degradation"""
    client = MinerClient()

    with patch('httpx.AsyncClient') as mock_httpx:
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=AsyncMock(),
            response=AsyncMock(status_code=500)
        )
        mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        # Should return empty list on HTTP error
        results = await client.search_corpus(device='light')

        assert results == []


@pytest.mark.asyncio
async def test_cache_hit():
    """Test cache returns cached results"""
    client = MinerClient(cache_ttl_days=7)

    # First query - cache miss
    mock_response = {'automations': [{'id': 1}], 'count': 1}

    with patch('httpx.AsyncClient') as mock_httpx:
        mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=AsyncMock(
                raise_for_status=AsyncMock(),
                json=AsyncMock(return_value=mock_response)
            )
        )

        results1 = await client.search_corpus(device='light')

        # Second query - should hit cache (no HTTP call)
        results2 = await client.search_corpus(device='light')

        assert results1 == results2
        assert len(results1) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

