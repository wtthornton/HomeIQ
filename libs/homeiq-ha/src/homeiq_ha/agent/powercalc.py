"""Powercalc-via-HACS recipe (TAP-5431).

Split from :mod:`.enablement` to keep both modules under the
maintainability gate; the recipe follows the same TeamTracker lesson —
schemas read from the live flow, entity_ids asserted from the registry.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAClientError, HAFlowError

from .core_restart import restart_core
from .recipe import (
    PHASE_HACS,
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient


#: Domains whose entities can carry a physical electrical load. A ``switch``
#: only qualifies as an outlet — HA models a smart plug as
#: ``device_class: outlet`` and a configuration toggle as ``switch`` or none,
#: and this home's 65 switches are entirely the latter (Inovelli device
#: parameters, WLED effect toggles, sensor enables). Metering a toggle is not
#: a gap to close; there is no load behind it.
_LOAD_DOMAINS = ("light", "media_player")


class PowercalcRecipe(Recipe):
    """Install Powercalc through HACS and confirm a discovered power sensor.

    Apply stages, each skipped when already true:

    1. Download ``bramstroker/homeassistant-powercalc`` via the HACS
       websocket API (``hacs/repository/download``, repository id read live
       from ``hacs/repositories/list`` — never derived).
    2. Restart HA to load the new custom component — config checked first,
       then polled back to life. The restart happens inside a converge apply,
       which is the gateway's backup-gated path.
    3. Confirm a Powercalc discovery flow (its profile library recognises
       supported lights and opens flows on its own). Forms are advanced
       empty only when they have no required field without a default;
       anything else raises with the live schema.
    4. Assert power sensors cover most of the home's *metering-eligible*
       entities, not merely that one exists.
    """

    name = "hacs.powercalc"
    phase = PHASE_HACS
    description = "Powercalc installed via HACS with a live power sensor"

    REPO_FULL_NAME = "bramstroker/homeassistant-powercalc"

    def __init__(
        self,
        *,
        restart_timeout: float = 240.0,
        restart_poll_interval: float = 5.0,
        restart_min_wait: float = 15.0,
        discovery_timeout: float = 90.0,
        discovery_poll_interval: float = 5.0,
        power_state_timeout: float = 30.0,
        coverage_target: float = 0.8,
    ) -> None:
        self.restart_timeout = restart_timeout
        self.restart_poll_interval = restart_poll_interval
        self.restart_min_wait = restart_min_wait
        self.discovery_timeout = discovery_timeout
        self.discovery_poll_interval = discovery_poll_interval
        self.power_state_timeout = power_state_timeout
        self.coverage_target = coverage_target

    async def _repo(self, ha: Any) -> dict[str, Any] | None:
        repos = await ha.ws.send_command(
            "hacs/repositories/list", fields={"categories": ["integration"]}
        )
        for repo in repos or []:
            if str(repo.get("full_name", "")).lower() == self.REPO_FULL_NAME:
                return dict(repo)
        return None

    async def _loaded_entry(self, ha: Any) -> dict[str, Any] | None:
        entries = await ha.rest.get_config_entries()
        for entry in entries or []:
            if entry.get("domain") == "powercalc" and entry.get("state") == "loaded":
                return dict(entry)
        return None

    async def _power_entities(self, ha: Any) -> list[str]:
        entities = await ha.ws.send_command("config/entity_registry/list")
        return [
            e["entity_id"]
            for e in entities or []
            if e.get("platform") == "powercalc" and str(e.get("entity_id", "")).endswith("_power")
        ]

    async def _reporting(self, ha: Any) -> tuple[list[str], list[str]]:
        """Power sensors that exist, and the subset carrying a number.

        A sensor for an unavailable light exists but reports nothing — it
        satisfies no one (observed live 2026-08-13:
        sensor.bottom_of_stairs_power stuck 'unavailable').
        """
        powered = await self._power_entities(ha)
        states = {s.get("entity_id"): s.get("state") for s in await ha.rest.get_states()}
        return powered, [eid for eid in powered if _is_number(states.get(eid))]

    async def _coverage(self, ha: Any) -> dict[str, Any]:
        """Which metering-eligible loads carry a power reading, and which do not.

        The join from a power sensor to the load it measures is the entity
        registry's ``device_id`` — never the entity_id string. Powercalc names
        its sensor after the source's *friendly name*
        (``light.stairs_bottom_of_stairs`` -> ``sensor.bottom_of_stairs_power``),
        so a string match silently misses; and a name-keyed join would break on
        a rename besides (``.claude/rules/friendly-names.md``).

        Any power sensor counts, not only Powercalc's: an Inovelli VZM31-SN
        reports real metering over ZHA, and a metered load is covered no matter
        which integration provides the number.

        Two exclusions carry a stated reason rather than silently shrinking the
        denominator:

        * **group entities** — a light group's power is the sum of its members,
          so metering the group double-counts every member.
        * **non-outlet switches** — configuration toggles, not loads. HA models
          a smart plug as ``device_class: outlet``.
        """
        registry = await ha.ws.send_command("config/entity_registry/list") or []
        device_of = {
            str(e.get("entity_id")): e.get("device_id") for e in registry if e.get("entity_id")
        }
        states = await ha.rest.get_states() or []

        metered_devices = {
            device_of.get(str(s.get("entity_id")))
            for s in states
            if (s.get("attributes") or {}).get("device_class") == "power"
            and _is_number(s.get("state"))
            and device_of.get(str(s.get("entity_id")))
        }

        eligible: set[str] = set()
        excluded: dict[str, list[str]] = {
            "group_entity_sums_its_members": [],
            "switch_is_a_config_toggle_not_a_load": [],
            "no_device_in_the_entity_registry": [],
        }
        for state in states:
            entity_id = str(state.get("entity_id", ""))
            domain, _, _ = entity_id.partition(".")
            attributes = state.get("attributes") or {}
            if domain in _LOAD_DOMAINS:
                if attributes.get("entity_id"):
                    excluded["group_entity_sums_its_members"].append(entity_id)
                    continue
            elif domain == "switch":
                if attributes.get("device_class") != "outlet":
                    excluded["switch_is_a_config_toggle_not_a_load"].append(entity_id)
                    continue
            else:
                continue
            if not device_of.get(entity_id):
                excluded["no_device_in_the_entity_registry"].append(entity_id)
                continue
            eligible.add(entity_id)

        covered = {eid for eid in eligible if device_of.get(eid) in metered_devices}

        # Why each uncovered load is uncovered. A bare list of 30 entity ids
        # says "something is wrong somewhere"; these say which of them a person
        # could act on, and how. The three causes need different actions and
        # only one of them is a software problem.
        state_of = {str(s.get("entity_id")): str(s.get("state")) for s in states}
        reasons: dict[str, str] = {}
        for entity_id in sorted(eligible - covered):
            state = state_of.get(entity_id, "unknown")
            if state == "unavailable":
                reasons[entity_id] = (
                    "the load itself is unavailable — a sensor cannot read a device "
                    "that is not reachable, so this clears when the device is powered"
                )
            elif entity_id.startswith("media_player."):
                reasons[entity_id] = (
                    "no Powercalc profile for this media player; it needs a manually "
                    "stated wattage, which is a fact about the hardware"
                )
            else:
                reasons[entity_id] = (
                    "Powercalc raised no discovery flow that closes on defaults — "
                    "typically a profile asking for supply voltage, which is a fact "
                    "about the installation rather than the device"
                )

        for entity_ids in excluded.values():
            entity_ids.sort()
        return {
            "eligible": eligible,
            "covered": covered,
            "excluded": excluded,
            "uncovered_reasons": reasons,
        }

    async def check(self, ha: HAClient) -> CheckResult:
        entry = await self._loaded_entry(ha)
        if entry is not None:
            powered, reporting = await self._reporting(ha)
            coverage = await self._coverage(ha)
            eligible, covered = coverage["eligible"], coverage["covered"]
            uncovered = sorted(eligible - covered)
            ratio = len(covered) / len(eligible) if eligible else 0.0
            details = {
                "entity_ids": powered,
                "reporting": reporting,
                "eligible": sorted(eligible),
                "covered": sorted(covered),
                "uncovered": uncovered,
                "uncovered_reasons": coverage["uncovered_reasons"],
                "excluded": coverage["excluded"],
                "coverage_ratio": round(ratio, 3),
                "coverage_target": self.coverage_target,
            }
            if not powered:
                return CheckResult(
                    CheckStatus.NEEDS_APPLY,
                    "Powercalc entry is loaded but provides no power sensor",
                    details,
                )
            if not reporting:
                # A distinct, more actionable diagnosis than a coverage figure:
                # the sensors exist, so the profile matched; they are silent
                # because their source entities are.
                return CheckResult(
                    CheckStatus.NEEDS_APPLY,
                    f"power sensor(s) {powered} exist but none reports a number",
                    details,
                )
            if eligible and ratio >= self.coverage_target:
                return CheckResult(
                    CheckStatus.SATISFIED,
                    f"Powercalc covers {len(covered)}/{len(eligible)} "
                    f"metering-eligible entities ({ratio:.0%})",
                    details,
                )
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"Powercalc covers {len(covered)}/{len(eligible)} "
                f"metering-eligible entities ({ratio:.0%}), below the "
                f"{self.coverage_target:.0%} target; {len(uncovered)} uncovered",
                details,
            )
        repo = await self._repo(ha)
        if repo is None:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                "Powercalc is absent from the HACS repository list",
            )
        if repo.get("installed"):
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                "Powercalc is downloaded but has no loaded config entry",
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            "Powercalc needs a HACS download and an HA restart",
        )

    async def plan(self, ha: HAClient) -> Plan:
        changes: list[Change] = []
        repo = await self._repo(ha)
        if repo is None or not repo.get("installed"):
            changes.append(Change("hacs download", self.REPO_FULL_NAME, after="installed"))
            changes.append(Change("restart", "homeassistant", after="powercalc loadable"))
        if await self._loaded_entry(ha) is None:
            changes.append(Change("configure integration", "powercalc", after="loaded"))
        return Plan(tuple(changes))

    async def apply(self, ha: HAClient) -> ApplyResult:
        changes: list[Change] = []

        repo = await self._repo(ha)
        if repo is None:
            raise HAClientError(
                f"{self.REPO_FULL_NAME} is not in the HACS repository list; "
                "cannot download what HACS does not offer"
            )
        if not repo.get("installed"):
            await ha.ws.send_command(
                "hacs/repository/download",
                timeout=300,
                fields={"repository": str(repo["id"])},
            )
            changes.append(Change("hacs download", self.REPO_FULL_NAME, after="installed"))
            await self._restart(ha)
            changes.append(Change("restart", "homeassistant", after="restarted"))

        _, reporting = await self._reporting(ha)
        if not reporting:
            changes.extend(await self._ensure_power_sensor(ha))

        # One reporting sensor proves the integration works; it does not meter a
        # home. Confirm every remaining discovery flow that closes on defaults,
        # so coverage tracks the loads that can carry a reading rather than
        # stopping at the first success.
        changes.extend(await self._cover_remaining(ha))

        powered, reporting = await self._reporting(ha)
        if not reporting:
            raise HAClientError(
                f"Powercalc applied but no power sensor reports a number "
                f"(existing: {powered}) — refusing to report success"
            )
        return ApplyResult(
            tuple(changes),
            f"Powercalc live with reporting power sensor(s): {reporting}",
        )

    async def _restart(self, ha: Any) -> None:
        """Config-checked restart, polled back to life. Loud on timeout."""
        await restart_core(
            ha,
            timeout=self.restart_timeout,
            poll_interval=self.restart_poll_interval,
            min_wait=self.restart_min_wait,
        )

    async def _ensure_power_sensor(self, ha: Any) -> list[Change]:
        """Get a discovered power sensor, bootstrapping discovery if needed.

        Powercalc only scans for supported devices once its integration is
        set up (verified live 2026-08-13: after download + restart, zero
        discovery flows exist until an entry does). The bootstrap is the
        flow menu's ``global_configuration`` branch — every form in it is
        defaulted, so it can be driven empty without guessing anything.
        """
        changes: list[Change] = []
        flows = await self._powercalc_flows(ha)
        if not flows:
            try:
                await self._create_global_entry(ha)
            except HAFlowError as err:
                if "already_in_progress" not in str(err):
                    raise
                # A previously failed attempt left its user flow open holding
                # the global-config unique_id (observed live 2026-08-13). The
                # flow/progress WS command filters source=="user" flows
                # server-side, so the debris cannot be enumerated and aborted
                # — but in-progress flows do not survive a core restart.
                await self._restart(ha)
                await self._create_global_entry(ha)
            changes.append(
                Change(
                    "configure integration",
                    "powercalc",
                    after="global configuration entry",
                )
            )
            flows = await self._wait_for_discovery(ha)
        changes.append(await self._confirm_any_discovery(ha, flows))
        return changes

    async def _cover_remaining(self, ha: Any) -> list[Change]:
        """Confirm every outstanding discovery flow that closes on defaults.

        Powercalc raises one flow per supported device it finds. Confirming a
        single one leaves the rest sitting in the wizard queue, which is how a
        home ends up 3/43 metered with the integration reporting healthy.

        A flow that asks for something is left alone, deliberately. WLED
        profiles require ``voltage``; that is a fact about the house, not about
        the device, and inventing it here would put a fabricated number behind
        every energy figure derived from it. Those flows stay in the triage
        queue with their reason recorded, which is where a question for a human
        belongs.
        """
        flows = await self._powercalc_flows(ha)
        if not flows:
            return []

        confirmed: list[Change] = []
        blocked: dict[str, str] = {}
        for flow, label in await self._ranked(ha, flows):
            try:
                confirmed.append(await self._confirm_discovery(ha, flow["flow_id"]))
            except HAFlowError as err:
                blocked[label] = str(err)

        if blocked:
            logger.info(
                "powercalc: %d flow(s) need a human fact and were left in triage: %s",
                len(blocked),
                blocked,
            )
        return confirmed

    async def _confirm_any_discovery(self, ha: Any, flows: list[dict[str, Any]]) -> Change:
        """Confirm discovery flows until one yields a live power number.

        Observed live 2026-08-13: WLED profiles require ``voltage`` while
        Hue LUT profiles confirm on defaults alone — and a confirmed sensor
        for an *unavailable* light reports no number, so flows whose source
        light is currently available rank first and confirmation continues
        until a sensor actually reports. Flows that block stay in the
        wizard triage queue where they belong.
        """
        blocked: dict[str, str] = {}
        for flow, label in await self._ranked(ha, flows):
            try:
                change = await self._confirm_discovery(ha, flow["flow_id"])
            except HAFlowError as err:
                blocked[label] = str(err)
                continue
            if await self._power_reports_a_number(ha):
                return change
            blocked[label] = "confirmed but its sensor reports no number"
        raise HAClientError(
            "no powercalc discovery flow produced a reporting power sensor "
            f"without human facts: {blocked}"
        )

    async def _ranked(
        self, ha: Any, flows: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], str]]:
        """Pair each flow with its device label, available lights first.

        The discovery title is ``"<light name> - <manufacturer>"``; the
        light half matches the light entity's friendly_name.
        """
        live_names = {
            (state.get("attributes") or {}).get("friendly_name")
            for state in await ha.rest.get_states()
            if str(state.get("entity_id", "")).startswith("light.")
            and state.get("state") not in ("unavailable", "unknown")
        }
        labelled = []
        for flow in flows:
            title = (flow.get("context") or {}).get("title_placeholders") or {}
            label = str(title.get("name") or flow["flow_id"])
            alive = label.rsplit(" - ", 1)[0].strip() in live_names
            labelled.append((not alive, flow, label))
        labelled.sort(key=lambda item: item[0])
        return [(flow, label) for _, flow, label in labelled]

    async def _power_reports_a_number(self, ha: Any) -> bool:
        """Poll until any powercalc power sensor carries a numeric state."""
        deadline = asyncio.get_running_loop().time() + self.power_state_timeout
        while True:
            _, reporting = await self._reporting(ha)
            if reporting:
                return True
            if asyncio.get_running_loop().time() > deadline:
                return False
            await asyncio.sleep(self.discovery_poll_interval)

    async def _powercalc_flows(self, ha: Any) -> list[dict[str, Any]]:
        # Only discovery-source flows arrive here: HA's flow/progress WS
        # handler hides user-source flows server-side.
        flows = await ha.ws.send_command("config_entries/flow/progress")
        return [f for f in flows or [] if f.get("handler") == "powercalc"]

    async def _create_global_entry(self, ha: Any) -> None:
        """Drive the user flow's global_configuration branch, defaults only."""
        step = await ha.rest.start_config_flow("powercalc")
        step_type = ha.rest.classify_flow_step(step)
        if step_type != "menu":
            raise HAFlowError(
                f"powercalc flow opened with {step_type!r}, expected a menu",
                step,
            )
        # menu_options serializes as a list of ids or an {id: label} dict;
        # list() yields the ids either way.
        option_ids = list(step.get("menu_options") or [])
        if "global_configuration" not in option_ids:
            raise HAFlowError(
                "powercalc menu lacks 'global_configuration' (already "
                f"configured?); live options: {option_ids}",
                step,
            )
        try:
            next_step = await ha.rest.advance_config_flow(
                step["flow_id"], {"next_step_id": "global_configuration"}
            )
            await self._drive_defaults(ha, step["flow_id"], next_step, "global configuration")
        except HAFlowError:
            # Leave nothing behind: an open flow holds the global-config
            # unique_id and aborts every later attempt already_in_progress.
            with contextlib.suppress(HAClientError, OSError):
                await ha.rest.abort_config_flow(step["flow_id"])
            raise

    async def _wait_for_discovery(self, ha: Any) -> list[dict[str, Any]]:
        deadline = asyncio.get_running_loop().time() + self.discovery_timeout
        while True:
            flows = await self._powercalc_flows(ha)
            if flows:
                return flows
            if asyncio.get_running_loop().time() > deadline:
                raise HAClientError(
                    "powercalc discovery produced no flow within "
                    f"{self.discovery_timeout}s of setup — no light matched "
                    "its profile library; a manual virtual_power flow needs "
                    "its schema read live first, refusing to guess one"
                )
            await asyncio.sleep(self.discovery_poll_interval)

    async def _confirm_discovery(self, ha: Any, flow_id: str) -> Change:
        """Advance one Powercalc discovery flow through its confirm forms."""
        step = await ha.rest.get_config_flow(flow_id)
        await self._drive_defaults(ha, flow_id, step, "discovery")
        return Change("configure integration", "powercalc", after="loaded")

    async def _drive_defaults(
        self, ha: Any, flow_id: str, step: dict[str, Any], label: str
    ) -> dict[str, Any]:
        """Advance defaulted forms until create_entry, guessing nothing.

        Refuses (loudly, with the live schema) any form carrying a required
        field without a default — that is a fact a person must supply.
        The global-configuration chain is 5 forms on the live instance.
        """
        for _ in range(8):
            step_type = ha.rest.classify_flow_step(step)
            if step_type == "create_entry":
                return step
            if step_type != "form":
                reason = step.get("reason")
                raise HAFlowError(
                    f"powercalc {label} flow hit a {step_type!r} step"
                    + (f" (reason: {reason})" if reason else ""),
                    step,
                )
            step = await ha.rest.advance_config_flow(
                flow_id, self._defaults_only_input(label, step)
            )
        raise HAFlowError(f"powercalc {label} flow did not complete within 8 steps", step)

    @staticmethod
    def _defaults_only_input(label: str, step: dict[str, Any]) -> dict[str, Any]:
        """Build a form submission that guesses nothing.

        Section containers (``vol.Section``, serialized with a nested
        ``schema`` list — powercalc's power_options/features/advanced) are
        submitted as ``{}`` so voluptuous fills their nested defaults; they
        group options, they are not facts. A required non-section field
        without a default is a blocker and raises.
        """
        payload: dict[str, Any] = {}
        blockers: list[str] = []
        for field in step.get("data_schema") or []:
            name = str(field.get("name"))
            nested = field.get("schema")
            if isinstance(nested, list):
                blockers.extend(
                    f"{name}.{sub.get('name')}"
                    for sub in nested
                    if sub.get("required") and "default" not in sub
                )
                payload[name] = {}
            elif field.get("required") and "default" not in field:
                blockers.append(name)
        if blockers:
            raise HAFlowError(
                f"powercalc {label} form requires input the agent must not guess: {blockers}",
                step,
            )
        return payload

    async def verify(self, ha: HAClient) -> VerifyResult:
        entry = await self._loaded_entry(ha)
        if entry is None:
            return VerifyResult(False, "no loaded Powercalc config entry")
        powered, reporting = await self._reporting(ha)
        if not powered:
            return VerifyResult(False, "Powercalc loaded but no power sensor")
        return VerifyResult(
            bool(reporting),
            f"power sensor(s) reporting a numeric state: {reporting}"
            if reporting
            else f"power sensor(s) {powered} exist but none reports a number",
            {"entity_ids": powered, "reporting": reporting},
        )


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


__all__ = ["PowercalcRecipe"]
