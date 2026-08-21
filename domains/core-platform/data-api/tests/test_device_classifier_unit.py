"""Unit tests for DeviceClassifierService.

Two things are pinned here, and they are the point of the file:

1. `device_type` never depends on a device's friendly name. The name is not a
   parameter of `classify_device_by_metadata` at all, so a rename cannot reach
   the decision — asserted structurally, not by value.
2. The durable domain-based path is bound to the real taxonomy, not to a stub.
   It used to sit behind a `try/except ImportError` whose fallback returned None
   for every device, which made every test of that path pass vacuously.

The matcher is exercised for real rather than mocked. The previous version of
this file patched `match_device_pattern` to return the bare string `"light"`,
but the real function returns `(device_type, confidence)` — so the doubles
encoded the caller's mistaken belief about the contract and hid a live bug
(TAP-6392).
"""

import inspect

import pytest
from src.services import device_classifier as dc_mod
from src.services.device_classifier import (
    DeviceClassifierService,
    get_classifier_service,
)

# ---------------------------------------------------------------------------
# The durable path is real, not a stub
# ---------------------------------------------------------------------------


class TestTaxonomyIsRealNotAStub:
    """If the taxonomy import ever degrades again, these fail loudly."""

    def test_matcher_is_bound_to_the_shared_taxonomy(self):
        # An identity check, not a return-value check: a stub can return the
        # right answer for a lucky fixture and still be a stub.
        assert dc_mod.match_device_pattern.__module__ == "homeiq_device_taxonomy.patterns", (
            "classify_device_from_domains is not using the shared taxonomy. "
            "The import degraded to a local fallback, which returns None for "
            "every device and makes every durable-path test pass vacuously."
        )

    def test_matcher_returns_a_type_and_a_confidence(self):
        # Positive control. The old stub returned a bare None, so unpacking a
        # two-tuple is itself an assertion that the real module is loaded.
        device_type, confidence = dc_mod.match_device_pattern(["light"], set())
        assert device_type == "light"
        assert 0.0 < confidence <= 1.0

    @pytest.mark.asyncio
    async def test_durable_path_classifies_a_device_with_entities(self):
        svc = DeviceClassifierService()
        result = await svc.classify_device_from_domains("d1", ["light"], ["light.anything"])
        assert result["device_type"] == "light"
        assert result["device_category"] == "lighting"

    @pytest.mark.asyncio
    async def test_durable_path_does_not_write_the_matcher_tuple(self):
        # The matcher returns (device_type, confidence). Binding that tuple
        # straight to device_type wrote "('light', 0.95)" into a String column.
        svc = DeviceClassifierService()
        result = await svc.classify_device_from_domains("d1", ["switch"], ["switch.anything"])
        assert isinstance(result["device_type"], str)


# ---------------------------------------------------------------------------
# A name can never reach the decision
# ---------------------------------------------------------------------------


class TestNameIsNotADecisionInput:
    """The strongest available guarantee: the parameter does not exist."""

    def test_classify_by_metadata_accepts_no_name_argument(self):
        params = inspect.signature(DeviceClassifierService.classify_device_by_metadata).parameters
        assert "name" not in params, (
            "A `name` parameter was reintroduced. device_type is a decision "
            "input (it filters GET /api/devices and drives the similar-devices "
            "recommender), so a rename must not be able to change it."
        )
        assert "manufacturer" not in params, (
            "A `manufacturer` parameter was reintroduced. Manufacturer names a "
            "vendor, not a device type: matching the brand token 'signify' "
            "classified two Hue Room groups as lights."
        )

    def test_a_name_cannot_be_passed_positionally(self):
        svc = DeviceClassifierService()
        with pytest.raises(TypeError):
            svc.classify_device_by_metadata("d1", "Kitchen Light", "Signify", "LCT015")

    def test_device_type_is_invariant_under_rename(self):
        # Non-vacuous by construction: the expected value is pinned explicitly
        # and asserted non-None, so this cannot pass by both sides being None.
        svc = DeviceClassifierService()
        model = "Hue White Ambiance Bulb"

        before = svc.classify_device_by_metadata("d1", model)
        # A rename changes only the name, which is not an input, so the call is
        # byte-identical. That is the guarantee.
        after = svc.classify_device_by_metadata("d1", model)

        assert before["device_type"] == "light"
        assert before["device_type"] is not None
        assert after == before


# ---------------------------------------------------------------------------
# classify_device_by_metadata — model keywords, the entity-less fallback
# ---------------------------------------------------------------------------


