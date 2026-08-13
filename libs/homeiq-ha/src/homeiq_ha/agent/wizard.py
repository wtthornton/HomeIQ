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
from .readonly import read_only
from .recipe import CheckStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from homeiq_ha.client import HAClient

    from .recipe import Recipe

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


def _decision_for_audit_row(
    outcome: RecipeOutcome, area_names: list[str]
) -> dict[str, Any]:
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
    }


async def build_queue(ha: HAClient, recipes: Sequence[Recipe]) -> dict[str, Any]:
    """The wizard's queue payload, generated from live truth on every call."""
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

    return {
        "items": items,
        "audit_outcomes": len(report.outcomes),
        "generated_from": "live audit + config_entries/flow/progress",
        # Read-only evidence: every HA call this payload was built from.
        "reads": report.reads + guarded.journal,
    }


__all__ = ["READINESS_HANDLERS", "build_queue"]
