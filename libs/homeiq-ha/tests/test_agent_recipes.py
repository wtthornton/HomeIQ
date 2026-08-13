"""Cross-cutting recipe tests against fixtures, never the live home.

The simulator (tests/simulators.py) mirrors the shapes read live from the
target instance, so a recipe that works here works there. Per-cluster tests
live with their recipe modules (test_backup.py, test_organization.py,
test_integration.py, test_diagnostics.py — TAP-5921); this file keeps the
whole-set audits plus the small phase-2/4 recipes that stayed in the hub.
"""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus, HAInitAgent
from homeiq_ha.agent.recipes import (
    AddonRecipe,
    AreasRecipe,
    CoreConfigRecipe,
    default_recipes,
)
from homeiq_ha.client.errors import HAHumanGateRequired

from tests.simulators import FRESH_INSTANCE, SimHA

# --- audit over the full default set --------------------------------------


@pytest.mark.asyncio
async def test_audit_of_the_default_set_writes_nothing_and_classifies_everything(sim):
    agent = HAInitAgent(default_recipes())

    report = await agent.audit(sim)

    assert sim.writes == [], f"audit wrote: {sim.writes}"
    assert report.wrote_nothing
    assert len(report.outcomes) == len(default_recipes())
    # Every recipe produced a status and none crashed.
    assert all(o.error is None for o in report.outcomes), [
        (o.name, o.error) for o in report.outcomes if o.error
    ]
    assert {o.check.status for o in report.outcomes} <= set(CheckStatus)


# --- core config ----------------------------------------------------------


@pytest.mark.asyncio
async def test_core_config_satisfied_when_already_correct(sim):
    result = await CoreConfigRecipe(currency="USD", country="US").check(sim)
    assert result.status is CheckStatus.SATISFIED


@pytest.mark.asyncio
async def test_core_config_detects_the_eur_default():
    sim = SimHA({**FRESH_INSTANCE, "core_config": {"currency": "EUR", "country": "US"}})
    result = await CoreConfigRecipe(currency="USD").check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert "EUR" in result.details["drift"][0]


# --- add-ons --------------------------------------------------------------


@pytest.mark.asyncio
async def test_addon_installs_and_starts(sim):
    recipe = AddonRecipe("core_ssh", title="Terminal & SSH")
    assert (await recipe.check(sim)).status is CheckStatus.NEEDS_APPLY

    result = await recipe.apply(sim)

    assert result.change_count == 2
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_addon_is_idempotent(sim):
    recipe = AddonRecipe("otbr")
    await recipe.apply(sim)
    assert (await recipe.apply(sim)).change_count == 0


@pytest.mark.asyncio
async def test_installed_but_stopped_addon_needs_apply():
    sim = SimHA({**FRESH_INSTANCE, "addons": [{"slug": "otbr", "state": "stopped"}]})
    result = await AddonRecipe("otbr").check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["state"] == "stopped"


@pytest.mark.asyncio
async def test_addon_with_unset_required_option_is_blocked_on_human():
    """OTBR live: required option 'device' is null and only a person knows
    which serial port carries the Thread radio. check classifies, apply
    raises the human gate before ever issuing a start."""
    sim = SimHA(
        {
            **FRESH_INSTANCE,
            "addons": [{"slug": "otbr", "state": "stopped"}],
            "addon_info": {
                "otbr": {
                    "options": {"device": None, "baudrate": "460800"},
                    "schema": [
                        {"name": "device", "required": True, "type": "select"},
                        {"name": "baudrate", "required": True, "type": "select"},
                    ],
                }
            },
        }
    )
    recipe = AddonRecipe("otbr")

    result = await recipe.check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert result.details["unconfigured"] == ["device"]

    with pytest.raises(HAHumanGateRequired):
        await recipe.apply(sim)
    assert not any("start" in w for w in sim.writes), "no start attempt allowed"


# --- end-to-end idempotency ----------------------------------------------


@pytest.mark.asyncio
async def test_second_apply_of_phase_three_makes_zero_changes(sim):
    agent = HAInitAgent([AreasRecipe(("Living Room", "Office"))])

    async def backup(_label: str) -> None:
        return None

    first = await agent.apply(sim, phase=3, backup=backup)
    second = await agent.apply(sim, phase=3, backup=backup)

    assert first.total_changes == 1
    assert second.total_changes == 0, second.describe()
