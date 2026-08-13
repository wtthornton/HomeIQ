"""Backup-subsystem helpers shared by the recipes and the snapshot loop.

Home Assistant creates backups **asynchronously**. ``backup/generate`` starts a
job and returns; ``backup/info`` reports a state machine that rests at ``idle``
when nothing is running. Two things in this package depend on that:

* :class:`FirstBackupRecipe` must not run ``verify``
  until the job it started has landed, or it declares failure over a backup that
  is merely still being written.
* :func:`~homeiq_ha.agent.snapshot.capture` must not read backup ids while a job
  is running. A backup that lands moments later is invisible to ``diff``,
  survives ``restore``, and leaves residue on an instance the caller was told is
  back at its baseline.

A backup also needs somewhere to go: ``backup/generate`` takes ``agent_ids``,
and an instance offering no agent cannot make one at all.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .recipe import (
    PHASE_SAFETY,
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeiq_ha.client import HAClient

#: ``backup/info`` state meaning no backup job is running.
IDLE = "idle"

#: How long to wait for a backup job. A full backup on a Pi-class host
#: archiving a real database takes minutes, not seconds.
BACKUP_TIMEOUT = 900.0

#: Gap between ``backup/info`` polls while waiting.
POLL_INTERVAL = 3.0


@dataclass(frozen=True)
class BackupStatus:
    """A point-in-time read of the backup subsystem."""

    state: str
    backup_ids: tuple[str, ...]

    @property
    def idle(self) -> bool:
        return self.state == IDLE


class BackupTimeout(RuntimeError):
    """The backup subsystem did not reach the expected state in time."""

    def __init__(self, what: str, timeout: float, last: BackupStatus) -> None:
        super().__init__(
            f"timed out after {timeout:.0f}s waiting for {what} "
            f"(state={last.state!r}, backups={len(last.backup_ids)})"
        )
        self.last = last


async def read_status(ha: HAClient) -> BackupStatus:
    """Read backup state and ids in one call. Read-only.

    ``state`` is absent on cores predating the backup state machine; treating
    that as idle degrades to the old single-read behaviour rather than
    blocking until the timeout.
    """
    info = await ha.ws.send_command("backup/info") or {}
    return BackupStatus(
        state=str(info.get("state") or IDLE),
        backup_ids=tuple(
            str(entry["backup_id"]) for entry in info.get("backups") or [] if entry.get("backup_id")
        ),
    )


async def available_agent_ids(ha: HAClient) -> tuple[str, ...]:
    """Backup destinations this instance can write to. Read-only."""
    result = await ha.ws.send_command("backup/agents/info") or {}
    return tuple(
        str(agent["agent_id"]) for agent in result.get("agents") or [] if agent.get("agent_id")
    )


def backup_taker(ha: HAClient) -> Callable[[str], Awaitable[None]]:
    """A pre-phase backup function for the engine's rule-2 gate.

    Generates a named backup to every available destination and waits for it
    to finish being written — ``backup/generate`` only starts the job.
    """

    async def take_backup(name: str) -> None:
        await ha.ws.send_command(
            "backup/generate",
            fields={
                "name": name,
                "agent_ids": list(await available_agent_ids(ha)),
            },
        )
        await wait_for_backup(ha)

    return take_backup


async def wait_for(
    ha: HAClient,
    predicate: Callable[[BackupStatus], bool],
    *,
    what: str,
    timeout: float = BACKUP_TIMEOUT,
) -> BackupStatus:
    """Poll ``backup/info`` until ``predicate`` holds.

    Raises:
        BackupTimeout: ``predicate`` never held within ``timeout``.
    """
    deadline = time.monotonic() + timeout
    while True:
        status = await read_status(ha)
        if predicate(status):
            return status
        if time.monotonic() >= deadline:
            raise BackupTimeout(what, timeout, status)
        await asyncio.sleep(POLL_INTERVAL)


async def wait_until_idle(ha: HAClient, *, timeout: float = BACKUP_TIMEOUT) -> BackupStatus:
    """Block while a backup job runs. Returns at once when already idle."""
    return await wait_for(
        ha,
        lambda status: status.idle,
        what="the backup subsystem to go idle",
        timeout=timeout,
    )


async def wait_for_backup(ha: HAClient, *, timeout: float = BACKUP_TIMEOUT) -> BackupStatus:
    """Block until a backup exists and no job is still writing one."""
    return await wait_for(
        ha,
        lambda status: status.idle and bool(status.backup_ids),
        what="a backup to finish being written",
        timeout=timeout,
    )


__all__ = [
    "BACKUP_TIMEOUT",
    "IDLE",
    "POLL_INTERVAL",
    "BackupStatus",
    "BackupTimeout",
    "available_agent_ids",
    "backup_taker",
    "read_status",
    "wait_for",
    "wait_for_backup",
    "wait_until_idle",
]


class BackupScheduleRecipe(Recipe):
    """Configure automatic backups.

    This is the gate for everything else. On a factory-fresh instance no
    backups exist at all, and ``automatic_backups_configured`` is false — the
    instance is one SD-card failure from total loss.
    """

    name = "safety.backup_schedule"
    phase = PHASE_SAFETY
    description = "Daily automatic backups with retention and encryption"

    def __init__(
        self,
        *,
        recurrence: str = "daily",
        copies: int = 7,
        agent_ids: tuple[str, ...] = (),
    ) -> None:
        self.recurrence = recurrence
        self.copies = copies
        #: Explicit destinations. Empty means "whatever this instance offers",
        #: resolved at run time from ``backup/agents/info``.
        self.agent_ids = agent_ids

    async def _config(self, ha: Any) -> dict[str, Any]:
        result = await ha.ws.send_command("backup/config/info")
        return dict((result or {}).get("config") or {})

    async def _available(self, ha: Any) -> tuple[str, ...]:
        return self.agent_ids or await available_agent_ids(ha)

    def _target_agent_ids(
        self, config: dict[str, Any], available: tuple[str, ...]
    ) -> tuple[str, ...]:
        """What ``create_backup.agent_ids`` should end up as.

        Explicitly named destinations are enforced. Otherwise an empty list is
        filled from what the instance offers, and a set the owner already chose
        is left alone.
        """
        if self.agent_ids:
            return self.agent_ids
        configured = self._configured_agent_ids(config)
        return configured or available

    @staticmethod
    def _configured_agent_ids(config: dict[str, Any]) -> tuple[str, ...]:
        create = config.get("create_backup") or {}
        return tuple(str(agent) for agent in create.get("agent_ids") or ())

    def _drift(self, config: dict[str, Any], available: tuple[str, ...]) -> list[Change]:
        """Drift this recipe can actually apply.

        The encryption key is deliberately excluded — not because the API
        can't set it (``backup/config/update`` accepts
        ``create_backup.password``; verified live 2026-08-11 on 2026.7.4)
        but because only a person can custody the key: a recipe-invented
        password makes every backup unrecoverable the day the store is lost.
        It is surfaced through :meth:`_needs_encryption_key` instead, and set
        on explicit human instruction only.
        """
        schedule = config.get("schedule") or {}
        retention = config.get("retention") or {}
        configured = self._configured_agent_ids(config)
        target = self._target_agent_ids(config, available)
        changes: list[Change] = []

        if schedule.get("recurrence") != self.recurrence:
            changes.append(
                Change("set", "schedule.recurrence", schedule.get("recurrence"), self.recurrence)
            )
        if retention.get("copies") != self.copies:
            changes.append(Change("set", "retention.copies", retention.get("copies"), self.copies))
        # A schedule with no destination is not a backup. Home Assistant leaves
        # automatic_backups_configured false and never writes anything, so a
        # recipe that skipped this would report success over a home with no
        # backups at all.
        if set(configured) != set(target):
            changes.append(Change("set", "create_backup.agent_ids", list(configured), list(target)))
        return changes

    @staticmethod
    def _needs_encryption_key(config: dict[str, Any]) -> bool:
        # Never read, log or diff the key itself — only whether one is set.
        return not (config.get("create_backup") or {}).get("password")

    async def check(self, ha: HAClient) -> CheckResult:
        config = await self._config(ha)
        available = await self._available(ha)
        drift = self._drift(config, available)
        details = {
            "automatic_backups_configured": config.get("automatic_backups_configured"),
            "drift": [c.describe() for c in drift],
            "encryption_key_set": not self._needs_encryption_key(config),
            "agent_ids": list(self._target_agent_ids(config, available)),
        }

        if not self._target_agent_ids(config, available):
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                "no backup destination is available",
                details,
                human_action=(
                    "Add a backup location in Settings > System > Backups. "
                    "Home Assistant has nowhere to write a backup without one."
                ),
            )
        if drift:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{len(drift)} backup setting(s) need changing",
                details,
            )
        if self._needs_encryption_key(config):
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                "backup schedule is configured but no encryption key is set",
                details,
                human_action=(
                    "Set a backup encryption password in Settings > System > "
                    "Backups and store the emergency kit off this host. "
                    "Without the key the backups are unrecoverable."
                ),
            )
        return CheckResult(CheckStatus.SATISFIED, "automatic backups configured", details)

    async def plan(self, ha: HAClient) -> Plan:
        config = await self._config(ha)
        return Plan(tuple(self._drift(config, await self._available(ha))))

    async def apply(self, ha: HAClient) -> ApplyResult:
        config = await self._config(ha)
        available = await self._available(ha)
        drift = self._drift(config, available)
        if not drift:
            return ApplyResult((), "already configured")

        payload: dict[str, Any] = {
            "schedule": {"recurrence": self.recurrence},
            "retention": {"copies": self.copies, "days": None},
        }
        target = self._target_agent_ids(config, available)
        if target:
            payload["create_backup"] = {"agent_ids": list(target)}
        await ha.ws.send_command("backup/config/update", fields=payload)
        return ApplyResult(tuple(drift), f"applied {len(drift)} backup setting(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        config = await self._config(ha)
        remaining = [c.describe() for c in self._drift(config, await self._available(ha))]
        return VerifyResult(
            not remaining,
            "backup configuration matches intent"
            if not remaining
            else f"still drifted: {remaining}",
            {
                "remaining": remaining,
                "encryption_key_set": not self._needs_encryption_key(config),
                "automatic_backups_configured": config.get("automatic_backups_configured"),
            },
        )


class FirstBackupRecipe(Recipe):
    """Ensure at least one backup exists. An untested backup is a hope."""

    name = "safety.first_backup"
    phase = PHASE_SAFETY
    description = "At least one backup exists"

    def __init__(
        self,
        *,
        agent_ids: tuple[str, ...] = (),
        timeout: float = BACKUP_TIMEOUT,
    ) -> None:
        #: Explicit destinations; empty resolves from ``backup/agents/info``.
        self.agent_ids = agent_ids
        #: How long ``verify`` waits for the backup to finish being written.
        self.timeout = timeout

    async def _backups(self, ha: Any) -> list[dict[str, Any]]:
        result = await ha.ws.send_command("backup/info")
        return list((result or {}).get("backups") or [])

    async def _destinations(self, ha: Any) -> tuple[str, ...]:
        return self.agent_ids or await available_agent_ids(ha)

    async def check(self, ha: HAClient) -> CheckResult:
        backups = await self._backups(ha)
        if backups:
            return CheckResult(
                CheckStatus.SATISFIED, f"{len(backups)} backup(s) exist", {"count": len(backups)}
            )
        destinations = await self._destinations(ha)
        if not destinations:
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                "no backups exist and there is nowhere to write one",
                {"count": 0, "agent_ids": []},
                human_action=(
                    "Add a backup location in Settings > System > Backups. "
                    "backup/generate needs at least one destination agent."
                ),
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            "no backups exist",
            {"count": 0, "agent_ids": list(destinations)},
        )

    async def plan(self, ha: HAClient) -> Plan:
        if await self._backups(ha):
            return Plan()
        destinations = await self._destinations(ha)
        return Plan((Change("create", "full backup", after=list(destinations)),))

    async def apply(self, ha: HAClient) -> ApplyResult:
        if await self._backups(ha):
            return ApplyResult((), "a backup already exists")
        destinations = await self._destinations(ha)
        await ha.ws.send_command(
            "backup/generate",
            fields={"name": "homeiq-initial", "agent_ids": list(destinations)},
        )
        return ApplyResult((Change("create", "full backup"),), "backup requested")

    async def verify(self, ha: HAClient) -> VerifyResult:
        # backup/generate only *starts* the job. Re-reading straight away would
        # see zero backups and fail a run that is merely still writing one.
        try:
            status = await wait_for_backup(ha, timeout=self.timeout)
        except BackupTimeout as exc:
            return VerifyResult(False, str(exc), {"count": len(exc.last.backup_ids)})
        return VerifyResult(
            True,
            f"{len(status.backup_ids)} backup(s) present",
            {"count": len(status.backup_ids)},
        )
