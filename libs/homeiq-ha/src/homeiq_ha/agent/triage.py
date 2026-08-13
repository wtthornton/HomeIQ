"""Discovery triage: apply one add / ignore / later decision per flow.

TAP-5947: the wizard's queue (``wizard.py``) surfaces discovered flows; this
module applies the person's decision on one of them.

- ``add`` drives the flow toward completion by advancing bare confirm steps
  (via ``triggers.hop_bare_confirms`` — for discovery-confirm-terminal
  handlers like dlna_dmr the confirm submission IS the completion, which
  is exactly what ``add`` means). A flow that lands on a PIN or code step
  is routed to the readiness triggers (TAP-5946), never auto-completed —
  completing needs knowledge only the human holds. A flow that completes
  is verified by read-back: its config entry must exist.
- ``ignore`` dismisses the flow through HA's own mechanism, the
  ``config_entries/ignore_flow`` websocket command (HA core
  ``components/config/config_entries.py``: requires the flow's context to
  carry a ``unique_id``, then creates an ignore-source entry so discovery
  stops re-offering the device — which is why the flow stays gone across
  restarts). Flows without a unique id error upstream; that error is
  surfaced honestly, not swallowed.
- ``later`` touches HA not at all: the flow's stable key is recorded in a
  :class:`LaterStore` and the queue route hides it by default.

Flow ids are ephemeral — HA mints a new one per rescan/restart — so
``later`` decisions key on :func:`flow_key` (handler + unique id, falling
back to the discovery title placeholders), which survives re-discovery.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HACommandError

from .triggers import hop_bare_confirms

if TYPE_CHECKING:
    from pathlib import Path

    from homeiq_ha.client import HAClient

DECISIONS = ("add", "ignore", "later")


def flow_key(flow: dict[str, Any]) -> str:
    """A flow identity that survives rescans (flow ids do not)."""
    handler = flow.get("handler") or "unknown"
    context = flow.get("context") or {}
    unique_id = context.get("unique_id")
    if unique_id:
        return f"{handler}:{unique_id}"
    placeholders = context.get("title_placeholders") or {}
    suffix = ",".join(f"{k}={placeholders[k]}" for k in sorted(placeholders)) or "no-id"
    return f"{handler}:{suffix}"


class LaterStore:
    """Durable set of flow keys deferred with ``later``.

    Backed by one JSON file on the gateway's bind-mounted ``config/`` dir,
    so deferrals survive restarts and are git-visible like the manifest.
    Writes are atomic (tmp + replace) — a crash never truncates the store.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def _load(self) -> set[str]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return set()
        return set(data.get("later") or [])

    def add(self, key: str) -> None:
        keys = self._load() | {key}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"later": sorted(keys)}, indent=2) + "\n", encoding="utf-8"
        )
        tmp.replace(self._path)

    def keys(self) -> set[str]:
        return self._load()


async def _find_flow(ha: HAClient, flow_id: str) -> dict[str, Any] | None:
    flows = await ha.ws.send_command("config_entries/flow/progress") or []
    return next((f for f in flows if f.get("flow_id") == flow_id), None)


async def _apply_add(ha: HAClient, flow_id: str) -> dict[str, Any]:
    """Advance toward completion; defer to readiness triggers at a PIN step."""
    step = await hop_bare_confirms(ha, flow_id)
    if step["step_type"] == "form" and step["fields"]:
        return {"decision": "add", "routed": "readiness", "step": step}
    if step["step_type"] == "create_entry":
        # Read-back: the flow's word is not the proof — the entry existing is.
        entries = await ha.rest.get_config_entries()
        entry = next(
            (e for e in entries if e.get("domain") == step.get("handler")), None
        )
        return {
            "decision": "add",
            "completed": True,
            "entry_state": entry.get("state") if entry else None,
            "step": step,
        }
    return {"decision": "add", "completed": False, "step": step}


async def _apply_ignore(ha: HAClient, flow_id: str) -> dict[str, Any]:
    flow = await _find_flow(ha, flow_id)
    if flow is None:
        return {"decision": "ignore", "ignored": False, "reason": "flow_not_found"}
    placeholders = (flow.get("context") or {}).get("title_placeholders") or {}
    title = placeholders.get("name") or flow.get("handler") or "Ignored device"
    try:
        await ha.ws.send_command(
            "config_entries/ignore_flow", flow_id=flow_id, title=str(title)
        )
    except HACommandError as exc:
        # Upstream refuses flows without a unique_id — an honest limit,
        # not a failure of this endpoint.
        return {"decision": "ignore", "ignored": False, "reason": exc.code}
    remaining = await _find_flow(ha, flow_id)
    return {
        "decision": "ignore",
        "ignored": remaining is None,
        "key": flow_key(flow),
    }


async def apply_decision(
    ha: HAClient, flow_id: str, decision: str, later: LaterStore
) -> dict[str, Any]:
    """Apply one triage decision; every outcome is read-back verified."""
    if decision == "add":
        return await _apply_add(ha, flow_id)
    if decision == "ignore":
        return await _apply_ignore(ha, flow_id)
    flow = await _find_flow(ha, flow_id)
    if flow is None:
        return {"decision": "later", "deferred": False, "reason": "flow_not_found"}
    key = flow_key(flow)
    later.add(key)
    return {"decision": "later", "deferred": True, "key": key}


__all__ = ["DECISIONS", "LaterStore", "apply_decision", "flow_key"]
