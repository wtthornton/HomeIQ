"""Unit tests for automation_analytics_endpoints.py

Tests all endpoint handlers and helper functions with mocked database sessions.
No real database required — all queries are mocked via AsyncMock/MagicMock.
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from src.automation_analytics_endpoints import (
    _automation_to_dict,
    _execution_to_dict,
    list_automations,
    stats_overview,
    stats_errors,
    stats_slow,
    stats_inactive,
    get_automation,
    list_executions,
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_automation(**overrides):
    """Create a mock Automation ORM object."""
    a = MagicMock()
    a.automation_id = overrides.get("automation_id", "automation.test_1")
    a.alias = overrides.get("alias", "Test Automation")
    a.description = overrides.get("description", "A test automation")
    a.mode = overrides.get("mode", "single")
    a.enabled = overrides.get("enabled", True)
    a.total_executions = overrides.get("total_executions", 100)
    a.total_errors = overrides.get("total_errors", 5)
    a.avg_duration_seconds = overrides.get("avg_duration_seconds", 1.5)
    a.success_rate = overrides.get("success_rate", 95.0)
    a.last_triggered = overrides.get("last_triggered", datetime(2026, 3, 15, 10, 0, 0))
    a.created_at = overrides.get("created_at", datetime(2026, 1, 1, 0, 0, 0))
    a.updated_at = overrides.get("updated_at", datetime(2026, 3, 15, 10, 0, 0))
    return a


def _make_execution(**overrides):
    """Create a mock AutomationExecution ORM object."""
    e = MagicMock()
    e.id = overrides.get("id", 1)
    e.automation_id = overrides.get("automation_id", "automation.test_1")
    e.run_id = overrides.get("run_id", "run-abc-123")
    e.started_at = overrides.get("started_at", datetime(2026, 3, 15, 10, 0, 0))
    e.finished_at = overrides.get("finished_at", datetime(2026, 3, 15, 10, 0, 2))
    e.duration_seconds = overrides.get("duration_seconds", 2.0)
    e.execution_result = overrides.get("execution_result", "finished_successfully")
    e.trigger_type = overrides.get("trigger_type", "state")
    e.trigger_entity = overrides.get("trigger_entity", "binary_sensor.motion")
    e.error_message = overrides.get("error_message", None)
    e.step_count = overrides.get("step_count", 3)
    e.last_step = overrides.get("last_step", "action/2")
    e.context_id = overrides.get("context_id", "ctx-999")
    return e


def _mock_db_session(execute_returns=None):
    """Create a mock AsyncSession.

    execute_returns: list of return values for successive db.execute() calls.
    Each value should be a mock Result object.
    """
    db = AsyncMock()
    if execute_returns is not None:
        db.execute = AsyncMock(side_effect=execute_returns)
    return db


def _scalars_result(items):
    """Mock a Result whose .scalars().all() returns items."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _scalar_result(value):
    """Mock a Result whose .scalar() returns a value."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _one_result(**kwargs):
    """Mock a Result whose .one() returns a row with named attributes."""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    result = MagicMock()
    result.one.return_value = row
    return result


def _scalar_one_or_none_result(value):
    """Mock a Result whose .scalar_one_or_none() returns value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ===========================================================================
# Helper function tests
# ===========================================================================


class TestAutomationToDict:
    """Tests for _automation_to_dict() serialization helper."""

    @pytest.mark.unit
    def test_full_fields(self):
        a = _make_automation()
        d = _automation_to_dict(a)
        assert d["automation_id"] == "automation.test_1"
        assert d["alias"] == "Test Automation"
        assert d["description"] == "A test automation"
        assert d["mode"] == "single"
        assert d["enabled"] is True
        assert d["total_executions"] == 100
        assert d["total_errors"] == 5
        assert d["avg_duration_seconds"] == 1.5
        assert d["success_rate"] == 95.0
        assert d["last_triggered"] == "2026-03-15T10:00:00"
        assert d["created_at"] == "2026-01-01T00:00:00"
        assert d["updated_at"] == "2026-03-15T10:00:00"

    @pytest.mark.unit
    def test_none_timestamps(self):
        a = _make_automation(last_triggered=None, created_at=None, updated_at=None)
        d = _automation_to_dict(a)
        assert d["last_triggered"] is None
        assert d["created_at"] is None
        assert d["updated_at"] is None

    @pytest.mark.unit
    def test_none_numeric_defaults_to_zero(self):
        a = _make_automation(
            total_executions=None,
            total_errors=None,
            avg_duration_seconds=None,
            success_rate=None,
        )
        d = _automation_to_dict(a)
        assert d["total_executions"] == 0
        assert d["total_errors"] == 0
        assert d["avg_duration_seconds"] == 0
        assert d["success_rate"] == 0

    @pytest.mark.unit
    def test_zero_values(self):
        a = _make_automation(total_executions=0, total_errors=0, success_rate=0)
        d = _automation_to_dict(a)
        assert d["total_executions"] == 0
        assert d["total_errors"] == 0
        assert d["success_rate"] == 0

    @pytest.mark.unit
    def test_dict_keys_complete(self):
        expected_keys = {
            "automation_id", "alias", "description", "mode", "enabled",
            "total_executions", "total_errors", "avg_duration_seconds",
            "success_rate", "last_triggered", "created_at", "updated_at",
        }
        d = _automation_to_dict(_make_automation())
        assert set(d.keys()) == expected_keys


