"""PowercalcRecipe tests (TAP-5431)."""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.powercalc import PowercalcRecipe
from homeiq_ha.client.errors import HAClientError, HAFlowError

from tests.simulators import SimHA

POWERCALC_REPO = {
    "id": "138121412",
    "full_name": "bramstroker/homeassistant-powercalc",
    "installed": False,
}

PC_DONE = {
    "type": "create_entry",
    "add_entities": [
        {"entity_id": "sensor.office_light_power", "platform": "powercalc"},
        {"entity_id": "sensor.office_light_energy", "platform": "powercalc"},
    ],
    "result": {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"},
}

POWER_OK = [{"entity_id": "sensor.office_light_power", "state": "3.4"}]

PC_MENU = {
    "type": "menu",
    "flow_id": "gc1",
    "menu_options": ["virtual_power", "menu_library", "group", "global_configuration"],
}


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


def powercalc_recipe() -> PowercalcRecipe:
    return PowercalcRecipe(
        restart_timeout=1.0,
        restart_poll_interval=0.0,
        restart_min_wait=0.0,
        discovery_timeout=0.05,
        discovery_poll_interval=0.0,
        power_state_timeout=0.05,
    )


@pytest.mark.asyncio
async def test_powercalc_check_reports_absence_from_hacs(sim):
    result = await powercalc_recipe().check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY
    assert "absent from the HACS repository list" in result.summary


@pytest.mark.asyncio
async def test_powercalc_check_distinguishes_download_from_flow(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO)]
    needs_download = await powercalc_recipe().check(sim)

    sim.state["hacs_repositories"][0]["installed"] = True
    needs_flow = await powercalc_recipe().check(sim)

    assert "HACS download" in needs_download.summary
    assert "no loaded config entry" in needs_flow.summary


@pytest.mark.asyncio
async def test_powercalc_check_refuses_a_sensor_that_reports_nothing(sim):
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["entities"].append({"entity_id": "sensor.dead_light_power", "platform": "powercalc"})
    sim.state["states"] = [{"entity_id": "sensor.dead_light_power", "state": "unavailable"}]

    result = await powercalc_recipe().check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY
    assert "none reports a number" in result.summary


@pytest.mark.asyncio
async def test_powercalc_apply_downloads_restarts_and_confirms_discovery(sim):
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO)]
    sim.state["flow_progress"] = [{"flow_id": "pf1", "handler": "powercalc"}]
    sim.state["flow_current_step"] = {"type": "form", "flow_id": "pf1", "data_schema": []}
    sim.state["flow_steps"] = [dict(PC_DONE)]

    result = await powercalc_recipe().apply(sim)

    assert sim.state["hacs_repositories"][0]["installed"] is True
    assert ("homeassistant", "restart", {}) in sim.state["service_calls"]
    assert [c.action for c in result.changed] == [
        "hacs download",
        "restart",
        "configure integration",
    ]
    assert "sensor.office_light_power" in result.summary


@pytest.mark.asyncio
async def test_powercalc_second_apply_reports_zero_changes(sim):
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["entities"].append(
        {"entity_id": "sensor.office_light_power", "platform": "powercalc"}
    )

    result = await powercalc_recipe().apply(sim)

    assert result.changed == ()
    assert sim.state.get("service_calls") is None


@pytest.mark.asyncio
async def test_powercalc_apply_bootstraps_discovery_via_global_config(sim):
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_current_step"] = {"type": "form", "flow_id": "pf1", "data_schema": []}
    sim.state["flow_steps"] = [
        {
            "type": "form",
            "flow_id": "gc1",
            "data_schema": [{"name": "create_energy_sensors", "default": True}],
        },
        {
            "type": "create_entry",
            "result": {"entry_id": "gc1", "domain": "powercalc", "state": "loaded"},
            "add_flows": [{"flow_id": "pf1", "handler": "powercalc"}],
        },
        dict(PC_DONE),
    ]

    result = await powercalc_recipe().apply(sim)

    assert [c.action for c in result.changed] == [
        "configure integration",
        "configure integration",
    ]
    assert result.changed[0].after == "global configuration entry"
    assert sim.state["flow_inputs"][0] == {"next_step_id": "global_configuration"}
    assert "sensor.office_light_power" in result.summary


