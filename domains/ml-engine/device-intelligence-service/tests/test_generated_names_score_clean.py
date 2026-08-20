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
