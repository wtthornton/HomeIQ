"""Registry-names recipes: floors, areas, labels exist; devices have areas.

Split out of the recipes hub (TAP-5921). These converge simple name sets in
one HA registry each — no manifest involvement (the manifest-driven recipes
live in :mod:`.organization`). ``DevicesHaveAreasRecipe`` is report-only by
design: which room a device is in is a human fact, never guessed.
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


class _RegistryNamesRecipe(Recipe):
    """Ensure a named set exists in one registry. Idempotent by name."""

    registry: str = ""

    def __init__(self, wanted: tuple[str, ...]) -> None:
        self.wanted = wanted

    async def _existing(self, ha: Any) -> set[str]:
        entries = await ha.ws.send_command(f"config/{self.registry}/list")
        return {entry["name"] for entry in entries or []}

    async def _missing(self, ha: Any) -> list[str]:
        existing = await self._existing(ha)
        return [name for name in self.wanted if name not in existing]

    async def check(self, ha: HAClient) -> CheckResult:
        missing = await self._missing(ha)
        if not missing:
            return CheckResult(CheckStatus.SATISFIED, f"all {len(self.wanted)} present")
        return CheckResult(CheckStatus.NEEDS_APPLY, f"{len(missing)} missing", {"missing": missing})

    async def plan(self, ha: HAClient) -> Plan:
        return Plan(
            tuple(
                Change("create", f"{self.registry}:{name}", after=name)
                for name in await self._missing(ha)
            )
        )

    async def apply(self, ha: HAClient) -> ApplyResult:
        created: list[Change] = []
        for name in await self._missing(ha):
            await ha.ws.send_command(f"config/{self.registry}/create", name=name)
            created.append(Change("create", f"{self.registry}:{name}", after=name))
        return ApplyResult(tuple(created), f"created {len(created)}")

    async def verify(self, ha: HAClient) -> VerifyResult:
        missing = await self._missing(ha)
        return VerifyResult(
            not missing,
            "all present" if not missing else f"still missing {missing}",
        )


class FloorsRecipe(_RegistryNamesRecipe):
    name = "organization.floors"
    phase = PHASE_ORGANIZATION
    description = "Floors exist"
    registry = "floor_registry"


class AreasRecipe(_RegistryNamesRecipe):
    """Areas are load-bearing, not cosmetic: 2026.7 graduated area-targeted
    triggers and conditions, so automations target areas and adapt as devices
    change."""

    name = "organization.areas"
    phase = PHASE_ORGANIZATION
    description = "Areas exist"
    registry = "area_registry"


class LabelsRecipe(_RegistryNamesRecipe):
    name = "organization.labels"
    phase = PHASE_ORGANIZATION
    description = "Labels exist"
    registry = "label_registry"


class DevicesHaveAreasRecipe(Recipe):
    """Report devices with no area.

    Assignment is intentionally not automated: guessing which room a device is
    in from its name is exactly the kind of plausible-but-wrong change that is
    expensive to unpick later. The recipe surfaces the list and stops.
    """

    name = "organization.device_areas"
    phase = PHASE_ORGANIZATION
    description = "Every device is assigned to an area"

    async def _unassigned(self, ha: Any) -> list[str]:
        devices = await ha.ws.send_command("config/device_registry/list")
        return [
            device.get("name_by_user") or device.get("name") or device["id"]
            for device in devices or []
            if not device.get("area_id") and not device.get("disabled_by")
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        unassigned = await self._unassigned(ha)
        if not unassigned:
            return CheckResult(CheckStatus.SATISFIED, "every device has an area")
        return CheckResult(
            CheckStatus.BLOCKED_ON_HUMAN,
            f"{len(unassigned)} device(s) have no area",
            {"unassigned": unassigned},
            human_action=(
                "Assign an area to each listed device. Which room a device is "
                "in cannot be inferred safely from its name."
            ),
        )

    async def plan(self, _ha: HAClient) -> Plan:
        return Plan()

    async def apply(self, _ha: HAClient) -> ApplyResult:
        return ApplyResult((), "device-to-area assignment is a human decision")

    async def verify(self, ha: HAClient) -> VerifyResult:
        unassigned = await self._unassigned(ha)
        return VerifyResult(not unassigned, f"{len(unassigned)} device(s) still unassigned")
