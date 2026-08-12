"""Device-registry convergence: manifest device→area assignments."""

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
