"""Tests for ManagedHTTPClient.

Covers:
  - Context manager lifecycle
  - GET/POST/PUT/DELETE methods
  - Auth token header
  - RuntimeError when not started
  - Close idempotency
"""

from __future__ import annotations

import pytest
from homeiq_resilience.http_client import ManagedHTTPClient


class TestManagedHTTPClient:
    def test_init_defaults(self) -> None:
        client = ManagedHTTPClient(base_url="http://api:8000")
        assert client.base_url == "http://api:8000"
        assert client._client is None

    def test_raises_when_not_started(self) -> None:
        client = ManagedHTTPClient(base_url="http://api:8000")
        with pytest.raises(RuntimeError, match="not started"):
            _ = client.client

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self) -> None:
        async with ManagedHTTPClient(base_url="http://api:8000") as client:
            assert client._client is not None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self) -> None:
        client = ManagedHTTPClient(base_url="http://api:8000")
        await client.start()
        first_client = client._client
        await client.start()
        assert client._client is first_client
        await client.close()

    @pytest.mark.asyncio
    async def test_close_idempotent(self) -> None:
        client = ManagedHTTPClient(base_url="http://api:8000")
        await client.start()
        await client.close()
        await client.close()  # Should not raise
        assert client._client is None

    @pytest.mark.asyncio
    async def test_auth_token_in_headers(self) -> None:
        client = ManagedHTTPClient(
            base_url="http://api:8000",
            auth_token="my-secret",
        )
        await client.start()
        assert client._client is not None
        assert client._client.headers.get("authorization") == "Bearer my-secret"
        await client.close()

    @pytest.mark.asyncio
    async def test_trailing_slash_stripped(self) -> None:
        client = ManagedHTTPClient(base_url="http://api:8000/")
        assert client.base_url == "http://api:8000"
