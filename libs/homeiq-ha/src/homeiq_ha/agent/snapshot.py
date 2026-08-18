"""Capture, diff, and restore Home Assistant state.

This is what makes the agent testable against a real instance. Without it,
running `apply` against someone's home is a one-way door: you find out the
recipe was wrong *after* it has already changed things, with no way back.

The loop this enables is:

    capture baseline -> apply -> verify -> restore -> diff == empty -> fix -> repeat

:func:`capture` is strictly read-only. :func:`diff` compares a live instance
against a captured baseline and is also read-only. :func:`restore` is the only
function here that writes, and it writes only what :func:`diff` reports.

**Restore is a targeted inverse, not a backup restore.** It deletes registry
entries that appeared, recreates ones that vanished, and puts changed fields
back. That is precise and cheap, but it is bounded: it reverts what the agent's
recipes can create. A Home Assistant backup remains the correct safety net for
anything wider, and :func:`restore` is not a substitute for one.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from .backup import wait_until_idle
from .recipe import Change

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

#: Registries captured by name, each keyed by its own id field.
REGISTRY_KEYS: dict[str, str] = {
    "area_registry": "area_id",
    "floor_registry": "floor_id",
    "label_registry": "label_id",
}

#: Core config fields the agent's recipes can change.
CORE_CONFIG_FIELDS = ("currency", "country", "time_zone", "language")

#: Device registry fields the agent's recipes can change.
DEVICE_FIELDS = ("area_id", "name_by_user", "labels", "disabled_by")

#: Entity registry fields the agent's recipes can change.
ENTITY_FIELDS = ("area_id", "name", "icon", "labels", "hidden_by", "disabled_by")


@dataclass
class Snapshot:
    """Everything the agent could plausibly change, as it was at capture time."""

    areas: dict[str, dict[str, Any]] = field(default_factory=dict)
    floors: dict[str, dict[str, Any]] = field(default_factory=dict)
    labels: dict[str, dict[str, Any]] = field(default_factory=dict)
    devices: dict[str, dict[str, Any]] = field(default_factory=dict)
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    config_entries: dict[str, str] = field(default_factory=dict)
    addons: dict[str, str] = field(default_factory=dict)
    core_config: dict[str, Any] = field(default_factory=dict)
    backup_config: dict[str, Any] = field(default_factory=dict)
    backup_ids: list[str] = field(default_factory=list)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, sort_keys=True, default=str)

    @classmethod
    def from_json(cls, raw: str) -> Snapshot:
        return cls(**json.loads(raw))

    def summary(self) -> str:
        return (
            f"areas={len(self.areas)} floors={len(self.floors)} "
            f"labels={len(self.labels)} devices={len(self.devices)} "
            f"entities={len(self.entities)} config_entries={len(self.config_entries)} "
            f"addons={len(self.addons)} backups={len(self.backup_ids)}"
        )


def _agent_ids(source: dict[str, Any]) -> list[str]:
    """Backup destinations, normalised so a missing key equals none configured.

    Baselines captured before destinations were tracked have no ``agent_ids``
    key at all; treating that as ``[]`` keeps them comparable instead of
    reporting a permanent difference that no restore could ever clear.
    """
    return [str(agent) for agent in source.get("agent_ids") or ()]


def _project(entry: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Keep only the fields the agent can change.

    Capturing everything would make `diff` fire on values Home Assistant
    updates on its own (last_seen, sw_version), which would drown the signal.
    """
    return {name: entry.get(name) for name in fields}