@pytest.mark.asyncio
async def test_powercalc_submits_sections_as_empty_dicts(sim):
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_current_step"] = {"type": "form", "flow_id": "pf1", "data_schema": []}
    sim.state["flow_steps"] = [
        {
            # The live global-configuration form: vol.Section containers.
            "type": "form",
            "flow_id": "gc1",
            "data_schema": [
                {
                    "name": "power_options",
                    "required": True,
                    "schema": [
                        {"name": "power_sensor_precision", "optional": True},
                    ],
                },
                {
                    "name": "features",
                    "required": True,
                    "schema": [
                        {"name": "create_energy_sensors", "default": True},
                    ],
                },
            ],
        },
        {
            "type": "create_entry",
            "result": {"entry_id": "gc1", "domain": "powercalc", "state": "loaded"},
            "add_flows": [{"flow_id": "pf1", "handler": "powercalc"}],
        },
        dict(PC_DONE),
    ]

    await powercalc_recipe().apply(sim)

    section_input = sim.state["flow_inputs"][1]
    assert section_input == {"power_options": {}, "features": {}}


@pytest.mark.asyncio
async def test_powercalc_refuses_a_section_with_a_required_undefaulted_field(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_steps"] = [
        {
            "type": "form",
            "flow_id": "gc1",
            "data_schema": [
                {
                    "name": "power_options",
                    "required": True,
                    "schema": [
                        {"name": "which_meter", "required": True},
                    ],
                },
            ],
        },
    ]

    with pytest.raises(HAFlowError, match="power_options.which_meter"):
        await powercalc_recipe().apply(sim)


@pytest.mark.asyncio
async def test_powercalc_apply_raises_when_discovery_never_appears(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_steps"] = [
        {
            "type": "create_entry",
            "result": {"entry_id": "gc1", "domain": "powercalc", "state": "loaded"},
        },
    ]

    with pytest.raises(HAClientError, match="refusing to guess"):
        await powercalc_recipe().apply(sim)


@pytest.mark.asyncio
async def test_powercalc_restarts_and_retries_on_already_in_progress(sim):
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_current_step"] = {"type": "form", "flow_id": "pf1", "data_schema": []}
    sim.state["flow_steps"] = [
        # First attempt hits invisible user-flow debris.
        {"type": "abort", "flow_id": "gc1", "reason": "already_in_progress"},
        # Retry after the restart clears it.
        {
            "type": "create_entry",
            "result": {"entry_id": "gc1", "domain": "powercalc", "state": "loaded"},
            "add_flows": [{"flow_id": "pf1", "handler": "powercalc"}],
        },
        dict(PC_DONE),
    ]

    result = await powercalc_recipe().apply(sim)

    assert ("homeassistant", "restart", {}) in sim.state["service_calls"]
    assert "sensor.office_light_power" in result.summary


@pytest.mark.asyncio
async def test_powercalc_aborts_its_own_flow_on_failure(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_steps"] = [
        {"type": "abort", "flow_id": "gc1", "reason": "not_allowed"},
    ]

    with pytest.raises(HAFlowError, match="not_allowed"):
        await powercalc_recipe().apply(sim)

    assert "flow_abort gc1" in sim.rest.writes


@pytest.mark.asyncio
async def test_powercalc_apply_refuses_a_menu_without_global_configuration(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = dict(PC_MENU, menu_options=["virtual_power", "group"])

    with pytest.raises(HAFlowError, match="global_configuration"):
        await powercalc_recipe().apply(sim)


@pytest.mark.asyncio
async def test_powercalc_refuses_when_every_discovery_needs_human_facts(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_progress"] = [
        {
            "flow_id": "pf1",
            "handler": "powercalc",
            "context": {"title_placeholders": {"name": "Office - WLED"}},
        }
    ]
    sim.state["flow_current_step"] = {
        "type": "form",
        "flow_id": "pf1",
        "data_schema": [{"name": "voltage", "required": True}],
    }

    with pytest.raises(HAClientError, match="Office - WLED.*voltage"):
        await powercalc_recipe().apply(sim)


@pytest.mark.asyncio
async def test_powercalc_skips_blocked_flows_and_confirms_the_next(sim):
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_progress"] = [
        {
            "flow_id": "wled1",
            "handler": "powercalc",
            "context": {"title_placeholders": {"name": "Office - WLED"}},
        },
        {
            "flow_id": "hue1",
            "handler": "powercalc",
            "context": {"title_placeholders": {"name": "Office Go - Philips Hue"}},
        },
    ]
    sim.state["flow_current_steps"] = {
        "wled1": {
            "type": "form",
            "flow_id": "wled1",
            "data_schema": [{"name": "voltage", "required": True}],
        },
        "hue1": {"type": "form", "flow_id": "hue1", "data_schema": []},
    }
    sim.state["flow_steps"] = [dict(PC_DONE)]

    result = await powercalc_recipe().apply(sim)

    assert "sensor.office_light_power" in result.summary
    # The blocked WLED flow was skipped, not advanced.
    assert "flow_advance wled1" not in sim.rest.writes
    assert "flow_advance hue1" in sim.rest.writes


