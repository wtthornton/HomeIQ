"""Backup recipes: schedule convergence, first backup, encryption-key gate.

Moved from test_agent_recipes.py (TAP-5921) alongside the recipes' move into
homeiq_ha.agent.backup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.recipes import BackupScheduleRecipe, FirstBackupRecipe

if TYPE_CHECKING:
    from tests.simulators import SimHA


@pytest.mark.asyncio
async def test_backup_schedule_detects_a_never_scheduled_instance(sim):
    result = await BackupScheduleRecipe().check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["automatic_backups_configured"] is False


@pytest.mark.asyncio
async def test_backup_schedule_uses_recurrence_not_state(sim):
    """schedule.state was renamed to schedule.recurrence; writing the old key
    would silently no-op."""
    await BackupScheduleRecipe(recurrence="daily", copies=7).apply(sim)
    assert sim.state["backup_config"]["schedule"]["recurrence"] == "daily"
    assert sim.state["backup_config"]["retention"]["copies"] == 7


@pytest.mark.asyncio
async def test_backup_schedule_is_idempotent(sim):
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    await recipe.apply(sim)
    sim.ws.writes.clear()

    second = await recipe.apply(sim)

    assert second.change_count == 0
    assert sim.writes == []


@pytest.mark.asyncio
async def test_a_missing_encryption_key_is_a_human_gate_not_an_endless_diff(sim):
    """The API can set the key (backup/config/update accepts
    create_backup.password) but only a person may custody it — treating it
    as appliable drift would make the recipe re-apply forever."""
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    await recipe.apply(sim)

    result = await recipe.check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert result.details["encryption_key_set"] is False
    assert "emergency kit" in (result.human_action or "")
    # The appliable half has converged — and verify() says exactly that,
    # scoping its claim and disclosing the missing key (TAP-6027 class).
    verified = await recipe.verify(sim)
    assert verified.ok
    assert "appliable" in verified.summary
    assert "encryption key still needs a person" in verified.summary


@pytest.mark.asyncio
async def test_backup_schedule_satisfied_once_a_key_exists(sim):
    sim.state["backup_config"]["create_backup"]["password"] = "set"
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    await recipe.apply(sim)

    assert (await recipe.check(sim)).status is CheckStatus.SATISFIED


@pytest.mark.asyncio
async def test_backup_schedule_summary_never_contradicts_its_details(sim):
    """TAP-6027: the satisfied summary claimed HA's frontend-only
    automatic_backups_configured flag, which stays false on an
    API-configured instance. The summary must state what was verified,
    never assert that flag."""
    sim.state["backup_config"]["create_backup"]["password"] = "set"
    # HA's frontend-onboarding flag stays false — exactly the live shape.
    sim.state["backup_config"]["automatic_backups_configured"] = False
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    await recipe.apply(sim)

    result = await recipe.check(sim)
    assert result.status is CheckStatus.SATISFIED
    assert result.details["automatic_backups_configured"] is False
    assert "automatic backups configured" not in result.summary
    assert "drift-free" in result.summary and "encryption key" in result.summary


@pytest.mark.asyncio
async def test_first_backup_reports_zero_backups(sim):
    result = await FirstBackupRecipe().check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["count"] == 0


@pytest.mark.asyncio
async def test_first_backup_is_idempotent(sim):
    recipe = FirstBackupRecipe()
    assert (await recipe.apply(sim)).change_count == 1
    # backup/generate only starts the job. verify is what waits for it to land,
    # so idempotency is a property of the apply->verify pair, not of apply.
    assert (await recipe.verify(sim)).ok
    assert (await recipe.apply(sim)).change_count == 0


def _fields_of(sim: SimHA, command_type: str) -> dict[str, Any]:
    """The fields carried by the first call to ``command_type``."""
    return next(args for name, args in sim.ws.calls if name == command_type)


@pytest.mark.asyncio
async def test_first_backup_names_a_destination(sim):
    """backup/generate needs agent_ids: a backup has to be written somewhere.

    Omitting them is rejected outright, so a recipe that left them off could
    never create the backup the whole safety phase is gated on.
    """
    await FirstBackupRecipe().apply(sim)

    assert _fields_of(sim, "backup/generate")["agent_ids"] == ["hassio.local"]


@pytest.mark.asyncio
async def test_first_backup_blocks_when_there_is_nowhere_to_write(sim):
    sim.state["backup_agents"] = []

    result = await FirstBackupRecipe().check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "nowhere to write" in result.summary


@pytest.mark.asyncio
async def test_first_backup_verify_waits_for_the_job_to_land(sim):
    """apply only starts the job; the backup does not exist when it returns.

    A verify that read once would report zero backups and fail a run that was
    merely still writing one.
    """
    await FirstBackupRecipe().apply(sim)
    assert sim.state["backups"] == []
    assert sim.state["pending_backup"] is not None

    result = await FirstBackupRecipe().verify(sim)

    assert result.ok
    assert result.details["count"] == 1


@pytest.mark.asyncio
async def test_first_backup_verify_fails_when_the_job_never_lands(sim):
    sim.state["polls_until_done"] = 10**6
    await FirstBackupRecipe().apply(sim)

    result = await FirstBackupRecipe(timeout=0).verify(sim)

    assert not result.ok
    assert "timed out" in result.summary


@pytest.mark.asyncio
async def test_backup_schedule_configures_a_destination(sim):
    """A schedule with no agent_ids is not a backup.

    Home Assistant leaves automatic_backups_configured false and writes
    nothing, so a recipe that skipped this would report success over a home
    that has no automatic backups at all.
    """
    await BackupScheduleRecipe(recurrence="daily", copies=7).apply(sim)

    config = sim.state["backup_config"]
    assert config["create_backup"]["agent_ids"] == ["hassio.local"]
    # The schedule is only live once it has a destination: confirmed against
    # the real instance, which began reporting next_automatic_backup only
    # after agent_ids was filled.
    assert config["next_automatic_backup"] is not None


@pytest.mark.asyncio
async def test_backup_schedule_leaves_a_chosen_destination_alone(sim):
    """A set the owner picked is theirs; only an empty one gets filled."""
    sim.state["backup_config"]["create_backup"]["agent_ids"] = ["my.nas"]
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)

    await recipe.apply(sim)

    assert sim.state["backup_config"]["create_backup"]["agent_ids"] == ["my.nas"]
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_backup_schedule_blocks_when_no_destination_exists(sim):
    sim.state["backup_agents"] = []

    result = await BackupScheduleRecipe().check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "no backup destination" in result.summary


@pytest.mark.asyncio
async def test_backup_schedule_converges_in_one_apply(sim):
    """The second apply must be a no-op, or live runs never settle."""
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    assert (await recipe.apply(sim)).change_count == 3

    assert (await recipe.apply(sim)).change_count == 0
    assert (await recipe.verify(sim)).ok
