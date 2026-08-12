"""Report-only organization diagnostics (scene governance, mesh health).

Split out of :mod:`.recipes` (the recipe hub) to keep that module cohesive —
these two recipes never write, so they cluster naturally. Re-exported from
``recipes`` so ``default_recipes`` and callers import them unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .recipe import (
    PHASE_ORGANIZATION,
    ApplyResult,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

    from .manifest import OrganizationManifest


class ScenePolicyRecipe(Recipe):
    """Report-only scene governance (TAP-5975).

    Classifies every live ``scene.*`` entity against the manifest's
    ``scene_policy`` rows (keyed by entity-registry platform). Covered scenes
    are governed — ``bridge_owned`` means observed-not-managed, so the audit
    neither regenerates nor drift-flags them. A scene NO rule covers reports
    BLOCKED_ON_HUMAN: a new scene source must get an explicit stance, never
    silent treatment. Never writes.
    """

    name = "organization.scene_policy"
    phase = PHASE_ORGANIZATION
    description = "Every scene entity has a declared governance stance"

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    async def check(self, ha: HAClient) -> CheckResult:
        if not self.manifest.scene_policy:
            return CheckResult(CheckStatus.SATISFIED, "no scene policy declared")
        entities = await ha.ws.send_command("config/entity_registry/list") or []
        scenes = [e for e in entities if e.get("entity_id", "").startswith("scene.")]
        rules = {r.platform: r for r in self.manifest.scene_policy}
        covered: dict[str, int] = {}
        uncovered: list[str] = []
        for scene in scenes:
            rule = rules.get(scene.get("platform") or "")
            if rule is None:
                uncovered.append(scene["entity_id"])
            else:
                covered[rule.platform] = covered.get(rule.platform, 0) + 1
        if uncovered:
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                f"{len(uncovered)} scene(s) have no declared stance",
                {"covered": covered, "uncovered": uncovered[:20]},
                human_action=(
                    "Add a scene_policy row for the platform(s) of: "
                    f"{sorted({u.split('.')[0] for u in uncovered})} — every "
                    "scene source needs an explicit curate-or-ignore stance."
                ),
            )
        summary = ", ".join(
            f"{count} {platform} ({rules[platform].stance})"
            for platform, count in sorted(covered.items())
        )
        return CheckResult(
            CheckStatus.SATISFIED,
            f"all {len(scenes)} scene(s) governed: {summary}" if scenes else "no scenes present",
            {"covered": covered},
        )

    async def plan(self, _ha: HAClient) -> Plan:
        return Plan(())

    async def apply(self, _ha: HAClient) -> ApplyResult:
        return ApplyResult((), "report-only")

    async def verify(self, _ha: HAClient) -> VerifyResult:
        return VerifyResult(True, "report-only")


class ZigbeeMeshHealthRecipe(Recipe):
    """Report-only per-device Zigbee mesh health (LQI + availability, TAP-5982).

    Emits one row per ZHA device (name, ieee, lqi, available, last_seen) into
    the audit so signal degradation is visible before it becomes a silent
    outage — the SLZB coordinator dropped mid-pairing 2026-08-12 and nothing
    reported it. Strictly report-only: never writes, never blocks, never
    alerts (the coordinator watchdog owns alerting). When ZHA is absent or its
    API errors, it degrades to SATISFIED with a note rather than crashing the
    nightly audit.
    """

    name = "zigbee.mesh_health"
    phase = PHASE_ORGANIZATION
    description = "Per-device Zigbee mesh LQI and availability (report-only)"

    #: Below this LQI a device is worth a human's attention (not an alert here).
    WEAK_LQI = 30

    async def check(self, ha: HAClient) -> CheckResult:
        try:
            devices = await ha.ws.send_command("zha/devices")
        except Exception as exc:  # ZHA loaded but the API errored
            return CheckResult(
                CheckStatus.SATISFIED,
                f"mesh health unavailable: {type(exc).__name__}",
                {"error": str(exc)},
            )
        if not devices:
            return CheckResult(CheckStatus.SATISFIED, "no ZHA mesh present")

        rows = [
            {
                "name": d.get("user_given_name") or d.get("name") or d.get("model"),
                "ieee": d.get("ieee"),
                "lqi": d.get("lqi"),
                "available": bool(d.get("available")),
                "last_seen": d.get("last_seen"),
                "is_coordinator": d.get("device_type") == "Coordinator",
            }
            for d in devices
        ]
        rows.sort(key=lambda r: (r["lqi"] is None, r["lqi"] if r["lqi"] is not None else 0))
        unavailable = [r["ieee"] for r in rows if not r["available"]]
        weak = [r["ieee"] for r in rows if isinstance(r["lqi"], int) and r["lqi"] < self.WEAK_LQI]
        lqis = [r["lqi"] for r in rows if isinstance(r["lqi"], int)]
        summary = (
            f"{len(rows)} device(s); {len(unavailable)} unavailable; "
            f"weakest LQI {min(lqis) if lqis else 'n/a'}"
        )
        return CheckResult(
            CheckStatus.SATISFIED,
            summary,
            {
                "device_count": len(rows),
                "unavailable": unavailable,
                "weak_lqi": weak,
                "devices": rows,
            },
        )

    async def plan(self, _ha: HAClient) -> Plan:
        return Plan(())

    async def apply(self, _ha: HAClient) -> ApplyResult:
        return ApplyResult((), "report-only")

    async def verify(self, _ha: HAClient) -> VerifyResult:
        return VerifyResult(True, "report-only")


__all__ = ["ScenePolicyRecipe", "ZigbeeMeshHealthRecipe"]