@pytest.mark.asyncio
async def test_powercalc_verify_requires_a_numeric_power_state(sim):
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["entities"].append(
        {"entity_id": "sensor.office_light_power", "platform": "powercalc"}
    )

    sim.state["states"] = [{"entity_id": "sensor.office_light_power", "state": "unavailable"}]


def _loaded_powercalc(sim) -> None:
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )


def _light(name: str, device_id: str) -> dict:
    return {"entity_id": f"light.{name}", "state": "on", "attributes": {}, "device_id": device_id}


def _power_sensor(name: str, device_id: str, state: str = "8.0") -> dict:
    return {
        "entity_id": f"sensor.{name}_power",
        "state": state,
        "attributes": {"device_class": "power"},
        "device_id": device_id,
    }


def _load(sim, rows: list[dict]) -> None:
    """Put rows in both the states list and the entity registry.

    Coverage joins a power sensor to the load it measures on the registry's
    device_id, so a fixture that sets states alone cannot exercise it.
    """
    sim.state["states"] = [{k: v for k, v in r.items() if k != "device_id"} for r in rows]
    sim.state["entities"] = [
        {"entity_id": r["entity_id"], "device_id": r.get("device_id"), "platform": "powercalc"}
        for r in rows
    ]


@pytest.mark.asyncio
async def test_powercalc_check_refuses_one_sensor_standing_in_for_a_whole_home(sim):
    """A floor of one is not coverage.

    Regression: the check asserted only that *some* powercalc sensor reported a
    number, so a home with 1 metered light out of 34 audited as satisfied.
    """
    _loaded_powercalc(sim)
    _load(
        sim,
        [_power_sensor("a", "dev0"), _light("l0", "dev0")]
        + [_light(f"l{i}", f"dev{i}") for i in range(1, 11)],
    )

    result = await powercalc_recipe().check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["coverage_ratio"] == round(1 / 11, 3)
    assert len(result.details["uncovered"]) == 10


@pytest.mark.asyncio
async def test_powercalc_check_is_satisfied_once_coverage_clears_the_target(sim):
    _loaded_powercalc(sim)
    _load(
        sim,
        [_power_sensor(f"l{i}", f"dev{i}") for i in range(4)]
        + [_light(f"l{i}", f"dev{i}") for i in range(5)],
    )

    result = await powercalc_recipe().check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert result.details["coverage_ratio"] == 0.8
    assert result.details["uncovered"] == ["light.l4"]


@pytest.mark.asyncio
async def test_powercalc_coverage_joins_on_device_id_not_on_the_entity_name(sim):
    """The sensor name never matches the load's name, and must not have to.

    Powercalc names its sensor after the source's friendly name, so live
    ``light.stairs_bottom_of_stairs`` is metered by
    ``sensor.bottom_of_stairs_power``. A string match misses it, and would
    break on a rename anyway (.claude/rules/friendly-names.md).
    """
    _loaded_powercalc(sim)
    _load(
        sim,
        [
            _power_sensor("bottom_of_stairs", "hue-dev-1", "7.32"),
            _light("stairs_bottom_of_stairs", "hue-dev-1"),
        ],
    )

    result = await powercalc_recipe().check(sim)

    assert result.details["covered"] == ["light.stairs_bottom_of_stairs"]
    assert result.details["coverage_ratio"] == 1.0


@pytest.mark.asyncio
async def test_powercalc_coverage_counts_a_non_powercalc_power_sensor(sim):
    """An Inovelli VZM31-SN meters itself over ZHA; that load is covered."""
    _loaded_powercalc(sim)
    rows = [_light("inovelli_vzm31_sn", "zha-dev-1")]
    sim.state["states"] = [{k: v for k, v in r.items() if k != "device_id"} for r in rows] + [
        {
            "entity_id": "sensor.inovelli_vzm31_sn_power",
            "state": "0.0",
            "attributes": {"device_class": "power"},
        }
    ]
    sim.state["entities"] = [
        {"entity_id": "light.inovelli_vzm31_sn", "device_id": "zha-dev-1", "platform": "zha"},
        {
            "entity_id": "sensor.inovelli_vzm31_sn_power",
            "device_id": "zha-dev-1",
            "platform": "zha",
        },
    ]

    result = await powercalc_recipe().check(sim)

    assert result.details["covered"] == ["light.inovelli_vzm31_sn"]


