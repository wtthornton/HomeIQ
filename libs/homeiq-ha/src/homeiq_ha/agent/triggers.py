"""Readiness triggers: actions fired at the human's physical-presence moment.

TAP-5946: the wizard's queue (``wizard.py``) *surfaces* readiness items —
pairing windows, PIN flows, HACS device codes. This module fires them when
the person is actually standing there, via three verbs the gateway exposes:
open a bounded ZHA join window, advance a discovered flow to its PIN step,
and begin HACS onboarding up to its GitHub device code.

ZHA permit — root cause of the failed 2026-08-12 probe
------------------------------------------------------
The working command, from HA core ``homeassistant/components/zha/
websocket_api.py`` (``SERVICE_PERMIT_PARAMS`` + ``websocket_permit_devices``):

    {"type": "zha/devices/permit", "duration": N}

``duration`` is optional upstream (default 60, ``vol.Range(0, 254)``) but is
always sent explicitly here — the window's length must be stated, not
inherited. The probe did not fail on command shape: ``websocket_permit_devices``
registers ``connection.subscriptions[msg["id"]]`` and forwards gateway events
under the *command's own id*, so event frames arrive before the result frame.
The client's read loop used to resolve the command future with the first
frame carrying the id, reporting an empty "unknown" error while the window
actually opened. Fixed in ``client/ws.py`` (commit ``2f0f9087``): the read
loop now ignores non-``result`` frames for pending commands.

Re-triggering permit during an open window is safe by upstream design: the
coordinator simply restarts the window with the new duration (an extend),
never an error.

Flow triggers are readiness-gated: ``advance_to_readiness`` only advances
flows whose handler is in ``wizard.READINESS_HANDLERS`` — the set whose
confirm steps initiate pairing and land on a human-readable step (PIN form,
device code). For every other handler a bare confirm submission is the
*completing* step (HA core ``helpers/config_entry_flow.py``
``DiscoveryFlowHandler.async_step_confirm`` creates the entry on any
non-None input — dlna_dmr, heos, denonavr all follow it), so those flows
are refused untouched and belong to the triage ``add`` decision
(TAP-5947), where completing is the point and is read-back verified. If a
readiness handler nevertheless completes on a confirm, the outcome is
reported honestly in the summary — never claimed impossible. The one
deliberate form auto-fill is HACS's acknowledgement form (all-boolean
fields), accepted because acknowledging is the prerequisite for the device
code this trigger exists to surface.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from .wizard import READINESS_HANDLERS

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

#: The ZHA websocket command that opens a Zigbee join window.
PERMIT_COMMAND = "zha/devices/permit"

#: Upstream bound: ``vol.Range(0, 254)``; 0 closes an open window early.
PERMIT_MAX_DURATION = 254

#: Confirm-step hops before giving up — a flow that keeps rendering bare
#: confirm forms is not converging on a human-readable step.
_MAX_CONFIRM_HOPS = 3


def _field_names(step: dict[str, Any]) -> list[str]:
    return [str(f.get("name")) for f in step.get("data_schema") or [] if f.get("name")]


def _summarize(ha: HAClient, step: dict[str, Any]) -> dict[str, Any]:
    """The step facts the wizard renders; never the raw HA payload."""
    return {
        "flow_id": step.get("flow_id"),
        "handler": step.get("handler"),
        "step_type": ha.rest.classify_flow_step(step),
        "step_id": step.get("step_id"),
        "description_placeholders": step.get("description_placeholders") or {},
        "fields": _field_names(step),
        "reason": step.get("reason"),
    }


async def open_permit_window(ha: HAClient, duration: int = 60) -> dict[str, Any]:
    """Open a bounded ZHA join window and state when it closes.

    Idempotent-safe: firing again while a window is open restarts it with
    the new duration (upstream behaviour), so the wizard can offer "extend".
    """
    await ha.ws.send_command(PERMIT_COMMAND, duration=int(duration))
    opened_at = datetime.now(tz=UTC)
    closes_at = opened_at + timedelta(seconds=duration)
    return {
        "opened": True,
        "duration": duration,
        "opened_at": opened_at.isoformat(timespec="seconds"),
        "closes_at": closes_at.isoformat(timespec="seconds"),
    }


async def hop_bare_confirms(ha: HAClient, flow_id: str) -> dict[str, Any]:
    """Advance bare confirm forms (no input fields) with ``{}``, bounded.

    Stops at the first step with input fields, placeholders to read, or a
    terminal state. For a discovery-confirm-terminal handler the ``{}``
    submission IS the completing step — callers own that semantic: triage
    ``add`` wants it (and read-back verifies), ``advance_to_readiness``
    gates on the readiness map so it never advances such a flow.
    """
    step = await ha.rest.get_config_flow(flow_id)
    for _ in range(_MAX_CONFIRM_HOPS):
        if ha.rest.classify_flow_step(step) != "form" or _field_names(step):
            break
        step = await ha.rest.advance_config_flow(flow_id, {})
    return _summarize(ha, step)


async def advance_to_readiness(ha: HAClient, flow_id: str) -> dict[str, Any]:
    """Advance a readiness flow to the step the person must act on.

    Only flows whose handler is in ``READINESS_HANDLERS`` are advanced —
    their confirm steps initiate pairing and land on a PIN/code step
    (apple_tv, androidtv_remote, braviatv). Any other handler's confirm
    would complete the flow outright, so it is returned untouched with
    ``reason: not_a_readiness_flow`` and belongs to the triage ``add``
    decision instead. A completion is reported as its real ``step_type``
    (``create_entry``), never masked.

    Idempotent-safe: a flow already sitting at its PIN form is returned
    as-is, without another advance.
    """
    flows = await ha.ws.send_command("config_entries/flow/progress") or []
    flow = next((f for f in flows if f.get("flow_id") == flow_id), None)
    if flow is None:
        return {
            "flow_id": flow_id,
            "handler": None,
            "step_type": None,
            "step_id": None,
            "description_placeholders": {},
            "fields": [],
            "reason": "flow_not_found",
        }
    if flow.get("handler") not in READINESS_HANDLERS:
        # GET only — re-render, never a submit — so the refusal still
        # tells the caller what step the flow is sitting on.
        summary = _summarize(ha, await ha.rest.get_config_flow(flow_id))
        summary["reason"] = "not_a_readiness_flow"
        return summary
    return await hop_bare_confirms(ha, flow_id)


async def start_hacs(ha: HAClient) -> dict[str, Any]:
    """Begin HACS onboarding and surface the GitHub device code.

    Reuses an in-progress hacs flow rather than erroring on
    ``already_in_progress``; auto-accepts the all-boolean acknowledgement
    form (the documented prerequisite for the device code); returns the
    progress step whose placeholders carry the code and URL. An abort
    (e.g. ``already_configured``) is surfaced honestly, not raised.
    """
    flows = await ha.ws.send_command("config_entries/flow/progress") or []
    existing = next((f for f in flows if f.get("handler") == "hacs"), None)
    if existing is not None:
        step = await ha.rest.get_config_flow(str(existing["flow_id"]))
    else:
        step = await ha.rest.start_config_flow("hacs")

    if ha.rest.classify_flow_step(step) == "form":
        schema = step.get("data_schema") or []
        names = _field_names(step)
        if names and all(f.get("type") == "boolean" for f in schema):
            step = await ha.rest.advance_config_flow(
                str(step["flow_id"]), dict.fromkeys(names, True)
            )
    return _summarize(ha, step)


__all__ = [
    "PERMIT_COMMAND",
    "PERMIT_MAX_DURATION",
    "advance_to_readiness",
    "hop_bare_confirms",
    "open_permit_window",
    "start_hacs",
]
