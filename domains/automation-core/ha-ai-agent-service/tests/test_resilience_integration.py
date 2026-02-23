"""Tests for resilience module integration in HA AI Agent Service.

Validates that CrossGroupClient, CircuitBreaker, and GroupHealthCheck
are properly integrated into the service's HTTP clients and health endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.ai_automation_client import AIAutomationClient
from src.clients.data_api_client import DataAPIClient

from homeiq_resilience import CircuitBreaker, CircuitOpenError, GroupHealthCheck

# ---------------------------------------------------------------------------
# DataAPIClient + CrossGroupClient
# ---------------------------------------------------------------------------


class TestDataAPIClientResilience:
    """Verify DataAPIClient uses CrossGroupClient internally."""

    def test_uses_cross_group_client(self):
        client = DataAPIClient(base_url="http://data-api:8006", api_key="test-key")
        assert hasattr(client, "_cross_client")
        assert client._cross_client._group_name == "core-platform"
        assert client._cross_client._auth_token == "test-key"

    def test_shared_circuit_breaker(self):
        """Multiple DataAPIClient instances share the core-platform breaker."""
        c1 = DataAPIClient(base_url="http://data-api:8006")
        c2 = DataAPIClient(base_url="http://data-api:8006")
        assert c1._cross_client._breaker is c2._cross_client._breaker

    @pytest.mark.asyncio
    async def test_fetch_entities_calls_cross_client(self):
        client = DataAPIClient(base_url="http://data-api:8006")
        mock_response = MagicMock()
        mock_response.json.return_value = [{"entity_id": "light.test"}]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._cross_client, "call", new_callable=AsyncMock, return_value=mock_response) as mock_call:
            entities = await client.fetch_entities(domain="light")
            mock_call.assert_called_once()
            assert mock_call.call_args[0] == ("GET", "/api/entities")
            assert "params" in mock_call.call_args[1]
            assert entities == [{"entity_id": "light.test"}]

    @pytest.mark.asyncio
    async def test_circuit_open_raises_exception(self):
        client = DataAPIClient(base_url="http://data-api:8006")
        with (
            patch.object(client._cross_client, "call", new_callable=AsyncMock, side_effect=CircuitOpenError("circuit open")),
            pytest.raises(Exception, match="circuit breaker open"),
        ):
            await client.fetch_entities()

    @pytest.mark.asyncio
    async def test_close_is_noop(self):
        """close() should not raise — it's a no-op with CrossGroupClient."""
        client = DataAPIClient(base_url="http://data-api:8006")
        await client.close()  # Should not raise


# ---------------------------------------------------------------------------
# AIAutomationClient + CrossGroupClient
# ---------------------------------------------------------------------------


class TestAIAutomationClientResilience:
    """Verify AIAutomationClient uses CrossGroupClient with X-HomeIQ-API-Key."""

    def test_uses_cross_group_client(self):
        client = AIAutomationClient(base_url="http://ai-automation:8000", api_key="my-key")
        assert hasattr(client, "_cross_client")
        assert client._cross_client._group_name == "automation-intelligence"
        # Auth token NOT set (uses header kwarg instead)
        assert client._cross_client._auth_token is None
        assert client._auth_headers == {"X-HomeIQ-API-Key": "my-key"}

    @pytest.mark.asyncio
    async def test_validate_yaml_passes_auth_header(self):
        client = AIAutomationClient(base_url="http://ai-automation:8000", api_key="my-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._cross_client, "call", new_callable=AsyncMock, return_value=mock_response) as mock_call:
            result = await client.validate_yaml("alias: Test\ntrigger: []")
            assert result["valid"] is True
            # Verify X-HomeIQ-API-Key was passed
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs["headers"] == {"X-HomeIQ-API-Key": "my-key"}


# ---------------------------------------------------------------------------
# DeviceIntelligenceClient + CrossGroupClient (X-API-Key header)
# ---------------------------------------------------------------------------


class TestDeviceIntelligenceClientResilience:
    """Verify DeviceIntelligenceClient passes X-API-Key via headers kwarg."""

    def test_uses_cross_group_client(self):
        from src.clients.device_intelligence_client import DeviceIntelligenceClient

        client = DeviceIntelligenceClient(base_url="http://device-intel:8019")
        assert hasattr(client, "_cross_client")
        assert client._cross_client._group_name == "ml-engine"

    def test_x_api_key_header(self):
        from src.clients.device_intelligence_client import DeviceIntelligenceClient

        # Mock settings
        settings = MagicMock()
        settings.device_intelligence_url = "http://device-intel:8019"
        settings.device_intelligence_enabled = True
        api_key_mock = MagicMock()
        api_key_mock.get_secret_value.return_value = "secret-key"
        settings.device_intelligence_api_key = api_key_mock

        client = DeviceIntelligenceClient(settings=settings)
        assert client._auth_headers == {"X-API-Key": "secret-key"}

    @pytest.mark.asyncio
    async def test_circuit_open_returns_empty(self):
        """When circuit is open, graceful degradation returns empty list."""
        from src.clients.device_intelligence_client import DeviceIntelligenceClient

        client = DeviceIntelligenceClient(base_url="http://device-intel:8019")
        with patch.object(
            client._cross_client, "call",
            new_callable=AsyncMock,
            side_effect=CircuitOpenError("circuit open"),
        ):
            devices = await client.get_devices()
            assert devices == []


# ---------------------------------------------------------------------------
# GroupHealthCheck integration
# ---------------------------------------------------------------------------


class TestGroupHealthCheck:
    """Verify GroupHealthCheck produces expected response format."""

    @pytest.mark.asyncio
    async def test_healthy_response_format(self):
        health = GroupHealthCheck(group_name="automation-intelligence", version="1.0.0")
        # No dependencies registered — should be healthy
        result = await health.to_dict()
        assert result["group"] == "automation-intelligence"
        assert result["version"] == "1.0.0"
        assert result["status"] == "healthy"
        assert "uptime_seconds" in result
        assert "dependencies" in result

    @pytest.mark.asyncio
    async def test_degraded_features_reported(self):
        health = GroupHealthCheck(group_name="automation-intelligence", version="1.0.0")
        health.add_degraded_feature("entity-resolution")
        result = await health.to_dict()
        assert "entity-resolution" in result["degraded_features"]

    @pytest.mark.asyncio
    async def test_unhealthy_dependency(self):
        health = GroupHealthCheck(group_name="test-group", version="0.1.0")
        # Register a dependency at an unreachable URL
        health.register_dependency("fake-service", "http://localhost:1")
        result = await health.to_dict()
        assert result["dependencies"]["fake-service"]["status"] == "unreachable"


# ---------------------------------------------------------------------------
# Circuit breaker state transitions
# ---------------------------------------------------------------------------


class TestCircuitBreakerIntegration:
    """Verify circuit breaker opens after threshold failures."""

    @pytest.mark.asyncio
    async def test_opens_after_failures(self):
        breaker = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=60)
        for _ in range(3):
            await breaker.record_failure()
        assert not breaker.allow_request()

    @pytest.mark.asyncio
    async def test_success_resets(self):
        breaker = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=60)
        await breaker.record_failure()
        await breaker.record_failure()
        await breaker.record_success()
        # Still below threshold after reset
        assert breaker.allow_request()
