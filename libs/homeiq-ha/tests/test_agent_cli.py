"""CLI wiring tests for ``python -m homeiq_ha.agent``.

The engine's backup gate is only useful if the CLI actually passes a backup
taker — the gap that made ``apply --phase 3`` impossible before activation.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent.__main__ import _parser
from homeiq_ha.agent.backup import backup_taker


def test_parser_defaults_to_audit_with_no_manifest_override():
    args = _parser().parse_args([])

    assert args.mode == "audit"
    assert args.manifest is None
    assert args.phase is None


def test_parser_accepts_apply_with_phase_and_manifest():
    args = _parser().parse_args(
        ["apply", "--phase", "3", "--manifest", "config/ha-organization-manifest.yaml"]
    )

    assert args.mode == "apply"
    assert args.phase == 3
    assert args.manifest == "config/ha-organization-manifest.yaml"


class _BackupWs:
    def __init__(self) -> None:
        self.generated: list[dict[str, Any]] = []
        self._polls = 0

    async def send_command(
        self, command_type: str, *, fields: dict[str, Any] | None = None, **_kw: Any
    ) -> Any:
        if command_type == "backup/agents/info":
            return {"agents": [{"agent_id": "hassio.local"}]}
        if command_type == "backup/generate":
            self.generated.append(dict(fields or {}))
            return {"backup_job_id": "job1"}
        if command_type == "backup/info":
            # First poll: still writing; second: landed.
            self._polls += 1
            backups = [{"backup_id": "b1"}] if self._polls > 1 else []
            return {"backups": backups, "state": "idle" if backups else "create_backup"}
        raise AssertionError(f"unexpected command {command_type}")


class _BackupHA:
    def __init__(self) -> None:
        self.ws = _BackupWs()


@pytest.mark.asyncio
async def test_backup_taker_generates_and_waits_for_the_backup():
    ha = _BackupHA()

    await backup_taker(ha)("pre-phase-3")

    assert ha.ws.generated == [{"name": "pre-phase-3", "agent_ids": ["hassio.local"]}]
    assert ha.ws._polls >= 2, "taker must wait for the backup to land, not just start it"
