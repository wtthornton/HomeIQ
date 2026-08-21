"""Tests for services/device_classifier.py + services/device_health.py.

DeviceClassifierService is covered exhaustively in test_device_classifier_unit.py;
what lives here is a smoke subset plus the DeviceHealthService cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Override conftest fresh_db — no real DB needed
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ===========================================================================
# DeviceClassifierService — smoke subset
# ===========================================================================
#
# The exhaustive keyword corpus lives in test_device_classifier_unit.py. This
# is a deliberately small smoke set; a second hand-copied corpus would drift
# from the first.


class TestClassifierSmoke:
    """One case per code path, plus the guarantee that matters."""

    def _svc(self):
        from src.services.device_classifier import DeviceClassifierService

        return DeviceClassifierService()

    @pytest.mark.asyncio
    async def test_durable_path_classifies_from_entity_domains(self):
        result = await self._svc().classify_device("dev-001", ["light.kitchen", "sensor.temp"])
        assert result["device_id"] == "dev-001"
        assert result["device_type"] == "light"

    @pytest.mark.asyncio
    async def test_empty_domains(self):
        result = await self._svc().classify_device_from_domains("dev-001", [])
        assert result["device_type"] is None
        assert result["device_category"] is None

    @pytest.mark.asyncio
    async def test_handles_exception(self, monkeypatch):
        from src.services import device_classifier as dc_mod

        def boom(*_args, **_kwargs):
            raise Exception("fail")

        monkeypatch.setattr(dc_mod, "match_device_pattern", boom)
        result = await self._svc().classify_device_from_domains("dev-001", ["light"])
        assert result["device_type"] is None

    def test_metadata_fallback_matches_on_model(self):
        result = self._svc().classify_device_by_metadata("dev-001", "Hue White Bulb")
        assert result["device_type"] == "light"
        assert result["device_category"] == "lighting"

    def test_metadata_fallback_returns_none_without_a_signal(self):
        result = self._svc().classify_device_by_metadata("dev-001", "Generic Widget")
        assert result["device_type"] is None
        assert result["device_category"] is None

    def test_metadata_fallback_takes_no_name(self):
        # The friendly name is not a parameter, so a rename cannot reach the
        # decision. See test_device_classifier_unit.py for the full argument.
        import inspect

        from src.services.device_classifier import DeviceClassifierService

        params = inspect.signature(DeviceClassifierService.classify_device_by_metadata).parameters
        assert "name" not in params


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
