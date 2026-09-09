"""Unit tests for the pure diff computation between two Snapshots.

Every function in :mod:`homeiq_ha.agent.snapshot_diff` takes two already-
captured :class:`~homeiq_ha.agent.snapshot.Snapshot` objects and does no I/O,
so these tests build the snapshots directly rather than going through the
simulator (see test_agent_snapshot.py for the capture/diff/restore
end-to-end behavior against a live-shaped fake).
"""

from __future__ import annotations

from homeiq_ha.agent.snapshot import Snapshot
from homeiq_ha.agent.snapshot_diff import (
    agent_ids,
    compute_diff,
    diff_backup_config,
    diff_backups,
    diff_config_entries,
    diff_core_config,
    diff_field_drift,
    diff_registries,
)

# --- agent_ids ----------------------------------------------------------------


def test_agent_ids_normalises_a_missing_key_to_empty():
    assert agent_ids({}) == []


def test_agent_ids_stringifies_every_entry():
    assert agent_ids({"agent_ids": ["hassio.local", 1]}) == ["hassio.local", "1"]


# --- diff_registries ------------------------------------------------------------


def test_diff_registries_reports_an_added_area():
    baseline = Snapshot()
    current = Snapshot(areas={"a1": {"name": "Office"}})

    changes = diff_registries(baseline, current)

    assert len(changes) == 1
    assert changes[0].action == "added"
    assert changes[0].target == "areas:Office"


def test_diff_registries_reports_a_removed_floor():
    baseline = Snapshot(floors={"f1": {"name": "Main Floor"}})
    current = Snapshot()

    changes = diff_registries(baseline, current)

    assert len(changes) == 1
    assert changes[0].action == "removed"
    assert changes[0].target == "floors:Main Floor"


def test_diff_registries_empty_when_unchanged():
    baseline = Snapshot(labels={"l1": {"name": "critical"}})
    current = Snapshot(labels={"l1": {"name": "critical"}})

    assert diff_registries(baseline, current) == []


# --- diff_field_drift -----------------------------------------------------------


def test_diff_field_drift_reports_a_changed_device_field():
    baseline = Snapshot(devices={"d1": {"area_id": "office", "name_by_user": None}})
    current = Snapshot(devices={"d1": {"area_id": "kitchen", "name_by_user": None}})

    changes = diff_field_drift(baseline, current)

    assert len(changes) == 1
    assert changes[0].target == "devices:d1.area_id"
    assert changes[0].before == "office"
    assert changes[0].after == "kitchen"


def test_diff_field_drift_ignores_a_device_present_only_on_one_side():
    baseline = Snapshot(devices={"d1": {"area_id": "office"}})
    current = Snapshot(devices={"d2": {"area_id": "kitchen"}})

    assert diff_field_drift(baseline, current) == []


# --- diff_config_entries ---------------------------------------------------------


def test_diff_config_entries_reports_added_and_removed():
    baseline = Snapshot(config_entries={"e1": "hacs"})
    current = Snapshot(config_entries={"e2": "powercalc"})

    changes = diff_config_entries(baseline, current)

    actions = {(c.action, c.target) for c in changes}
    assert ("added", "config_entry:powercalc") in actions
    assert ("removed", "config_entry:hacs") in actions


# --- diff_core_config -------------------------------------------------------------


def test_diff_core_config_reports_only_changed_fields():
    baseline = Snapshot(core_config={"currency": "EUR", "country": "US"})
    current = Snapshot(core_config={"currency": "USD", "country": "US"})

    changes = diff_core_config(baseline, current)

    assert len(changes) == 1
    assert changes[0].target == "core_config.currency"
    assert changes[0].before == "EUR"
    assert changes[0].after == "USD"


# --- diff_backup_config -----------------------------------------------------------


def test_diff_backup_config_reports_a_changed_schedule():
    baseline = Snapshot(backup_config={"schedule": "never"})
    current = Snapshot(backup_config={"schedule": "daily"})

    changes = diff_backup_config(baseline, current)

    assert any(c.target == "backup_config.schedule" for c in changes)


def test_diff_backup_config_reports_changed_agent_ids():
    baseline = Snapshot(backup_config={"agent_ids": []})
    current = Snapshot(backup_config={"agent_ids": ["hassio.local"]})

    changes = diff_backup_config(baseline, current)

    assert any(c.target == "backup_config.agent_ids" for c in changes)


def test_diff_backup_config_empty_when_unchanged():
    config = {"schedule": "daily", "retention": 3, "agent_ids": ["hassio.local"]}
    baseline = Snapshot(backup_config=dict(config))
    current = Snapshot(backup_config=dict(config))

    assert diff_backup_config(baseline, current) == []


# --- diff_backups -----------------------------------------------------------------


def test_diff_backups_reports_a_new_backup_id():
    baseline = Snapshot(backup_ids=["b1"])
    current = Snapshot(backup_ids=["b1", "b2"])

    changes = diff_backups(baseline, current)

    assert len(changes) == 1
    assert changes[0].target == "backup:b2"


# --- compute_diff (orchestration) --------------------------------------------------


def test_compute_diff_is_empty_for_identical_snapshots():
    baseline = Snapshot(areas={"a1": {"name": "Office"}}, core_config={"currency": "USD"})
    current = Snapshot(areas={"a1": {"name": "Office"}}, core_config={"currency": "USD"})

    assert compute_diff(baseline, current) == []


def test_compute_diff_aggregates_every_section():
    baseline = Snapshot()
    current = Snapshot(
        areas={"a1": {"name": "Office"}},
        core_config={"currency": "USD"},
        backup_ids=["b1"],
    )

    changes = compute_diff(baseline, current)
    targets = {c.target for c in changes}

    assert "areas:Office" in targets
    assert "core_config.currency" in targets
    assert "backup:b1" in targets
