"""Core-integration recipes: ensure a domain has a loaded config entry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAHumanGateRequired

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


class IntegrationRecipe(Recipe):
    """Ensure a core integration has a loaded config entry.

    ``needs_user_input`` marks integrations whose config flow requires
    personal or site facts (which sports team, which weather station) that
    the agent must never guess: their check reports ``BLOCKED_ON_HUMAN``
    with that action, and apply raises the human gate rather than driving
    the flow with placeholder input (verified live: an empty step makes the
    flow error, it does not configure anything).
    """

    phase = PHASE_INTEGRATIONS

    def __init__(
        self,
        domain: str,
        *,
        title: str | None = None,
        steps: tuple[dict[str, Any], ...] = ({},),
        needs_user_input: str | None = None,
    ) -> None:
        self.domain = domain
        self.title = title or domain
        self.steps = steps
        self.needs_user_input = needs_user_input
        self.name = f"integrations.{domain}"
        self.description = f"{self.title} integration configured"

    async def _entries(self, ha: Any) -> list[dict[str, Any]]:
        entries = await ha.rest.get_config_entries()
        return [e for e in entries or [] if e.get("domain") == self.domain]

    async def check(self, ha: HAClient) -> CheckResult:
        entries = await self._entries(ha)
        if any(entry.get("state") == "loaded" for entry in entries):
            return CheckResult(CheckStatus.SATISFIED, f"{self.title} is loaded")
        if entries:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{self.title} entry exists but is {entries[0].get('state')}",
            )
        if self.needs_user_input:
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                f"{self.title} is not configured",
                human_action=self.needs_user_input,
            )
        return CheckResult(CheckStatus.NEEDS_APPLY, f"{self.title} is not configured")

    async def plan(self, ha: HAClient) -> Plan:
        if await self._entries(ha):
            return Plan()
        return Plan((Change("configure integration", self.domain, after="loaded"),))

    async def apply(self, ha: HAClient) -> ApplyResult:
        if await self._entries(ha):
            return ApplyResult((), f"{self.title} already has a config entry")
        if self.needs_user_input:
            raise HAHumanGateRequired(
                f"{self.title} config flow needs a person: {self.needs_user_input}",
                {"type": "integration_user_input", "domain": self.domain},
            )
        await ha.rest.run_config_flow(self.domain, list(self.steps))
        return ApplyResult(
            (Change("configure integration", self.domain, after="loaded"),),
            f"{self.title} configured",
        )

    async def verify(self, ha: HAClient) -> VerifyResult:
        entries = await self._entries(ha)
        loaded = [e for e in entries if e.get("state") == "loaded"]
        return VerifyResult(bool(loaded), f"{self.title}: {len(loaded)} loaded entry/entries")


__all__ = ["IntegrationRecipe"]