async def capture(ha: HAClient) -> Snapshot:
    """Read the current state. Issues no writes."""
    snapshot = Snapshot()

    for registry, id_field in REGISTRY_KEYS.items():
        entries = await ha.ws.send_command(f"config/{registry}/list") or []
        attr = {"area_registry": "areas", "floor_registry": "floors", "label_registry": "labels"}[
            registry
        ]
        target = getattr(snapshot, attr)
        for entry in entries:
            target[str(entry[id_field])] = {"name": entry.get("name")}

    for device in await ha.ws.send_command("config/device_registry/list") or []:
        snapshot.devices[str(device["id"])] = _project(device, DEVICE_FIELDS)

    for entity in await ha.ws.send_command("config/entity_registry/list") or []:
        snapshot.entities[str(entity["entity_id"])] = _project(entity, ENTITY_FIELDS)

    for entry in await ha.rest.get_config_entries() or []:
        snapshot.config_entries[str(entry["entry_id"])] = str(entry.get("domain"))

    core = await ha.ws.send_command("get_config") or {}
    snapshot.core_config = _project(core, CORE_CONFIG_FIELDS)

    backup = await ha.ws.send_command("backup/config/info") or {}
    config = dict(backup.get("config") or {})
    snapshot.backup_config = {
        "schedule": config.get("schedule"),
        "retention": config.get("retention"),
        # Destinations are written by the backup-schedule recipe, so restore
        # has to be able to put them back too.
        "agent_ids": _agent_ids(config.get("create_backup") or {}),
        # Whether a key exists, never the key itself.
        "encryption_key_set": bool((config.get("create_backup") or {}).get("password")),
    }

    # Reading ids mid-job would miss a backup that lands moments later, which
    # would then be invisible to `diff` and survive `restore` — leaving residue
    # on an instance the caller was told is back at its baseline.
    snapshot.backup_ids = list((await wait_until_idle(ha)).backup_ids)

    try:
        addons = await ha.ws.supervisor_api("/addons", timeout=60) or {}
        for addon in addons.get("addons") or []:
            snapshot.addons[str(addon["slug"])] = str(addon.get("state"))
    except Exception:  # noqa: BLE001 - a non-Supervised install has no Supervisor
        snapshot.addons = {}

    return snapshot


async def diff(ha: HAClient, baseline: Snapshot) -> list[Change]:
    """Report how the live instance differs from ``baseline``. Read-only.

    An empty list is the assertion that a restore worked.
    """
    current = await capture(ha)
    changes: list[Change] = []

    for kind in ("areas", "floors", "labels"):
        before: dict[str, Any] = getattr(baseline, kind)
        after: dict[str, Any] = getattr(current, kind)
        for key in after.keys() - before.keys():
            name = after[key].get("name", key)
            changes.append(Change("added", f"{kind}:{name}", after=key))
        for key in before.keys() - after.keys():
            name = before[key].get("name", key)
            changes.append(Change("removed", f"{kind}:{name}", before=key))

    for kind, fields in (("devices", DEVICE_FIELDS), ("entities", ENTITY_FIELDS)):
        before = getattr(baseline, kind)
        after = getattr(current, kind)
        for key in before.keys() & after.keys():
            for name in fields:
                if before[key].get(name) != after[key].get(name):
                    changes.append(
                        Change(
                            "changed",
                            f"{kind}:{key}.{name}",
                            before[key].get(name),
                            after[key].get(name),
                        )
                    )

    for entry_id in current.config_entries.keys() - baseline.config_entries.keys():
        domain = current.config_entries[entry_id]
        changes.append(Change("added", f"config_entry:{domain}", after=entry_id))
    for entry_id in baseline.config_entries.keys() - current.config_entries.keys():
        domain = baseline.config_entries[entry_id]
        changes.append(Change("removed", f"config_entry:{domain}", before=entry_id))

    for slug in current.addons.keys() - baseline.addons.keys():
        changes.append(Change("added", f"addon:{slug}", after=current.addons[slug]))
    for slug in baseline.addons.keys() - current.addons.keys():
        changes.append(Change("removed", f"addon:{slug}", before=baseline.addons[slug]))

    for name in CORE_CONFIG_FIELDS:
        if baseline.core_config.get(name) != current.core_config.get(name):
            changes.append(
                Change(
                    "changed",
                    f"core_config.{name}",
                    baseline.core_config.get(name),
                    current.core_config.get(name),
                )
            )

    for name in ("schedule", "retention"):
        if baseline.backup_config.get(name) != current.backup_config.get(name):
            changes.append(
                Change(
                    "changed",
                    f"backup_config.{name}",
                    baseline.backup_config.get(name),
                    current.backup_config.get(name),
                )
            )

    before_agents = _agent_ids(baseline.backup_config)
    after_agents = _agent_ids(current.backup_config)
    if before_agents != after_agents:
        changes.append(Change("changed", "backup_config.agent_ids", before_agents, after_agents))

    for backup_id in set(current.backup_ids) - set(baseline.backup_ids):
        changes.append(Change("added", f"backup:{backup_id}", after=backup_id))

    return changes


class RestoreIncomplete(RuntimeError):
    """Restore ran but the instance still differs from the baseline."""

    def __init__(self, remaining: list[Change]) -> None:
        super().__init__(
            f"{len(remaining)} difference(s) remain after restore: "
            + "; ".join(c.describe() for c in remaining[:5])
        )
        self.remaining = remaining


