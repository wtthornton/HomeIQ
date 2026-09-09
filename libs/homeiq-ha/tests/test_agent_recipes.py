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
from homeiq_ha.agent.recipe import PHASE_HACS
from homeiq_ha.agent.recipes import (
    AreasRecipe,
    CoreConfigRecipe,
    HACSAbsentRecipe,
    default_recipes,
)

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


# --- HACS confirm-absent (TAP-6486) ---------------------------------------


@pytest.mark.asyncio
async def test_hacs_absent_is_satisfied_on_a_real_absent_entry_list(sim):
    """A real absent config-entries list, never a mocked truthy."""
    result = await HACSAbsentRecipe().check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert (await HACSAbsentRecipe().verify(sim)).ok


@pytest.mark.asyncio
async def test_hacs_absent_is_never_satisfied_when_hacs_is_present():
    sim = SimHA(
        {
            **FRESH_INSTANCE,
            "config_entries": [{"entry_id": "e1", "domain": "hacs", "state": "loaded"}],
        }
    )

    result = await HACSAbsentRecipe().check(sim)

    assert result.status is not CheckStatus.SATISFIED
    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert not (await HACSAbsentRecipe().verify(sim)).ok


def test_phase_5_carries_no_recipe_that_requires_a_human():
    """No add-on/HACS bootstrap step survives; phase 5 is confirm-only."""
    phase_5 = [r for r in default_recipes() if r.phase == PHASE_HACS]

    assert phase_5, "expected at least one phase-5 recipe"
    assert not any(r.requires_human for r in phase_5), [r.name for r in phase_5 if r.requires_human]


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
