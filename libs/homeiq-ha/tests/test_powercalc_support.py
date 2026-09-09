"""Unit tests for the pure computation behind PowercalcRecipe.

Every function in :mod:`homeiq_ha.agent.powercalc_support` takes plain data
and does no I/O, so these tests build the fixtures directly rather than
going through the simulator (see test_powercalc.py for the recipe-level,
end-to-end behavior).
"""

from __future__ import annotations

from homeiq_ha.agent.powercalc_support import (
    compute_coverage,
    flow_label,
    is_number,
    live_light_names,
)

# --- is_number --------------------------------------------------------------


def test_is_number_true_for_numeric_strings():
    assert is_number("5")
    assert is_number("5.5")
    assert is_number(5)


def test_is_number_false_for_non_numeric_and_none():
    assert not is_number("unavailable")
    assert not is_number(None)
    assert not is_number("")


# --- live_light_names --------------------------------------------------------


def test_live_light_names_includes_only_available_lights():
    states = [
        {"entity_id": "light.kitchen", "state": "on", "attributes": {"friendly_name": "Kitchen"}},
        {
            "entity_id": "light.stairs",
            "state": "unavailable",
            "attributes": {"friendly_name": "Stairs"},
        },
        {"entity_id": "switch.fan", "state": "on", "attributes": {"friendly_name": "Fan"}},
    ]
    assert live_light_names(states) == {"Kitchen"}


# --- flow_label ---------------------------------------------------------------


def test_flow_label_ranks_available_light_first():
    live_names = {"Kitchen"}
    flow = {"flow_id": "f1", "context": {"title_placeholders": {"name": "Kitchen - Signify"}}}

    not_alive, returned_flow, label = flow_label(flow, live_names)

    assert not_alive is False
    assert returned_flow is flow
    assert label == "Kitchen - Signify"


def test_flow_label_ranks_unavailable_light_last():
    not_alive, _, _ = flow_label(
        {"flow_id": "f2", "context": {"title_placeholders": {"name": "Stairs - Signify"}}},
        live_names=set(),
    )
    assert not_alive is True


# --- compute_coverage ---------------------------------------------------------


def _power_state(entity_id: str, device_class: str = "power", state: str = "42") -> dict:
    return {
        "entity_id": entity_id,
        "state": state,
        "attributes": {"device_class": device_class},
    }


def test_compute_coverage_marks_a_metered_light_covered():
    states = [
        {"entity_id": "light.kitchen", "state": "on", "attributes": {}},
        _power_state("sensor.kitchen_power"),
    ]
    registry = [
        {"entity_id": "light.kitchen", "device_id": "dev1"},
        {"entity_id": "sensor.kitchen_power", "device_id": "dev1"},
    ]

    result = compute_coverage(states, registry, devices_registry=[])

    assert result["eligible"] == {"light.kitchen"}
    assert result["covered"] == {"light.kitchen"}
    assert result["uncovered_reasons"] == {}


def test_compute_coverage_excludes_group_entities():
    states = [{"entity_id": "light.group", "state": "on", "attributes": {"entity_id": ["light.a"]}}]

    result = compute_coverage(states, registry=[], devices_registry=[])

    assert result["excluded"]["group_entity_sums_its_members"] == ["light.group"]
    assert "light.group" not in result["eligible"]


def test_compute_coverage_excludes_non_outlet_switches():
    states = [{"entity_id": "switch.config_toggle", "state": "on", "attributes": {}}]

    result = compute_coverage(states, registry=[], devices_registry=[])

    assert result["excluded"]["switch_is_a_config_toggle_not_a_load"] == ["switch.config_toggle"]


def test_compute_coverage_excludes_entities_with_no_device():
    states = [{"entity_id": "light.orphan", "state": "on", "attributes": {}}]

    result = compute_coverage(states, registry=[], devices_registry=[])

    assert result["excluded"]["no_device_in_the_entity_registry"] == ["light.orphan"]


def test_compute_coverage_dedupes_entities_sharing_a_mac():
    """Two HA devices for one physical unit (e.g. samsungtv + cast) count once."""
    states = [
        {"entity_id": "media_player.tv_samsungtv", "state": "on", "attributes": {}},
        {"entity_id": "media_player.tv_cast", "state": "on", "attributes": {}},
        _power_state("sensor.tv_power"),
    ]
    registry = [
        {"entity_id": "media_player.tv_samsungtv", "device_id": "dev_samsungtv"},
        {"entity_id": "media_player.tv_cast", "device_id": "dev_cast"},
        {"entity_id": "sensor.tv_power", "device_id": "dev_samsungtv"},
    ]
    devices_registry = [
        {"id": "dev_samsungtv", "connections": [["mac", "AA:BB:CC:DD:EE:FF"]]},
        {"id": "dev_cast", "connections": [["mac", "AA:BB:CC:DD:EE:FF"]]},
    ]

    result = compute_coverage(states, registry, devices_registry)

    assert len(result["eligible"]) == 1
    assert result["excluded"]["same_physical_device_already_counted"]
    assert result["covered"] == result["eligible"]


def test_compute_coverage_reasons_unavailable_load():
    states = [{"entity_id": "light.stairs", "state": "unavailable", "attributes": {}}]
    registry = [{"entity_id": "light.stairs", "device_id": "dev1"}]

    result = compute_coverage(states, registry, devices_registry=[])

    assert "unavailable" in result["uncovered_reasons"]["light.stairs"]


def test_compute_coverage_reasons_media_player_needs_manual_wattage():
    states = [{"entity_id": "media_player.tv", "state": "on", "attributes": {}}]
    registry = [{"entity_id": "media_player.tv", "device_id": "dev1"}]

    result = compute_coverage(states, registry, devices_registry=[])

    assert "manually" in result["uncovered_reasons"]["media_player.tv"]


def test_compute_coverage_reasons_default_is_no_closing_discovery_flow():
    states = [{"entity_id": "light.wled", "state": "on", "attributes": {}}]
    registry = [{"entity_id": "light.wled", "device_id": "dev1"}]

    result = compute_coverage(states, registry, devices_registry=[])

    assert "discovery flow" in result["uncovered_reasons"]["light.wled"]
