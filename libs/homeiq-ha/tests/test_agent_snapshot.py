"""Tests for capture / diff / restore.

This is the safety net that makes running the agent against a real Home
Assistant re-testable: apply, verify, restore, and assert the instance is back
where it started. If these tests are wrong, every live test result after a
restore is suspect, so they check the round trip rather than the parts.
"""

from __future__ import annotations

import pytest
from homeiq_ha.agent import HAInitAgent
from homeiq_ha.agent.recipes import AreasRecipe, CoreConfigRecipe, LabelsRecipe
from homeiq_ha.agent.snapshot import (
    RestoreIncomplete,
    capture,
    diff,
    restore,
)

from .simulators import SimHA


async def _noop_backup(_label: str) -> None:
    return None


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


# --- capture / diff -------------------------------------------------------


@pytest.mark.asyncio
async def test_capture_is_read_only(sim):
    await capture(sim)
    assert sim.writes == []


@pytest.mark.asyncio
async def test_capture_records_the_fixture_shape(sim):
    snap = await capture(sim)
    assert len(snap.areas) == 3
    assert len(snap.devices) == 21  # 19 WLED + 2 service-type (TAP-6227 fixtures)
    assert len(snap.entities) == 164
    assert snap.labels == {}
    assert snap.core_config["currency"] == "USD"


@pytest.mark.asyncio
async def test_diff_against_self_is_empty(sim):
    """The assertion every restore relies on."""
    baseline = await capture(sim)
    assert await diff(sim, baseline) == []


@pytest.mark.asyncio
async def test_diff_is_read_only(sim):
    baseline = await capture(sim)
    sim.ws.writes.clear()
    await diff(sim, baseline)
    assert sim.writes == []


@pytest.mark.asyncio
async def test_diff_detects_an_added_label(sim):
    baseline = await capture(sim)
    await LabelsRecipe(("critical",)).apply(sim)

    changes = await diff(sim, baseline)

    assert len(changes) == 1
    assert changes[0].action == "added"
    assert "critical" in changes[0].target


@pytest.mark.asyncio
async def test_diff_detects_a_core_config_change(sim):
    baseline = await capture(sim)
    await CoreConfigRecipe(currency="EUR").apply(sim)

    changes = await diff(sim, baseline)

    assert any(c.target == "core_config.currency" for c in changes)


@pytest.mark.asyncio
async def test_snapshot_round_trips_through_json(sim):
    from homeiq_ha.agent.snapshot import Snapshot

    snap = await capture(sim)
    assert Snapshot.from_json(snap.to_json()) == snap


@pytest.mark.asyncio
async def test_snapshot_never_records_the_encryption_key(sim):
    sim.state["backup_config"]["create_backup"]["password"] = "super-secret-key"

    snap = await capture(sim)

    assert "super-secret-key" not in snap.to_json()
    assert snap.backup_config["encryption_key_set"] is True


# --- restore --------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_removes_what_was_created(sim):
    baseline = await capture(sim)
    await LabelsRecipe(("critical", "exterior")).apply(sim)
    await AreasRecipe(("Living Room", "Office", "Garage")).apply(sim)
    assert await diff(sim, baseline) != []

    reverted = await restore(sim, baseline)

    assert len(reverted) == 4  # 2 labels + 2 areas
    assert await diff(sim, baseline) == []


@pytest.mark.asyncio
async def test_restore_puts_core_config_back(sim):
    baseline = await capture(sim)
    await CoreConfigRecipe(currency="EUR").apply(sim)

    await restore(sim, baseline)

    assert sim.state["core_config"]["currency"] == "USD"
    assert await diff(sim, baseline) == []


@pytest.mark.asyncio
async def test_restore_is_idempotent(sim):
    baseline = await capture(sim)
    await LabelsRecipe(("critical",)).apply(sim)
    await restore(sim, baseline)

    second = await restore(sim, baseline)

    assert second == []


@pytest.mark.asyncio
async def test_restore_on_an_unchanged_instance_writes_nothing(sim):
    baseline = await capture(sim)
    sim.ws.writes.clear()

    reverted = await restore(sim, baseline)

    assert reverted == []
    assert sim.writes == []


@pytest.mark.asyncio
async def test_strict_restore_raises_when_something_survives(sim, monkeypatch):
    """A restore that silently half-works poisons every later test run, so the
    default is to fail loudly rather than return a partial success."""
    baseline = await capture(sim)
    await LabelsRecipe(("critical",)).apply(sim)

    # Simulate a delete that Home Assistant refuses.
    original = sim.ws.send_command

    async def refuse_label_delete(command_type, **kwargs):
        if command_type == "config/label_registry/delete":
            return None  # pretend it worked; state is unchanged
        return await original(command_type, **kwargs)

    monkeypatch.setattr(sim.ws, "send_command", refuse_label_delete)

    with pytest.raises(RestoreIncomplete) as excinfo:
        await restore(sim, baseline)
    assert excinfo.value.remaining


