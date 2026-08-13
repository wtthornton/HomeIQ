"""LocalCalendarRecipe tests (TAP-5431)."""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.enablement import LocalCalendarRecipe
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




@pytest.fixture
def sim() -> SimHA:
    return SimHA()





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
