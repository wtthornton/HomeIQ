"""Readiness triggers (TAP-5946): permit window, PIN-flow advance, HACS start.

Behavioural, simulator-backed: every assertion is on what was sent to the
instance or on the summary the wizard renders — never on internals.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from homeiq_ha.agent.triggers import (
    PERMIT_COMMAND,
    advance_to_readiness,
    open_permit_window,
    start_hacs,
)

from .simulators import SimHA

pytestmark = pytest.mark.asyncio

# -- ZHA permit window -----------------------------------------------------


async def test_permit_sends_the_root_caused_command_with_explicit_duration(
    sim: SimHA,
) -> None:
    """The exact upstream shape: zha/devices/permit with a stated duration."""
    result = await open_permit_window(sim, duration=120)
    assert (PERMIT_COMMAND, {"duration": 120}) in sim.ws.calls
    assert result["opened"] is True
    assert result["duration"] == 120


async def test_permit_default_duration_is_still_sent_explicitly(sim: SimHA) -> None:
    """Never inherit the server default — 60 goes over the wire."""
    await open_permit_window(sim)
    assert (PERMIT_COMMAND, {"duration": 60}) in sim.ws.calls


async def test_permit_response_states_when_the_window_closes(sim: SimHA) -> None:
    result = await open_permit_window(sim, duration=90)
    opened = datetime.fromisoformat(result["opened_at"])
    closes = datetime.fromisoformat(result["closes_at"])
    assert (closes - opened).total_seconds() == 90


async def test_permit_retrigger_never_errors(sim: SimHA) -> None:
    """Upstream restarts the window with the new duration; two calls, two sends."""
    await open_permit_window(sim, duration=60)
    await open_permit_window(sim, duration=120)
    permits = [c for c in sim.ws.calls if c[0] == PERMIT_COMMAND]
    assert [c[1]["duration"] for c in permits] == [60, 120]


# -- discovered-flow advance ----------------------------------------------


async def test_flow_start_advances_bare_confirm_to_the_pin_form(sim: SimHA) -> None:
    """apple_tv shape: confirm (no fields) -> pairing starts -> PIN form."""
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
        "description_placeholders": {"name": "Living Room"},
    }
    result = await advance_to_readiness(sim, "f1")
    assert result["step_type"] == "form"
    assert result["fields"] == ["pin"]
    assert result["description_placeholders"] == {"name": "Living Room"}
    assert sim.state["flow_inputs"] == [{}]  # confirm advanced with {}, nothing else


async def test_flow_start_is_idempotent_on_a_flow_already_at_its_pin_form(
    sim: SimHA,
) -> None:
    """A flow sitting at its PIN form is returned as-is — no second advance."""
    sim.state["flow_current_step"] = {
        "type": "form",
        "flow_id": "f1",
        "step_id": "pair",
        "data_schema": [{"name": "pin", "type": "string", "required": True}],
    }
    result = await advance_to_readiness(sim, "f1")
    assert result["fields"] == ["pin"]
    assert not any(w.startswith("flow_advance") for w in sim.rest.writes)


async def test_flow_start_never_completes_a_flow(sim: SimHA) -> None:
    """Only empty confirm submissions ever go over the wire."""
    sim.state["flow_current_step"] = {
        "type": "form",
        "flow_id": "f1",
        "step_id": "confirm",
        "data_schema": [],
    }
    sim.state["flow_next_step"] = {
        "type": "form",
        "flow_id": "f1",
        "step_id": "pair",
        "data_schema": [{"name": "pin", "type": "string", "required": True}],
    }
    await advance_to_readiness(sim, "f1")
    assert all(submitted == {} for submitted in sim.state.get("flow_inputs", []))


async def test_flow_start_hops_are_bounded(sim: SimHA) -> None:
    """A flow that keeps rendering bare confirms stops after 3 hops."""
    bare = {"type": "form", "flow_id": "f1", "step_id": "confirm", "data_schema": []}
    sim.state["flow_current_step"] = dict(bare)
    sim.state["flow_next_step"] = dict(bare)
    result = await advance_to_readiness(sim, "f1")
    assert result["step_type"] == "form"
    assert len(sim.state["flow_inputs"]) == 3


async def test_flow_start_surfaces_an_abort_honestly(sim: SimHA) -> None:
    sim.state["flow_current_step"] = {
        "type": "abort",
        "flow_id": "f1",
        "reason": "already_configured",
    }
    result = await advance_to_readiness(sim, "f1")
    assert result["step_type"] == "abort"
    assert result["reason"] == "already_configured"
    assert not any(w.startswith("flow_advance") for w in sim.rest.writes)


# -- HACS onboarding -------------------------------------------------------


async def test_hacs_start_reuses_an_in_progress_flow(sim: SimHA) -> None:
    """already_in_progress is prevented by reusing, not raised."""
    sim.state["flow_progress"] = [{"flow_id": "h1", "handler": "hacs"}]
    sim.state["flow_current_step"] = {
        "type": "progress",
        "flow_id": "h1",
        "step_id": "wait_for_device",
        "description_placeholders": {"url": "https://github.com/login/device", "code": "AB12-CD34"},
    }
    result = await start_hacs(sim)
    assert result["step_type"] == "progress"
    assert result["description_placeholders"]["code"] == "AB12-CD34"
    assert not any(w.startswith("flow_start") for w in sim.rest.writes)


async def test_hacs_start_acks_the_boolean_form_and_surfaces_the_device_code(
    sim: SimHA,
) -> None:
    sim.state["flow_first_step"] = {
        "type": "form",
        "flow_id": "h1",
        "step_id": "user",
        "data_schema": [
            {"name": "acc_logs", "type": "boolean", "required": True},
            {"name": "acc_addons", "type": "boolean", "required": True},
        ],
    }
    sim.state["flow_next_step"] = {
        "type": "progress",
        "flow_id": "h1",
        "step_id": "wait_for_device",
        "description_placeholders": {"url": "https://github.com/login/device", "code": "AB12-CD34"},
    }
    result = await start_hacs(sim)
    assert result["step_type"] == "progress"
    assert result["description_placeholders"] == {
        "url": "https://github.com/login/device",
        "code": "AB12-CD34",
    }
    assert sim.state["flow_inputs"] == [{"acc_logs": True, "acc_addons": True}]


async def test_hacs_start_never_guesses_at_a_non_boolean_form(sim: SimHA) -> None:
    """A form with non-boolean fields is surfaced, not auto-filled."""
    sim.state["flow_first_step"] = {
        "type": "form",
        "flow_id": "h1",
        "step_id": "user",
        "data_schema": [{"name": "token", "type": "string", "required": True}],
    }
    result = await start_hacs(sim)
    assert result["step_type"] == "form"
    assert result["fields"] == ["token"]
    assert "flow_inputs" not in sim.state


async def test_hacs_start_surfaces_already_configured_abort(sim: SimHA) -> None:
    sim.state["flow_first_step"] = {
        "type": "abort",
        "flow_id": "h1",
        "reason": "already_configured",
    }
    result = await start_hacs(sim)
    assert result["step_type"] == "abort"
    assert result["reason"] == "already_configured"
