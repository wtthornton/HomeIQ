"""Enablement recipes: Local Calendar and Powercalc-via-HACS (TAP-5431).

Both follow the TeamTracker lesson: every schema is read from the live flow
and every resulting entity_id is asserted from the registry, never assumed
from documentation. A surprising flow shape raises loudly instead of being
driven with guessed input.

The power/energy alias sensors (``sensor.total_power``/``sensor.daily_energy``)
are deliberately NOT recipes here: helpers are manifest rows created by
:class:`~homeiq_ha.agent.helpers.ManifestHelpersRecipe`, and their template
sources are the Powercalc entity ids that only exist after this module's
recipes have applied live.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAClientError, HAFlowError

from .recipe import (
    PHASE_HACS,
    PHASE_INTEGRATIONS,
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


def _schema_fields(step: dict[str, Any]) -> set[str]:
    """Field names in a serialized flow step's ``data_schema``."""
    return {
        str(field.get("name"))
        for field in step.get("data_schema") or []
        if field.get("name")
    }


def _require_form(domain: str, step: dict[str, Any], *fields: str) -> None:
    """Assert the step is a form carrying the expected fields, else raise.

    This is the never-guess gate: when the live flow does not look like the
    one we designed against, surface its actual shape instead of submitting
    input that happens to fit nothing.
    """
    step_type = str(step.get("type") or "form")
    if step_type != "form":
        raise HAFlowError(
            f"{domain} flow: expected a form step, got {step_type!r}", step
        )
    present = _schema_fields(step)
    missing = [f for f in fields if f not in present]
    if missing:
        raise HAFlowError(
            f"{domain} flow form lacks expected field(s) {missing}; "
            f"live schema has {sorted(present)}",
            step,
        )


class LocalCalendarRecipe(Recipe):
    """Create a Local Calendar entry and assert the calendar entity it makes.

    The flow schema (read live, cross-checked against HA core
    ``local_calendar/config_flow.py``): required ``calendar_name`` plus an
    optional ``import`` selector defaulting to ``create_empty``. Only
    ``calendar_name`` is submitted; the default covers the rest.
    """

    name = "integrations.local_calendar"
    phase = PHASE_INTEGRATIONS
    description = "Local Calendar configured with a live-asserted entity"

    def __init__(self, calendar_name: str = "HomeIQ") -> None:
        self.calendar_name = calendar_name

    async def _calendar_entities(self, ha: Any) -> list[str]:
        entities = await ha.ws.send_command("config/entity_registry/list")
        return [
            e["entity_id"]
            for e in entities or []
            if e.get("platform") == "local_calendar"
            and str(e.get("entity_id", "")).startswith("calendar.")
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        existing = await self._calendar_entities(ha)
        if existing:
            return CheckResult(
                CheckStatus.SATISFIED,
                f"Local Calendar provides {len(existing)} calendar entity/entities",
                {"entity_ids": existing},
            )
        return CheckResult(CheckStatus.NEEDS_APPLY, "no Local Calendar entity exists")

    async def plan(self, ha: HAClient) -> Plan:
        if await self._calendar_entities(ha):
            return Plan()
        return Plan((Change("create calendar", self.calendar_name, after="calendar.*"),))

    async def apply(self, ha: HAClient) -> ApplyResult:
        before = set(await self._calendar_entities(ha))
        if before:
            return ApplyResult((), "Local Calendar already present")

        step = await ha.rest.start_config_flow("local_calendar")
        _require_form("local_calendar", step, "calendar_name")
        result = await ha.rest.advance_config_flow(
            step["flow_id"], {"calendar_name": self.calendar_name}
        )
        result_type = ha.rest.classify_flow_step(result)
        if result_type != "create_entry":
            raise HAFlowError(
                f"local_calendar flow ended on {result_type!r}, not create_entry",
                result,
            )

        created = [e for e in await self._calendar_entities(ha) if e not in before]
        if not created:
            raise HAClientError(
                "local_calendar flow completed but no calendar.* entity appeared "
                "in the entity registry — refusing to report success"
            )
        return ApplyResult(
            (Change("create calendar", self.calendar_name, after=created[0]),),
            f"Local Calendar created as {created[0]}",
        )

    async def verify(self, ha: HAClient) -> VerifyResult:
        existing = await self._calendar_entities(ha)
        return VerifyResult(
            bool(existing),
            f"calendar entities: {existing}" if existing else "no calendar entity",
            {"entity_ids": existing},
        )


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
    ) -> None:
        self.restart_timeout = restart_timeout
        self.restart_poll_interval = restart_poll_interval

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

        if await self._loaded_entry(ha) is None:
            changes.append(await self._confirm_discovery(ha))

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
        await ha.rest.call_service("homeassistant", "restart")
        deadline = asyncio.get_running_loop().time() + self.restart_timeout
        while True:
            await asyncio.sleep(self.restart_poll_interval)
            try:
                await ha.rest.request("GET", "/api/")
                return
            except (HAClientError, OSError):
                if asyncio.get_running_loop().time() > deadline:
                    raise HAClientError(
                        f"HA did not answer /api/ within {self.restart_timeout}s "
                        "of the restart"
                    ) from None

    async def _confirm_discovery(self, ha: Any) -> Change:
        """Advance one Powercalc discovery flow through its confirm forms."""
        flows = await ha.ws.send_command("config_entries/flow/progress")
        pc_flows = [f for f in flows or [] if f.get("handler") == "powercalc"]
        if not pc_flows:
            raise HAClientError(
                "no Powercalc discovery flow is in progress after install; "
                "a manual virtual_power flow needs its schema read live first "
                "— refusing to guess one"
            )
        flow_id = pc_flows[0]["flow_id"]
        step = await ha.rest.get_config_flow(flow_id)
        for _ in range(5):
            step_type = ha.rest.classify_flow_step(step)
            if step_type == "create_entry":
                return Change(
                    "configure integration", "powercalc", after="loaded"
                )
            if step_type != "form":
                raise HAFlowError(
                    f"powercalc discovery flow hit a {step_type!r} step", step
                )
            blockers = [
                str(field.get("name"))
                for field in step.get("data_schema") or []
                if field.get("required") and "default" not in field
            ]
            if blockers:
                raise HAFlowError(
                    "powercalc discovery form requires input the agent must "
                    f"not guess: {blockers}",
                    step,
                )
            step = await ha.rest.advance_config_flow(flow_id, {})
        raise HAFlowError(
            "powercalc discovery flow did not complete within 5 steps", step
        )

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


__all__ = ["LocalCalendarRecipe", "PowercalcRecipe"]