class TestExecutionToDict:
    """Tests for _execution_to_dict() serialization helper."""

    @pytest.mark.unit
    def test_full_fields(self):
        e = _make_execution()
        d = _execution_to_dict(e)
        assert d["id"] == 1
        assert d["automation_id"] == "automation.test_1"
        assert d["run_id"] == "run-abc-123"
        assert d["started_at"] == "2026-03-15T10:00:00"
        assert d["finished_at"] == "2026-03-15T10:00:02"
        assert d["duration_seconds"] == 2.0
        assert d["execution_result"] == "finished_successfully"
        assert d["trigger_type"] == "state"
        assert d["trigger_entity"] == "binary_sensor.motion"
        assert d["error_message"] is None
        assert d["step_count"] == 3
        assert d["last_step"] == "action/2"
        assert d["context_id"] == "ctx-999"

    @pytest.mark.unit
    def test_none_timestamps(self):
        e = _make_execution(started_at=None, finished_at=None)
        d = _execution_to_dict(e)
        assert d["started_at"] is None
        assert d["finished_at"] is None

    @pytest.mark.unit
    def test_error_execution(self):
        e = _make_execution(
            execution_result="error",
            error_message="Service unavailable",
            finished_at=None,
        )
        d = _execution_to_dict(e)
        assert d["execution_result"] == "error"
        assert d["error_message"] == "Service unavailable"
        assert d["finished_at"] is None

    @pytest.mark.unit
    def test_dict_keys_complete(self):
        expected_keys = {
            "id", "automation_id", "run_id", "started_at", "finished_at",
            "duration_seconds", "execution_result", "trigger_type",
            "trigger_entity", "error_message", "step_count", "last_step",
            "context_id",
        }
        d = _execution_to_dict(_make_execution())
        assert set(d.keys()) == expected_keys


# ===========================================================================
# Endpoint tests — list_automations
# ===========================================================================


