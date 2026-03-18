"""
Tests for automation internal endpoints and automation analytics endpoints.

Covers:
- POST /internal/automations/bulk_upsert (no auth)
- POST /internal/automations/executions/bulk_upsert (no auth)
- GET /api/v1/automations (with auth, anonymous allowed in tests)
- GET /api/v1/automations/stats/overview
- GET /api/v1/automations/stats/errors
- GET /api/v1/automations/stats/slow
- GET /api/v1/automations/stats/inactive
- GET /api/v1/automations/{automation_id}
- GET /api/v1/automations/{automation_id}/executions
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_automation(
    automation_id: str = "automation.test_one",
    alias: str = "Test One",
    enabled: bool = True,
    **overrides,
) -> dict:
    data = {
        "automation_id": automation_id,
        "alias": alias,
        "enabled": enabled,
        "description": "A test automation",
        "mode": "single",
    }
    data.update(overrides)
    return data


def _make_execution(
    automation_id: str = "automation.test_one",
    run_id: str = "run-001",
    result: str = "finished_successfully",
    duration: float = 1.5,
    **overrides,
) -> dict:
    now = datetime.now(UTC)
    data = {
        "automation_id": automation_id,
        "run_id": run_id,
        "started_at": now.isoformat(),
        "finished_at": (now + timedelta(seconds=duration)).isoformat(),
        "duration_seconds": duration,
        "execution_result": result,
        "trigger_type": "state",
        "trigger_entity": "binary_sensor.motion",
        "step_count": 3,
        "last_step": "action/0",
        "context_id": "ctx-001",
    }
    data.update(overrides)
    return data


async def _seed_automation(client, automation_id="automation.test_one", alias="Test One", **kw):
    """Insert a single automation via the bulk_upsert endpoint."""
    resp = await client.post(
        "/internal/automations/bulk_upsert",
        json=[_make_automation(automation_id=automation_id, alias=alias, **kw)],
    )
    assert resp.status_code == 200
    return resp.json()


async def _seed_execution(client, automation_id="automation.test_one", run_id="run-001", **kw):
    """Insert a single execution via the bulk_upsert endpoint."""
    resp = await client.post(
        "/internal/automations/executions/bulk_upsert",
        json=[_make_execution(automation_id=automation_id, run_id=run_id, **kw)],
    )
    assert resp.status_code == 200
    return resp.json()


# ===========================================================================
# Internal: POST /internal/automations/bulk_upsert
# ===========================================================================


class TestBulkUpsertAutomations:
    """Tests for the internal bulk_upsert automations endpoint."""

    async def test_empty_list(self, client):
        resp = await client.post("/internal/automations/bulk_upsert", json=[])
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["upserted"] == 0

    async def test_single_insert(self, client):
        resp = await client.post(
            "/internal/automations/bulk_upsert",
            json=[_make_automation()],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["upserted"] == 1
        assert "timestamp" in body

    async def test_update_existing(self, client):
        await _seed_automation(client, alias="Original Alias")

        # Update alias
        resp = await client.post(
            "/internal/automations/bulk_upsert",
            json=[_make_automation(alias="Updated Alias")],
        )
        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1

        # Verify update persisted
        detail = await client.get("/api/v1/automations/automation.test_one")
        assert detail.status_code == 200
        assert detail.json()["alias"] == "Updated Alias"

    async def test_skip_missing_automation_id(self, client):
        resp = await client.post(
            "/internal/automations/bulk_upsert",
            json=[
                {"alias": "No ID"},  # missing automation_id
                _make_automation(),
            ],
        )
        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1  # only the valid one

    async def test_multiple_inserts(self, client):
        automations = [
            _make_automation("automation.a", "Alpha"),
            _make_automation("automation.b", "Bravo"),
            _make_automation("automation.c", "Charlie"),
        ]
        resp = await client.post("/internal/automations/bulk_upsert", json=automations)
        assert resp.status_code == 200
        assert resp.json()["upserted"] == 3

    async def test_update_enabled_field(self, client):
        await _seed_automation(client, enabled=True)

        resp = await client.post(
            "/internal/automations/bulk_upsert",
            json=[{"automation_id": "automation.test_one", "enabled": False}],
        )
        assert resp.status_code == 200

        detail = await client.get("/api/v1/automations/automation.test_one")
        assert detail.json()["enabled"] is False


# ===========================================================================
# Internal: POST /internal/automations/executions/bulk_upsert
# ===========================================================================


class TestBulkUpsertExecutions:
    """Tests for the internal bulk_upsert executions endpoint."""

    async def test_empty_list(self, client):
        resp = await client.post(
            "/internal/automations/executions/bulk_upsert", json=[]
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["upserted"] == 0

    async def test_single_insert(self, client):
        await _seed_automation(client)
        resp = await client.post(
            "/internal/automations/executions/bulk_upsert",
            json=[_make_execution()],
        )
        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1

    async def test_auto_create_parent_automation(self, client):
        """When parent automation doesn't exist, it should be auto-created."""
        resp = await client.post(
            "/internal/automations/executions/bulk_upsert",
            json=[_make_execution(automation_id="automation.new_one", run_id="run-new")],
        )
        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1

        # Verify the parent was auto-created
        detail = await client.get("/api/v1/automations/automation.new_one")
        assert detail.status_code == 200
        assert detail.json()["automation_id"] == "automation.new_one"

    async def test_skip_duplicate_run_id(self, client):
        await _seed_automation(client)
        await _seed_execution(client, run_id="run-dup")

        # Try again with same run_id
        resp = await client.post(
            "/internal/automations/executions/bulk_upsert",
            json=[_make_execution(run_id="run-dup")],
        )
        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0  # skipped

    async def test_skip_missing_required_fields(self, client):
        resp = await client.post(
            "/internal/automations/executions/bulk_upsert",
            json=[
                {"run_id": "run-no-auto"},  # missing automation_id
                {"automation_id": "automation.x"},  # missing run_id
            ],
        )
        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0

    async def test_parent_stats_update_total_executions(self, client):
        await _seed_automation(client)
        await _seed_execution(client, run_id="run-1", duration=2.0)
        await _seed_execution(client, run_id="run-2", duration=4.0)

        detail = await client.get("/api/v1/automations/automation.test_one")
        body = detail.json()
        assert body["total_executions"] == 2

    async def test_parent_stats_update_errors(self, client):
        await _seed_automation(client)
        await _seed_execution(client, run_id="run-ok", result="finished_successfully")
        await _seed_execution(client, run_id="run-err", result="error")

        detail = await client.get("/api/v1/automations/automation.test_one")
        body = detail.json()
        assert body["total_errors"] == 1
        assert body["total_executions"] == 2

    async def test_parent_stats_success_rate(self, client):
        await _seed_automation(client)
        await _seed_execution(client, run_id="r1", result="finished_successfully")
        await _seed_execution(client, run_id="r2", result="finished_successfully")
        await _seed_execution(client, run_id="r3", result="error")

        detail = await client.get("/api/v1/automations/automation.test_one")
        body = detail.json()
        # 2 success out of 3 = 66.7%
        assert body["success_rate"] == pytest.approx(66.7, abs=0.1)

    async def test_parent_stats_avg_duration(self, client):
        await _seed_automation(client)
        await _seed_execution(client, run_id="r1", duration=2.0)
        await _seed_execution(client, run_id="r2", duration=4.0)

        detail = await client.get("/api/v1/automations/automation.test_one")
        body = detail.json()
        # Incremental average: first=2.0, then 2.0 + (4.0-2.0)/2 = 3.0
        assert body["avg_duration_seconds"] == pytest.approx(3.0, abs=0.01)


