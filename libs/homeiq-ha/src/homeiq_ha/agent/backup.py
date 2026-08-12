"""Backup-subsystem helpers shared by the recipes and the snapshot loop.

Home Assistant creates backups **asynchronously**. ``backup/generate`` starts a
job and returns; ``backup/info`` reports a state machine that rests at ``idle``
when nothing is running. Two things in this package depend on that:

* :class:`~homeiq_ha.agent.recipes.FirstBackupRecipe` must not run ``verify``
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
from typing import TYPE_CHECKING

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
