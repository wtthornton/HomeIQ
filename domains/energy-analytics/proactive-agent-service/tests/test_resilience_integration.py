"""Resilience integration tests for proactive-agent-service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient


# ---------------------------------------------------------------------------
# Shared breakers
# ---------------------------------------------------------------------------


class TestSharedBreakers:

    def test_core_platform_breaker_is_singleton(self):
        from src.clients.breakers import core_platform_breaker
        assert isinstance(core_platform_breaker, CircuitBreaker)
        assert core_platform_breaker.name == "core-platform"

    def test_data_collectors_breaker_is_singleton(self):
        from src.clients.breakers import data_collectors_breaker
        assert isinstance(data_collectors_breaker, CircuitBreaker)
        assert data_collectors_breaker.name == "data-collectors"


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

    def test_activity_client_has_short_timeout(self):
        client = _make_data_client()
        assert hasattr(client, "_activity_client")
        assert isinstance(client._activity_client, CrossGroupClient)

    def test_shared_circuit_breaker(self):
        c1 = _make_data_client()
        c2 = _make_data_client()
        assert c1._cross_client._breaker is c2._cross_client._breaker

    @pytest.mark.asyncio
    async def test_circuit_open_events_returns_empty(self):
        client = _make_data_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_events()
            assert result == []

    @pytest.mark.asyncio
    async def test_circuit_open_activity_returns_none(self):
        client = _make_data_client()
        with patch.object(
            client._activity_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_activity()
            assert result is None

    @pytest.mark.asyncio
    async def test_circuit_open_activity_history_returns_empty(self):
        client = _make_data_client()
        with patch.object(
            client._activity_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_activity_history()
            assert result == []

    @pytest.mark.asyncio
    async def test_successful_events_fetch(self):
        client = _make_data_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"events": [{"entity_id": "light.test"}]}

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.get_events()
            assert len(result) == 1
            assert result[0]["entity_id"] == "light.test"


# ---------------------------------------------------------------------------
# WeatherAPIClient
# ---------------------------------------------------------------------------


def _make_weather_client():
    from src.clients.weather_api_client import WeatherAPIClient
    return WeatherAPIClient(base_url="http://weather-api:8009")


class TestWeatherAPIClientResilience:

    def test_uses_cross_group_client(self):
        client = _make_weather_client()
        assert isinstance(client._cross_client, CrossGroupClient)
        assert client._cross_client._group_name == "data-collectors"

    def test_uses_data_collectors_breaker(self):
        from src.clients.breakers import data_collectors_breaker
        client = _make_weather_client()
        assert client._cross_client._breaker is data_collectors_breaker

    @pytest.mark.asyncio
    async def test_circuit_open_returns_none(self):
        client = _make_weather_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_current_weather()
            assert result is None

    @pytest.mark.asyncio
    async def test_successful_weather_fetch(self):
        client = _make_weather_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"temperature": 22, "condition": "sunny"}

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.get_current_weather()
            assert result["temperature"] == 22


# ---------------------------------------------------------------------------
# SportsDataClient
# ---------------------------------------------------------------------------


def _make_sports_client():
    from src.clients.sports_data_client import SportsDataClient
    return SportsDataClient(base_url="http://data-api:8006")


class TestSportsDataClientResilience:

    def test_uses_core_platform_breaker(self):
        from src.clients.breakers import core_platform_breaker
        client = _make_sports_client()
        assert client._cross_client._breaker is core_platform_breaker

    @pytest.mark.asyncio
    async def test_circuit_open_live_games_returns_empty(self):
        client = _make_sports_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_live_games()
            assert result == []

    @pytest.mark.asyncio
    async def test_circuit_open_upcoming_games_returns_empty(self):
        client = _make_sports_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_upcoming_games()
            assert result == []


# ---------------------------------------------------------------------------
# CarbonIntensityClient
# ---------------------------------------------------------------------------


def _make_carbon_client():
    from src.clients.carbon_intensity_client import CarbonIntensityClient
    return CarbonIntensityClient(data_api_url="http://data-api:8006")


class TestCarbonIntensityClientResilience:

    def test_uses_core_platform_breaker(self):
        from src.clients.breakers import core_platform_breaker
        client = _make_carbon_client()
        assert client._cross_client._breaker is core_platform_breaker

    @pytest.mark.asyncio
    async def test_circuit_open_intensity_returns_none(self):
        client = _make_carbon_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_current_intensity()
            assert result is None

    @pytest.mark.asyncio
    async def test_circuit_open_trends_returns_none(self):
        client = _make_carbon_client()
        with patch.object(
            client._cross_client, "call",
            side_effect=CircuitOpenError("circuit open"),
        ):
            result = await client.get_trends()
            assert result is None

    @pytest.mark.asyncio
    async def test_successful_intensity_fetch(self):
        client = _make_carbon_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "intensity": 150,
            "renewable_percentage": 40,
            "fossil_percentage": 60,
        }

        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock, return_value=mock_resp,
        ):
            result = await client.get_current_intensity()
            assert result["intensity"] == 150
            assert result["renewable_percentage"] == 40


# ---------------------------------------------------------------------------
# GroupHealthCheck
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