# ===========================================================================
# Analytics: GET /api/v1/automations
# ===========================================================================


class TestListAutomations:
    """Tests for GET /api/v1/automations."""

    async def test_empty_db(self, client):
        resp = await client.get("/api/v1/automations")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["automations"] == []

    async def test_with_data(self, client):
        await _seed_automation(client, "automation.a", "Alpha")
        await _seed_automation(client, "automation.b", "Bravo")

        resp = await client.get("/api/v1/automations")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2

    async def test_enabled_only_filter(self, client):
        await _seed_automation(client, "automation.on", "Enabled", enabled=True)
        await _seed_automation(client, "automation.off", "Disabled", enabled=False)

        resp = await client.get("/api/v1/automations", params={"enabled_only": True})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["automations"][0]["automation_id"] == "automation.on"

    async def test_sort_by_alias(self, client):
        await _seed_automation(client, "automation.z", "Zulu")
        await _seed_automation(client, "automation.a", "Alpha")

        resp = await client.get("/api/v1/automations", params={"sort_by": "alias"})
        aliases = [a["alias"] for a in resp.json()["automations"]]
        assert aliases == ["Alpha", "Zulu"]

    async def test_limit(self, client):
        for i in range(5):
            await _seed_automation(client, f"automation.{i}", f"Auto {i}")

        resp = await client.get("/api/v1/automations", params={"limit": 3})
        assert resp.json()["count"] == 3


