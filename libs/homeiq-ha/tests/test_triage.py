"""Discovery triage (TAP-5947): add / ignore / later against captured shapes.

Behavioural, simulator-backed. The three decisions are asserted on what was
sent to the instance and what is readable back — never on internals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeiq_ha.agent.triage import LaterStore, apply_decision
from homeiq_ha.agent.wizard import flow_key

if TYPE_CHECKING:
    from pathlib import Path

    from .simulators import SimHA


def _store(tmp_path: Path) -> LaterStore:
    return LaterStore(tmp_path / "init-triage.json")


# -- flow_key --------------------------------------------------------------


def test_flow_key_prefers_unique_id() -> None:
    flow = {"handler": "dlna_dmr", "context": {"unique_id": "uuid:abc"}}
    assert flow_key(flow) == "dlna_dmr:uuid:abc"


def test_flow_key_falls_back_to_title_placeholders() -> None:
    flow = {"handler": "heos", "context": {"title_placeholders": {"name": "Den AVR"}}}
    assert flow_key(flow) == "heos:name=Den AVR"


# -- add -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_completes_a_confirm_flow_and_reads_back_the_entry(
    sim: SimHA, tmp_path: Path
) -> None:
    """dlna_dmr shape: bare confirm -> create_entry, verified by entry_id."""
    sim.state["flow_progress"] = [
        {"flow_id": "f1", "handler": "dlna_dmr", "context": {"unique_id": "u1"}}
    ]
    sim.state["flow_current_step"] = {
        "type": "form",
        "flow_id": "f1",
        "step_id": "confirm",
        "data_schema": [],
    }
    sim.state["flow_next_step"] = {
        "type": "create_entry",
        "flow_id": "f1",
        "handler": "dlna_dmr",
        "result": {"entry_id": "e1", "domain": "dlna_dmr", "state": "loaded"},
    }
    result = await apply_decision(sim, "f1", "add", _store(tmp_path))
    assert result["completed"] is True
    assert result["entry_state"] == "loaded"
    assert result["read_back"] == "entry_id"


@pytest.mark.asyncio
async def test_add_routes_a_pin_flow_to_readiness_not_completion(
    sim: SimHA, tmp_path: Path
) -> None:
    sim.state["flow_progress"] = [{"flow_id": "f1", "handler": "apple_tv"}]
    sim.state["flow_current_step"] = {
        "type": "form",
        "flow_id": "f1",
        "step_id": "confirm",
        "data_schema": [],
    }
    sim.state["flow_next_step"] = {
        "type": "form",
        "flow_id": "f1",
        "step_id": "pair_with_pin",
        "data_schema": [{"name": "pin", "type": "string", "required": True}],
    }
    result = await apply_decision(sim, "f1", "add", _store(tmp_path))
    assert result["routed"] == "readiness"
    assert result["step"]["fields"] == ["pin"]
    assert "completed" not in result


@pytest.mark.asyncio
async def test_add_does_not_claim_completion_without_a_readable_entry(
    sim: SimHA, tmp_path: Path
) -> None:
    """A create_entry answer with no entry readable back is not a success."""
    sim.state["flow_progress"] = [{"flow_id": "f1", "handler": "dlna_dmr"}]
    sim.state["flow_current_step"] = {
        "type": "form",
        "flow_id": "f1",
        "step_id": "confirm",
        "data_schema": [],
    }
    # No result payload -> the simulator lands no entry -> read-back finds none.
    sim.state["flow_next_step"] = {
        "type": "create_entry",
        "flow_id": "f1",
        "handler": "dlna_dmr",
    }
    result = await apply_decision(sim, "f1", "add", _store(tmp_path))
    assert result["completed"] is False
    assert result["entry_state"] is None
    assert result["read_back"] == "domain"


# -- ignore ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_ignore_dismisses_via_has_ignore_mechanism(sim: SimHA, tmp_path: Path) -> None:
    """The flow is gone from progress and an ignore-source entry persists it."""
    sim.state["flow_progress"] = [
        {
            "flow_id": "f1",
            "handler": "heos",
            "context": {"unique_id": "u-heos", "title_placeholders": {"name": "Den"}},
        }
    ]
    result = await apply_decision(sim, "f1", "ignore", _store(tmp_path))
    assert result["ignored"] is True
    assert result["key"] == "heos:u-heos"
    assert ("config_entries/ignore_flow", {"flow_id": "f1", "title": "Den"}) in sim.ws.calls
    assert sim.state["flow_progress"] == []
    assert any(
        e.get("source") == "ignore" and e.get("domain") == "heos"
        for e in sim.state["config_entries"]
    )


@pytest.mark.asyncio
async def test_ignore_without_unique_id_is_surfaced_not_swallowed(
    sim: SimHA, tmp_path: Path
) -> None:
    """Upstream refuses flows lacking unique_id — the refusal is the answer."""
    sim.state["flow_progress"] = [{"flow_id": "f1", "handler": "heos", "context": {}}]
    result = await apply_decision(sim, "f1", "ignore", _store(tmp_path))
    assert result["ignored"] is False
    assert result["reason"] == "no_unique_id"
    assert sim.state["flow_progress"] != []  # flow untouched


@pytest.mark.asyncio
async def test_ignore_unknown_flow_is_an_honest_not_found(sim: SimHA, tmp_path: Path) -> None:
    sim.state["flow_progress"] = []
    result = await apply_decision(sim, "ghost", "ignore", _store(tmp_path))
    assert result["ignored"] is False
    assert result["reason"] == "flow_not_found"


# -- later -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_later_persists_across_store_instances(sim: SimHA, tmp_path: Path) -> None:
    """The deferral keys on flow identity, not the ephemeral flow_id."""
    sim.state["flow_progress"] = [
        {"flow_id": "f1", "handler": "denonavr", "context": {"unique_id": "u-avr"}}
    ]
    store = _store(tmp_path)
    result = await apply_decision(sim, "f1", "later", store)
    assert result["deferred"] is True
    assert result["key"] == "denonavr:u-avr"
    # A fresh store over the same file (a service restart) still knows it.
    assert "denonavr:u-avr" in _store(tmp_path)
    # Nothing was sent to HA.
    assert sim.writes == []


@pytest.mark.asyncio
async def test_later_on_unknown_flow_defers_nothing(sim: SimHA, tmp_path: Path) -> None:
    sim.state["flow_progress"] = []
    result = await apply_decision(sim, "ghost", "later", _store(tmp_path))
    assert result["deferred"] is False
    assert result["reason"] == "flow_not_found"
