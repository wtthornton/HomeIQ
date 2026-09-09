"""Wizard queue assembly: the human-action queue the setup wizard renders.

TAP-5943: merges the init agent's ``blocked_on_human`` audit rows with Home
Assistant's pending discovery flows (``config_entries/flow/progress``) into
one UI-consumable payload, attaching a machine-readable decision schema per
item kind. Read-only by construction — the audit runs behind the engine's
read-only proxy and every extra read here goes through the same proxy, so a
write attempt raises instead of reaching the instance. The returned payload
carries the read journal as evidence.

Generated from live truth on every call, never hand-maintained: the artifact
page this replaces missed the Hue bridge and the Apple TVs precisely because
its item list was static.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .engine import HAInitAgent, RecipeOutcome
from .readiness import ReadinessResult, check_readiness
from .readonly import read_only
from .recipe import CheckStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from homeiq_ha.client import HAClient

    from .recipe import Recipe

#: TAP-7272 decision (recorded 2026-09-09): captured network metadata is kept
#: on a 30-day rolling basis and the customer can erase it from HomeIQ's UI.
#: The rolling-deletion job and the erase action are TAP-6490, a separate
#: story — this step states the policy, never a control that does not exist
#: yet, which is why it names "Settings -> Network capture" as prose rather
#: than a link.
# TODO(TAP-6490): no "Settings -> Network capture" UI route exists yet to
# link from here; wire it once that story ships the erase action.
NETWORK_CAPTURE_HUMAN_ACTION = (
    "Network metadata capture (Zeek) is optional and off unless you turn it "
    "on. If enabled, captured data is kept for 30 days on a rolling basis; "
    "you can erase it at any time from Settings -> Network capture."
)


def _network_capture_item() -> dict[str, Any]:
    """The opt-in step for network metadata capture (TAP-7272).

    Always ``readiness: False`` — turning this on never needs a person
    physically at a device, unlike the pairing-style items above.
    """
    return {
        "kind": "opt_in",
        "id": "optin:network_capture",
        "title": "Network metadata capture (optional)",
        "human_action": NETWORK_CAPTURE_HUMAN_ACTION,
        "decision": {"type": "toggle", "field": "network_capture_enabled", "default": False},
        "readiness": False,
    }


#: Discovery handlers whose next step needs the person physically present,
#: mapped to why (surfaced as the item's readiness reason).
READINESS_HANDLERS = {
    "zha": "Zigbee pairing window — press the device's pairing button",
    "homekit_controller": "HomeKit PIN entry from the device label",
    "matter": "Matter pairing code from the device label",
    "hacs": "GitHub device-code authorization in a browser",
    "apple_tv": "PIN displayed on the Apple TV screen",
    "androidtv_remote": "Pairing code displayed on the TV screen",
    "braviatv": "PIN displayed on the TV screen",
}


def _decision_for_audit_row(outcome: RecipeOutcome, area_names: list[str]) -> dict[str, Any]:
    """Machine-readable decision schema for one blocked audit row.

    Derived from the recipe kind — never parsed out of the human_action
    prose. Unknown kinds degrade to an acknowledge so a new recipe can never
    crash the queue.
    """
    details = outcome.check.details or {}
    if outcome.name == "organization.device_areas":
        return {
            "type": "area_assignment",
            "devices": list(details.get("unassigned") or ()),
            "options": area_names,
        }
    if outcome.name == "safety.backup_schedule":
        # Machine-readable discriminators, never the summary prose. The
        # check's details carry both facts; no destination blocks first.
        if not details.get("agent_ids"):
            return {"type": "acknowledge", "action": "add_backup_location"}
        if details.get("encryption_key_set") is False:
            # Write-only secret: accepted by the wizard, set via
            # backup/config/update, never persisted or echoed (TAP-5942).
            return {"type": "secret", "field": "backup_password", "write_only": True}
        return {"type": "acknowledge"}
    if outcome.name == "safety.first_backup":
        return {"type": "acknowledge", "action": "add_backup_location"}
    if outcome.name == "organization.scene_policy":
        return {
            "type": "select_per_item",
            "items": list(details.get("uncovered") or ()),
            "options": ["curate", "bridge_owned", "remove"],
        }
    if outcome.name.startswith("addons.") and details.get("unconfigured"):
        return {"type": "text_fields", "fields": list(details["unconfigured"])}
    if outcome.name == "hacs.bootstrap":
        return {"type": "readiness", "action": "github_device_code"}
    if outcome.name == "zigbee.coordinator_watchdog":
        return {"type": "acknowledge", "action": "power_cycle_coordinator"}
    return {"type": "acknowledge"}


def _audit_item(outcome: RecipeOutcome, area_names: list[str]) -> dict[str, Any]:
    return {
        "kind": "audit_blocked",
        "id": f"audit:{outcome.name}",
        "name": outcome.name,
        "phase": outcome.phase,
        "title": outcome.check.summary,
        # Verbatim by contract: the recipe's words are the instruction.
        "human_action": outcome.check.human_action,
        "decision": _decision_for_audit_row(outcome, area_names),
        "readiness": False,
    }


def flow_key(flow: dict[str, Any]) -> str:
    """A flow identity that survives rescans (flow ids do not).

    ``later`` triage decisions (TAP-5947) persist across restarts, but HA
    mints a fresh flow_id per rediscovery — so deferral keys on handler +
    unique id, falling back to the discovery title placeholders.
    """
    handler = flow.get("handler") or "unknown"
    context = flow.get("context") or {}
    unique_id = context.get("unique_id")
    if unique_id:
        return f"{handler}:{unique_id}"
    placeholders = context.get("title_placeholders") or {}
    suffix = ",".join(f"{k}={placeholders[k]}" for k in sorted(placeholders)) or "no-id"
    return f"{handler}:{suffix}"


def _discovery_item(flow: dict[str, Any]) -> dict[str, Any]:
    handler = flow.get("handler")
    context = flow.get("context") or {}
    return {
        "kind": "discovery",
        "id": f"flow:{flow.get('flow_id')}",
        "handler": handler,
        "source": context.get("source"),
        "title_placeholders": context.get("title_placeholders") or {},
        "decision": {"type": "select", "options": ["add", "ignore", "later"]},
        "readiness": handler in READINESS_HANDLERS,
        "readiness_reason": READINESS_HANDLERS.get(handler),
        # Stable across rescans — what a "later" deferral is keyed on.
        "triage_key": flow_key(flow),
    }


def _readiness_item(result: ReadinessResult) -> dict[str, Any]:
    """The single queue item shown while the appliance's own HA is not ready.

    Never an ``audit_blocked`` or ``discovery`` item — a person reading the
    queue must not mistake "still booting" for "nothing to configure".
    """
    return {
        "kind": "readiness",
        "id": "readiness:appliance-ha",
        "title": "Home Assistant is starting up",
        "human_action": (
            f"Home Assistant is not ready yet ({result.named}). Wait a moment and refresh."
        ),
        "decision": {"type": "acknowledge"},
        "readiness": False,
        "state": result.named,
    }


def not_ready_queue_payload(result: ReadinessResult) -> dict[str, Any]:
    """The queue's shape while readiness is unverified (TAP-6468).

    HTTP 200 with an actionable payload — never an empty ``items`` list (which
    reads as "nothing to do" on an instance that is simply not up yet) and
    never a propagated exception from a live call this appliance's HA cannot
    yet answer.
    """
    return {
        "items": [_readiness_item(result)],
        "audit_outcomes": 0,
        "generated_from": "readiness gate",
        "reads": [],
        "ready": False,
        "readiness": result.named,
    }


async def build_queue(
    ha: HAClient,
    recipes: Sequence[Recipe],
    *,
    readiness: ReadinessResult | None = None,
) -> dict[str, Any]:
    """The wizard's queue payload, generated from live truth on every call.

    Gated at the producer (TAP-6468): the audit and the discovery-flow reads
    below never run until the appliance's own Home Assistant answers ready —
    an unauthenticated instance mid-boot cannot answer either honestly, and a
    caller that tried anyway would either 502 or read a fresh instance's
    "nothing configured yet" as "no blockers", which is indistinguishable from
    done.

    Args:
        readiness: A pre-computed result — callers that already probed
            readiness (e.g. the route, to decide whether to open ``ha`` at
            all) pass it through rather than probing twice. Defaults to
            probing ``ha.base_url`` directly, so this gate holds even when
            ``build_queue`` is called on its own.
    """
    result = readiness if readiness is not None else await check_readiness(ha.base_url)
    if not result.ready:
        return not_ready_queue_payload(result)

    report = await HAInitAgent(recipes).audit(ha)
    guarded = read_only(ha)
    flows = await guarded.ws.send_command("config_entries/flow/progress") or []
    areas = await guarded.ws.send_command("config/area_registry/list") or []
    area_names = [a["name"] for a in areas]

    items = [
        _audit_item(outcome, area_names)
        for outcome in report.by_status(CheckStatus.BLOCKED_ON_HUMAN)
    ]
    items.extend(_discovery_item(flow) for flow in flows)
    items.append(_network_capture_item())

    return {
        "items": items,
        "audit_outcomes": len(report.outcomes),
        "generated_from": "live audit + config_entries/flow/progress",
        # Read-only evidence: every HA call this payload was built from.
        "reads": report.reads + guarded.journal,
        "ready": True,
        "readiness": result.named,
    }


__all__ = [
    "NETWORK_CAPTURE_HUMAN_ACTION",
    "READINESS_HANDLERS",
    "build_queue",
    "flow_key",
    "not_ready_queue_payload",
]
