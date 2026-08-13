"""Wizard queue assembly: audit-row mapping, discovery mapping, read-only (TAP-5943)."""

from __future__ import annotations

import pytest
from homeiq_ha.agent.recipes import DevicesHaveAreasRecipe, default_recipes
from homeiq_ha.agent.wizard import build_queue

from tests.simulators import SimHA


@pytest.mark.asyncio
async def test_blocked_audit_rows_become_items_with_verbatim_human_action(sim: SimHA):
    """FRESH_INSTANCE has 19 unassigned devices, so DevicesHaveAreasRecipe
    blocks — its human_action must land on the item word-for-word."""
    recipe = DevicesHaveAreasRecipe()
    expected = (await recipe.check(sim)).human_action

    payload = await build_queue(sim, [recipe])

    (item,) = payload["items"]
    assert item["kind"] == "audit_blocked"
    assert item["id"] == "audit:organization.device_areas"
    assert item["human_action"] == expected
    assert item["decision"]["type"] == "area_assignment"
    assert len(item["decision"]["devices"]) == 19
    # options come from the live area registry, not a hardcoded list
    assert item["decision"]["options"] == ["Living Room", "Kitchen", "Bedroom"]


@pytest.mark.asyncio
async def test_discovery_flows_become_triage_items_with_readiness(sim: SimHA):
    sim.state["flow_progress"] = [
        {
            "flow_id": "f1",
            "handler": "homekit_controller",
            "context": {"source": "zeroconf", "title_placeholders": {"name": "Ecobee"}},
        },
        {
            "flow_id": "f2",
            "handler": "dlna_dmr",
            "context": {"source": "ssdp", "title_placeholders": {"name": "TV"}},
        },
    ]
    payload = await build_queue(sim, [])

    homekit, dlna = payload["items"]
    assert homekit["kind"] == "discovery"
    assert homekit["id"] == "flow:f1"
    assert homekit["handler"] == "homekit_controller"
    assert homekit["source"] == "zeroconf"
    assert homekit["title_placeholders"] == {"name": "Ecobee"}
    assert homekit["decision"] == {"type": "select", "options": ["add", "ignore", "later"]}
    # HomeKit needs a person at the device for the PIN; DLNA does not.
    assert homekit["readiness"] is True and homekit["readiness_reason"]
    assert dlna["readiness"] is False and dlna["readiness_reason"] is None


@pytest.mark.asyncio
async def test_queue_over_the_full_default_set_issues_zero_writes(sim: SimHA):
    payload = await build_queue(sim, default_recipes())
    assert sim.writes == [], f"queue wrote: {sim.writes}"
    assert payload["reads"], "read journal is the read-only evidence"
    assert all(r.startswith(("ws ", "rest GET ")) for r in payload["reads"])
    # every blocked row surfaced as an item, none invented
    blocked_ids = {i["id"] for i in payload["items"] if i["kind"] == "audit_blocked"}
    assert "audit:organization.device_areas" in blocked_ids


@pytest.mark.asyncio
async def test_unknown_blocked_kind_degrades_to_acknowledge(sim: SimHA):
    """A future recipe with a new name must not crash the queue."""
    from homeiq_ha.agent.recipe import (
        ApplyResult,
        CheckResult,
        CheckStatus,
        Plan,
        Recipe,
        VerifyResult,
    )

    class Odd(Recipe):
        name = "future.new_thing"
        phase = 3

        async def check(self, _ha):
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN, "novel", human_action="do the thing"
            )

        async def plan(self, _ha):
            return Plan(())

        async def apply(self, _ha):
            return ApplyResult((), "")

        async def verify(self, _ha):
            return VerifyResult(True, "")

    payload = await build_queue(sim, [Odd()])
    (item,) = payload["items"]
    assert item["decision"] == {"type": "acknowledge"}
    assert item["human_action"] == "do the thing"
