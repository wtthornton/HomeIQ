"""Recipe contract for the HA init/setup agent.

A recipe is one unit of setup work. The engine is declarative and idempotent —
Terraform-shaped, not wizard-shaped — because setup must be safely re-runnable.
The previous wizard model (in-memory sessions, step numbers, no rollback) could
not be re-run without either duplicating work or lying about it.

Every recipe implements four methods with strict contracts:

===========  ==============================================================
``check``    Read-only. Returns a :class:`CheckResult`. **Must not write.**
``plan``     Returns the human-readable diff ``apply`` would produce. No writes.
``apply``    Performs the change. Must be safe to re-run.
``verify``   Independently re-reads state to confirm the change landed.
===========  ==============================================================

``verify`` re-reads rather than trusting ``apply``'s return value on purpose:
Home Assistant's config-write POSTs return ``200 {"result": "ok"}`` once the
change is *written*, which is before the reload has landed.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient


class CheckStatus(str, Enum):
    """Outcome of a recipe's read-only check."""

    SATISFIED = "satisfied"
    NEEDS_APPLY = "needs_apply"
    BLOCKED_ON_HUMAN = "blocked_on_human"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class CheckResult:
    """What a recipe found when it read the current state.

    Attributes:
        status: The classification.
        summary: One line a human can read.
        details: Structured evidence backing the classification.
        human_action: What a person must do, when ``BLOCKED_ON_HUMAN``.
    """

    status: CheckStatus
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    human_action: str | None = None

    @property
    def needs_apply(self) -> bool:
        return self.status is CheckStatus.NEEDS_APPLY


@dataclass(frozen=True)
class Change:
    """One concrete mutation a recipe intends to make."""

    action: str
    target: str
    before: Any = None
    after: Any = None

    def describe(self) -> str:
        if self.before is None:
            return f"{self.action} {self.target} -> {self.after!r}"
        return f"{self.action} {self.target}: {self.before!r} -> {self.after!r}"


@dataclass(frozen=True)
class Plan:
    """The diff a recipe would apply. Empty means already converged."""

    changes: tuple[Change, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.changes

    def describe(self) -> str:
        if self.is_empty:
            return "no changes"
        return "\n".join(f"  - {change.describe()}" for change in self.changes)


@dataclass(frozen=True)
class ApplyResult:
    """What a recipe actually did."""

    changed: tuple[Change, ...] = ()
    summary: str = ""

    @property
    def change_count(self) -> int:
        return len(self.changed)


@dataclass(frozen=True)
class VerifyResult:
    """Whether an independent re-read agrees the change landed."""

    ok: bool
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


class Recipe(abc.ABC):
    """Base class for one unit of setup work.

    Subclasses set :attr:`name` and :attr:`phase` and implement the four
    methods. :attr:`phase` orders execution — phase 1 is the backup gate and
    must succeed before any later phase runs.
    """

    #: Stable identifier, used in reports and to select a single recipe.
    name: str = ""
    #: Execution phase. See docs/ha-init-agent-design.md §7.
    phase: int = 0
    #: One-line description for the audit report.
    description: str = ""
    #: True when applying this recipe needs a person mid-flow.
    requires_human: bool = False

    @abc.abstractmethod
    async def check(self, ha: HAClient) -> CheckResult:
        """Read current state and classify it. Must issue no writes."""

    @abc.abstractmethod
    async def plan(self, ha: HAClient) -> Plan:
        """Return the diff `apply` would produce. Must issue no writes."""

    @abc.abstractmethod
    async def apply(self, ha: HAClient) -> ApplyResult:
        """Make the change. Must be safe to run twice."""

    @abc.abstractmethod
    async def verify(self, ha: HAClient) -> VerifyResult:
        """Independently re-read state to confirm the change landed."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} phase={self.phase}>"
