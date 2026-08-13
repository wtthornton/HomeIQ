"""Powercalc-via-HACS recipe (TAP-5431).

Split from :mod:`.enablement` to keep both modules under the
maintainability gate; the recipe follows the same TeamTracker lesson —
schemas read from the live flow, entity_ids asserted from the registry.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

import aiohttp

from homeiq_ha.client.errors import HAClientError, HAFlowError

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

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient


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
    4. Assert at least one ``platform == "powercalc"`` power sensor exists.
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
    ) -> None:
        self.restart_timeout = restart_timeout
        self.restart_poll_interval = restart_poll_interval
        self.restart_min_wait = restart_min_wait
        self.discovery_timeout = discovery_timeout
        self.discovery_poll_interval = discovery_poll_interval

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
            if e.get("platform") == "powercalc"
            and str(e.get("entity_id", "")).endswith("_power")
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        entry = await self._loaded_entry(ha)
        if entry is not None:
            powered = await self._power_entities(ha)
            if powered:
                return CheckResult(
                    CheckStatus.SATISFIED,
                    f"Powercalc loaded with {len(powered)} power sensor(s)",
                    {"entity_ids": powered},
                )
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                "Powercalc entry is loaded but provides no power sensor",
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

        if not await self._power_entities(ha):
            changes.extend(await self._ensure_power_sensor(ha))

        powered = await self._power_entities(ha)
        if not powered:
            raise HAClientError(
                "Powercalc applied but no powercalc-platform *_power sensor "
                "exists in the entity registry — refusing to report success"
            )
        return ApplyResult(
            tuple(changes),
            f"Powercalc live with power sensor(s): {powered}",
        )

    async def _restart(self, ha: Any) -> None:
        """Config-checked restart, polled back to life. Loud on timeout."""
        check = await ha.rest.check_config()
        if (check or {}).get("result") != "valid":
            raise HAClientError(
                f"refusing to restart: config check returned {check!r}"
            )
        # HA drops the connection as it shuts down (observed live 2026-08-13:
        # aiohttp.ServerDisconnectedError, which is a ClientError — neither
        # an OSError nor HAClientError, rest.request does not wrap transport
        # errors). The poll below is the real verification.
        with contextlib.suppress(HAClientError, OSError, aiohttp.ClientError):
            await ha.rest.call_service("homeassistant", "restart")
        # Let the shutdown actually begin: polling immediately would see the
        # OLD instance still RUNNING and report success before it exits.
        await asyncio.sleep(self.restart_min_wait)
        deadline = asyncio.get_running_loop().time() + self.restart_timeout
        while True:
            try:
                config = await ha.rest.request("GET", "/api/config")
                if (config or {}).get("state") == "RUNNING":
                    break
            except (HAClientError, OSError, aiohttp.ClientError):
                pass  # still rebooting; the deadline below bounds the wait
            if asyncio.get_running_loop().time() > deadline:
                raise HAClientError(
                    f"HA did not reach state RUNNING within "
                    f"{self.restart_timeout}s of the restart"
                )
            await asyncio.sleep(self.restart_poll_interval)
        # The restart killed the WebSocket; reconnect it for the discovery
        # reads that follow (the client has no auto-reconnect here).
        await ha.ws.close()
        await ha.ws.connect()

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
        changes.append(await self._confirm_discovery(ha, flows[0]["flow_id"]))
        return changes

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
            await self._drive_defaults(
                ha, step["flow_id"], next_step, "global configuration"
            )
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
        raise HAFlowError(
            f"powercalc {label} flow did not complete within 8 steps", step
        )

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
                f"powercalc {label} form requires input the agent must "
                f"not guess: {blockers}",
                step,
            )
        return payload

    async def verify(self, ha: HAClient) -> VerifyResult:
        entry = await self._loaded_entry(ha)
        if entry is None:
            return VerifyResult(False, "no loaded Powercalc config entry")
        powered = await self._power_entities(ha)
        if not powered:
            return VerifyResult(False, "Powercalc loaded but no power sensor")
        states = {s.get("entity_id"): s.get("state") for s in await ha.rest.get_states()}
        reporting = [
            eid
            for eid in powered
            if _is_number(states.get(eid))
        ]
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
