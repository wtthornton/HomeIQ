"""
Tests for automation_analytics + automation_internal + jobs endpoints — Epic 80, Story 80.10a

Covers 16 scenarios:

automation_analytics:
1.  _automation_to_dict — serializes all fields
2.  _automation_to_dict — handles None timestamps
3.  _execution_to_dict — serializes all fields
4.  _execution_to_dict — handles None timestamps
5.  list_automations — returns list via mock DB
6.  get_automation — 404 for missing automation

automation_internal:
7.  bulk_upsert_automations — creates new automation
8.  bulk_upsert_automations — skips entries without automation_id
9.  bulk_upsert_automations — updates existing automation
10. bulk_upsert_executions — creates execution and updates parent stats
11. bulk_upsert_executions — skips duplicate run_id
12. bulk_upsert_executions — handles DB error with rollback

jobs:
13. JobStatusResponse — validates fields
14. ConsolidationMetricsResponse — validates defaults
15. TriggerResponse — validates defaults
16. _get_scheduler — raises 503 when scheduler is None
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Override conftest fresh_db — no real DB needed
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ===========================================================================
# automation_analytics helper tests
# ===========================================================================


class TestAutomationToDict:
    """_automation_to_dict serialization."""

    def test_serializes_all_fields(self):
        from src.automation_analytics_endpoints import _automation_to_dict

        a = MagicMock()
        a.automation_id = "auto-001"
        a.alias = "Morning Lights"
        a.description = "Turn on lights"
        a.mode = "single"
        a.enabled = True
        a.total_executions = 42
        a.total_errors = 2
        a.avg_duration_seconds = 1.5
        a.success_rate = 95.2
        a.last_triggered = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)
        a.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        a.updated_at = datetime(2026, 3, 15, tzinfo=UTC)

        result = _automation_to_dict(a)
        assert result["automation_id"] == "auto-001"
        assert result["alias"] == "Morning Lights"
        assert result["total_executions"] == 42
        assert result["success_rate"] == 95.2
        assert "2026-03-15" in result["last_triggered"]

    def test_handles_none_timestamps(self):
        from src.automation_analytics_endpoints import _automation_to_dict

        a = MagicMock()
        a.automation_id = "auto-002"
        a.alias = "Test"
        a.description = None
        a.mode = "single"
        a.enabled = True
        a.total_executions = None
        a.total_errors = None
        a.avg_duration_seconds = None
        a.success_rate = None
        a.last_triggered = None
        a.created_at = None
        a.updated_at = None

        result = _automation_to_dict(a)
        assert result["total_executions"] == 0
        assert result["last_triggered"] is None
        assert result["created_at"] is None


class TestExecutionToDict:
    """_execution_to_dict serialization."""

    def test_serializes_all_fields(self):
        from src.automation_analytics_endpoints import _execution_to_dict

        e = MagicMock()
        e.id = 1
        e.automation_id = "auto-001"
        e.run_id = "run-abc"
        e.started_at = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)
        e.finished_at = datetime(2026, 3, 15, 10, 0, 5, tzinfo=UTC)
        e.duration_seconds = 5.0
        e.execution_result = "success"
        e.trigger_type = "state"
        e.trigger_entity = "light.kitchen"
        e.error_message = None
        e.step_count = 3
        e.last_step = "action"
        e.context_id = "ctx-001"

        result = _execution_to_dict(e)
        assert result["id"] == 1
        assert result["run_id"] == "run-abc"
        assert result["duration_seconds"] == 5.0
        assert result["trigger_type"] == "state"

    def test_handles_none_timestamps(self):
        from src.automation_analytics_endpoints import _execution_to_dict

        e = MagicMock()
        e.id = 2
        e.automation_id = "auto-001"
        e.run_id = "run-xyz"
        e.started_at = None
        e.finished_at = None
        e.duration_seconds = None
        e.execution_result = "unknown"
        e.trigger_type = None
        e.trigger_entity = None
        e.error_message = None
        e.step_count = None
        e.last_step = None
        e.context_id = None

        result = _execution_to_dict(e)
        assert result["started_at"] is None
        assert result["finished_at"] is None


# ===========================================================================
# automation_analytics endpoint tests (mock DB)
# ===========================================================================


class TestAutomationAnalyticsEndpoints:
    """automation_analytics_endpoints route handlers."""

    @pytest.mark.asyncio
    async def test_list_automations(self):
        from src.automation_analytics_endpoints import list_automations

        mock_auto = MagicMock()
        mock_auto.automation_id = "auto-001"
        mock_auto.alias = "Test"
        mock_auto.description = None
        mock_auto.mode = "single"
        mock_auto.enabled = True
        mock_auto.total_executions = 10
        mock_auto.total_errors = 0
        mock_auto.avg_duration_seconds = 1.0
        mock_auto.success_rate = 100.0
        mock_auto.last_triggered = None
        mock_auto.created_at = None
        mock_auto.updated_at = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_auto]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_automations(
            enabled_only=False, sort_by="alias", limit=100, db=mock_db
        )
        assert result["count"] == 1
        assert result["automations"][0]["automation_id"] == "auto-001"

    @pytest.mark.asyncio
    async def test_get_automation_404(self):
        from fastapi import HTTPException
        from src.automation_analytics_endpoints import get_automation

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_automation(automation_id="missing", db=mock_db)
        assert exc_info.value.status_code == 404


# ===========================================================================
# automation_internal endpoint tests (mock DB)
# ===========================================================================


class TestAutomationInternalEndpoints:
    """automation_internal_endpoints bulk upsert handlers."""

    @pytest.mark.asyncio
    async def test_bulk_upsert_creates_new(self):
        from src.automation_internal_endpoints import bulk_upsert_automations

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = [{"automation_id": "auto-new", "alias": "New Auto"}]
        result = await bulk_upsert_automations(automations=data, db=mock_db)
        assert result["success"] is True
        assert result["upserted"] == 1
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_skips_no_id(self):
        from src.automation_internal_endpoints import bulk_upsert_automations

        mock_db = AsyncMock()
        data = [{"alias": "No ID"}]
        result = await bulk_upsert_automations(automations=data, db=mock_db)
        assert result["upserted"] == 0

    @pytest.mark.asyncio
    async def test_bulk_upsert_updates_existing(self):
        from src.automation_internal_endpoints import bulk_upsert_automations

        existing = MagicMock()
        existing.alias = "Old"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = [{"automation_id": "auto-001", "alias": "Updated"}]
        result = await bulk_upsert_automations(automations=data, db=mock_db)
        assert result["upserted"] == 1
        assert existing.alias == "Updated"

    @pytest.mark.asyncio
    async def test_bulk_upsert_executions_creates(self):
        from src.automation_internal_endpoints import bulk_upsert_executions

        # First call: check duplicate run_id → None (not found)
        # Second call: get parent automation → existing automation
        mock_auto = MagicMock()
        mock_auto.total_executions = 5
        mock_auto.total_errors = 1
        mock_auto.avg_duration_seconds = 2.0
        mock_auto.last_triggered = None
        mock_auto.success_rate = 80.0

        mock_db = AsyncMock()

        mock_dup_result = MagicMock()
        mock_dup_result.scalar_one_or_none.return_value = None

        mock_auto_result = MagicMock()
        mock_auto_result.scalar_one_or_none.return_value = mock_auto

        mock_db.execute = AsyncMock(side_effect=[mock_dup_result, mock_auto_result])

        data = [{
            "run_id": "run-001",
            "automation_id": "auto-001",
            "started_at": "2026-03-15T10:00:00+00:00",
            "duration_seconds": 3.0,
            "execution_result": "success",
        }]
        result = await bulk_upsert_executions(executions=data, db=mock_db)
        assert result["success"] is True
        assert result["upserted"] == 1
        assert mock_auto.total_executions == 6

    @pytest.mark.asyncio
    async def test_bulk_upsert_executions_skips_duplicate(self):
        from src.automation_internal_endpoints import bulk_upsert_executions

        existing_exec = MagicMock()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_exec
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = [{"run_id": "run-dup", "automation_id": "auto-001"}]
        result = await bulk_upsert_executions(executions=data, db=mock_db)
        assert result["upserted"] == 0

    @pytest.mark.asyncio
    async def test_bulk_upsert_executions_handles_db_error(self):
        from fastapi import HTTPException
        from src.automation_internal_endpoints import bulk_upsert_executions

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB down"))

        with pytest.raises(HTTPException) as exc_info:
            await bulk_upsert_executions(
                executions=[{"run_id": "r1", "automation_id": "a1"}], db=mock_db
            )
        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


# ===========================================================================
# jobs endpoint tests
# ===========================================================================


class TestJobsResponseModels:
    """Jobs endpoint response models."""

    def test_job_status_response(self):
        from src.jobs_endpoints import JobStatusResponse

        r = JobStatusResponse(
            running=True,
            apscheduler_available=True,
            jobs=[{"name": "consolidation", "next_run": "2026-03-16T00:00:00"}],
            consolidation={"last_run": "2026-03-15T18:00:00"},
        )
        assert r.running is True
        assert len(r.jobs) == 1

    def test_consolidation_metrics_defaults(self):
        from src.jobs_endpoints import ConsolidationMetricsResponse

        r = ConsolidationMetricsResponse(started_at="2026-03-15T18:00:00")
        assert r.memories_created == 0
        assert r.success is True
        assert r.duration_ms == 0.0

    def test_trigger_response_defaults(self):
        from src.jobs_endpoints import TriggerResponse

        r = TriggerResponse()
        assert r.success is True
        assert r.memories_reinforced == 0

    def test_get_scheduler_raises_503(self):
        from fastapi import HTTPException
        from src.jobs_endpoints import _get_scheduler

        mock_service = MagicMock()
        mock_service.job_scheduler = None

        with patch("src.main.data_api_service", mock_service):
            with pytest.raises(HTTPException) as exc_info:
                _get_scheduler()
            assert exc_info.value.status_code == 503
