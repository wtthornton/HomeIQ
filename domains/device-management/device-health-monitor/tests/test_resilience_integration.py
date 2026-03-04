"""Resilience integration tests for device-health-monitor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeiq_resilience import CircuitOpenError, CrossGroupClient

# ---------------------------------------------------------------------------
# DataAPIClient
# ---------------------------------------------------------------------------


def _make_data_client():
    from src.clients.data_api_client import DataAPIClient
    return DataAPIClient(base_url="http://data-api:8006")


class TestDataAPIClientResilience:

    def test_uses_cross_group_client(self):
        client = _make_data_client()
        assert hasattr(client, "_cross_client")
        assert isinstance(client._cross_client, CrossGroupClient)
        assert client._cross_client._group_name == "core-platform"

    def test_shared_circuit_breaker(self):
        c1 = _make_data_client()
        c2 = _make_data_client()
        assert c1._cross_client._breaker is c2._cross_client._breaker

    @pytest.mark.asyncio
    async def test_circuit_open_entities_returns_empty(self):
        client = _make_data_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.fetch_entities()
            assert result == []

    @pytest.mark.asyncio
    async def test_circuit_open_devices_returns_empty(self):
        client = _make_data_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_devices()
            assert result == []

    @pytest.mark.asyncio
    async def test_successful_entities_fetch(self):
        client = _make_data_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"entities": [{"entity_id": "sensor.temp"}]}

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.fetch_entities()
            assert len(result) == 1
            assert result[0]["entity_id"] == "sensor.temp"

    @pytest.mark.asyncio
    async def test_successful_devices_fetch(self):
        client = _make_data_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"devices": [{"id": "abc123"}]}

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.get_devices()
            assert len(result) == 1
            assert result[0]["id"] == "abc123"


# ---------------------------------------------------------------------------
# DeviceIntelligenceClient
# ---------------------------------------------------------------------------


def _make_intel_client():
    from src.clients.device_intelligence_client import DeviceIntelligenceClient
    return DeviceIntelligenceClient(base_url="http://device-intelligence:8023")


class TestDeviceIntelligenceClientResilience:

    def test_uses_cross_group_client(self):
        client = _make_intel_client()
        assert isinstance(client._cross_client, CrossGroupClient)
        assert client._cross_client._group_name == "ml-engine"

    def test_shared_circuit_breaker(self):
        c1 = _make_intel_client()
        c2 = _make_intel_client()
        assert c1._cross_client._breaker is c2._cross_client._breaker

    @pytest.mark.asyncio
    async def test_circuit_open_capabilities_returns_none(self):
        client = _make_intel_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_device_capabilities("device-1")
            assert result is None

    @pytest.mark.asyncio
    async def test_circuit_open_type_returns_none(self):
        client = _make_intel_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_device_type("device-1")
            assert result is None

    @pytest.mark.asyncio
    async def test_successful_capabilities_fetch(self):
        client = _make_intel_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "device_id": "device-1",
            "capabilities": ["dimming", "color_temp"],
        }

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.get_device_capabilities("device-1")
            assert result["device_id"] == "device-1"

    @pytest.mark.asyncio
    async def test_404_capabilities_returns_none(self):
        client = _make_intel_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.get_device_capabilities("unknown-device")
            assert result is None


# ---------------------------------------------------------------------------
# GroupHealthCheck
# ---------------------------------------------------------------------------


class TestGroupHealthCheck:

    @pytest.mark.asyncio
    async def test_healthy_response_format(self):
        from homeiq_resilience import GroupHealthCheck
        health = GroupHealthCheck(
            group_name="device-management", version="1.0.0",
        )
        result = await health.to_dict()
        assert result["group"] == "device-management"
        assert result["version"] == "1.0.0"
        assert "status" in result
        assert "uptime_seconds" in result
