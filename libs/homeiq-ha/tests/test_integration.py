"""IntegrationRecipe base-class tests, independent of any subclass.

Reuses the fixture simulator from ``test_agent_recipes``.
"""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.integration import IntegrationRecipe, TeamTrackerRecipe

from tests.simulators import FRESH_INSTANCE, SimHA


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


@pytest.mark.asyncio
async def test_check_reports_needs_apply_when_unconfigured(sim):
    result = await IntegrationRecipe("nws").check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY


@pytest.mark.asyncio
async def test_check_is_satisfied_on_a_loaded_entry(sim):
    sim.state["config_entries"].append({"entry_id": "e1", "domain": "nws", "state": "loaded"})

    result = await IntegrationRecipe("nws").check(sim)

    assert result.status is CheckStatus.SATISFIED


@pytest.mark.asyncio
async def test_apply_skips_the_flow_when_an_entry_already_exists(sim):
    sim.state["config_entries"].append({"entry_id": "e1", "domain": "nws", "state": "setup_retry"})

    result = await IntegrationRecipe("nws").apply(sim)

    assert result.change_count == 0
    assert sim.rest.writes == []


@pytest.mark.asyncio
async def test_apply_runs_the_flow_and_verify_rereads(sim):
    recipe = IntegrationRecipe("nws")

    applied = await recipe.apply(sim)

    assert applied.change_count == 1
    verified = await recipe.verify(sim)
    assert verified.ok


@pytest.mark.asyncio
async def test_needs_user_input_blocks_instead_of_guessing(sim):
    from homeiq_ha.client.errors import HAHumanGateRequired

    recipe = IntegrationRecipe("nws", needs_user_input="Pick your weather station — a site fact.")

    result = await recipe.check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "weather station" in (result.human_action or "")

    with pytest.raises(HAHumanGateRequired):
        await recipe.apply(sim)
    assert sim.rest.writes == [], "no flow may be driven with placeholder input"


@pytest.mark.asyncio
async def test_needs_user_input_is_satisfied_once_a_person_configured_it(sim):
    sim.state["config_entries"].append({"entry_id": "e1", "domain": "nws", "state": "loaded"})

    result = await IntegrationRecipe("nws", needs_user_input="anything").check(sim)

    assert result.status is CheckStatus.SATISFIED


# --- Team Tracker entity_id trap (moved from test_agent_recipes.py, TAP-5921) ---


@pytest.mark.asyncio
async def test_team_tracker_blocks_when_the_entity_id_lacks_the_marker():
    """The UI flow names the sensor "{league} - {team}", so the entity_id is
    sensor.nfl_las_vegas_raiders and sports-api — which filters on the
    substring 'team_tracker' — would match nothing."""
    sim = SimHA(
        {
            **FRESH_INSTANCE,
            "config_entries": [{"entry_id": "e1", "domain": "teamtracker", "state": "loaded"}],
            "entities": [{"entity_id": "sensor.nfl_las_vegas_raiders"}],
        }
    )

    result = await TeamTrackerRecipe().check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "team_tracker" in (result.human_action or "")
    assert not (await TeamTrackerRecipe().verify(sim)).ok


@pytest.mark.asyncio
async def test_team_tracker_satisfied_when_the_entity_id_carries_the_marker():
    sim = SimHA(
        {
            **FRESH_INSTANCE,
            "config_entries": [{"entry_id": "e1", "domain": "teamtracker", "state": "loaded"}],
            "entities": [{"entity_id": "sensor.team_tracker_raiders"}],
        }
    )

    result = await TeamTrackerRecipe().check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert result.details["entity_ids"] == ["sensor.team_tracker_raiders"]
    assert (await TeamTrackerRecipe().verify(sim)).ok
