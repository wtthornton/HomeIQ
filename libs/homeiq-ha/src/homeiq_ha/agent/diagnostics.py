"""Report-only organization diagnostics (scene governance, mesh health, watchdog).

Split out of :mod:`.recipes` (the recipe hub) to keep that module cohesive —
these recipes never write, so they cluster naturally. Re-exported from
``recipes`` so ``default_recipes`` and callers import them unchanged.
"""

from __future__ import annotations

import asyncio
import contextlib
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
    """Per-device Zigbee mesh health (LQI + availability, TAP-5982).

    Emits one row per ZHA device (name, ieee, lqi, available, last_seen) into
    the audit so signal degradation is visible before it becomes a silent
    outage — the SLZB coordinator dropped mid-pairing 2026-08-12 and nothing
    reported it.

    Originally strictly report-only, which turned out to reproduce the very
    failure it was written for: an Aqara FP1E went unreachable 2026-08-12 and
    six consecutive nightly audits rendered it as ``SATISFIED`` — "6 device(s);
    1 unavailable" printed in green. An unreachable device now degrades the
    check to ``BLOCKED_ON_HUMAN``, because restoring one means going to the
    hardware: mains, batteries, or a wake button. LQI stays informational —
    weak links are worth seeing but do not yet imply an action.

    Availability is ZHA's own verdict rather than a threshold invented here.
    ZHA marks a device unavailable only after ``consider_unavailable_mains``
    (2 h) or ``consider_unavailable_battery`` (6 h) of silence, so anything
    still flagged at audit time has been quiet for hours, not seconds. This
    also avoids parsing ``last_seen``, which ZHA reports as a naive local
    timestamp that a UTC container would misread by the whole offset.

    Never writes. When ZHA is absent or its API errors, it degrades to
    SATISFIED with a note rather than crashing the nightly audit. Field names
    in the ``zha/devices`` payload
    (``user_given_name``/``lqi``/``last_seen``/``device_type``) are as of
    HA 2026.8.1, verified live 2026-08-12.
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
        # The coordinator is excluded: it has no availability of its own, and
        # its health is the coordinator watchdog's job, not this check's.
        offline = [r for r in rows if not r["available"] and not r["is_coordinator"]]
        unavailable = [r["ieee"] for r in offline]
        weak = [r["ieee"] for r in rows if isinstance(r["lqi"], int) and r["lqi"] < self.WEAK_LQI]
        lqis = [r["lqi"] for r in rows if isinstance(r["lqi"], int)]
        summary = (
            f"{len(rows)} device(s); {len(unavailable)} unavailable; "
            f"weakest LQI {min(lqis) if lqis else 'n/a'}"
        )
        details = {
            "device_count": len(rows),
            "unavailable": unavailable,
            "weak_lqi": weak,
            "devices": rows,
        }
        if offline:
            names = ", ".join(
                f"{r['name']} ({r['ieee']}, last seen {r['last_seen']})" for r in offline
            )
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                summary,
                details,
                human_action=(
                    f"{len(offline)} Zigbee device(s) unreachable: {names}. "
                    "Check mains or batteries first — a device off the mesh for "
                    "hours has usually lost power rather than lost signal. If it "
                    "is powered, press its button once to wake the radio so it "
                    "can rejoin."
                ),
            )
        return CheckResult(CheckStatus.SATISFIED, summary, details)

    async def plan(self, _ha: HAClient) -> Plan:
        return Plan(())

    async def apply(self, _ha: HAClient) -> ApplyResult:
        return ApplyResult((), "report-only")

    async def verify(self, _ha: HAClient) -> VerifyResult:
        return VerifyResult(True, "report-only")


class ZigbeeCoordinatorWatchdogRecipe(Recipe):
    """Coordinator watchdog: stuck ZHA or unreachable SLZB becomes an alert (TAP-5983).

    On 2026-08-12 the SLZB coordinator dropped off the network mid-pairing and
    both the ``zha`` and ``smlight`` config entries sat in ``setup_retry``
    silently — a human had to notice pairing had stalled. This recipe turns
    both failure modes into a ``BLOCKED_ON_HUMAN`` audit row (the engine's
    alert channel: it names a ``human_action`` and renders as a blocked
    outcome row in every mode; a converge additionally records it in the
    report's ``blocked_on_human`` list and halts the phases behind it —
    an audit surfaces it in ``outcomes[]`` only):

    1. any watched config entry stuck in a retry/error state, and
    2. the coordinator's TCP socket not accepting connections.

    The probe connects and immediately closes without sending a byte — the
    SLZB-06 series (deployed unit: SLZB-06p7) accepts up to 5 concurrent TCP
    clients on the Zigbee socket and only concurrent *data* corrupts the
    stream (SMLIGHT manual, "Zigbee2MQTT / ZHA settings"; verified live
    2026-08-13 on HA 2026.8.1: probe accepted while ZHA held its session,
    mesh unaffected). It is a raw socket read outside the HA API, so the
    audit's read-only proxy does not see it; it is inherently read-only.
    When no zha entry exists at all there is nothing to watch (that is
    :class:`~.zha.ZHARecipe`'s finding), so the recipe reports
    ``NOT_APPLICABLE`` without probing.
    """

    name = "zigbee.coordinator_watchdog"
    phase = PHASE_ORGANIZATION
    description = "ZHA config entry loaded and Zigbee coordinator reachable"

    #: The only entry states that do NOT alert: healthy, or transiently
    #: starting up. Everything else — setup_retry, setup_error,
    #: migration_error, failed_unload, and also not_loaded (a disabled or
    #: unloaded entry means every Zigbee device is dead) — is alert-worthy,
    #: including states future HA versions may add. (HA 2026.8.1 state names.)
    HEALTHY_STATES = frozenset({"loaded", "setup_in_progress"})
    #: Domains whose entries watch this coordinator (zha + the SLZB's own
    #: smlight integration — both sat in setup_retry during the outage).
    WATCHED_DOMAINS = frozenset({"zha", "smlight"})

    def __init__(self, serial_path: str, *, probe_timeout: float = 5.0) -> None:
        self.serial_path = serial_path
        self.probe_timeout = probe_timeout

    async def check(self, ha: HAClient) -> CheckResult:
        entries = await ha.rest.get_config_entries() or []
        watched = [
            {
                "domain": e.get("domain"),
                "entry_id": e.get("entry_id"),
                "state": e.get("state"),
            }
            for e in entries
            if e.get("domain") in self.WATCHED_DOMAINS
        ]
        if not any(e["domain"] == "zha" for e in watched):
            return CheckResult(
                CheckStatus.NOT_APPLICABLE,
                "no zha config entry; nothing to watch",
                {"entries": watched},
            )

        stuck = [e for e in watched if e["state"] not in self.HEALTHY_STATES]
        reachable, probe_detail = await self._probe_coordinator()
        details = {
            "entries": watched,
            "coordinator": {
                "target": self.serial_path,
                "reachable": reachable,
                "detail": probe_detail,
            },
        }

        problems = []
        if stuck:
            problems.append(
                "config entries stuck: " + ", ".join(f"{e['domain']}={e['state']}" for e in stuck)
            )
        if reachable is False:
            problems.append(f"coordinator {self.serial_path} unreachable ({probe_detail})")
        if problems:
            if reachable is False:
                human_action = (
                    f"Power-cycle the Zigbee coordinator at {self.serial_path} "
                    "(the 2026-08-12 outage recovered after a 30s power-cycle), "
                    "then reload any stuck zha/smlight config entries."
                )
            else:
                human_action = (
                    "The coordinator socket answers, so the radio link is up — "
                    "reload the stuck config entries from Settings → Devices & "
                    "Services (re-enable them first if deliberately disabled; "
                    "restart Home Assistant if reload loops)."
                )
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                "ZIGBEE ALERT: " + "; ".join(problems),
                details,
                human_action=human_action,
            )

        states = ", ".join(f"{e['domain']}={e['state']}" for e in watched)
        return CheckResult(CheckStatus.SATISFIED, f"{states}; {probe_detail}", details)

    async def _probe_coordinator(self) -> tuple[bool | None, str]:
        """TCP-connect to a ``socket://host:port`` coordinator, sending nothing.

        Returns ``(None, reason)`` when the path is not a network coordinator
        (serial devices can't be probed from here) — never a false alert.
        """
        if not self.serial_path.startswith("socket://"):
            return None, f"{self.serial_path!r} is not network-attached; probe skipped"
        host, _, port_text = self.serial_path.removeprefix("socket://").partition(":")
        try:
            port = int(port_text)
        except ValueError:
            return None, f"unparseable coordinator port in {self.serial_path!r}; probe skipped"
        try:
            _reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), self.probe_timeout
            )
        except (OSError, TimeoutError) as exc:
            return False, f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        writer.close()
        with contextlib.suppress(OSError):
            await writer.wait_closed()
        return True, f"coordinator tcp connect ok in <{self.probe_timeout}s"

    async def plan(self, _ha: HAClient) -> Plan:
        return Plan(())

    async def apply(self, _ha: HAClient) -> ApplyResult:
        return ApplyResult((), "report-only")

    async def verify(self, _ha: HAClient) -> VerifyResult:
        return VerifyResult(True, "report-only")


__all__ = ["ScenePolicyRecipe", "ZigbeeCoordinatorWatchdogRecipe", "ZigbeeMeshHealthRecipe"]
