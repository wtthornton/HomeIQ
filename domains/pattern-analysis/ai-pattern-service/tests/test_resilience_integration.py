"""Resilience integration tests for ai-pattern-service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from homeiq_resilience import CircuitOpenError, CrossGroupClient


def _make_client():
    """Create a DataAPIClient without hitting real settings."""
    from src.clients.data_api_client import DataAPIClient
    return DataAPIClient(base_url="http://data-api:8006")


class TestDataAPIClientResilience:

    def test_uses_cross_group_client(self):
        client = _make_client()
        assert hasattr(client, "_cross_client")
        assert isinstance(client._cross_client, CrossGroupClient)
        assert client._cross_client._group_name == "core-platform"

    def test_shared_circuit_breaker(self):
        c1 = _make_client()
        c2 = _make_client()
        assert c1._cross_client._breaker is c2._cross_client._breaker

    @pytest.mark.asyncio
    async def test_circuit_open_events_returns_empty_df(self):
        client = _make_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.fetch_events()
            assert isinstance(result, pd.DataFrame)
            assert result.empty

    @pytest.mark.asyncio
    async def test_circuit_open_devices_returns_empty(self):
        client = _make_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.fetch_devices()
            assert result == []

    @pytest.mark.asyncio
    async def test_circuit_open_entities_returns_empty(self):
        client = _make_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.fetch_entities()
            assert result == []

    @pytest.mark.asyncio
    async def test_circuit_open_get_returns_empty_dict(self):
        client = _make_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get("/api/test")
            assert result == {}

    @pytest.mark.asyncio
    async def test_successful_entities_fetch(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"entities": [{"entity_id": "light.test"}]}

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.fetch_entities()
            assert len(result) == 1
            assert result[0]["entity_id"] == "light.test"

    @pytest.mark.asyncio
    async def test_close_is_noop(self):
        client = _make_client()
        await client.close()  # Should not raise
