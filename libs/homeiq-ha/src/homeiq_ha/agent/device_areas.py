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
    """Converge device→area assignments to the committed manifest.

    The report-only :class:`DevicesHaveAreasRecipe` stays for devices the
    manifest does not cover — this recipe only ever touches devices the
    AF author placed with evidence and a judge reviewed.

    A manifest ``device_id`` missing from the live registry is deletion
    drift: reported in details and skipped, never a crash (stable ids only
    protect against renames, not removals).
    """

    name = "organization.device_area_assignments"
    phase = PHASE_ORGANIZATION
    description = "Manifest-assigned devices are in their areas"

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    async def _state(self, ha: Any) -> tuple[list[Change], list[str]]:
        devices = await ha.ws.send_command("config/device_registry/list")
        by_id = {device["id"]: device for device in devices or []}
        drift: list[Change] = []
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
                f"{len(drift)} device(s) not in their manifest area",
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
        drift, _ = await self._state(ha)
        applied: list[Change] = []
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
        return ApplyResult(tuple(applied), f"assigned {len(applied)} device(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        drift, stale = await self._state(ha)
        return VerifyResult(
            not drift,
            "device areas match the manifest"
            if not drift
            else f"still drifted: {[c.describe() for c in drift]}",
            {"stale_device_ids": stale},
        )


__all__ = ["ManifestDeviceAreasRecipe"]
