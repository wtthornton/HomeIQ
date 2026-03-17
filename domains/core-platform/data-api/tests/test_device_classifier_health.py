"""
Tests for services/device_classifier.py + services/device_health.py — Epic 80, Story 80.9

Covers 14 scenarios:

DeviceClassifierService:
1.  classify_device — extracts domains from entity_ids
2.  classify_device_from_domains — empty domains returns None
3.  classify_device_from_domains — handles exception
4.  classify_device_by_metadata — light keywords
5.  classify_device_by_metadata — switch/plug keywords
6.  classify_device_by_metadata — sensor keywords
7.  classify_device_by_metadata — vacuum keywords
8.  classify_device_by_metadata — thermostat keywords
9.  classify_device_by_metadata — lock keywords
10. classify_device_by_metadata — camera keywords
11. classify_device_by_metadata — unknown device returns None

DeviceHealthService:
12. get_device_health — returns basic report when HA not configured
13. get_device_health — handles exception gracefully
14. Singleton getter returns same instance
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Override conftest fresh_db — no real DB needed
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ===========================================================================
# DeviceClassifierService Tests
# ===========================================================================


class TestClassifyDevice:
    """DeviceClassifierService.classify_device()."""

    @pytest.mark.asyncio
    async def test_extracts_domains_from_entity_ids(self):
        from src.services.device_classifier import DeviceClassifierService

        svc = DeviceClassifierService()
        result = await svc.classify_device("dev-001", ["light.kitchen", "sensor.temp"])
        # Should call classify_device_from_domains with ["light", "sensor"]
        assert result["device_id"] == "dev-001"


class TestClassifyDeviceFromDomains:
    """DeviceClassifierService.classify_device_from_domains()."""

    @pytest.mark.asyncio
    async def test_empty_domains(self):
        from src.services.device_classifier import DeviceClassifierService

        svc = DeviceClassifierService()
        result = await svc.classify_device_from_domains("dev-001", [])
        assert result["device_type"] is None
        assert result["device_category"] is None

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        from src.services.device_classifier import DeviceClassifierService

        svc = DeviceClassifierService()
        with patch("src.services.device_classifier.match_device_pattern", side_effect=Exception("fail")):
            result = await svc.classify_device_from_domains("dev-001", ["light"])
        assert result["device_type"] is None


class TestClassifyDeviceByMetadata:
    """DeviceClassifierService.classify_device_by_metadata()."""

    def _classify(self, name, manufacturer=None, model=None):
        from src.services.device_classifier import DeviceClassifierService
        svc = DeviceClassifierService()
        return svc.classify_device_by_metadata("dev-001", name, manufacturer, model)

    def test_light_keywords(self):
        result = self._classify("Hue White Bulb", "Signify")
        assert result["device_type"] == "light"
        assert result["device_category"] == "lighting"

    def test_switch_keywords(self):
        result = self._classify("Smart Plug S31", "Sonoff")
        assert result["device_type"] == "switch"
        assert result["device_category"] == "control"

    def test_sensor_keywords(self):
        result = self._classify("Motion Sensor", "Aqara")
        assert result["device_type"] == "sensor"
        assert result["device_category"] == "sensor"

    def test_vacuum_keywords(self):
        result = self._classify("S7 MaxV", "Roborock")
        assert result["device_type"] == "vacuum"
        assert result["device_category"] == "appliance"

    def test_thermostat_keywords(self):
        result = self._classify("Learning Thermostat", "Nest")
        assert result["device_type"] == "thermostat"
        assert result["device_category"] == "climate"

    def test_lock_keywords(self):
        result = self._classify("Smart Lock Pro", "August")
        assert result["device_type"] == "lock"
        assert result["device_category"] == "security"

    def test_camera_keywords(self):
        result = self._classify("Indoor Cam", "Ring")
        assert result["device_type"] == "camera"
        assert result["device_category"] == "security"

    def test_unknown_device(self):
        result = self._classify("Generic Widget", "Acme Corp")
        assert result["device_type"] is None
        assert result["device_category"] is None


# ===========================================================================
# DeviceHealthService Tests
# ===========================================================================


class TestDeviceHealthService:
    """DeviceHealthService basic tests."""

    @pytest.mark.asyncio
    async def test_returns_basic_report_when_ha_not_configured(self):
        from src.services.device_health import DeviceHealthService

        svc = DeviceHealthService()
        svc.ha_url = None
        svc.ha_token = None

        result = await svc.get_device_health("dev-001", "Test Device", ["light.test"])
        assert result["device_id"] == "dev-001"
        assert result["overall_status"] == "unknown"
        assert result["issues"] == []

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        from src.services.device_health import DeviceHealthService

        svc = DeviceHealthService()
        svc.ha_url = "http://fake-ha:8123"
        svc.ha_token = "fake-token"

        # Make _get_session itself raise so the outer try/except triggers
        svc._get_session = AsyncMock(side_effect=Exception("connection failed"))

        result = await svc.get_device_health("dev-001", "Test", ["light.test"])
        assert result["overall_status"] == "error"
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "health_check_failed"


class TestSingletonGetters:
    """Singleton factory functions."""

    def test_get_classifier_service(self):
        from src.services.device_classifier import get_classifier_service
        svc1 = get_classifier_service()
        svc2 = get_classifier_service()
        assert svc1 is svc2

    def test_get_health_service(self):
        from src.services.device_health import get_health_service
        svc1 = get_health_service()
        svc2 = get_health_service()
        assert svc1 is svc2
