"""LocalCalendarRecipe and PowercalcRecipe tests (TAP-5431)."""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.enablement import LocalCalendarRecipe, PowercalcRecipe
from homeiq_ha.client.errors import HAClientError, HAFlowError

from tests.simulators import SimHA

CAL_FORM = {
    "type": "form",
    "flow_id": "f1",
    "data_schema": [
        {"name": "calendar_name", "required": True},
        {"name": "import", "default": "create_empty"},
    ],
}

CAL_DONE = {
    "type": "create_entry",
    "add_entities": [{"entity_id": "calendar.homeiq", "platform": "local_calendar"}],
    "result": {"entry_id": "lc1", "domain": "local_calendar", "state": "loaded"},
}

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


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


def powercalc_recipe() -> PowercalcRecipe:
    return PowercalcRecipe(
        restart_timeout=1.0,
        restart_poll_interval=0.0,
        discovery_timeout=0.05,
        discovery_poll_interval=0.0,
    )


PC_MENU = {
    "type": "menu",
    "flow_id": "gc1",
    "menu_options": ["virtual_power", "menu_library", "group", "global_configuration"],
}


# ---------------------------------------------------------------------------
# LocalCalendarRecipe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calendar_check_needs_apply_on_fresh_instance(sim):
    result = await LocalCalendarRecipe().check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY


@pytest.mark.asyncio
async def test_calendar_apply_asserts_the_created_entity(sim):
    sim.state["flow_first_step"] = CAL_FORM
    sim.state["flow_steps"] = [dict(CAL_DONE)]

    result = await LocalCalendarRecipe().apply(sim)

    assert result.changed[0].after == "calendar.homeiq"
    assert sim.state["flow_inputs"] == [{"calendar_name": "HomeIQ"}]
    check = await LocalCalendarRecipe().check(sim)
    assert check.status is CheckStatus.SATISFIED
    assert check.details["entity_ids"] == ["calendar.homeiq"]


@pytest.mark.asyncio
async def test_calendar_second_apply_reports_zero_changes(sim):
    sim.state["entities"].append(
        {"entity_id": "calendar.homeiq", "platform": "local_calendar"}
    )
    writes_before = list(sim.writes)

    result = await LocalCalendarRecipe().apply(sim)

    assert result.changed == ()
    assert sim.writes == writes_before


@pytest.mark.asyncio
async def test_calendar_apply_refuses_an_unexpected_schema(sim):
    sim.state["flow_first_step"] = {
        "type": "form",
        "flow_id": "f1",
        "data_schema": [{"name": "name", "required": True}],
    }

    with pytest.raises(HAFlowError, match="calendar_name"):
        await LocalCalendarRecipe().apply(sim)

    assert not any(w.startswith("flow_advance") for w in sim.writes)


@pytest.mark.asyncio
async def test_calendar_apply_refuses_success_without_an_entity(sim):
    sim.state["flow_first_step"] = CAL_FORM
    sim.state["flow_steps"] = [{"type": "create_entry"}]

    with pytest.raises(HAClientError, match="no calendar"):
        await LocalCalendarRecipe().apply(sim)


@pytest.mark.asyncio
async def test_calendar_verify_reports_the_live_entities(sim):
    sim.state["entities"].append(
        {"entity_id": "calendar.homeiq", "platform": "local_calendar"}
    )

    result = await LocalCalendarRecipe().verify(sim)

    assert result.ok
    assert result.details["entity_ids"] == ["calendar.homeiq"]


# ---------------------------------------------------------------------------
# PowercalcRecipe
# ---------------------------------------------------------------------------


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
async def test_powercalc_apply_downloads_restarts_and_confirms_discovery(sim):
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
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_current_step"] = {"type": "form", "flow_id": "pf1", "data_schema": []}
    sim.state["flow_steps"] = [
        {"type": "form", "flow_id": "gc1", "data_schema": [{"name": "create_energy_sensors", "default": True}]},
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
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = PC_MENU
    sim.state["flow_current_step"] = {"type": "form", "flow_id": "pf1", "data_schema": []}
    sim.state["flow_steps"] = [
        {
            # The live global-configuration form: vol.Section containers.
            "type": "form",
            "flow_id": "gc1",
            "data_schema": [
                {"name": "power_options", "required": True, "schema": [
                    {"name": "power_sensor_precision", "optional": True},
                ]},
                {"name": "features", "required": True, "schema": [
                    {"name": "create_energy_sensors", "default": True},
                ]},
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
                {"name": "power_options", "required": True, "schema": [
                    {"name": "which_meter", "required": True},
                ]},
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
async def test_powercalc_apply_refuses_a_menu_without_global_configuration(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_first_step"] = dict(PC_MENU, menu_options=["virtual_power", "group"])

    with pytest.raises(HAFlowError, match="global_configuration"):
        await powercalc_recipe().apply(sim)


@pytest.mark.asyncio
async def test_powercalc_apply_refuses_a_form_needing_human_facts(sim):
    sim.state["hacs_repositories"] = [dict(POWERCALC_REPO, installed=True)]
    sim.state["flow_progress"] = [{"flow_id": "pf1", "handler": "powercalc"}]
    sim.state["flow_current_step"] = {
        "type": "form",
        "flow_id": "pf1",
        "data_schema": [{"name": "entity_id", "required": True}],
    }

    with pytest.raises(HAFlowError, match="entity_id"):
        await powercalc_recipe().apply(sim)


@pytest.mark.asyncio
async def test_powercalc_verify_requires_a_numeric_power_state(sim):
    sim.state["config_entries"].append(
        {"entry_id": "pc1", "domain": "powercalc", "state": "loaded"}
    )
    sim.state["entities"].append(
        {"entity_id": "sensor.office_light_power", "platform": "powercalc"}
    )

    sim.state["states"] = [{"entity_id": "sensor.office_light_power", "state": "unavailable"}]
    stale = await powercalc_recipe().verify(sim)

    sim.state["states"] = [{"entity_id": "sensor.office_light_power", "state": "3.4"}]
    live = await powercalc_recipe().verify(sim)

    assert not stale.ok
    assert live.ok
    assert live.details["reporting"] == ["sensor.office_light_power"]
