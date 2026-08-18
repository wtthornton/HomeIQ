"""Local Calendar enablement recipe (TAP-5431).

Follows the TeamTracker lesson: the flow schema is read from the live flow
and the resulting entity_id is asserted from the registry, never assumed
from documentation. A surprising flow shape raises loudly instead of being
driven with guessed input. Powercalc lives in :mod:`.powercalc`.

The power/energy alias sensors (``sensor.total_power``/``sensor.daily_energy``)
are deliberately NOT recipes here: helpers are manifest rows created by
:class:`~homeiq_ha.agent.helpers.ManifestHelpersRecipe`, and their template
sources are the Powercalc entity ids that only exist after this module's
recipes have applied live.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAClientError, HAFlowError

from .recipe import (
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
    return {str(field.get("name")) for field in step.get("data_schema") or [] if field.get("name")}


def _require_form(domain: str, step: dict[str, Any], *fields: str) -> None:
    """Assert the step is a form carrying the expected fields, else raise.

    This is the never-guess gate: when the live flow does not look like the
    one we designed against, surface its actual shape instead of submitting
    input that happens to fit nothing.
    """
    step_type = str(step.get("type") or "form")
    if step_type != "form":
        raise HAFlowError(f"{domain} flow: expected a form step, got {step_type!r}", step)
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


__all__ = ["LocalCalendarRecipe"]
