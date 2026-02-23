"""Resilience integration tests for blueprint-suggestion-service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient


# ---------------------------------------------------------------------------
# DataApiClient tests
# ---------------------------------------------------------------------------


def _make_client():
    """Create a DataApiClient without hitting real settings."""
    with patch("src.clients.data_api_client.settings") as mock_settings:
        mock_settings.data_api_url = "http://data-api:8006"
        from src.clients.data_api_client import DataApiClient
        return DataApiClient(base_url="http://data-api:8006", api_key="test-key")


class TestDataApiClientResilience:

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
    async def test_circuit_open_entities_returns_empty(self):
        client = _make_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_all_entities()
            assert result == []

    @pytest.mark.asyncio
    async def test_circuit_open_devices_returns_empty(self):
        client = _make_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_all_devices()
            assert result == []

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
            result = await client.get_all_entities()
            assert len(result) == 1
            assert result[0]["entity_id"] == "light.test"

    @pytest.mark.asyncio
    async def test_successful_devices_fetch(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"devices": [{"id": "abc123"}]}

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.get_all_devices()
            assert len(result) == 1
            assert result[0]["id"] == "abc123"


# ---------------------------------------------------------------------------
# GroupHealthCheck response format
# ---------------------------------------------------------------------------


class TestGroupHealthCheck:

    @pytest.mark.asyncio
    async def test_healthy_response_format(self):
        from homeiq_resilience import GroupHealthCheck
        health = GroupHealthCheck(
            group_name="automation-intelligence", version="1.0.0",
        )
        result = await health.to_dict()
        assert result["group"] == "automation-intelligence"
        assert result["version"] == "1.0.0"
        assert "status" in result
        assert "uptime_seconds" in result

    @pytest.mark.asyncio
    async def test_degraded_features_reported(self):
        from homeiq_resilience import GroupHealthCheck
        health = GroupHealthCheck(
            group_name="automation-intelligence", version="1.0.0",
        )
        health.add_degraded_feature("blueprint-matching")
        result = await health.to_dict()
        assert "blueprint-matching" in result.get("degraded_features", [])