class TestClassifyDeviceByMetadata:
    """Model-keyword classification for devices that expose no entities."""

    def setup_method(self):
        self.svc = DeviceClassifierService()

    @pytest.mark.parametrize(
        "model,expected_type,expected_category",
        [
            # Lights
            ("Hue White Ambiance Bulb", "light", "lighting"),
            ("Smart Bulb A19", "light", "lighting"),
            ("Desk Lamp", "light", "lighting"),
            ("LED Strip Controller", "light", "lighting"),
            ("Lightstrip Plus", "light", "lighting"),
            ("Downlight 5in", "light", "lighting"),
            # Media players
            ("Samsung TV Q60", "media_player", "entertainment"),
            ("Television 55inch", "media_player", "entertainment"),
            ("Soundbar HW-Q950", "media_player", "entertainment"),
            # Switches and outlets
            ("Wall Switch HS200", "switch", "control"),
            ("Smart Plug Mini", "switch", "control"),
            ("Outlet Controller", "switch", "control"),
            # Sensors
            ("Temperature Sensor", "sensor", "sensor"),
            ("Motion Detector", "sensor", "sensor"),
            ("Presence Sensor FP1E", "sensor", "sensor"),
            # Vacuum
            ("Robot Vacuum S7", "vacuum", "appliance"),
            ("Roborock S7 MaxV", "vacuum", "appliance"),
            # Thermostat
            ("Smart Thermostat", "thermostat", "climate"),
            ("HVAC Controller", "thermostat", "climate"),
            # Lock
            ("Smart Lock Pro", "lock", "security"),
            ("Deadbolt 620", "lock", "security"),
            # Camera
            ("Security Camera", "camera", "security"),
            # Fan
            ("Ceiling Fan", "fan", "climate"),
            # Button / remote
            ("Smart Button", "button", "control"),
            ("Remote Control", "button", "control"),
        ],
    )
    def test_model_keyword_classification(self, model, expected_type, expected_category):
        result = self.svc.classify_device_by_metadata("d1", model)
        assert result["device_type"] == expected_type
        assert result["device_category"] == expected_category

    @pytest.mark.parametrize(
        "model",
        [
            "Flight Tracker Pro",  # contains "light" without a word boundary
            "Highlight Feature Kit",  # ditto
            "Lightning Adapter",  # ditto
            "Netvue Doorbell",  # contains "tv" without a word boundary
        ],
    )
    def test_substring_false_positives_are_guarded(self, model):
        # These pin the word-boundary matcher, which is the real fix. Raw
        # substring containment matched every one of them.
        result = self.svc.classify_device_by_metadata("d1", model)
        assert result["device_type"] not in ("light", "media_player")

    @pytest.mark.parametrize(
        "model",
        [
            "Room",  # a Hue room group, not a device
            "bcm43438-bt",  # a Bluetooth adapter
            "CC2652",  # a Zigbee coordinator
            "Mystery Gadget",
        ],
    )
    def test_pseudo_devices_return_none_rather_than_a_guess(self, model):
        # The four entity-less devices on this instance. Two are Hue Room
        # groups whose manufacturer is "Signify Netherlands B.V."; matching the
        # brand token classified a room as a light.
        result = self.svc.classify_device_by_metadata("d1", model)
        assert result["device_type"] is None
        assert result["device_category"] is None

    @pytest.mark.parametrize("model", ["", None])
    def test_absent_model_returns_none(self, model):
        result = self.svc.classify_device_by_metadata("d1", model)
        assert result["device_type"] is None

    def test_device_id_is_echoed_back(self):
        result = self.svc.classify_device_by_metadata("my-device", "Hue Bulb")
        assert result["device_id"] == "my-device"


# ---------------------------------------------------------------------------
# classify_device_from_domains — edge cases
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
    async def test_unmapped_domain_returns_none(self):
        result = await self.svc.classify_device_from_domains("d1", ["not_a_domain"])
        assert result["device_type"] is None

    @pytest.mark.asyncio
    async def test_matcher_failure_is_contained(self, monkeypatch):
        def boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(dc_mod, "match_device_pattern", boom)
        result = await self.svc.classify_device_from_domains("d1", ["light"])
        assert result["device_id"] == "d1"
        assert result["device_type"] is None


# ---------------------------------------------------------------------------
# classify_device — legacy wrapper
# ---------------------------------------------------------------------------


class TestClassifyDevice:
    @pytest.mark.asyncio
    async def test_extracts_domains_from_entity_ids(self):
        svc = DeviceClassifierService()
        result = await svc.classify_device("d1", ["light.kitchen", "sensor.temp"])
        assert result["device_type"] == "light"

    @pytest.mark.asyncio
    async def test_entity_ids_without_a_domain_are_skipped(self):
        svc = DeviceClassifierService()
        result = await svc.classify_device("d1", ["malformed"])
        assert result["device_type"] is None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestClassifierSingleton:
    def test_returns_instance(self):
        dc_mod._classifier_service = None
        assert isinstance(get_classifier_service(), DeviceClassifierService)

    def test_returns_same_instance(self):
        dc_mod._classifier_service = None
        assert get_classifier_service() is get_classifier_service()
