"""Unit tests for DeviceClassifierService — Story 85.1

Tests device classification logic:
- classify_device_from_domains() with mocked pattern functions
- classify_device_by_metadata() — pure pattern matching (no I/O)
- classify_device() — legacy wrapper
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.device_classifier import (
    DeviceClassifierService,
    get_classifier_service,
)


# ---------------------------------------------------------------------------
# classify_device_by_metadata — pure logic, no I/O
# ---------------------------------------------------------------------------

class TestClassifyDeviceByMetadata:
    """Test metadata-based classification (name/manufacturer/model patterns)."""

    def setup_method(self):
        self.svc = DeviceClassifierService()

    # -- Lights -------------------------------------------------------------

    def test_hue_light(self):
        result = self.svc.classify_device_by_metadata("d1", "Hue White Ambiance")
        assert result["device_type"] == "light"
        assert result["device_category"] == "lighting"

    def test_bulb(self):
        result = self.svc.classify_device_by_metadata("d1", "Smart Bulb")
        assert result["device_type"] == "light"

    def test_lamp(self):
        result = self.svc.classify_device_by_metadata("d1", "Desk Lamp")
        assert result["device_type"] == "light"

    def test_led_strip(self):
        result = self.svc.classify_device_by_metadata("d1", "LED Strip Controller")
        assert result["device_type"] == "light"

    def test_lightstrip(self):
        result = self.svc.classify_device_by_metadata("d1", "Lightstrip Plus")
        assert result["device_type"] == "light"

    def test_signify(self):
        result = self.svc.classify_device_by_metadata("d1", "Device", manufacturer="Signify")
        assert result["device_type"] == "light"

    def test_light_keyword_not_flight(self):
        """'flight' should NOT match as light."""
        result = self.svc.classify_device_by_metadata("d1", "Flight Tracker")
        assert result["device_type"] != "light"

    def test_light_keyword_not_highlight(self):
        result = self.svc.classify_device_by_metadata("d1", "Highlight Feature")
        assert result["device_type"] != "light"

    def test_light_keyword_standalone(self):
        """'light' without false-positive words should match."""
        result = self.svc.classify_device_by_metadata("d1", "Kitchen Light")
        assert result["device_type"] == "light"

    # -- Media players ------------------------------------------------------

    def test_samsung_tv(self):
        result = self.svc.classify_device_by_metadata("d1", "Samsung TV")
        assert result["device_type"] == "media_player"
        assert result["device_category"] == "entertainment"

    def test_television(self):
        result = self.svc.classify_device_by_metadata("d1", "Television 55inch")
        assert result["device_type"] == "media_player"

    def test_tv_fallback(self):
        result = self.svc.classify_device_by_metadata("d1", "Living Room TV")
        assert result["device_type"] == "media_player"

    # -- Switches -----------------------------------------------------------

    def test_switch(self):
        result = self.svc.classify_device_by_metadata("d1", "Wall Switch")
        assert result["device_type"] == "switch"
        assert result["device_category"] == "control"

    def test_smart_plug(self):
        result = self.svc.classify_device_by_metadata("d1", "Smart Plug Mini")
        assert result["device_type"] == "switch"

    def test_outlet(self):
        result = self.svc.classify_device_by_metadata("d1", "Outlet Controller")
        assert result["device_type"] == "switch"

    # -- Sensors ------------------------------------------------------------

    def test_sensor(self):
        result = self.svc.classify_device_by_metadata("d1", "Temperature Sensor")
        assert result["device_type"] == "sensor"
        assert result["device_category"] == "sensor"

    def test_motion_sensor(self):
        result = self.svc.classify_device_by_metadata("d1", "Motion Detector")
        assert result["device_type"] == "sensor"

    def test_presence_sensor(self):
        result = self.svc.classify_device_by_metadata("d1", "Presence Detector")
        assert result["device_type"] == "sensor"

    # -- Vacuum -------------------------------------------------------------

    def test_vacuum(self):
        result = self.svc.classify_device_by_metadata("d1", "Robot Vacuum S7")
        assert result["device_type"] == "vacuum"
        assert result["device_category"] == "appliance"

    def test_roborock(self):
        result = self.svc.classify_device_by_metadata("d1", "Roborock S7 MaxV")
        assert result["device_type"] == "vacuum"

    # -- Thermostat ---------------------------------------------------------

    def test_thermostat(self):
        result = self.svc.classify_device_by_metadata("d1", "Smart Thermostat")
        assert result["device_type"] == "thermostat"
        assert result["device_category"] == "climate"

    def test_hvac(self):
        result = self.svc.classify_device_by_metadata("d1", "HVAC Controller")
        assert result["device_type"] == "thermostat"

    # -- Lock ---------------------------------------------------------------

    def test_lock(self):
        result = self.svc.classify_device_by_metadata("d1", "Smart Lock Pro")
        assert result["device_type"] == "lock"
        assert result["device_category"] == "security"

    # -- Camera -------------------------------------------------------------

    def test_camera(self):
        result = self.svc.classify_device_by_metadata("d1", "Security Camera")
        assert result["device_type"] == "camera"
        assert result["device_category"] == "security"

    # -- Fan ----------------------------------------------------------------

    def test_fan(self):
        result = self.svc.classify_device_by_metadata("d1", "Ceiling Fan")
        assert result["device_type"] == "fan"
        assert result["device_category"] == "climate"

    # -- Button/Remote ------------------------------------------------------

    def test_button(self):
        result = self.svc.classify_device_by_metadata("d1", "Smart Button")
        assert result["device_type"] == "button"
        assert result["device_category"] == "control"

    def test_remote(self):
        result = self.svc.classify_device_by_metadata("d1", "Remote Control")
        assert result["device_type"] == "button"

    # -- Unknown ------------------------------------------------------------

    def test_unknown_device(self):
        result = self.svc.classify_device_by_metadata("d1", "Mystery Gadget")
        assert result["device_type"] is None
        assert result["device_category"] is None
        assert result["device_id"] == "d1"

    # -- Edge cases ---------------------------------------------------------

    def test_empty_name(self):
        result = self.svc.classify_device_by_metadata("d1", "")
        assert result["device_type"] is None

    def test_none_name(self):
        result = self.svc.classify_device_by_metadata("d1", None)
        assert result["device_type"] is None

    def test_manufacturer_model_used(self):
        result = self.svc.classify_device_by_metadata(
            "d1", "Device", manufacturer="Signify", model="LCA001"
        )
        assert result["device_type"] == "light"

    def test_device_id_always_returned(self):
        result = self.svc.classify_device_by_metadata("my-device", "Anything")
        assert result["device_id"] == "my-device"


# ---------------------------------------------------------------------------
# classify_device_from_domains — async, uses imported pattern functions
# ---------------------------------------------------------------------------

class TestClassifyDeviceFromDomains:

    def setup_method(self):
        self.svc = DeviceClassifierService()

    @pytest.mark.asyncio
    async def test_empty_domains_returns_none(self):
        result = await self.svc.classify_device_from_domains("d1", [])
        assert result["device_type"] is None
        assert result["device_category"] is None

    @pytest.mark.asyncio
    async def test_uses_pattern_matcher(self):
        with patch("src.services.device_classifier.match_device_pattern", return_value="light"), \
             patch("src.services.device_classifier.get_device_category", return_value="lighting"):
            result = await self.svc.classify_device_from_domains("d1", ["light"])
            assert result["device_type"] == "light"
            assert result["device_category"] == "lighting"

    @pytest.mark.asyncio
    async def test_pattern_matcher_returns_none(self):
        with patch("src.services.device_classifier.match_device_pattern", return_value=None), \
             patch("src.services.device_classifier.get_device_category", return_value=None):
            result = await self.svc.classify_device_from_domains("d1", ["unknown"])
            assert result["device_type"] is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self):
        with patch("src.services.device_classifier.match_device_pattern", side_effect=Exception("boom")):
            result = await self.svc.classify_device_from_domains("d1", ["light"])
            assert result["device_type"] is None


# ---------------------------------------------------------------------------
# classify_device — legacy wrapper
# ---------------------------------------------------------------------------

class TestClassifyDevice:

    def setup_method(self):
        self.svc = DeviceClassifierService()

    @pytest.mark.asyncio
    async def test_extracts_domains_from_entity_ids(self):
        with patch("src.services.device_classifier.match_device_pattern", return_value="light"), \
             patch("src.services.device_classifier.get_device_category", return_value="lighting"):
            result = await self.svc.classify_device("d1", ["light.kitchen", "sensor.temp"])
            assert result["device_type"] == "light"

    @pytest.mark.asyncio
    async def test_handles_entity_ids_without_dots(self):
        with patch("src.services.device_classifier.match_device_pattern", return_value=None), \
             patch("src.services.device_classifier.get_device_category", return_value=None):
            result = await self.svc.classify_device("d1", ["nodot"])
            assert result["device_type"] is None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestClassifierSingleton:

    def test_returns_instance(self):
        import src.services.device_classifier as mod
        mod._classifier_service = None
        svc = get_classifier_service()
        assert isinstance(svc, DeviceClassifierService)

    def test_returns_same_instance(self):
        import src.services.device_classifier as mod
        mod._classifier_service = None
        assert get_classifier_service() is get_classifier_service()
