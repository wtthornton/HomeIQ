"""Organization recipes: registry names and manifest-driven convergence.

These converge the live instance to the desired-state manifest AgentForge
authored and a judge reviewed (config/ha-organization-manifest.yaml).
Deterministic on purpose: every decision about which room, which label, which
alias lives in the manifest — never here.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .recipe import (
    PHASE_ORGANIZATION,
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

    from .manifest import OrganizationManifest


def _slugify(name: str) -> str:
    """Approximate HA's registry slugification (lowercase, non-alnum -> _).

    Same rule as admin-api's label resolver (commit 02b5b42a): HA stores
    label_ids as slugs, and matching by name alone mints ``<slug>_2``
    duplicates on every re-apply.
    """
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class ManifestEntityLabelsRecipe(Recipe):
    """Converge entity labels to the manifest, managed-set semantics.

    Labels under ``managed_label_prefixes`` are fully reconciled — added when
    the manifest lists them, removed when it no longer does. Labels outside
    the managed prefixes are never touched, so a person's ad-hoc label
    survives every converge.

    Registry hygiene: a wanted label is matched against existing registry
    entries by exact name OR by slug before being created (the ``<slug>_2``
    trap — admin-api commit 02b5b42a; same discipline here).
    """

    name = "organization.entity_labels"
    phase = PHASE_ORGANIZATION
    description = "Manifest entity labels converged (managed prefixes only)"

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    def _is_managed(self, label_name: str, label_id: str) -> bool:
        return any(
            label_name.startswith(prefix) or label_id.startswith(_slugify(prefix) + "_")
            for prefix in self.manifest.managed_label_prefixes
        )

    @staticmethod
    def _resolve(wanted: str, registry: list[dict[str, Any]]) -> str | None:
        """Existing label_id for ``wanted``, or None when it must be created."""
        slug = _slugify(wanted)
        for entry in registry:
            if entry.get("name") == wanted or entry.get("label_id") == slug:
                return str(entry["label_id"])
            if _slugify(str(entry.get("name") or "")) == slug:
                return str(entry["label_id"])
        return None

    def _desired_ids(
        self,
        labels: tuple[str, ...],
        registry: list[dict[str, Any]],
        to_create: list[str],
    ) -> list[str]:
        """Resolve manifest label strings to registry ids, queueing creations."""
        desired: list[str] = []
        for label in labels:
            resolved = self._resolve(label, registry)
            if resolved is None:
                if label not in to_create:
                    to_create.append(label)
                # Not yet in the registry: its id after creation is the slug.
                resolved = _slugify(label)
            desired.append(resolved)
        return desired

    def _target(
        self,
        entity: dict[str, Any],
        desired_ids: list[str],
        names_by_id: dict[str, str],
    ) -> tuple[list[str], list[str]]:
        """(current, target) label ids: unmanaged survive, managed reconcile."""
        current = [str(label) for label in entity.get("labels") or []]
        unmanaged = [
            label_id
            for label_id in current
            if not self._is_managed(names_by_id.get(label_id, label_id), label_id)
        ]
        return current, unmanaged + [i for i in desired_ids if i not in unmanaged]

    async def _state(
        self, ha: Any
    ) -> tuple[list[str], dict[str, tuple[list[str], list[str]]], list[str]]:
        """(labels to create, entity -> (current, target) label ids, stale ids)."""
        registry = list(await ha.ws.send_command("config/label_registry/list") or [])
        entities = await ha.ws.send_command("config/entity_registry/list")
        by_entity = {e["entity_id"]: e for e in entities or []}
        names_by_id = {str(e["label_id"]): str(e.get("name") or e["label_id"]) for e in registry}

        to_create: list[str] = []
        moves: dict[str, tuple[list[str], list[str]]] = {}
        stale: list[str] = []

        for row in self.manifest.entity_labels:
            entity = by_entity.get(row.entity_id)
            if entity is None:
                stale.append(row.entity_id)
                continue
            desired_ids = self._desired_ids(row.labels, registry, to_create)
            current, target = self._target(entity, desired_ids, names_by_id)
            if set(target) != set(current):
                moves[row.entity_id] = (current, target)

        return to_create, moves, stale

    def _changes(
        self, to_create: list[str], moves: dict[str, tuple[list[str], list[str]]]
    ) -> list[Change]:
        changes = [Change("create", f"label:{name}", after=name) for name in to_create]
        changes.extend(
            Change("set", f"entity:{entity_id}.labels", sorted(current), sorted(target))
            for entity_id, (current, target) in moves.items()
        )
        return changes

    async def check(self, ha: HAClient) -> CheckResult:
        to_create, moves, stale = await self._state(ha)
        changes = self._changes(to_create, moves)
        details = {
            "drift": [c.describe() for c in changes],
            "stale_entity_ids": stale,
        }
        if changes:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{len(to_create)} label(s) to create, {len(moves)} entity/entities to relabel",
                details,
            )
        summary = "manifest entity labels converged"
        if stale:
            summary += f" ({len(stale)} stale manifest row(s) skipped)"
        return CheckResult(CheckStatus.SATISFIED, summary, details)

    async def plan(self, ha: HAClient) -> Plan:
        to_create, moves, _ = await self._state(ha)
        return Plan(tuple(self._changes(to_create, moves)))

    async def apply(self, ha: HAClient) -> ApplyResult:
        to_create, moves, _ = await self._state(ha)
        applied = self._changes(to_create, moves)
        if not applied:
            return ApplyResult((), "already converged")

        for name in to_create:
            await ha.ws.send_command("config/label_registry/create", name=name)

        if to_create:
            # Re-resolve against the registry as it now exists rather than
            # trusting the predicted slugs.
            to_create_after, moves, _ = await self._state(ha)
            if to_create_after:
                return ApplyResult(
                    (),
                    f"label creation did not land: {to_create_after}",
                )

        for entity_id, (_current, target) in moves.items():
            await ha.ws.send_command(
                "config/entity_registry/update",
                entity_id=entity_id,
                labels=target,
            )
        return ApplyResult(
            tuple(applied),
            f"created {len(to_create)} label(s), relabelled {len(moves)} entity/entities",
        )

    async def verify(self, ha: HAClient) -> VerifyResult:
        to_create, moves, stale = await self._state(ha)
        remaining = self._changes(to_create, moves)
        return VerifyResult(
            not remaining,
            "entity labels match the manifest"
            if not remaining
            else f"still drifted: {[c.describe() for c in remaining]}",
            {"stale_entity_ids": stale},
        )


class ManifestEntityAliasesRecipe(Recipe):
    """Converge entity aliases to the manifest, additively.

    Aliases have no namespace to scope a managed set to, so this recipe only
    ever adds manifest aliases — an alias a person taught their voice
    assistant by hand survives every converge.
    """

    name = "organization.entity_aliases"
    phase = PHASE_ORGANIZATION
    description = "Manifest entity aliases present"

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    async def _state(self, ha: Any) -> tuple[dict[str, tuple[list[str], list[str]]], list[str]]:
        """Diff manifest aliases against the registry.

        Existence is settled from the list, but aliases are read one entity at
        a time: ``config/entity_registry/list`` returns a trimmed row that omits
        ``aliases`` entirely, so every entity looked like it had none. The check
        could never reach SATISFIED and a nightly converge rewrote the same
        aliases forever. ``config/entity_registry/get`` returns the full entry.
        The extra round trips are bounded by the manifest, not the instance —
        only entities this recipe manages are fetched.
        """
        entities = await ha.ws.send_command("config/entity_registry/list")
        known = {e["entity_id"] for e in entities or []}
        moves: dict[str, tuple[list[str], list[str]]] = {}
        stale: list[str] = []
        for row in self.manifest.entity_aliases:
            if row.entity_id not in known:
                stale.append(row.entity_id)
                continue
            entry = await ha.ws.send_command("config/entity_registry/get", entity_id=row.entity_id)
            current = [str(a) for a in (entry or {}).get("aliases") or []]
            missing = [a for a in row.aliases if a not in current]
            if missing:
                moves[row.entity_id] = (current, current + missing)
        return moves, stale

    def _changes(self, moves: dict[str, tuple[list[str], list[str]]]) -> list[Change]:
        return [
            Change("set", f"entity:{entity_id}.aliases", current, target)
            for entity_id, (current, target) in moves.items()
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        moves, stale = await self._state(ha)
        details = {
            "drift": [c.describe() for c in self._changes(moves)],
            "stale_entity_ids": stale,
        }
        if moves:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{len(moves)} entity/entities missing manifest aliases",
                details,
            )
        summary = "manifest aliases present"
        if stale:
            summary += f" ({len(stale)} stale manifest row(s) skipped)"
        return CheckResult(CheckStatus.SATISFIED, summary, details)

    async def plan(self, ha: HAClient) -> Plan:
        moves, _ = await self._state(ha)
        return Plan(tuple(self._changes(moves)))

    async def apply(self, ha: HAClient) -> ApplyResult:
        moves, _ = await self._state(ha)
        applied = self._changes(moves)
        for entity_id, (_current, target) in moves.items():
            await ha.ws.send_command(
                "config/entity_registry/update",
                entity_id=entity_id,
                aliases=target,
            )
        return ApplyResult(tuple(applied), f"updated {len(moves)} entity/entities")

    async def verify(self, ha: HAClient) -> VerifyResult:
        moves, stale = await self._state(ha)
        remaining = self._changes(moves)
        return VerifyResult(
            not remaining,
            "aliases match the manifest"
            if not remaining
            else f"still drifted: {[c.describe() for c in remaining]}",
            {"stale_entity_ids": stale},
        )


__all__ = [
    "ManifestEntityAliasesRecipe",
    "ManifestEntityLabelsRecipe",
]