# ===========================================================================
# Analytics: GET /api/v1/automations/stats/overview
# ===========================================================================


class TestStatsOverview:
    """Tests for GET /api/v1/automations/stats/overview."""

    async def test_empty_db(self, client):
        resp = await client.get("/api/v1/automations/stats/overview")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_automations"] == 0
        assert body["total_executions"] == 0
        assert body["total_errors"] == 0
        assert body["error_rate_percent"] == 0

    async def test_with_data(self, client):
        await _seed_automation(client, "automation.a", "Alpha")
        await _seed_execution(client, "automation.a", "r1", result="finished_successfully", duration=1.0)
        await _seed_execution(client, "automation.a", "r2", result="error", duration=2.0)

        resp = await client.get("/api/v1/automations/stats/overview")
        body = resp.json()
        assert body["total_automations"] == 1
        assert body["total_executions"] == 2
        assert body["total_errors"] == 1
        assert body["error_rate_percent"] == 50.0
        assert len(body["top_errors"]) == 1
        assert len(body["top_active"]) == 1


# ===========================================================================
# Analytics: GET /api/v1/automations/stats/errors
# ===========================================================================


class TestStatsErrors:
    """Tests for GET /api/v1/automations/stats/errors."""

    async def test_no_errors(self, client):
        await _seed_automation(client)
        await _seed_execution(client, result="finished_successfully")

        resp = await client.get("/api/v1/automations/stats/errors")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    async def test_returns_error_sorted(self, client):
        await _seed_automation(client, "automation.a", "A")
        await _seed_automation(client, "automation.b", "B")
        # A gets 1 error, B gets 2 errors
        await _seed_execution(client, "automation.a", "ra1", result="error")
        await _seed_execution(client, "automation.b", "rb1", result="error")
        await _seed_execution(client, "automation.b", "rb2", result="error")

        resp = await client.get("/api/v1/automations/stats/errors")
        body = resp.json()
        assert body["count"] == 2
        # B should come first (more errors)
        assert body["automations"][0]["automation_id"] == "automation.b"
        assert body["automations"][1]["automation_id"] == "automation.a"


# ===========================================================================
# Analytics: GET /api/v1/automations/stats/slow
# ===========================================================================


class TestStatsSlow:
    """Tests for GET /api/v1/automations/stats/slow."""

    async def test_returns_duration_sorted(self, client):
        await _seed_automation(client, "automation.fast", "Fast")
        await _seed_automation(client, "automation.slow", "Slow")
        await _seed_execution(client, "automation.fast", "rf1", duration=0.5)
        await _seed_execution(client, "automation.slow", "rs1", duration=10.0)

        resp = await client.get("/api/v1/automations/stats/slow")
        body = resp.json()
        assert body["count"] == 2
        # Slow should come first
        assert body["automations"][0]["automation_id"] == "automation.slow"

    async def test_empty_when_no_durations(self, client):
        await _seed_automation(client)
        # No executions, so avg_duration_seconds is 0
        resp = await client.get("/api/v1/automations/stats/slow")
        assert resp.json()["count"] == 0


