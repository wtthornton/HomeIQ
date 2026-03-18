"""Unit tests for DeviceHealthService — Story 85.10

Tests health analysis logic with mocked HA API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.device_health import DeviceHealthService, get_health_service


class TestDeviceHealthNoConfig:

    def test_init(self):
        svc = DeviceHealthService()
        assert svc._session is None

    @pytest.mark.asyncio
    async def test_no_ha_config_returns_unknown(self):
        svc = DeviceHealthService()
        svc.ha_url = None
        svc.ha_token = None
        result = await svc.get_device_health("dev-1", "Test Device", [])
        assert result["overall_status"] == "unknown"
        assert result["device_id"] == "dev-1"
        assert result["issues"] == []

    @pytest.mark.asyncio
    async def test_no_ha_url_returns_unknown(self):
        svc = DeviceHealthService()
        svc.ha_url = None
        svc.ha_token = "token"
        result = await svc.get_device_health("dev-1", "Test", [])
        assert result["overall_status"] == "unknown"


class TestDeviceHealthWithMockedHA:

    def _make_svc(self):
        svc = DeviceHealthService()
        svc.ha_url = "http://ha:8123"
        svc.ha_token = "test-token"
        return svc

    @pytest.mark.asyncio
    async def test_healthy_device(self):
        svc = self._make_svc()
        svc._get_battery_level = AsyncMock(return_value=80.0)
        svc._get_last_seen = AsyncMock(return_value=datetime.now())
        result = await svc.get_device_health("dev-1", "Test", ["sensor.bat"])
        assert result["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_low_battery_warning(self):
        svc = self._make_svc()
        svc._get_battery_level = AsyncMock(return_value=15.0)
        svc._get_last_seen = AsyncMock(return_value=datetime.now())
        result = await svc.get_device_health("dev-1", "Test", ["sensor.bat"])
        assert result["overall_status"] == "warning"
        assert any(i["type"] == "low_battery" for i in result["issues"])

    @pytest.mark.asyncio
    async def test_critical_battery(self):
        svc = self._make_svc()
        svc._get_battery_level = AsyncMock(return_value=5.0)
        svc._get_last_seen = AsyncMock(return_value=datetime.now())
        result = await svc.get_device_health("dev-1", "Test", ["sensor.bat"])
        assert result["overall_status"] == "error"
        battery_issue = next(i for i in result["issues"] if i["type"] == "low_battery")
        assert battery_issue["severity"] == "error"

    @pytest.mark.asyncio
    async def test_device_not_seen_warning(self):
        svc = self._make_svc()
        svc._get_battery_level = AsyncMock(return_value=None)
        svc._get_last_seen = AsyncMock(
            return_value=datetime.now() - timedelta(hours=30)
        )
        result = await svc.get_device_health("dev-1", "Test", ["sensor.x"])
        assert result["overall_status"] == "warning"
        assert any(i["type"] == "device_not_responding" for i in result["issues"])

    @pytest.mark.asyncio
    async def test_device_not_seen_error(self):
        svc = self._make_svc()
        svc._get_battery_level = AsyncMock(return_value=None)
        svc._get_last_seen = AsyncMock(
            return_value=datetime.now() - timedelta(hours=50)
        )
        result = await svc.get_device_health("dev-1", "Test", ["sensor.x"])
        assert result["overall_status"] == "error"

    @pytest.mark.asyncio
    async def test_no_battery_no_last_seen(self):
        svc = self._make_svc()
        svc._get_battery_level = AsyncMock(return_value=None)
        svc._get_last_seen = AsyncMock(return_value=None)
        result = await svc.get_device_health("dev-1", "Test", [])
        assert result["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_exception_returns_error(self):
        svc = self._make_svc()
        svc._get_session = AsyncMock(side_effect=Exception("conn error"))
        result = await svc.get_device_health("dev-1", "Test", ["x"])
        assert result["overall_status"] == "error"
        assert any("health_check_failed" in i["type"] for i in result["issues"])


class TestSingleton:

    def test_returns_instance(self):
        import src.services.device_health as mod
        mod._health_service = None
        svc = get_health_service()
        assert isinstance(svc, DeviceHealthService)

    def test_returns_same_instance(self):
        import src.services.device_health as mod
        mod._health_service = None
        s1 = get_health_service()
        s2 = get_health_service()
        assert s1 is s2