@pytest.mark.asyncio
async def test_powercalc_check_excludes_groups_and_config_toggles_with_reasons(sim):
    """The denominator is physical loads, and every exclusion states why."""
    _loaded_powercalc(sim)
    sim.state["states"] = [
        {"entity_id": "sensor.real_power", "state": "9.1", "attributes": {"device_class": "power"}},
        {"entity_id": "light.real", "state": "on", "attributes": {}},
        {
            "entity_id": "light.kitchen_group",
            "state": "on",
            "attributes": {"entity_id": ["light.real"]},
        },
        {"entity_id": "switch.smart_bulb_mode", "state": "off", "attributes": {}},
        {"entity_id": "switch.a_plug", "state": "on", "attributes": {"device_class": "outlet"}},
    ]
    sim.state["entities"] = [
        {"entity_id": "sensor.real_power", "device_id": "dev-a", "platform": "powercalc"},
        {"entity_id": "light.real", "device_id": "dev-a", "platform": "hue"},
        {"entity_id": "light.kitchen_group", "device_id": "dev-g", "platform": "hue"},
        {"entity_id": "switch.smart_bulb_mode", "device_id": "dev-i", "platform": "zha"},
        {"entity_id": "switch.a_plug", "device_id": "dev-p", "platform": "zha"},
    ]

    result = await powercalc_recipe().check(sim)

    excluded = result.details["excluded"]
    assert excluded["group_entity_sums_its_members"] == ["light.kitchen_group"]
    assert excluded["switch_is_a_config_toggle_not_a_load"] == ["switch.smart_bulb_mode"]
    # the outlet is a real load, so it counts against coverage
    assert sorted(result.details["eligible"]) == ["light.real", "switch.a_plug"]
    assert result.details["uncovered"] == ["switch.a_plug"]


@pytest.mark.asyncio
async def test_powercalc_apply_confirms_every_defaulted_flow_not_just_one(sim):
    """One reporting sensor proves the integration works; it does not meter a home.

    The apply path used to stop at the first flow that produced a number, which
    left every other discovered device sitting in the wizard queue — the reason
    this home read 3 of 43 metered while the integration reported healthy.
    """
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    # One sensor already reports, so the "get at least one" bootstrap is
    # satisfied and what is under test is what happens to the REST.
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["entities"].append(
        {"entity_id": "sensor.office_light_power", "platform": "powercalc"}
    )
    sim.state["flow_progress"] = [
        {
            "flow_id": f"hue{n}",
            "handler": "powercalc",
            "context": {"title_placeholders": {"name": f"Downlight {n} - Philips Hue"}},
        }
        for n in range(1, 5)
    ]
    sim.state["flow_current_step"] = {"type": "form", "flow_id": "hue1", "data_schema": []}

    result = await powercalc_recipe().apply(sim)

    confirmed = [c for c in result.changed if c.action == "configure integration"]
    assert len(confirmed) == 4, (
        f"expected all four defaulted flows confirmed, got {len(confirmed)} — "
        "apply stopped early and left devices unmetered"
    )
    assert not sim.state["flow_progress"], "flows were left outstanding after apply"


@pytest.mark.asyncio
async def test_powercalc_apply_leaves_flows_needing_human_facts_in_triage(sim):
    """A question for a human is not something to answer with an invented number.

    WLED profiles require `voltage` — a fact about the house, not the device.
    Guessing it would put a fabricated figure behind every energy number derived
    from that sensor.
    """
    sim.state["states"] = list(POWER_OK)
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["entities"].append(
        {"entity_id": "sensor.office_light_power", "platform": "powercalc"}
    )
    sim.state["flow_progress"] = [
        {
            "flow_id": "hue1",
            "handler": "powercalc",
            "context": {"title_placeholders": {"name": "Downlight - Philips Hue"}},
        },
        {
            "flow_id": "wled1",
            "handler": "powercalc",
            "context": {"title_placeholders": {"name": "Strip - WLED"}},
        },
    ]
    sim.state["flow_current_steps"] = {
        "hue1": {"type": "form", "flow_id": "hue1", "data_schema": []},
        "wled1": {
            "type": "form",
            "flow_id": "wled1",
            "data_schema": [{"name": "voltage", "required": True}],
        },
    }

    result = await powercalc_recipe().apply(sim)

    assert any(c.action == "configure integration" for c in result.changed)
    # The blocked flow is still outstanding, where a human can answer it.
    assert [f["flow_id"] for f in sim.state["flow_progress"]] == ["wled1"]