async def restore(ha: HAClient, baseline: Snapshot, *, strict: bool = True) -> list[Change]:
    """Put the instance back to ``baseline`` and return what was reverted.

    Args:
        strict: Re-run :func:`diff` afterwards and raise
            :class:`RestoreIncomplete` if anything still differs. On by
            default — a restore that silently half-works is worse than one
            that fails loudly, because the next test run starts from a
            polluted baseline and every result after it is suspect.

    Known limitation: an area, floor or label that was *deleted* since the
    baseline is recreated by name and receives a **new id**. Anything that
    referenced the old id will not be reattached. The agent's recipes only ever
    create these, so this path is defensive rather than routine.
    """
    current = await capture(ha)
    reverted: list[Change] = []

    # Registry entries that appeared -> delete. Do these before restoring
    # device/entity fields, so an area being removed does not leave devices
    # pointing at an id that no longer exists.
    for kind, registry, id_field in (
        ("labels", "label_registry", "label_id"),
        ("floors", "floor_registry", "floor_id"),
        ("areas", "area_registry", "area_id"),
    ):
        before: dict[str, Any] = getattr(baseline, kind)
        after: dict[str, Any] = getattr(current, kind)
        for key in after.keys() - before.keys():
            await ha.ws.send_command(f"config/{registry}/delete", **{id_field: key})
            name = after[key].get("name", key)
            reverted.append(Change("delete", f"{kind}:{name}"))
        for key in before.keys() - after.keys():
            await ha.ws.send_command(f"config/{registry}/create", name=before[key].get("name"))
            reverted.append(Change("recreate", f"{kind}:{before[key].get('name', key)}"))

    # Field-level reverts on devices and entities.
    for kind, registry, id_field, fields in (
        ("devices", "device_registry", "device_id", DEVICE_FIELDS),
        ("entities", "entity_registry", "entity_id", ENTITY_FIELDS),
    ):
        before = getattr(baseline, kind)
        after = getattr(current, kind)
        for key in before.keys() & after.keys():
            drift = {
                name: before[key].get(name)
                for name in fields
                if before[key].get(name) != after[key].get(name)
            }
            if drift:
                await ha.ws.send_command(f"config/{registry}/update", **{id_field: key}, **drift)
                reverted.append(Change("revert", f"{kind}:{key}", after=list(drift)))

    # Config entries that appeared -> remove.
    for entry_id in current.config_entries.keys() - baseline.config_entries.keys():
        domain = current.config_entries[entry_id]
        await ha.rest.request("DELETE", f"/api/config/config_entries/entry/{entry_id}")
        reverted.append(Change("delete", f"config_entry:{domain}"))

    # Add-ons that appeared -> uninstall.
    for slug in current.addons.keys() - baseline.addons.keys():
        await ha.ws.supervisor_api(f"/addons/{slug}/uninstall", method="post")
        reverted.append(Change("uninstall", f"addon:{slug}"))

    core_drift = {
        name: baseline.core_config.get(name)
        for name in CORE_CONFIG_FIELDS
        if baseline.core_config.get(name) != current.core_config.get(name)
    }
    if core_drift:
        await ha.ws.send_command("config/core/update", fields=core_drift)
        reverted.append(Change("revert", "core_config", after=list(core_drift)))

    backup_drift: dict[str, Any] = {
        name: baseline.backup_config.get(name)
        for name in ("schedule", "retention")
        if baseline.backup_config.get(name) != current.backup_config.get(name)
    }
    # Destinations live under create_backup in the update payload, not at the
    # top level like schedule and retention.
    if _agent_ids(baseline.backup_config) != _agent_ids(current.backup_config):
        backup_drift["create_backup"] = {"agent_ids": _agent_ids(baseline.backup_config)}
    if backup_drift:
        await ha.ws.send_command("backup/config/update", fields=backup_drift)
        reverted.append(Change("revert", "backup_config", after=list(backup_drift)))

    for backup_id in set(current.backup_ids) - set(baseline.backup_ids):
        await ha.ws.send_command("backup/delete", fields={"backup_id": backup_id})
        reverted.append(Change("delete", f"backup:{backup_id}"))

    if strict:
        remaining = await diff(ha, baseline)
        if remaining:
            raise RestoreIncomplete(remaining)

    return reverted
