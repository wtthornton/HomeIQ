"""Unit tests for EntityEnrichmentService — Story 85.1

Tests the pure business logic in entity_enrichment.py:
- _extract_capabilities() for all domain types
- enrich_entity_capabilities() with mocked HA API
- get_available_services_for_domain() with mocked DB
- Singleton accessor
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.entity_enrichment import (
    EntityEnrichmentService,
    get_entity_enrichment_service,
)


# ---------------------------------------------------------------------------
# _extract_capabilities — pure logic, no I/O
# ---------------------------------------------------------------------------

class TestExtractCapabilities:
    """Test _extract_capabilities for all supported domains."""

    def setup_method(self):
        self.svc = EntityEnrichmentService()

    # -- light domain -------------------------------------------------------

    def test_light_brightness_from_features(self):
        caps = self.svc._extract_capabilities("light", {}, 1)  # SUPPORT_BRIGHTNESS
        assert "brightness" in caps

    def test_light_color_temp_from_features(self):
        caps = self.svc._extract_capabilities("light", {}, 2)  # SUPPORT_COLOR_TEMP
        assert "color_temp" in caps

    def test_light_effect_from_features(self):
        caps = self.svc._extract_capabilities("light", {}, 4)  # SUPPORT_EFFECT
        assert "effect" in caps

    def test_light_transition_from_features(self):
        caps = self.svc._extract_capabilities("light", {}, 16)  # SUPPORT_TRANSITION
        assert "transition" in caps

    def test_light_color_from_features(self):
        caps = self.svc._extract_capabilities("light", {}, 128)  # SUPPORT_COLOR
        assert "color" in caps

    def test_light_white_value_from_features(self):
        caps = self.svc._extract_capabilities("light", {}, 256)  # SUPPORT_WHITE_VALUE
        assert "white_value" in caps

    def test_light_combined_features(self):
        # brightness + color_temp + color = 1 + 2 + 128 = 131
        caps = self.svc._extract_capabilities("light", {}, 131)
        assert "brightness" in caps
        assert "color_temp" in caps
        assert "color" in caps

    def test_light_brightness_from_attributes(self):
        caps = self.svc._extract_capabilities("light", {"brightness": 200}, None)
        assert "brightness" in caps

    def test_light_color_from_rgb_attribute(self):
        caps = self.svc._extract_capabilities("light", {"rgb_color": [255, 0, 0]}, None)
        assert "color" in caps

    def test_light_color_from_hs_attribute(self):
        caps = self.svc._extract_capabilities("light", {"hs_color": [0, 100]}, None)
        assert "color" in caps

    def test_light_color_from_xy_attribute(self):
        caps = self.svc._extract_capabilities("light", {"xy_color": [0.3, 0.3]}, None)
        assert "color" in caps

    def test_light_color_temp_from_attribute(self):
        caps = self.svc._extract_capabilities("light", {"color_temp": 370}, None)
        assert "color_temp" in caps

    def test_light_effect_from_effect_list(self):
        caps = self.svc._extract_capabilities("light", {"effect_list": ["rainbow"]}, None)
        assert "effect" in caps

    def test_light_no_duplicates(self):
        """Features + attributes should not produce duplicate capabilities."""
        caps = self.svc._extract_capabilities(
            "light",
            {"brightness": 200, "rgb_color": [255, 0, 0]},
            129,  # brightness(1) + color(128)
        )
        assert caps.count("brightness") == 1
        assert caps.count("color") == 1

    def test_light_capabilities_sorted(self):
        caps = self.svc._extract_capabilities("light", {}, 131)
        assert caps == sorted(caps)

    # -- switch domain ------------------------------------------------------

    def test_switch_on_off(self):
        caps = self.svc._extract_capabilities("switch", {}, None)
        assert caps == ["on_off"]

    # -- sensor domain ------------------------------------------------------

    def test_sensor_device_class(self):
        caps = self.svc._extract_capabilities("sensor", {"device_class": "temperature"}, None)
        assert "measure_temperature" in caps

    def test_sensor_state_class(self):
        caps = self.svc._extract_capabilities("sensor", {"state_class": "measurement"}, None)
        assert "state_measurement" in caps

    def test_sensor_both_classes(self):
        caps = self.svc._extract_capabilities(
            "sensor", {"device_class": "humidity", "state_class": "measurement"}, None
        )
        assert "measure_humidity" in caps
        assert "state_measurement" in caps

    # -- cover domain -------------------------------------------------------

    def test_cover_open_close(self):
        caps = self.svc._extract_capabilities("cover", {}, 3)  # OPEN(1) + CLOSE(2)
        assert "open" in caps
        assert "close" in caps

    def test_cover_position(self):
        caps = self.svc._extract_capabilities("cover", {}, 4)  # SET_POSITION
        assert "position" in caps

    def test_cover_stop(self):
        caps = self.svc._extract_capabilities("cover", {}, 8)  # STOP
        assert "stop" in caps

    # -- fan domain ---------------------------------------------------------

    def test_fan_speed(self):
        caps = self.svc._extract_capabilities("fan", {}, 1)  # SET_SPEED
        assert "speed" in caps

    def test_fan_oscillate(self):
        caps = self.svc._extract_capabilities("fan", {}, 2)  # OSCILLATE
        assert "oscillate" in caps

    def test_fan_direction(self):
        caps = self.svc._extract_capabilities("fan", {}, 4)  # DIRECTION
        assert "direction" in caps

    # -- attribute-based capabilities (cross-domain) -------------------------

    def test_volume_attribute(self):
        caps = self.svc._extract_capabilities("media_player", {"volume_level": 0.5}, None)
        assert "volume" in caps

    def test_media_content_type_attribute(self):
        caps = self.svc._extract_capabilities("media_player", {"media_content_type": "music"}, None)
        assert "media" in caps

    def test_temperature_attribute(self):
        caps = self.svc._extract_capabilities("climate", {"temperature": 22}, None)
        assert "temperature_control" in caps

    def test_humidity_attribute(self):
        caps = self.svc._extract_capabilities("climate", {"humidity": 50}, None)
        assert "humidity_control" in caps

    # -- edge cases ---------------------------------------------------------

    def test_empty_attributes_no_features(self):
        result = self.svc._extract_capabilities("light", {}, None)
        assert result is None

    def test_unknown_domain_no_features(self):
        result = self.svc._extract_capabilities("unknown_domain", {}, None)
        assert result is None

    def test_none_supported_features(self):
        """None supported_features should still check attributes."""
        caps = self.svc._extract_capabilities("light", {"brightness": 200}, None)
        assert "brightness" in caps


# ---------------------------------------------------------------------------
# enrich_entity_capabilities — async with mocked HA API
# ---------------------------------------------------------------------------

class TestEnrichEntityCapabilities:
    """Test enrich_entity_capabilities with mocked HTTP session."""

    def setup_method(self):
        self.svc = EntityEnrichmentService()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_ha_config(self):
        """No HA_URL/HA_TOKEN should return null capabilities."""
        self.svc.ha_url = None
        self.svc.ha_token = None
        result = await self.svc.enrich_entity_capabilities("light.kitchen", "light")
        assert result["supported_features"] is None
        assert result["capabilities"] is None

    @pytest.mark.asyncio
    async def test_returns_capabilities_on_200(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "state": "on",
            "attributes": {"supported_features": 1, "brightness": 200},
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        self.svc.ha_url = "http://ha:8123"
        self.svc.ha_token = "test-token"
        self.svc._get_session = AsyncMock(return_value=mock_session)

        result = await self.svc.enrich_entity_capabilities("light.kitchen", "light")
        assert result["supported_features"] == 1
        assert "brightness" in result["capabilities"]

    @pytest.mark.asyncio
    async def test_returns_none_on_non_200(self):
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        self.svc.ha_url = "http://ha:8123"
        self.svc.ha_token = "test-token"
        self.svc._get_session = AsyncMock(return_value=mock_session)

        result = await self.svc.enrich_entity_capabilities("light.kitchen", "light")
        assert result["supported_features"] is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        self.svc.ha_url = "http://ha:8123"
        self.svc.ha_token = "test-token"
        self.svc._get_session = AsyncMock(side_effect=Exception("connection error"))

        result = await self.svc.enrich_entity_capabilities("light.kitchen", "light")
        assert result["supported_features"] is None
        assert result["capabilities"] is None

    @pytest.mark.asyncio
    async def test_supported_features_cast_to_int(self):
        """String supported_features should be cast to int."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "state": "on",
            "attributes": {"supported_features": "3"},
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        self.svc.ha_url = "http://ha:8123"
        self.svc.ha_token = "test-token"
        self.svc._get_session = AsyncMock(return_value=mock_session)

        result = await self.svc.enrich_entity_capabilities("light.kitchen", "light")
        assert result["supported_features"] == 3

    @pytest.mark.asyncio
    async def test_invalid_supported_features_becomes_none(self):
        """Non-numeric supported_features should become None."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "state": "on",
            "attributes": {"supported_features": "not_a_number"},
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        self.svc.ha_url = "http://ha:8123"
        self.svc.ha_token = "test-token"
        self.svc._get_session = AsyncMock(return_value=mock_session)

        result = await self.svc.enrich_entity_capabilities("light.kitchen", "light")
        assert result["supported_features"] is None


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# get_available_services_for_domain — mocked DB
# ---------------------------------------------------------------------------

class TestGetAvailableServicesForDomain:

    def setup_method(self):
        self.svc = EntityEnrichmentService()

    @pytest.mark.asyncio
    async def test_returns_formatted_services(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["turn_on", "turn_off", "toggle"]
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.svc.get_available_services_for_domain("light", mock_db)
        assert result == ["light.turn_on", "light.turn_off", "light.toggle"]

    @pytest.mark.asyncio
    async def test_returns_none_when_no_services(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.svc.get_available_services_for_domain("light", mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("db error"))

        result = await self.svc.get_available_services_for_domain("light", mock_db)
        assert result is None


# ---------------------------------------------------------------------------
# enrich_entity — combined enrichment
# ---------------------------------------------------------------------------

class TestEnrichEntity:

    def setup_method(self):
        self.svc = EntityEnrichmentService()

    @pytest.mark.asyncio
    async def test_combines_capabilities_and_services(self):
        self.svc.enrich_entity_capabilities = AsyncMock(return_value={
            "supported_features": 1,
            "capabilities": ["brightness"],
        })
        self.svc.get_available_services_for_domain = AsyncMock(
            return_value=["light.turn_on"]
        )
        mock_db = AsyncMock()

        result = await self.svc.enrich_entity("light.kitchen", "light", mock_db)
        assert result["supported_features"] == 1
        assert result["capabilities"] == ["brightness"]
        assert result["available_services"] == ["light.turn_on"]


class TestSingleton:

    def test_get_entity_enrichment_service_returns_instance(self):
        import src.services.entity_enrichment as mod
        mod._enrichment_service = None  # reset
        svc = get_entity_enrichment_service()
        assert isinstance(svc, EntityEnrichmentService)

    def test_get_entity_enrichment_service_returns_same_instance(self):
        import src.services.entity_enrichment as mod
        mod._enrichment_service = None
        svc1 = get_entity_enrichment_service()
        svc2 = get_entity_enrichment_service()
        assert svc1 is svc2
