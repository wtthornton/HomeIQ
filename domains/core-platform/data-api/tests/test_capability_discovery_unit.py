"""Unit tests for CapabilityDiscoveryService — Story 85.3

Tests capability discovery and formatting with mocked discoverer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.capability_discovery import (
    CapabilityDiscoveryService,
    get_capability_service,
)


class TestDiscoverDeviceCapabilities:

    def setup_method(self):
        self.svc = CapabilityDiscoveryService()

    @pytest.mark.asyncio
    async def test_no_discoverer_returns_empty(self):
        """When HACapabilityDiscoverer import fails, returns empty."""
        result = await self.svc.discover_device_capabilities("d1", ["light.kitchen"])
        assert result == {"capabilities": [], "features": {}}

    @pytest.mark.asyncio
    async def test_delegates_to_discoverer(self):
        mock_discoverer = MagicMock()
        mock_discoverer.discover_capabilities = AsyncMock(
            return_value={"capabilities": ["brightness", "color"], "features": {"dimming": True}}
        )
        self.svc._discoverer = mock_discoverer

        result = await self.svc.discover_device_capabilities("d1", ["light.kitchen"])
        assert result["capabilities"] == ["brightness", "color"]
        assert result["features"]["dimming"] is True

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        mock_discoverer = MagicMock()
        mock_discoverer.discover_capabilities = AsyncMock(side_effect=Exception("fail"))
        self.svc._discoverer = mock_discoverer

        result = await self.svc.discover_device_capabilities("d1", ["light.kitchen"])
        assert result == {"capabilities": [], "features": {}}


class TestFormatCapabilitiesForStorage:

    def setup_method(self):
        self.svc = CapabilityDiscoveryService()

    def test_none_input_returns_none(self):
        assert self.svc.format_capabilities_for_storage(None) is None

    def test_empty_dict_returns_none(self):
        assert self.svc.format_capabilities_for_storage({}) is None

    def test_valid_dict_returns_json_string(self):
        data = {"capabilities": ["brightness"]}
        result = self.svc.format_capabilities_for_storage(data)
        assert '"brightness"' in result

    def test_non_serializable_returns_none(self):
        data = {"bad": object()}
        result = self.svc.format_capabilities_for_storage(data)
        assert result is None


class TestSingleton:

    def test_returns_same_instance(self):
        import src.services.capability_discovery as mod
        mod._capability_service = None
        assert get_capability_service() is get_capability_service()
