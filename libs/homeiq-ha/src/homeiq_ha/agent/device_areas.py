"""Area lifecycle from the manifest: device→area assignment, artifact-area removal.

``ManifestAreasRemoveRecipe`` lives here with ``ManifestDeviceAreasRecipe``
because removal is gated on the areas that recipe empties (TAP-5974).
"""

from __future__ import annotations

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


class ManifestDeviceAreasRecipe(Recipe):
    """Converge manifest areas and device→area assignments.

    Missing manifest areas are created first (keyed by HA's own slug — a
    device name that names a room is sufficient evidence to create that
    room, per the owner's standing rule 2026-08-12), then devices are
    assigned. The report-only :class:`DevicesHaveAreasRecipe` stays for
    devices the manifest does not cover.

    A manifest ``device_id`` missing from the live registry is deletion
    drift: reported in details and skipped, never a crash (stable ids only
    protect against renames, not removals).
    """

    name = "organization.device_area_assignments"
    phase = PHASE_ORGANIZATION
    description = "Manifest areas exist and manifest-assigned devices are in them"

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    async def _missing_areas(self, ha: Any) -> list[Any]:
        existing = {
            area["area_id"] for area in await ha.ws.send_command("config/area_registry/list") or []
        }
        return [area for area in self.manifest.areas if area.area_id not in existing]

    async def _state(self, ha: Any) -> tuple[list[Change], list[str]]:
        drift: list[Change] = [
            Change("create", f"area:{area.area_id}", after=area.name)
            for area in await self._missing_areas(ha)
        ]
        devices = await ha.ws.send_command("config/device_registry/list")
        by_id = {device["id"]: device for device in devices or []}
        stale: list[str] = []
        for row in self.manifest.device_areas:
            device = by_id.get(row.device_id)
            if device is None:
                stale.append(row.device_id)
                continue
            if device.get("area_id") != row.area_id:
                drift.append(
                    Change(
                        "set", f"device:{row.device_id}.area_id", device.get("area_id"), row.area_id
                    )
                )
        return drift, stale

    async def check(self, ha: HAClient) -> CheckResult:
        drift, stale = await self._state(ha)
        details = {"drift": [c.describe() for c in drift], "stale_device_ids": stale}
        if drift:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{len(drift)} area/device change(s) needed",
                details,
            )
        summary = "manifest device areas converged"
        if stale:
            summary += f" ({len(stale)} stale manifest row(s) skipped)"
        return CheckResult(CheckStatus.SATISFIED, summary, details)

    async def plan(self, ha: HAClient) -> Plan:
        drift, _ = await self._state(ha)
        return Plan(tuple(drift))

    async def apply(self, ha: HAClient) -> ApplyResult:
        applied: list[Change] = []
        for area in await self._missing_areas(ha):
            created = await ha.ws.send_command("config/area_registry/create", name=area.name)
            change = Change("create", f"area:{area.area_id}", after=area.name)
            applied.append(change)
            created_id = (created or {}).get("area_id")
            if created_id and created_id != area.area_id:
                # HA slugified the name differently than the manifest predicted
                # — surface loudly instead of assigning devices into a void.
                return ApplyResult(
                    tuple(applied),
                    f"area {area.name!r} created as {created_id!r}, "
                    f"manifest says {area.area_id!r} — fix the manifest slug",
                )

        drift, _ = await self._state(ha)
        for row in self.manifest.device_areas:
            target = f"device:{row.device_id}.area_id"
            for change in drift:
                if change.target == target:
                    await ha.ws.send_command(
                        "config/device_registry/update",
                        device_id=row.device_id,
                        area_id=row.area_id,
                    )
                    applied.append(change)
        return ApplyResult(tuple(applied), f"{len(applied)} area/device change(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        drift, stale = await self._state(ha)
        return VerifyResult(
            not drift,
            "areas and device assignments match the manifest"
            if not drift
            else f"still drifted: {[c.describe() for c in drift]}",
            {"stale_device_ids": stale},
        )


__all__ = ["ManifestDeviceAreasRecipe"]


class ManifestAreasRemoveRecipe(Recipe):
    """Remove areas the manifest declares as artifacts (``areas_remove``).

    Hard guard: removal only ever applies to an EMPTY area. While any device
    or entity is still assigned, the row reports BLOCKED_ON_HUMAN instead of
    deleting — the standing never-do is "deleting areas with assigned
    devices", and a stale removal row must not orphan anything. Runs after
    :class:`ManifestDeviceAreasRecipe` so manifest-declared device moves
    (e.g. the Hue "tv" zone's strips moving to living_room, TAP-5974) have
    already emptied the area by the time removal is considered.
    """

    name = "organization.areas_remove"
    phase = PHASE_ORGANIZATION
    description = "Manifest-declared artifact areas are absent"

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    async def _occupancy(self, ha: Any) -> dict[str, dict[str, int]]:
        """area_id -> counts of devices/entities still assigned, for rows that exist."""
        existing = {
            area["area_id"]
            for area in await ha.ws.send_command("config/area_registry/list") or []
        }
        wanted = [r for r in self.manifest.areas_remove if r.area_id in existing]
        if not wanted:
            return {}
        devices = await ha.ws.send_command("config/device_registry/list") or []
        entities = await ha.ws.send_command("config/entity_registry/list") or []
        occupancy: dict[str, dict[str, int]] = {}
        for removal in wanted:
            occupancy[removal.area_id] = {
                "devices": sum(1 for d in devices if d.get("area_id") == removal.area_id),
                "entities": sum(1 for e in entities if e.get("area_id") == removal.area_id),
            }
        return occupancy

    async def check(self, ha: HAClient) -> CheckResult:
        occupancy = await self._occupancy(ha)
        if not occupancy:
            return CheckResult(
                CheckStatus.SATISFIED,
                f"all {len(self.manifest.areas_remove)} declared removal(s) absent",
            )
        occupied = {a: c for a, c in occupancy.items() if c["devices"] or c["entities"]}
        if occupied:
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                f"{len(occupied)} removal-declared area(s) still occupied",
                {"occupied": occupied},
                human_action=(
                    "Areas declared for removal still hold devices/entities: "
                    f"{sorted(occupied)}. Move or unassign them (or drop the "
                    "manifest areas_remove row) before removal can apply."
                ),
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            f"{len(occupancy)} empty artifact area(s) to remove",
            {"to_remove": sorted(occupancy)},
        )

    async def plan(self, ha: HAClient) -> Plan:
        occupancy = await self._occupancy(ha)
        return Plan(
            tuple(
                Change("delete", f"area:{area_id}", before=area_id)
                for area_id, counts in sorted(occupancy.items())
                if not counts["devices"] and not counts["entities"]
            )
        )

    async def apply(self, ha: HAClient) -> ApplyResult:
        # Re-check emptiness at apply time — the registry may have changed
        # since check(); the guard is load-bearing, not advisory.
        occupancy = await self._occupancy(ha)
        deleted: list[Change] = []
        for area_id, counts in sorted(occupancy.items()):
            if counts["devices"] or counts["entities"]:
                continue
            await ha.ws.send_command("config/area_registry/delete", area_id=area_id)
            deleted.append(Change("delete", f"area:{area_id}", before=area_id))
        return ApplyResult(tuple(deleted), f"deleted {len(deleted)} empty area(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        existing = {
            area["area_id"]
            for area in await ha.ws.send_command("config/area_registry/list") or []
        }
        lingering = [r.area_id for r in self.manifest.areas_remove if r.area_id in existing]
        return VerifyResult(
            not lingering,
            "all declared removals absent" if not lingering else f"still present: {lingering}",
        )
