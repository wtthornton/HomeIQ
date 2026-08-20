"""Generated names must not be penalized by the rubric that scores them (TAP-6234).

The generator emitted "Office Aqara Sensor" while `convention_rules` docks
brand words — the system generated names its own scorer flagged. These tests
pin the policy: no brand ever appears in a generated or suggested name, and a
generated name scores clean on the name-quality rule.
"""

from types import SimpleNamespace

import pytest
from src.services.name_enhancement.name_generator import DeviceNameGenerator
from src.services.naming_convention.convention_rules import score_friendly_name


def _device(**overrides):
    base = {
        "id": "dev1",
        "name": "lumi.sensor_occupy.agl8",
        "area_name": "Office",
        "manufacturer": "Aqara",
        "model": "FP1E",
        "device_class": "sensor",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def generator() -> DeviceNameGenerator:
    return DeviceNameGenerator(SimpleNamespace())


def test_generated_name_never_contains_the_manufacturer(generator):
    suggestion = generator._pattern_based_generation(_device(), None)

    assert "aqara" not in suggestion.name.lower()
    # area_id is the key the rubric actually reads (area_name is ignored) —
    # passing the wrong key silently skips the area-prefix check.
    result = score_friendly_name({"friendly_name": suggestion.name, "area_id": "office"})
    assert result.issues == []
    assert result.earned_points == result.max_points


def test_no_area_still_never_falls_back_to_a_brand(generator):
    suggestion = generator._pattern_based_generation(_device(area_name=None), None)

    assert "aqara" not in suggestion.name.lower()


def test_every_composer_produces_the_same_name_for_the_same_device(generator):
    """One composition policy (TAP-6231): the router's convention builder and
    the generator's pattern strategy must agree, because both delegate to
    naming_convention.name_builder.compose_name."""
    from src.api.naming_router import _build_convention_name

    router_name, _confidence, _reasoning = _build_convention_name(
        area_id="office", domain="sensor", device_class=None
    )
    generator_name = generator._pattern_based_generation(_device(), None).name

    assert router_name == generator_name == "Office Sensor"


def test_compose_name_strips_brand_tokens_structurally():
    """The no-brand rule is code, not a docstring (TAP-6234 round 2): the
    hygiene suggester emitted 'Office Hue' from a brand-first model token —
    30 of 93 live devices have one."""
    from src.services.naming_convention.name_builder import compose_name

    assert compose_name("Office", "Hue") == "Office"
    assert compose_name("Office", "Hue Bridge") == "Office Bridge"
    assert compose_name(None, "Aqara") == "Device"


def test_hygiene_suggester_never_emits_a_brand():
    from types import SimpleNamespace

    from src.services.hygiene_analyzer import DeviceHygieneAnalyzer

    analyzer = DeviceHygieneAnalyzer.__new__(DeviceHygieneAnalyzer)
    areas = {"office": SimpleNamespace(name="Office")}
    device = SimpleNamespace(
        area_id="office",
        suggested_area=None,
        model="FP1E Presence",
        integration="zha",
        manufacturer="Aqara",
    )

    name = analyzer._suggest_device_name(device, areas)

    assert name == "Office FP1E"
    result = score_friendly_name({"friendly_name": name, "area_id": "office"})
    assert result.issues == []


def test_strip_brands_matches_the_rubric_substring_semantics():
    """The scorer checks `brand in name_lower` — the composer must drop the
    same tokens it would dock ('Hue-Bridge', 'HueSync', 'Zigbee2MQTT')."""
    from src.services.naming_convention.name_builder import compose_name

    assert compose_name("Office", "Hue-Bridge") == "Office"
    assert compose_name("Office", "HueSync Box") == "Office Box"
    assert compose_name("Office", "Zigbee2MQTT Bridge") == "Office Bridge"


def test_hygiene_suggests_nothing_when_only_brands_are_available():
    """'Device' is not a name — a Hue Bridge on the hue integration with no
    area gets NO rename suggestion rather than a useless one."""
    from types import SimpleNamespace

    from src.services.hygiene_analyzer import DeviceHygieneAnalyzer

    analyzer = DeviceHygieneAnalyzer.__new__(DeviceHygieneAnalyzer)
    device = SimpleNamespace(
        area_id=None,
        suggested_area=None,
        model="Hue Bridge",
        integration="hue",
        manufacturer="Signify Netherlands B.V.",
    )

    assert analyzer._suggest_device_name(device, {}) is None
