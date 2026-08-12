"""IntegrationRecipe base-class tests, independent of any subclass.

Reuses the fixture simulator from ``test_agent_recipes``.
"""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.integration import IntegrationRecipe

from tests.test_agent_recipes import SimHA


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
