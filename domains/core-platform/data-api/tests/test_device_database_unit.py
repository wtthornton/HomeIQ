"""Unit tests for DeviceDatabaseService — Story 85.2

Tests device enrichment and update logic with mocked external client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.device_database import (
    DeviceDatabaseService,
    get_device_database_service,
)


class TestEnrichDevice:
    """Test enrich_device with mocked db_client and cache."""

    def setup_method(self):
        self.svc = DeviceDatabaseService()

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_manufacturer(self):
        assert await self.svc.enrich_device("", "Model X") is None

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_model(self):
        assert await self.svc.enrich_device("Philips", "") is None

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_manufacturer(self):
        assert await self.svc.enrich_device("Unknown", "Unknown") is None

    @pytest.mark.asyncio
    async def test_returns_none_for_none_inputs(self):
        assert await self.svc.enrich_device(None, None) is None

    @pytest.mark.asyncio
    async def test_returns_cached_result(self):
        mock_cache = MagicMock()
        mock_cache.get.return_value = {"power_consumption": {"idle_w": 5}}
        self.svc._cache = mock_cache

        result = await self.svc.enrich_device("Philips", "Hue")
        assert result == {"power_consumption": {"idle_w": 5}}
        mock_cache.get.assert_called_once_with("Philips", "Hue")

    @pytest.mark.asyncio
    async def test_queries_db_client_on_cache_miss(self):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_device_info = AsyncMock(return_value={"rating": 4.5})

        self.svc._cache = mock_cache
        self.svc._db_client = mock_client

        result = await self.svc.enrich_device("Philips", "Hue")
        assert result == {"rating": 4.5}
        mock_cache.set.assert_called_once_with("Philips", "Hue", {"rating": 4.5})

    @pytest.mark.asyncio
    async def test_returns_none_when_no_client(self):
        """No db_client and no cache returns None."""
        result = await self.svc.enrich_device("Philips", "Hue")
        assert result is None

    @pytest.mark.asyncio
    async def test_handles_db_client_exception(self):
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_device_info = AsyncMock(side_effect=Exception("timeout"))
        self.svc._db_client = mock_client

        result = await self.svc.enrich_device("Philips", "Hue")
        assert result is None


class TestUpdateDeviceFromDatabase:
    """Test update_device_from_database extracts correct fields."""

    def setup_method(self):
        self.svc = DeviceDatabaseService()

    @pytest.mark.asyncio
    async def test_no_device_info_returns_empty(self):
        device = MagicMock(manufacturer="Unknown", model="Unknown")
        updates = await self.svc.update_device_from_database(device, device_info=None)
        assert updates == {}

    @pytest.mark.asyncio
    async def test_extracts_power_consumption(self):
        device_info = {"power_consumption": {"idle_w": 2, "active_w": 10, "max_w": 15}}
        device = MagicMock()
        updates = await self.svc.update_device_from_database(device, device_info)
        assert updates["power_consumption_idle_w"] == 2
        assert updates["power_consumption_active_w"] == 10
        assert updates["power_consumption_max_w"] == 15

    @pytest.mark.asyncio
    async def test_extracts_setup_url(self):
        device_info = {"setup_instructions_url": "https://example.com/setup"}
        device = MagicMock()
        updates = await self.svc.update_device_from_database(device, device_info)
        assert updates["setup_instructions_url"] == "https://example.com/setup"

    @pytest.mark.asyncio
    async def test_extracts_troubleshooting_as_json(self):
        device_info = {"troubleshooting": [{"issue": "reset", "fix": "power cycle"}]}
        device = MagicMock()
        updates = await self.svc.update_device_from_database(device, device_info)
        assert '"issue"' in updates["troubleshooting_notes"]

    @pytest.mark.asyncio
    async def test_extracts_features_as_json(self):
        device_info = {"features": ["dimming", "color"]}
        device = MagicMock()
        updates = await self.svc.update_device_from_database(device, device_info)
        assert '"dimming"' in updates["device_features_json"]

    @pytest.mark.asyncio
    async def test_extracts_rating(self):
        device_info = {"rating": 4.5}
        device = MagicMock()
        updates = await self.svc.update_device_from_database(device, device_info)
        assert updates["community_rating"] == 4.5

    @pytest.mark.asyncio
    async def test_extracts_infrared_codes(self):
        device_info = {"infrared_codes": {"power": "0x20DF10EF"}}
        device = MagicMock()
        updates = await self.svc.update_device_from_database(device, device_info)
        assert "0x20DF10EF" in updates["infrared_codes_json"]

    @pytest.mark.asyncio
    async def test_empty_device_info_returns_empty(self):
        device = MagicMock()
        updates = await self.svc.update_device_from_database(device, device_info={})
        assert updates == {}


class TestSingleton:

    def test_returns_same_instance(self):
        import src.services.device_database as mod
        mod._device_db_service = None
        assert get_device_database_service() is get_device_database_service()
