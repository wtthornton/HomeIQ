"""Desired-state organization manifest, authored by AgentForge, committed to git.

The manifest is the contract between AF cognition (which rooms, which labels,
which aliases) and the deterministic recipes here (which converge the live
instance to it). Loading is read-only and side-effect free; recipes receive the
frozen result and never re-derive decisions from it.

Reconciliation semantics (per expert-architecture consultation 3715b66a):

- ``entity_labels`` are a **managed set**: labels whose registry name starts
  with one of ``managed_label_prefixes`` are fully reconciled — added when the
  manifest lists them, removed when it no longer does. Labels outside the
  managed prefixes are never touched.
- ``entity_aliases`` are **additive**: aliases have no namespace to scope a
  managed set to, so the recipe only ever adds manifest aliases and never
  removes one a person created by hand.
- ``not_applicable`` rows are for people and audits; convergence ignores them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

#: Where the committed manifest lives, relative to the repo root.
DEFAULT_MANIFEST_PATH = Path("config/ha-organization-manifest.yaml")


@dataclass(frozen=True)
class DeviceArea:
    device_id: str
    area_id: str
    reason: str


@dataclass(frozen=True)
class EntityLabels:
    entity_id: str
    labels: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class EntityAliases:
    entity_id: str
    aliases: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class Helper:
    """One helper the manifest declares.

    ``kind`` is the config-flow handler (``group``, ``template``,
    ``input_boolean``); ``slug`` is the stable identity the recipe keys on
    (the expected object id of the created entity); ``config`` carries the
    flow's form fields minus the name.
    """

    kind: str
    slug: str
    name: str
    config: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class OrganizationManifest:
    managed_label_prefixes: tuple[str, ...]
    device_areas: tuple[DeviceArea, ...]
    entity_labels: tuple[EntityLabels, ...]
    entity_aliases: tuple[EntityAliases, ...]
    helpers: tuple[Helper, ...]


def load_manifest(path: str | Path = DEFAULT_MANIFEST_PATH) -> OrganizationManifest:
    """Load and freeze the committed manifest.

    Raises:
        FileNotFoundError: no manifest at ``path``.
        KeyError: the document has no ``manifest`` mapping — a truncated or
            hand-mangled file must fail loudly, not converge to nothing.
    """
    document = yaml.safe_load(Path(path).read_text())
    body = document["manifest"]
    return OrganizationManifest(
        managed_label_prefixes=tuple(body.get("managed_label_prefixes") or ()),
        device_areas=tuple(
            DeviceArea(row["device_id"], row["area_id"], row.get("reason", ""))
            for row in body.get("device_areas") or ()
        ),
        entity_labels=tuple(
            EntityLabels(row["entity_id"], tuple(row.get("labels") or ()), row.get("reason", ""))
            for row in body.get("entity_labels") or ()
        ),
        entity_aliases=tuple(
            EntityAliases(row["entity_id"], tuple(row.get("aliases") or ()), row.get("reason", ""))
            for row in body.get("entity_aliases") or ()
        ),
        helpers=tuple(
            Helper(
                row["kind"],
                row["slug"],
                row["name"],
                dict(row.get("config") or {}),
                row.get("reason", ""),
            )
            for row in body.get("helpers") or ()
        ),
    )


__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "DeviceArea",
    "EntityAliases",
    "EntityLabels",
    "Helper",
    "OrganizationManifest",
    "load_manifest",
]