@pytest.mark.asyncio
async def test_non_strict_restore_reports_instead_of_raising(sim, monkeypatch):
    baseline = await capture(sim)
    await LabelsRecipe(("critical",)).apply(sim)
    original = sim.ws.send_command

    async def refuse_label_delete(command_type, **kwargs):
        if command_type == "config/label_registry/delete":
            return None
        return await original(command_type, **kwargs)

    monkeypatch.setattr(sim.ws, "send_command", refuse_label_delete)

    reverted = await restore(sim, baseline, strict=False)

    assert reverted  # it tried
    assert await diff(sim, baseline) != []  # and the caller can see it failed


# --- the full test loop ---------------------------------------------------


@pytest.mark.asyncio
async def test_apply_verify_restore_returns_to_baseline(sim):
    """The loop this whole module exists to support."""
    baseline = await capture(sim)
    agent = HAInitAgent(
        [AreasRecipe(("Living Room", "Kitchen", "Bedroom", "Office")), LabelsRecipe(("critical",))]
    )

    report = await agent.apply(sim, phase=3, backup=_noop_backup)
    assert report.total_changes == 2
    assert all(o.verified is None or o.verified.ok for o in report.outcomes)

    await restore(sim, baseline)

    assert await diff(sim, baseline) == [], "instance did not return to baseline"
    # And the agent now sees the same work outstanding as it did the first time.
    rerun = await agent.audit(sim)
    assert rerun.total_changes == 0
    assert sum(1 for o in rerun.outcomes if o.check.needs_apply) == 2


@pytest.mark.asyncio
async def test_restore_leaves_pre_existing_state_alone(sim):
    """Restore must not delete the three areas that were there to begin with."""
    baseline = await capture(sim)
    await AreasRecipe(("Office",)).apply(sim)

    await restore(sim, baseline)

    names = {a["name"] for a in sim.state["areas"]}
    assert names == {"Living Room", "Kitchen", "Bedroom"}


@pytest.mark.asyncio
async def test_restore_deletes_a_backup_it_did_not_start_with(sim):
    from homeiq_ha.agent.recipes import FirstBackupRecipe

    baseline = await capture(sim)
    recipe = FirstBackupRecipe()
    await recipe.apply(sim)
    # The job is still running here; verify is what waits for it to land.
    assert (await recipe.verify(sim)).ok
    assert sim.state["backups"]

    await restore(sim, baseline)

    assert await diff(sim, baseline) == []


@pytest.mark.asyncio
async def test_restore_puts_backup_destinations_back(sim):
    """The schedule recipe writes create_backup.agent_ids, so restore must
    revert it. Tracking only schedule and retention would leave the
    destination behind on an instance reported as back at its baseline."""
    from homeiq_ha.agent.recipes import BackupScheduleRecipe

    baseline = await capture(sim)
    await BackupScheduleRecipe(recurrence="daily", copies=7).apply(sim)
    assert sim.state["backup_config"]["create_backup"]["agent_ids"] == ["hassio.local"]

    await restore(sim, baseline)

    assert sim.state["backup_config"]["create_backup"]["agent_ids"] == []
    assert await diff(sim, baseline) == []


@pytest.mark.asyncio
async def test_diff_tolerates_a_baseline_without_destinations(sim):
    """Baselines captured before destinations were tracked have no agent_ids
    key; treating that as a permanent difference would make restore
    unsatisfiable."""
    baseline = await capture(sim)
    del baseline.backup_config["agent_ids"]

    assert await diff(sim, baseline) == []


@pytest.mark.asyncio
async def test_capture_waits_for_an_in_flight_backup(sim):
    """A backup still being written must not slip past capture.

    Recording ids mid-job would make the backup invisible to diff, so restore
    would not delete it and it would be left behind on an instance the caller
    was told is back at its baseline.
    """
    from homeiq_ha.agent.recipes import FirstBackupRecipe

    baseline = await capture(sim)
    await FirstBackupRecipe().apply(sim)
    assert sim.state["backups"] == []  # the job has not landed yet

    snapshot = await capture(sim)

    assert snapshot.backup_ids == ["b1"]
    assert [c.target for c in await diff(sim, baseline)] == ["backup:b1"]


@pytest.mark.asyncio
async def test_restore_removes_a_backup_that_lands_late(sim):
    """The end-to-end version: a job started but not awaited leaves nothing."""
    from homeiq_ha.agent.recipes import FirstBackupRecipe

    baseline = await capture(sim)
    await FirstBackupRecipe().apply(sim)

    await restore(sim, baseline)

    assert sim.state["backups"] == []
    assert await diff(sim, baseline) == []
