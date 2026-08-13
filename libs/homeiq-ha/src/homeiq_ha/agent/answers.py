"""Wizard answers ingestion: the ha-human-actions-answers contract (TAP-5945).

One submitted wizard form becomes a converged, verified instance:

1. Device room choices land in the committed manifest
   (``config/ha-organization-manifest.yaml`` — the gateway bind-mounts the
   repo's copy, so the write is durable and git-visible) as new ``areas``
   and ``device_areas`` rows whose reasons cite the wizard submission. The
   append is comment-preserving text surgery — a YAML round-trip would
   destroy the manifest's provenance block.
2. The backup encryption password is **write-only**: set via
   ``backup/config/update``, then only ``encryption_key_set`` is read back.
   The secret never appears in the manifest, the response, or logs.
3. Add-on options land via ``/addons/<slug>/options`` and the add-on is
   started. Team Tracker flows are driven one per submitted team, reading
   the flow's own ``data_schema`` for field names — never assumed.
4. A backup-gated converge runs, then every item is verified by live
   read-back, not by the writes' return values.

Idempotent by construction: rows already present are skipped, a password
already set is not overwritten, a started add-on with matching options is
left alone, an existing team entity short-circuits its flow — so a second
identical submission applies zero changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .backup import backup_taker
from .engine import HAInitAgent
from .manifest import DEFAULT_MANIFEST_PATH
from .manifest_edit import merge_device_areas_into_manifest

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from homeiq_ha.client import HAClient

    from .recipe import Recipe

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


#: Substring sports-api filters on; wizard-created team sensors must carry it.
TEAM_MARKER = "team_tracker"


@dataclass(frozen=True)
class Answers:
    """One wizard submission. ``backup_password`` is write-only by contract."""

    device_areas: tuple[tuple[str, str], ...] = ()  # (device_id, area NAME)
    addon_options: tuple[tuple[str, dict[str, Any]], ...] = ()  # (slug, options)
    teams: tuple[dict[str, str], ...] = ()  # flow-field values per team
    backup_password: str | None = None


@dataclass
class _Item:
    id: str
    status: str  # converged | blocked | failed | skipped
    evidence: dict[str, Any] = field(default_factory=dict)


async def _set_backup_password(ha: HAClient, password: str) -> _Item:
    config = (await ha.ws.send_command("backup/config/info") or {}).get("config") or {}
    if (config.get("create_backup") or {}).get("password"):
        return _Item("backup_password", "skipped", {"encryption_key_set": True})
    await ha.ws.send_command(
        "backup/config/update", fields={"create_backup": {"password": password}}
    )
    # Read-back: only whether a key is set — never the key.
    config = (await ha.ws.send_command("backup/config/info") or {}).get("config") or {}
    key_set = bool((config.get("create_backup") or {}).get("password"))
    return _Item(
        "backup_password",
        "converged" if key_set else "failed",
        {"encryption_key_set": key_set},
    )


async def _apply_addon_options(ha: HAClient, slug: str, options: dict[str, Any]) -> _Item:
    info = await ha.ws.supervisor_api(f"/addons/{slug}/info", timeout=60) or {}
    current = info.get("options") or {}
    if all(current.get(k) == v for k, v in options.items()) and info.get("state") == "started":
        return _Item(f"addon:{slug}", "skipped", {"state": "started"})
    await ha.ws.supervisor_api(
        f"/addons/{slug}/options", method="post", payload={"options": options}
    )
    if info.get("state") != "started":
        await ha.ws.supervisor_api(f"/addons/{slug}/start", method="post")
    addons = (await ha.ws.supervisor_api("/addons", timeout=60) or {}).get("addons") or []
    state = next((a.get("state") for a in addons if a.get("slug") == slug), None)
    return _Item(
        f"addon:{slug}",
        "converged" if state == "started" else "failed",
        {"state": state},
    )


async def _team_entities(ha: HAClient, team_slug: str) -> list[str]:
    # Anchored: 'la' must not match team_tracker_lakers (verifier finding).
    pattern = re.compile(rf"{TEAM_MARKER}_{re.escape(team_slug)}(?![a-z0-9])")
    entities = await ha.ws.send_command("config/entity_registry/list") or []
    return [e["entity_id"] for e in entities if pattern.search(e.get("entity_id", ""))]


async def _drive_team_flow(ha: HAClient, team: dict[str, str]) -> _Item:
    team_slug = _slugify(team.get("team_id") or team.get("team") or "")
    item_id = f"team:{team_slug or 'unnamed'}"
    if not team_slug:
        return _Item(item_id, "failed", {"error": "answer has no team_id/team field"})
    if existing := await _team_entities(ha, team_slug):
        return _Item(item_id, "skipped", {"entity_ids": existing})

    step = await ha.rest.start_config_flow("teamtracker")
    first_kind = ha.rest.classify_flow_step(step)
    if first_kind == "abort":
        return _Item(item_id, "failed", {"error": f"flow aborted: {step.get('reason')}"})
    if first_kind == "create_entry":
        verified = await _team_entities(ha, team_slug)
        return _Item(item_id, "converged" if verified else "failed", {"entity_ids": verified})
    flow_id = step.get("flow_id")
    schema_fields = {str(f.get("name")) for f in step.get("data_schema") or []}
    # Fill only fields the flow itself declares — never assume the schema.
    user_input = {k: v for k, v in team.items() if k in schema_fields}
    if "name" in schema_fields and "name" not in user_input:
        # The entity_id derives from the name; sports-api filters on the marker.
        user_input["name"] = f"{TEAM_MARKER} {team_slug}"
    missing = schema_fields - set(user_input)
    if missing and not user_input:
        await ha.rest.abort_config_flow(flow_id)
        return _Item(
            item_id, "failed", {"error": f"no answer fields match flow schema {sorted(schema_fields)}"}
        )
    step = await ha.rest.advance_config_flow(flow_id, user_input)
    if ha.rest.classify_flow_step(step) != "create_entry":
        return _Item(
            item_id, "blocked", {"step": step.get("step_id"), "type": step.get("type")}
        )
    verified = await _team_entities(ha, team_slug)
    return _Item(
        item_id,
        "converged" if verified else "failed",
        {"entity_ids": verified},
    )


async def _validated_device_areas(
    ha: HAClient, device_areas: Sequence[tuple[str, str]]
) -> tuple[list[tuple[str, str]], list[_Item]]:
    """Split answers into registry-valid pairs and typed failures.

    A display name (or any unknown id) posted as a device_id would land as
    a junk manifest row that no converge can ever match — refused up front
    instead (Wave 7 panel finding).
    """
    known_ids = {
        d.get("id") for d in await ha.ws.send_command("config/device_registry/list") or []
    }
    valid: list[tuple[str, str]] = []
    failures: list[_Item] = []
    for device_id, area in device_areas:
        if device_id in known_ids:
            valid.append((device_id, area))
        else:
            failures.append(
                _Item(
                    f"device_area:{device_id}",
                    "failed",
                    {
                        "reason": "unknown_device_id",
                        "hint": "device_id must be a registry id, not a display name",
                    },
                )
            )
    return valid, failures


async def apply_answers(
    ha: HAClient,
    answers: Answers,
    recipes_factory: Callable[[], Sequence[Recipe]],
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """Apply one wizard submission end-to-end. See the module docstring.

    ``recipes_factory`` is invoked AFTER the manifest merge so the converge
    runs over the manifest the wizard just extended, not a stale load.
    """
    valid_areas, items = await _validated_device_areas(ha, answers.device_areas)

    reason = f"wizard submission {datetime.now(UTC).date().isoformat()}"
    try:
        merged = merge_device_areas_into_manifest(
            manifest_path, valid_areas, reason=reason
        )
        items.append(
            _Item(
                "manifest",
                "converged"
                if (merged["areas_added"] or merged["device_areas_added"])
                else "skipped",
                merged,
            )
        )
    except OSError as exc:
        # An unwritable mount must be a diagnosable item, never a 500.
        items.append(_Item("manifest", "failed", {"error": f"{type(exc).__name__}: {exc}"}))

    if answers.backup_password:
        items.append(await _set_backup_password(ha, answers.backup_password))
    for slug, options in answers.addon_options:
        items.append(await _apply_addon_options(ha, slug, options))
    for team in answers.teams:
        items.append(await _drive_team_flow(ha, team))

    # Backup-gated converge over the (possibly extended) manifest, then
    # verify the manifest-driven items by live read-back.
    report = await HAInitAgent(recipes_factory()).apply(ha, backup=backup_taker(ha))
    registry_areas = {
        a.get("area_id") for a in await ha.ws.send_command("config/area_registry/list") or []
    }
    devices = {
        d.get("id"): d.get("area_id")
        for d in await ha.ws.send_command("config/device_registry/list") or []
    }
    for device_id, area_name in valid_areas:
        area_id = _slugify(area_name)
        ok = area_id in registry_areas and devices.get(device_id) == area_id
        items.append(
            _Item(
                f"device_area:{device_id}",
                "converged" if ok else "blocked",
                {"area_id": area_id, "live_area": devices.get(device_id)},
            )
        )

    return {
        "items": [{"id": i.id, "status": i.status, "evidence": i.evidence} for i in items],
        "converge": {
            "total_changes": report.total_changes,
            "wrote_nothing": report.wrote_nothing,
            "halted_reason": report.halted_reason,
            "blocked_on_human": report.blocked_on_human,
            "outcomes": [
                {"name": o.name, "status": o.check.status.value, "error": o.error}
                for o in report.outcomes
            ],
        },
    }


__all__ = [
    "TEAM_MARKER",
    "Answers",
    "apply_answers",
    "merge_device_areas_into_manifest",
]  # merge re-exported from .manifest_edit for callers
