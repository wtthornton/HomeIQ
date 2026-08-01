"""HA init/setup agent: a declarative, idempotent plan/apply engine.

``audit`` is the default mode and writes nothing — enforced by a read-only
proxy, not by convention. See :mod:`homeiq_ha.agent.readonly`.
"""

from __future__ import annotations

from .engine import (
    BACKUP_PHASE,
    BackupGateNotSatisfied,
    HAInitAgent,
    Mode,
    RecipeOutcome,
    RunReport,
)
from .readonly import ReadOnlyHAClient, ReadOnlyViolation, is_read_command, read_only
from .recipe import (
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

__all__ = [
    "BACKUP_PHASE",
    "ApplyResult",
    "BackupGateNotSatisfied",
    "Change",
    "CheckResult",
    "CheckStatus",
    "HAInitAgent",
    "Mode",
    "Plan",
    "ReadOnlyHAClient",
    "ReadOnlyViolation",
    "Recipe",
    "RecipeOutcome",
    "RunReport",
    "VerifyResult",
    "is_read_command",
    "read_only",
]