class TestListAutomations:
    """Tests for GET /automations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_default_params(self):
        automations = [_make_automation(), _make_automation(automation_id="automation.test_2")]
        db = _mock_db_session([_scalars_result(automations)])
        result = await list_automations(enabled_only=False, sort_by="alias", limit=100, db=db)
        assert result["count"] == 2
        assert len(result["automations"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enabled_only_filter(self):
        db = _mock_db_session([_scalars_result([_make_automation(enabled=True)])])
        result = await list_automations(enabled_only=True, sort_by="alias", limit=100, db=db)
        assert result["count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sort_by_total_executions(self):
        db = _mock_db_session([_scalars_result([_make_automation()])])
        result = await list_automations(enabled_only=False, sort_by="total_executions", limit=100, db=db)
        assert result["count"] == 1
        db.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sort_by_success_rate(self):
        db = _mock_db_session([_scalars_result([_make_automation()])])
        result = await list_automations(enabled_only=False, sort_by="success_rate", limit=100, db=db)
        assert result["count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sort_by_last_triggered(self):
        db = _mock_db_session([_scalars_result([_make_automation()])])
        result = await list_automations(enabled_only=False, sort_by="last_triggered", limit=100, db=db)
        assert result["count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sort_by_errors(self):
        db = _mock_db_session([_scalars_result([_make_automation()])])
        result = await list_automations(enabled_only=False, sort_by="errors", limit=100, db=db)
        assert result["count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_sort_by_falls_back(self):
        """Unknown sort_by should fall back to Automation.alias (default)."""
        db = _mock_db_session([_scalars_result([_make_automation()])])
        result = await list_automations(enabled_only=False, sort_by="nonexistent", limit=100, db=db)
        assert result["count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_limit_1(self):
        db = _mock_db_session([_scalars_result([_make_automation()])])
        result = await list_automations(enabled_only=False, sort_by="alias", limit=1, db=db)
        assert result["count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_limit_500(self):
        db = _mock_db_session([_scalars_result([])])
        result = await list_automations(enabled_only=False, sort_by="alias", limit=500, db=db)
        assert result["count"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_database(self):
        db = _mock_db_session([_scalars_result([])])
        result = await list_automations(enabled_only=False, sort_by="alias", limit=100, db=db)
        assert result["count"] == 0
        assert result["automations"] == []


# ===========================================================================
# Endpoint tests — stats_overview
# ===========================================================================


class TestStatsOverview:
    """Tests for GET /automations/stats/overview."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_normal_data(self):
        agg = _one_result(
            total_automations=10,
            total_executions=1000,
            total_errors=50,
            avg_success_rate=95.0,
            avg_duration=1.234,
        )
        top_err = _scalars_result([_make_automation(total_errors=20)])
        top_act = _scalars_result([_make_automation(total_executions=500)])
        db = _mock_db_session([agg, top_err, top_act])

        result = await stats_overview(db=db)
        assert result["total_automations"] == 10
        assert result["total_executions"] == 1000
        assert result["total_errors"] == 50
        assert result["error_rate_percent"] == 5.0
        assert result["avg_success_rate"] == 95.0
        assert result["avg_duration_seconds"] == 1.234
        assert len(result["top_errors"]) == 1
        assert len(result["top_active"]) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_data(self):
        """No automations at all — all aggregates return None."""
        agg = _one_result(
            total_automations=None,
            total_executions=None,
            total_errors=None,
            avg_success_rate=None,
            avg_duration=None,
        )
        top_err = _scalars_result([])
        top_act = _scalars_result([])
        db = _mock_db_session([agg, top_err, top_act])

        result = await stats_overview(db=db)
        assert result["total_automations"] == 0
        assert result["total_executions"] == 0
        assert result["total_errors"] == 0
        assert result["error_rate_percent"] == 0
        assert result["avg_success_rate"] == 0
        assert result["avg_duration_seconds"] == 0
        assert result["top_errors"] == []
        assert result["top_active"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_zero_executions_avoids_division_by_zero(self):
        agg = _one_result(
            total_automations=5,
            total_executions=0,
            total_errors=0,
            avg_success_rate=100.0,
            avg_duration=0,
        )
        db = _mock_db_session([agg, _scalars_result([]), _scalars_result([])])
        result = await stats_overview(db=db)
        assert result["error_rate_percent"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_rate_rounding(self):
        agg = _one_result(
            total_automations=3,
            total_executions=300,
            total_errors=7,
            avg_success_rate=97.7,
            avg_duration=0.5,
        )
        db = _mock_db_session([agg, _scalars_result([]), _scalars_result([])])
        result = await stats_overview(db=db)
        # 7/300*100 = 2.333... -> rounded to 2.3
        assert result["error_rate_percent"] == round(7 / 300 * 100, 1)


# ===========================================================================
# Endpoint tests — stats_errors
# ===========================================================================


class TestStatsErrors:
    """Tests for GET /automations/stats/errors."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_automations(self):
        items = [_make_automation(total_errors=10), _make_automation(total_errors=3)]
        db = _mock_db_session([_scalars_result(items)])
        result = await stats_errors(limit=20, db=db)
        assert result["count"] == 2
        assert len(result["automations"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_errors(self):
        db = _mock_db_session([_scalars_result([])])
        result = await stats_errors(limit=20, db=db)
        assert result["count"] == 0
        assert result["automations"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_limit_param(self):
        db = _mock_db_session([_scalars_result([_make_automation(total_errors=1)])])
        result = await stats_errors(limit=1, db=db)
        assert result["count"] == 1


# ===========================================================================
# Endpoint tests — stats_slow
# ===========================================================================


class TestStatsSlow:
    """Tests for GET /automations/stats/slow."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_slow_automations(self):
        items = [
            _make_automation(avg_duration_seconds=10.5),
            _make_automation(avg_duration_seconds=5.2),
        ]
        db = _mock_db_session([_scalars_result(items)])
        result = await stats_slow(limit=20, db=db)
        assert result["count"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_slow(self):
        db = _mock_db_session([_scalars_result([])])
        result = await stats_slow(limit=20, db=db)
        assert result["count"] == 0
        assert result["automations"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_limit_param(self):
        db = _mock_db_session([_scalars_result([_make_automation(avg_duration_seconds=99.0)])])
        result = await stats_slow(limit=1, db=db)
        assert result["count"] == 1


# ===========================================================================
# Endpoint tests — stats_inactive
# ===========================================================================


class TestStatsInactive:
    """Tests for GET /automations/stats/inactive."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_inactive_automations(self):
        old = _make_automation(last_triggered=datetime(2026, 1, 1))
        db = _mock_db_session([_scalars_result([old])])
        result = await stats_inactive(days=30, db=db)
        assert result["threshold_days"] == 30
        assert result["count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_days_param(self):
        db = _mock_db_session([_scalars_result([])])
        result = await stats_inactive(days=7, db=db)
        assert result["threshold_days"] == 7
        assert result["count"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_max_days_365(self):
        db = _mock_db_session([_scalars_result([])])
        result = await stats_inactive(days=365, db=db)
        assert result["threshold_days"] == 365

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_database(self):
        db = _mock_db_session([_scalars_result([])])
        result = await stats_inactive(days=30, db=db)
        assert result["count"] == 0
        assert result["automations"] == []


# ===========================================================================
# Endpoint tests — get_automation
# ===========================================================================


class TestGetAutomation:
    """Tests for GET /automations/{automation_id}."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_found(self):
        auto = _make_automation()
        execs = [_make_execution(), _make_execution(id=2, run_id="run-def-456")]
        db = _mock_db_session([
            _scalar_one_or_none_result(auto),
            _scalars_result(execs),
        ])
        result = await get_automation(automation_id="automation.test_1", db=db)
        assert result["automation_id"] == "automation.test_1"
        assert len(result["recent_executions"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        db = _mock_db_session([_scalar_one_or_none_result(None)])
        with pytest.raises(HTTPException) as exc_info:
            await get_automation(automation_id="automation.nonexistent", db=db)
        assert exc_info.value.status_code == 404
        assert "nonexistent" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_found_no_executions(self):
        auto = _make_automation()
        db = _mock_db_session([
            _scalar_one_or_none_result(auto),
            _scalars_result([]),
        ])
        result = await get_automation(automation_id="automation.test_1", db=db)
        assert result["recent_executions"] == []


# ===========================================================================
# Endpoint tests — list_executions
# ===========================================================================


class TestListExecutions:
    """Tests for GET /automations/{automation_id}/executions."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_default_pagination(self):
        execs = [_make_execution(id=i) for i in range(3)]
        db = _mock_db_session([_scalars_result(execs), _scalar_result(3)])
        result = await list_executions(
            automation_id="automation.test_1", limit=50, offset=0,
            result_filter=None, db=db,
        )
        assert result["automation_id"] == "automation.test_1"
        assert result["total"] == 3
        assert result["offset"] == 0
        assert result["limit"] == 50
        assert len(result["executions"]) == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_with_result_filter(self):
        execs = [_make_execution(execution_result="error")]
        db = _mock_db_session([_scalars_result(execs), _scalar_result(1)])
        result = await list_executions(
            automation_id="automation.test_1", limit=50, offset=0,
            result_filter="error", db=db,
        )
        assert result["total"] == 1
        assert len(result["executions"]) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_results(self):
        db = _mock_db_session([_scalars_result([]), _scalar_result(0)])
        result = await list_executions(
            automation_id="automation.test_1", limit=50, offset=0,
            result_filter=None, db=db,
        )
        assert result["total"] == 0
        assert result["executions"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pagination_offset(self):
        db = _mock_db_session([_scalars_result([_make_execution()]), _scalar_result(10)])
        result = await list_executions(
            automation_id="automation.test_1", limit=5, offset=5,
            result_filter=None, db=db,
        )
        assert result["offset"] == 5
        assert result["limit"] == 5
        assert result["total"] == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_limit_boundary_1(self):
        db = _mock_db_session([_scalars_result([_make_execution()]), _scalar_result(1)])
        result = await list_executions(
            automation_id="automation.test_1", limit=1, offset=0,
            result_filter=None, db=db,
        )
        assert result["limit"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_limit_boundary_500(self):
        db = _mock_db_session([_scalars_result([]), _scalar_result(0)])
        result = await list_executions(
            automation_id="automation.test_1", limit=500, offset=0,
            result_filter=None, db=db,
        )
        assert result["limit"] == 500

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_total_none_defaults_to_zero(self):
        """When count query returns None, total should be 0."""
        db = _mock_db_session([_scalars_result([]), _scalar_result(None)])
        result = await list_executions(
            automation_id="automation.test_1", limit=50, offset=0,
            result_filter=None, db=db,
        )
        assert result["total"] == 0
