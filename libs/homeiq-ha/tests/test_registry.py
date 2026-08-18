"""Registry-names recipes: create-if-missing semantics and the human gate.

Moved from test_agent_recipes.py (TAP-5921) alongside the recipes' move into
homeiq_ha.agent.registry.
"""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.recipes import AreasRecipe, DevicesHaveAreasRecipe


@pytest.mark.asyncio
async def test_areas_creates_only_what_is_missing(sim):
    recipe = AreasRecipe(("Living Room", "Kitchen", "Bedroom", "Office"))

    result = await recipe.apply(sim)

    assert result.change_count == 1
    assert "Office" in result.changed[0].target


@pytest.mark.asyncio
async def test_areas_is_idempotent(sim):
    recipe = AreasRecipe(("Living Room", "Office"))
    await recipe.apply(sim)
    assert (await recipe.apply(sim)).change_count == 0
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_unassigned_devices_are_a_human_decision_not_a_guess(sim):
    result = await DevicesHaveAreasRecipe().check(sim)
    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert len(result.details["unassigned"]) == 19
    # {id, name} pairs: the id is what /answers consumes (a display name
    # posted as a device_id could never converge), the name is displayed.
    assert result.details["unassigned"][0] == {"id": "dev0", "name": "WLED 0"}
    # Nothing is inferred from device names.
    assert (await DevicesHaveAreasRecipe().apply(sim)).change_count == 0
