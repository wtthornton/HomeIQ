"""Pure diff computation between two :class:`~homeiq_ha.agent.snapshot.Snapshot` captures.

Split out of :mod:`.snapshot` to keep both files under the maintainability
gate (TAP-6486 round 2) — every function here takes two already-captured
snapshots and does no I/O of its own, so each is also independently
unit-testable without a simulator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .recipe import Change

if TYPE_CHECKING:
    from .snapshot import Snapshot

#: Core config fields the agent's recipes can change.
CORE_CONFIG_FIELDS = ("currency", "country", "time_zone", "language")

#: Device registry fields the agent's recipes can change.
DEVICE_FIELDS = ("area_id", "name_by_user", "labels", "disabled_by")

#: Entity registry fields the agent's recipes can change.
ENTITY_FIELDS = ("area_id", "name", "icon", "labels", "hidden_by", "disabled_by")


def agent_ids(source: dict[str, Any]) -> list[str]:
    """Backup destinations, normalised so a missing key equals none configured.

    Baselines captured before destinations were tracked have no ``agent_ids``
    key at all; treating that as ``[]`` keeps them comparable instead of
    reporting a permanent difference that no restore could ever clear.
    """
    return [str(agent) for agent in source.get("agent_ids") or ()]


def diff_registries(baseline: Snapshot, current: Snapshot) -> list[Change]:
    """Areas/floors/labels added or removed since ``baseline``."""
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
    return changes


def diff_field_drift(baseline: Snapshot, current: Snapshot) -> list[Change]:
    """Field-level changes on devices and entities present in both."""
    changes: list[Change] = []
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
    return changes


def diff_config_entries(baseline: Snapshot, current: Snapshot) -> list[Change]:
    changes: list[Change] = []
    for entry_id in current.config_entries.keys() - baseline.config_entries.keys():
        domain = current.config_entries[entry_id]
        changes.append(Change("added", f"config_entry:{domain}", after=entry_id))
    for entry_id in baseline.config_entries.keys() - current.config_entries.keys():
        domain = baseline.config_entries[entry_id]
        changes.append(Change("removed", f"config_entry:{domain}", before=entry_id))
    return changes


def diff_core_config(baseline: Snapshot, current: Snapshot) -> list[Change]:
    return [
        Change(
            "changed",
            f"core_config.{name}",
            baseline.core_config.get(name),
            current.core_config.get(name),
        )
        for name in CORE_CONFIG_FIELDS
        if baseline.core_config.get(name) != current.core_config.get(name)
    ]


def diff_backup_config(baseline: Snapshot, current: Snapshot) -> list[Change]:
    changes: list[Change] = [
        Change(
            "changed",
            f"backup_config.{name}",
            baseline.backup_config.get(name),
            current.backup_config.get(name),
        )
        for name in ("schedule", "retention")
        if baseline.backup_config.get(name) != current.backup_config.get(name)
    ]
    before_agents = agent_ids(baseline.backup_config)
    after_agents = agent_ids(current.backup_config)
    if before_agents != after_agents:
        changes.append(Change("changed", "backup_config.agent_ids", before_agents, after_agents))
    return changes


def diff_backups(baseline: Snapshot, current: Snapshot) -> list[Change]:
    return [
        Change("added", f"backup:{backup_id}", after=backup_id)
        for backup_id in set(current.backup_ids) - set(baseline.backup_ids)
    ]


def compute_diff(baseline: Snapshot, current: Snapshot) -> list[Change]:
    """How ``current`` differs from ``baseline``, one section at a time.

    An empty list is the assertion that a restore worked.
    """
    changes: list[Change] = []
    changes.extend(diff_registries(baseline, current))
    changes.extend(diff_field_drift(baseline, current))
    changes.extend(diff_config_entries(baseline, current))
    changes.extend(diff_core_config(baseline, current))
    changes.extend(diff_backup_config(baseline, current))
    changes.extend(diff_backups(baseline, current))
    return changes


__all__ = [
    "CORE_CONFIG_FIELDS",
    "DEVICE_FIELDS",
    "ENTITY_FIELDS",
    "agent_ids",
    "compute_diff",
]
