"""Helper creation from the manifest, driven through HA config flows."""

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


class ManifestHelpersRecipe(Recipe):
    """Create manifest-declared helpers via their config flows, keyed by slug.

    A helper exists when ``<domain>.<slug>`` is in the entity registry — the
    slug is the manifest's stable identity for it, so a display rename in the
    HA UI does not cause a duplicate on the next converge.

    Flow shapes captured live during the office presence run: ``group`` and
    ``template`` open with a menu selecting the member type; the following
    form takes ``name`` plus the manifest's ``config`` fields.
    """

    name = "helpers.manifest"
    phase = PHASE_ORGANIZATION
    description = "Manifest-declared helpers exist"

    #: Handlers whose flows open with a type-selection menu.
    _MENU_FIRST = frozenset({"group", "template"})

    #: Handlers whose created entity lands in a different domain than the
    #: flow handler (a utility_meter entry creates sensor.<slug>, so keying
    #: existence on utility_meter.<slug> would re-create it every converge).
    _CREATED_DOMAIN = {"utility_meter": "sensor"}

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    @staticmethod
    def _menu_choice(helper: Any) -> str:
        """Which menu branch a menu-first flow takes.

        Prefer an explicit ``menu`` config key; fall back to ``type`` for
        backward compatibility. The distinction matters for sensor groups,
        whose FORM also has a ``type`` field (the aggregation function) —
        with only ``type`` available, declaring a mean-aggregated sensor
        group was impossible (TAP-5976).
        """
        return str(helper.config.get("menu") or helper.config.get("type") or "")

    @staticmethod
    def _domain(helper: Any) -> str:
        # A group of binary_sensors creates binary_sensor.<slug>; a template
        # sensor creates sensor.<slug>, etc.
        if helper.kind in ManifestHelpersRecipe._MENU_FIRST:
            return ManifestHelpersRecipe._menu_choice(helper) or helper.kind
        return ManifestHelpersRecipe._CREATED_DOMAIN.get(helper.kind, helper.kind)

    async def _missing(self, ha: Any) -> list[Any]:
        entities = await ha.ws.send_command("config/entity_registry/list")
        existing = {e["entity_id"] for e in entities or []}
        return [
            helper
            for helper in self.manifest.helpers
            if f"{self._domain(helper)}.{helper.slug}" not in existing
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        missing = await self._missing(ha)
        if not missing:
            return CheckResult(
                CheckStatus.SATISFIED,
                f"all {len(self.manifest.helpers)} manifest helper(s) exist",
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            f"{len(missing)} helper(s) missing",
            {"missing": [h.slug for h in missing]},
        )

    async def plan(self, ha: HAClient) -> Plan:
        return Plan(
            tuple(
                Change("create", f"helper:{helper.kind}.{helper.slug}", after=helper.name)
                for helper in await self._missing(ha)
            )
        )

    async def apply(self, ha: HAClient) -> ApplyResult:
        created: list[Change] = []
        for helper in await self._missing(ha):
            steps: list[dict[str, Any]] = []
            form = {"name": helper.name}
            if helper.kind in self._MENU_FIRST and "menu" in helper.config:
                # Explicit menu key: everything else (including "type", e.g.
                # a sensor group's aggregation function) belongs to the form.
                form.update({k: v for k, v in helper.config.items() if k != "menu"})
                steps.append({"next_step_id": self._menu_choice(helper)})
            else:
                form.update({k: v for k, v in helper.config.items() if k != "type"})
                if helper.kind in self._MENU_FIRST:
                    steps.append({"next_step_id": self._menu_choice(helper)})
            steps.append(form)
            await ha.rest.run_config_flow(helper.kind, steps)
            created.append(
                Change("create", f"helper:{helper.kind}.{helper.slug}", after=helper.name)
            )
        return ApplyResult(tuple(created), f"created {len(created)} helper(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        missing = await self._missing(ha)
        return VerifyResult(
            not missing,
            "all manifest helpers exist"
            if not missing
            else f"still missing: {[h.slug for h in missing]}",
        )


__all__ = ["ManifestHelpersRecipe"]
