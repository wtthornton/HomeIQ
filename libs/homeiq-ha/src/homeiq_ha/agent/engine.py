"""The HA init/setup agent engine.

Runs recipes in one of four modes. ``audit`` is the default and is the only one
that should run unattended: it executes every ``check()`` behind a read-only
proxy that makes a write impossible rather than merely discouraged.

Safety rules, from docs/ha-init-agent-design.md §4.3, are enforced here rather
than left to individual recipes:

1. Phase 1 (backup) must succeed before any other phase applies. A setup agent
   that mutates an unbacked-up instance is a liability.
2. A backup is taken immediately before each subsequent phase, so every phase
   is individually revertible.
3. ``verify()`` re-reads state independently — a config-write POST returns once
   the change is written, which is before the reload has landed.
4. Human gates are hard stops, not timeouts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from homeiq_ha.client.errors import HAHumanGateRequired

from .readonly import read_only
from .recipe import (
    ApplyResult,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from homeiq_ha.client import HAClient

logger = logging.getLogger(__name__)

#: The backup gate. Nothing in a later phase applies until this one has passed.
BACKUP_PHASE = 1


class Mode(str, Enum):
    AUDIT = "audit"
    PLAN = "plan"
    APPLY = "apply"


@dataclass
class RecipeOutcome:
    """What happened to one recipe during a run."""

    name: str
    phase: int
    check: CheckResult
    plan: Plan | None = None
    applied: ApplyResult | None = None
    verified: VerifyResult | None = None
    error: str | None = None

    @property
    def change_count(self) -> int:
        return self.applied.change_count if self.applied else 0

    @property
    def ok(self) -> bool:
        if self.error is not None:
            return False
        if self.verified is not None:
            return self.verified.ok
        return True


@dataclass
class RunReport:
    """The result of one engine run."""

    mode: Mode
    outcomes: list[RecipeOutcome] = field(default_factory=list)
    halted_reason: str | None = None
    reads: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return sum(outcome.change_count for outcome in self.outcomes)

    @property
    def wrote_nothing(self) -> bool:
        return self.total_changes == 0

    def by_status(self, status: CheckStatus) -> list[RecipeOutcome]:
        return [o for o in self.outcomes if o.check.status is status]

    def describe(self) -> str:
        lines = [f"mode: {self.mode.value}"]
        for outcome in sorted(self.outcomes, key=lambda o: (o.phase, o.name)):
            marker = "ok " if outcome.ok else "ERR"
            lines.append(
                f"  [{marker}] phase {outcome.phase} {outcome.name}: "
                f"{outcome.check.status.value} — {outcome.check.summary}"
            )
            if outcome.error:
                lines.append(f"          error: {outcome.error}")
        if self.halted_reason:
            lines.append(f"halted: {self.halted_reason}")
        lines.append(f"changes applied: {self.total_changes}")
        return "\n".join(lines)


class HAInitAgent:
    """Runs a set of recipes against one Home Assistant instance."""

    def __init__(self, recipes: Sequence[Recipe]) -> None:
        self._recipes = sorted(recipes, key=lambda r: (r.phase, r.name))

    @property
    def recipes(self) -> tuple[Recipe, ...]:
        return tuple(self._recipes)

    def _selected(self, phase: int | None, only: str | None) -> list[Recipe]:
        recipes = self._recipes
        if phase is not None:
            recipes = [r for r in recipes if r.phase == phase]
        if only is not None:
            recipes = [r for r in recipes if r.name == only]
        return list(recipes)

    # -- audit -------------------------------------------------------------

    async def audit(self, ha: HAClient, *, only: str | None = None) -> RunReport:
        """Run every ``check()`` behind a read-only proxy.

        Returns a status for every recipe. A run in which every recipe reports
        ``NEEDS_APPLY`` is a correct, passing result on a fresh instance — the
        home is genuinely unconfigured. It is not a failure.
        """
        guarded = read_only(ha)
        report = RunReport(mode=Mode.AUDIT)

        for recipe in self._selected(None, only):
            outcome = await self._check_one(recipe, guarded)
            report.outcomes.append(outcome)

        report.reads = list(guarded.journal)
        return report

    async def _check_one(self, recipe: Recipe, ha: object) -> RecipeOutcome:
        try:
            result = await recipe.check(ha)  # type: ignore[arg-type]
        except HAHumanGateRequired as gate:
            result = CheckResult(
                status=CheckStatus.BLOCKED_ON_HUMAN,
                summary=str(gate),
                details={"placeholders": gate.placeholders, "url": gate.external_url},
                human_action=str(gate),
            )
        except Exception as exc:  # a broken check must not abort the audit
            logger.exception("check failed for recipe %s", recipe.name)
            return RecipeOutcome(
                name=recipe.name,
                phase=recipe.phase,
                check=CheckResult(
                    status=CheckStatus.NOT_APPLICABLE,
                    summary=f"check raised: {exc}",
                ),
                error=str(exc),
            )
        return RecipeOutcome(name=recipe.name, phase=recipe.phase, check=result)

    # -- plan --------------------------------------------------------------

    async def plan(
        self, ha: HAClient, *, phase: int | None = None, only: str | None = None
    ) -> RunReport:
        """Show the diff ``apply`` would produce. Also runs read-only."""
        guarded = read_only(ha)
        report = RunReport(mode=Mode.PLAN)

        for recipe in self._selected(phase, only):
            outcome = await self._check_one(recipe, guarded)
            if outcome.check.needs_apply and outcome.error is None:
                try:
                    outcome.plan = await recipe.plan(guarded)  # type: ignore[arg-type]
                except Exception as exc:
                    logger.exception("plan failed for recipe %s", recipe.name)
                    outcome.error = str(exc)
            report.outcomes.append(outcome)

        report.reads = list(guarded.journal)
        return report

    # -- apply -------------------------------------------------------------

    async def apply(
        self,
        ha: HAClient,
        *,
        phase: int | None = None,
        only: str | None = None,
        backup: BackupTaker | None = None,
    ) -> RunReport:
        """Apply recipes, verifying each one independently.

        Args:
            phase: Restrict to a single phase. ``None`` runs every phase in
                order.
            only: Restrict to a single recipe by name.
            backup: Takes a backup before each phase. Required for any phase
                past the backup gate — refusing to run without one is the
                point of rule 1, not an inconvenience to work around.

        Raises:
            BackupGateNotSatisfied: a phase past :data:`BACKUP_PHASE` was
                requested without a means of taking a backup.
        """
        report = RunReport(mode=Mode.APPLY)
        selected = self._selected(phase, only)
        phases = sorted({recipe.phase for recipe in selected})

        if any(p > BACKUP_PHASE for p in phases) and backup is None:
            raise BackupGateNotSatisfied(
                "Refusing to apply a phase past the backup gate without a way "
                "to take a backup. Run phase 1 first, or pass backup=."
            )

        for current_phase in phases:
            if current_phase > BACKUP_PHASE and backup is not None:
                # Rule 2: a backup immediately before each subsequent phase, so
                # the phase about to run is individually revertible.
                try:
                    await backup(f"pre-phase-{current_phase}")
                except Exception as exc:
                    report.halted_reason = (
                        f"pre-phase-{current_phase} backup failed: {exc}"
                    )
                    return report

            for recipe in (r for r in selected if r.phase == current_phase):
                outcome = await self._apply_one(recipe, ha)
                report.outcomes.append(outcome)

                if outcome.check.status is CheckStatus.BLOCKED_ON_HUMAN:
                    # Rule 5: human gates are hard stops, not timeouts.
                    report.halted_reason = (
                        f"{recipe.name} needs a person: "
                        f"{outcome.check.human_action or outcome.check.summary}"
                    )
                    return report

                if not outcome.ok:
                    report.halted_reason = f"{recipe.name} failed: {outcome.error}"
                    return report

            if current_phase == BACKUP_PHASE and not all(
                o.ok for o in report.outcomes if o.phase == BACKUP_PHASE
            ):
                # Rule 1: nothing past the gate runs on an unbacked-up instance.
                report.halted_reason = "backup phase did not pass; halting"
                return report

        return report

    async def _apply_one(self, recipe: Recipe, ha: HAClient) -> RecipeOutcome:
        outcome = await self._check_one(recipe, read_only(ha))
        if outcome.error is not None:
            return outcome
        if outcome.check.status is not CheckStatus.NEEDS_APPLY:
            # Already satisfied, not applicable, or blocked — nothing to do.
            return outcome

        try:
            outcome.applied = await recipe.apply(ha)
            # Rule 3: re-read rather than trusting apply's return value.
            outcome.verified = await recipe.verify(ha)
            if not outcome.verified.ok:
                outcome.error = outcome.verified.summary
        except HAHumanGateRequired as gate:
            outcome.check = CheckResult(
                status=CheckStatus.BLOCKED_ON_HUMAN,
                summary=str(gate),
                details={"placeholders": gate.placeholders, "url": gate.external_url},
                human_action=str(gate),
            )
        except Exception as exc:
            logger.exception("apply failed for recipe %s", recipe.name)
            outcome.error = str(exc)
        return outcome


class BackupGateNotSatisfied(RuntimeError):
    """Raised when a phase past the backup gate is requested unprotected."""


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    BackupTaker = Callable[[str], Awaitable[object]]
else:  # pragma: no cover - runtime alias only
    BackupTaker = object