# ===========================================================================
# Analytics: GET /api/v1/automations/stats/inactive
# ===========================================================================


class TestStatsInactive:
    """Tests for GET /api/v1/automations/stats/inactive."""

    async def test_never_triggered_is_inactive(self, client):
        await _seed_automation(client)
        # No executions, so last_triggered is None -> inactive

        resp = await client.get("/api/v1/automations/stats/inactive", params={"days": 1})
        body = resp.json()
        assert body["threshold_days"] == 1
        assert body["count"] == 1

    async def test_recently_triggered_not_inactive(self, client):
        await _seed_automation(client)
        await _seed_execution(client)  # triggers now

        resp = await client.get("/api/v1/automations/stats/inactive", params={"days": 1})
        assert resp.json()["count"] == 0

    async def test_disabled_excluded(self, client):
        """Disabled automations are excluded from inactive list."""
        await _seed_automation(client, enabled=False)

        resp = await client.get("/api/v1/automations/stats/inactive", params={"days": 1})
        assert resp.json()["count"] == 0


# ===========================================================================
# Analytics: GET /api/v1/automations/{automation_id}
# ===========================================================================


class TestGetAutomation:
    """Tests for GET /api/v1/automations/{automation_id}."""

    async def test_found(self, client):
        await _seed_automation(client)
        resp = await client.get("/api/v1/automations/automation.test_one")
        assert resp.status_code == 200
        body = resp.json()
        assert body["automation_id"] == "automation.test_one"
        assert body["alias"] == "Test One"

    async def test_not_found(self, client):
        resp = await client.get("/api/v1/automations/automation.nonexistent")
        assert resp.status_code == 404

    async def test_includes_recent_executions(self, client):
        await _seed_automation(client)
        await _seed_execution(client, run_id="r1")
        await _seed_execution(client, run_id="r2")

        resp = await client.get("/api/v1/automations/automation.test_one")
        body = resp.json()
        assert "recent_executions" in body
        assert len(body["recent_executions"]) == 2


# ===========================================================================
# Analytics: GET /api/v1/automations/{automation_id}/executions
# ===========================================================================


class TestListExecutions:
    """Tests for GET /api/v1/automations/{automation_id}/executions."""

    async def test_empty(self, client):
        await _seed_automation(client)
        resp = await client.get("/api/v1/automations/automation.test_one/executions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["executions"] == []
        assert body["automation_id"] == "automation.test_one"

    async def test_paginated(self, client):
        await _seed_automation(client)
        for i in range(5):
            await _seed_execution(client, run_id=f"run-{i}")

        resp = await client.get(
            "/api/v1/automations/automation.test_one/executions",
            params={"limit": 2, "offset": 0},
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["executions"]) == 2
        assert body["limit"] == 2
        assert body["offset"] == 0

    async def test_offset(self, client):
        await _seed_automation(client)
        for i in range(5):
            await _seed_execution(client, run_id=f"run-{i}")

        resp = await client.get(
            "/api/v1/automations/automation.test_one/executions",
            params={"limit": 10, "offset": 3},
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["executions"]) == 2  # 5 - 3 offset = 2 remaining

    async def test_filter_by_result(self, client):
        await _seed_automation(client)
        await _seed_execution(client, run_id="r-ok", result="finished_successfully")
        await _seed_execution(client, run_id="r-err", result="error")

        resp = await client.get(
            "/api/v1/automations/automation.test_one/executions",
            params={"result_filter": "error"},
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["executions"][0]["execution_result"] == "error"

    async def test_execution_fields(self, client):
        await _seed_automation(client)
        await _seed_execution(client)

        resp = await client.get("/api/v1/automations/automation.test_one/executions")
        body = resp.json()
        assert len(body["executions"]) == 1
        exe = body["executions"][0]
        assert exe["run_id"] == "run-001"
        assert exe["trigger_type"] == "state"
        assert exe["trigger_entity"] == "binary_sensor.motion"
        assert exe["step_count"] == 3
        assert exe["last_step"] == "action/0"
        assert exe["context_id"] == "ctx-001"
        assert exe["duration_seconds"] == pytest.approx(1.5)
