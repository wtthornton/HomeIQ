"""Cross-cutting recipe tests against fixtures, never the live home.

The simulator (tests/simulators.py) mirrors the shapes read live from the
target instance, so a recipe that works here works there. Per-cluster tests
live with their recipe modules (test_backup.py, test_organization.py,
test_integration.py, test_diagnostics.py — TAP-5921); this file keeps the
whole-set audits plus the small phase-2/4 recipes that stayed in the hub.
"""

from __future__ import annotations

import os

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


class _FakeHostFiles:
    """A ``HostFiles`` double that never touches disk, network, or the environment.

    Applicability wiring (:func:`~homeiq_ha.agent.host_files.host_files_from_env`)
    is a build-time concern, resolved once in :func:`default_recipes`; this
    double stands in for whatever transport that resolution produced so the
    guard test below can drive every recipe's ``check()`` without an SSH
    add-on or a real ``/config`` mount, and so a bogus env read inside
    ``check()`` itself has nothing legitimate to hide behind.
    """

    async def read_text(self, path: str) -> str:  # noqa: ARG002 - Protocol shape
        return ""

    async def write_text(self, path: str, content: str) -> str | None:  # noqa: ARG002
        return None


@pytest.mark.asyncio
async def test_no_default_recipe_reads_ssh_host_during_applicab_check(sim, monkeypatch):
    """Guards VAL-031: applicability must come from the transport a recipe was
    already built with, never a recipe re-reading ``HOMEIQ_HA_SSH_HOST``
    inside ``check()`` itself.

    Regression for a mutation that inserted, at the top of one recipe's
    ``check()``::

        import os
        if not os.environ.get("HOMEIQ_HA_SSH_HOST"):
            return <the not-applicable outcome that method already returns>

    ``host_files_from_env`` is patched to a transport double that needs no
    env var, so every default recipe is fully "provisioned" — any read of
    ``HOMEIQ_HA_SSH_HOST`` observed during ``check()`` can only be the
    mutation re-deriving applicability on its own, never the recipe's real
    ``self.host_files is None`` gate (see ``host_files_from_env``'s own
    docstring: ``HOMEIQ_HA_BACKEND`` is the only switch between transports;
    ``HOMEIQ_HA_SSH_HOST``'s presence never is).
    """
    monkeypatch.setattr("homeiq_ha.agent.recipes.host_files_from_env", lambda: _FakeHostFiles())
    monkeypatch.delenv("HOMEIQ_HA_SSH_HOST", raising=False)
    recipes = default_recipes()

    class _SentinelEnviron(dict):
        """A copy of the real environment that traps reads of one key.

        Subclassing ``dict`` (rather than wrapping ``os.environ`` itself)
        keeps every other env lookup a plain, working dict lookup, so nothing
        outside the mutation's own read is disturbed.
        """

        def get(self, key, *args):
            if key == "HOMEIQ_HA_SSH_HOST":
                raise AssertionError("os.environ.get('HOMEIQ_HA_SSH_HOST') read during check()")
            return dict.get(self, key, *args)

        def __getitem__(self, key):
            if key == "HOMEIQ_HA_SSH_HOST":
                raise AssertionError("os.environ['HOMEIQ_HA_SSH_HOST'] read during check()")
            return dict.__getitem__(self, key)

    monkeypatch.setattr(os, "environ", _SentinelEnviron(os.environ))

    for recipe in recipes:
        try:
            result = await recipe.check(sim)
        except AssertionError as exc:
            raise AssertionError(
                f"{recipe.name} read HOMEIQ_HA_SSH_HOST during check(): {exc}"
            ) from None
        text = f"{result.summary} {result.details}".lower()
        assert "homeiq_ha_ssh_host" not in text, (recipe.name, result.summary, result.details)
        assert "ssh" not in text, (recipe.name, result.summary, result.details)


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
