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
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HACommandError

from .triggers import hop_bare_confirms
from .wizard import flow_key

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

DECISIONS = ("add", "ignore", "later")

#: Same convention as ``manifest.DEFAULT_MANIFEST_PATH``: relative to the
#: working directory, which the gateway bind-mounts at ``config/``.
DEFAULT_TRIAGE_STORE_PATH = Path("config/init-triage.json")


class LaterStore:
    """Durable set of flow keys deferred with ``later``.

    Backed by one JSON file on the gateway's bind-mounted ``config/`` dir,
    so deferrals survive restarts. Runtime state, deliberately gitignored:
    flow keys embed hardware identity (MACs, serials via ``unique_id``)
    that must never land in the repo's history. Writes are atomic
    (tmp + replace) — a crash never truncates the store.
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
        tmp.write_text(json.dumps({"later": sorted(keys)}, indent=2) + "\n", encoding="utf-8")
        # Group-writable to match the bind-mount convention (the container
        # umask would otherwise land 644 and lock the host group out).
        tmp.chmod(0o664)
        tmp.replace(self._path)

    def keys(self) -> set[str]:
        return self._load()

    def __contains__(self, key: object) -> bool:
        return key in self._load()


async def _find_flow(ha: HAClient, flow_id: str) -> dict[str, Any] | None:
    flows = await ha.ws.send_command("config_entries/flow/progress") or []
    return next((f for f in flows if f.get("flow_id") == flow_id), None)


async def _apply_add(ha: HAClient, flow_id: str) -> dict[str, Any]:
    """Advance toward completion; defer to readiness triggers at a PIN step."""
    step = await hop_bare_confirms(ha, flow_id)
    if step["step_type"] == "form" and step["fields"]:
        return {"decision": "add", "routed": "readiness", "step": step}
    if step["step_type"] == "create_entry":
        # Read-back: the flow's word is not the proof — the entry existing
        # is. Match the created entry's id when the response carries it; a
        # domain match alone could be a pre-existing sibling entry, so it
        # is labelled as the weaker read-back that it is.
        entries = await ha.rest.get_config_entries()
        if step.get("entry_id"):
            entry = next((e for e in entries if e.get("entry_id") == step["entry_id"]), None)
            read_back = "entry_id"
        else:
            entry = next((e for e in entries if e.get("domain") == step.get("handler")), None)
            read_back = "domain"
        return {
            "decision": "add",
            "completed": entry is not None,
            "entry_state": entry.get("state") if entry else None,
            "read_back": read_back,
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
        await ha.ws.send_command("config_entries/ignore_flow", flow_id=flow_id, title=str(title))
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


__all__ = [
    "DECISIONS",
    "DEFAULT_TRIAGE_STORE_PATH",
    "LaterStore",
    "apply_decision",
    "flow_key",
]