@pytest.mark.asyncio
async def test_powercalc_check_says_why_each_load_is_uncovered(sim):
    """A bare list of uncovered ids says "something is wrong somewhere".

    The three causes need different actions and only one is a software problem:
    a device that is not powered, a profile that wants a fact about the
    installation, and hardware Powercalc has no profile for at all.
    """
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["entities"] = [
        {"entity_id": "light.dead", "device_id": "d1"},
        {"entity_id": "light.strip", "device_id": "d2"},
        {"entity_id": "media_player.tv", "device_id": "d3"},
        {"entity_id": "sensor.office_light_power", "platform": "powercalc"},
    ]
    sim.state["states"] = [
        {"entity_id": "light.dead", "state": "unavailable", "attributes": {}},
        {"entity_id": "light.strip", "state": "on", "attributes": {}},
        {"entity_id": "media_player.tv", "state": "on", "attributes": {}},
        {"entity_id": "sensor.office_light_power", "state": "3.4"},
    ]

    result = await powercalc_recipe().check(sim)

    reasons = result.details["uncovered_reasons"]
    assert "not reachable" in reasons["light.dead"]
    assert "no Powercalc profile" in reasons["media_player.tv"]
    assert "supply voltage" in reasons["light.strip"]
    # Every uncovered load has one; a reason nobody can act on is still better
    # than a silent gap, but a missing one is a hole.
    assert set(reasons) == set(result.details["uncovered"])


@pytest.mark.asyncio
async def test_powercalc_counts_one_physical_device_once(sim):
    """A TV found by three integrations is one load, not three.

    samsungtv, dlna_dmr and cast each register their own Home Assistant device
    for the same television, so a per-entity count meters it up to three times —
    the same double-count a light group commits, arriving from the other
    direction. The MAC is protocol-native identity and settles it; the identical
    NAMES those integrations report would not, and matching on them would be a
    name match wearing a better job title.
    """
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["devices"] = [
        {"id": "d_samsung", "connections": [["mac", "28:AF:42:1E:40:78"]]},
        {"id": "d_dlna", "connections": [["upnp", "uuid:x"], ["mac", "28:af:42:1e:40:78"]]},
        {"id": "d_other", "connections": [["mac", "aa:bb:cc:dd:ee:ff"]]},
    ]
    sim.state["entities"] = [
        {"entity_id": "media_player.tv_samsung", "device_id": "d_samsung"},
        {"entity_id": "media_player.tv_dlna", "device_id": "d_dlna"},
        {"entity_id": "media_player.other_tv", "device_id": "d_other"},
        {"entity_id": "sensor.tv_power", "device_id": "d_samsung", "platform": "powercalc"},
    ]
    sim.state["states"] = [
        {"entity_id": "media_player.tv_samsung", "state": "on", "attributes": {}},
        {"entity_id": "media_player.tv_dlna", "state": "on", "attributes": {}},
        {"entity_id": "media_player.other_tv", "state": "on", "attributes": {}},
        {
            "entity_id": "sensor.tv_power",
            "state": "42.0",
            "attributes": {"device_class": "power"},
        },
    ]

    result = await powercalc_recipe().check(sim)
    det = result.details

    assert len(det["eligible"]) == 2, f"the same TV was counted twice: {det['eligible']}"
    # The representative is chosen by sort order, so the count cannot drift
    # between runs on dict ordering.
    assert det["excluded"]["same_physical_device_already_counted"] == ["media_player.tv_samsung"]
    # The reading belongs to the hardware, not to the integration that surfaced
    # it: the power sensor sits on d_samsung, and the surviving representative
    # is the dlna entity, yet the physical TV still counts as metered.
    assert "media_player.tv_dlna" in det["covered"]
    assert "media_player.other_tv" not in det["covered"]


@pytest.mark.asyncio
async def test_powercalc_keeps_devices_without_a_mac_separate(sim):
    """Absence of a MAC is not evidence that two devices are the same one."""
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["devices"] = [{"id": "d1", "connections": []}, {"id": "d2", "connections": []}]
    sim.state["entities"] = [
        {"entity_id": "media_player.a", "device_id": "d1"},
        {"entity_id": "media_player.b", "device_id": "d2"},
    ]
    sim.state["states"] = [
        {"entity_id": "media_player.a", "state": "on", "attributes": {}},
        {"entity_id": "media_player.b", "state": "on", "attributes": {}},
    ]

    result = await powercalc_recipe().check(sim)

    assert len(result.details["eligible"]) == 2
    assert result.details["excluded"]["same_physical_device_already_counted"] == []
