"""The simulator harness itself: read/write classification and HA quirks.

The whole suite leans on ``sim.writes == []`` to prove recipes are
read-only, so the harness's own classification is load-bearing and gets
pinned here (TAP-5921 panel finding: the harness moved without tests).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.simulators import SimHA


@pytest.mark.asyncio
async def test_reads_are_never_recorded_as_writes(sim: SimHA):
    await sim.ws.send_command("get_config")
    await sim.ws.send_command("backup/info")
    await sim.ws.send_command("config/area_registry/list")
    await sim.ws.send_command("zha/devices")
    await sim.rest.get_config_entries()
    assert sim.writes == []


@pytest.mark.asyncio
async def test_writes_are_recorded(sim: SimHA):
    await sim.ws.send_command("config/area_registry/create", name="Den")
    await sim.rest.request("DELETE", "/api/config/config_entries/entry/x1")
    assert sim.ws.writes == ["config/area_registry/create"]
    assert sim.rest.writes == ["DELETE /api/config/config_entries/entry/x1"]


@pytest.mark.asyncio
async def test_registry_create_mints_slug_ids_like_ha(sim: SimHA):
    created = await sim.ws.send_command("config/area_registry/create", name="Guest Room!")
    assert created == {"area_id": "guest_room", "name": "Guest Room!"}
    areas = await sim.ws.send_command("config/area_registry/list")
    assert any(a["area_id"] == "guest_room" for a in areas)


@pytest.mark.asyncio
async def test_backup_job_lands_only_after_polling(sim: SimHA):
    """Mirrors HA: backup/generate returns a job handle; the backup appears
    in backup/info only after the job finishes, partway through a poll loop."""
    sim.state["backup_agents"] = [{"agent_id": "backup.local"}]
    await sim.ws.send_command(
        "backup/generate", fields={"name": "b", "agent_ids": ["backup.local"]}
    )
    first = await sim.ws.send_command("backup/info")
    assert first["backups"] == []
    second = await sim.ws.send_command("backup/info")
    assert len(second["backups"]) == 1
