"""Regression: recipe execution order is fixed at the producer (TAP-6467/6468).

Phase order lives in the ``PHASE_*`` constants (``agent/recipe.py:35-40``) and
the ``sorted(recipes, key=lambda r: (r.phase, r.name))`` in
``HAInitAgent.__init__`` (``agent/engine.py:123``) -- never in ``wizard.py``,
which must consume whatever order the engine hands it. This test fails if
either producer regresses: a name-only sort or an unsorted (insertion-order)
constructor both produce a different sequence than the one asserted here.
"""

from __future__ import annotations

from typing import Any

from homeiq_ha.agent.engine import HAInitAgent
from homeiq_ha.agent.recipe import (
    PHASE_ADDONS,
    PHASE_CORRECTNESS,
    PHASE_HACS,
    PHASE_SAFETY,
    ApplyResult,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)


class _StubRecipe(Recipe):
    """A recipe that does nothing; only ``name``/``phase`` matter here."""

    def __init__(self, name: str, phase: int) -> None:
        self.name = name
        self.phase = phase

    async def check(self, _ha: Any) -> CheckResult:
        return CheckResult(CheckStatus.SATISFIED, "stub")

    async def plan(self, _ha: Any) -> Plan:
        return Plan(())

    async def apply(self, _ha: Any) -> ApplyResult:
        return ApplyResult((), "stub")

    async def verify(self, _ha: Any) -> VerifyResult:
        return VerifyResult(True, "stub")


def test_recipes_run_in_ascending_phase_then_name_order() -> None:
    """Inserted out of phase order, with names that disagree with phase order
    both alphabetically and by insertion position -- so neither a name-only
    sort nor "whatever order the caller passed" would coincidentally pass.
    """
    recipes = [
        _StubRecipe(name="zzz_last_by_name", phase=PHASE_SAFETY),
        _StubRecipe(name="aaa_first_by_name", phase=PHASE_HACS),
        _StubRecipe(name="mmm_middle_by_name", phase=PHASE_CORRECTNESS),
        _StubRecipe(name="bbb_early_by_name", phase=PHASE_ADDONS),
    ]

    agent = HAInitAgent(recipes)

    assert [r.name for r in agent.recipes] == [
        "zzz_last_by_name",  # phase 1 (safety) runs first regardless of name
        "mmm_middle_by_name",  # phase 2 (correctness)
        "bbb_early_by_name",  # phase 4 (addons)
        "aaa_first_by_name",  # phase 5 (hacs) runs last regardless of name
    ]
    assert [r.phase for r in agent.recipes] == sorted(r.phase for r in recipes)


def test_same_phase_recipes_break_ties_by_name() -> None:
    recipes = [
        _StubRecipe(name="z", phase=PHASE_SAFETY),
        _StubRecipe(name="a", phase=PHASE_SAFETY),
        _StubRecipe(name="m", phase=PHASE_SAFETY),
    ]

    agent = HAInitAgent(recipes)

    assert [r.name for r in agent.recipes] == ["a", "m", "z"]
