"""Degraded-start recovery tests for DatabaseManager.

A service that lost the startup race to Postgres used to stay degraded for the
life of the process: `initialize` set `_available = False`, and nothing ever
re-attempted it, so every later `get_db()` raised even once the database was
healthy again. Observed live on automation-miner, which
started one second before Postgres accepted connections and then reported
"Database not available" indefinitely while `SELECT 1` succeeded from inside the
same container.

These tests pin the recovery, and pin that it stays rate-limited so a service
taking traffic against a genuinely down database does not reconnect per request.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from homeiq_data.database_manager import DatabaseManager


def _manager() -> DatabaseManager:
    return DatabaseManager(
        schema="testschema",
        service_name="test-service",
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
    )


class TestRecoversAfterDegradedStart:
    @pytest.mark.asyncio
    async def test_get_db_retries_initialize_and_succeeds(self):
        db = _manager()

        # Startup: database unreachable.
        with patch.object(DatabaseManager, "initialize", new=AsyncMock(return_value=False)):
            assert await db.initialize() is False
        db._init_args = {"base": None, "run_alembic": False, "alembic_ini_path": None}
        assert db._available is False

        # Database comes back; the next session request must retry rather than
        # raise for the life of the process.
        async def _recovered(**_kwargs):
            db._available = True
            db._session_maker = object()
            return True

        with patch.object(DatabaseManager, "initialize", new=AsyncMock(side_effect=_recovered)):
            assert await db._try_recover() is True

        assert db._available is True

    @pytest.mark.asyncio
    async def test_still_raises_when_recovery_also_fails(self):
        """The failure mode callers already handle must be preserved."""
        db = _manager()
        db._init_args = {"base": None, "run_alembic": False, "alembic_ini_path": None}

        with (
            patch.object(DatabaseManager, "initialize", new=AsyncMock(return_value=False)),
            pytest.raises(RuntimeError, match="degraded mode"),
        ):
            async with db.get_db():
                pass

    @pytest.mark.asyncio
    async def test_no_recovery_before_initialize_was_ever_called(self):
        """Nothing to replay, so it must not invent an initialize() call."""
        db = _manager()
        init = AsyncMock(return_value=True)
        with patch.object(DatabaseManager, "initialize", new=init):
            assert await db._try_recover() is False
        init.assert_not_awaited()


class TestRecoveryIsRateLimited:
    @pytest.mark.asyncio
    async def test_second_attempt_within_cooldown_is_skipped(self):
        db = _manager()
        db._init_args = {"base": None, "run_alembic": False, "alembic_ini_path": None}

        init = AsyncMock(return_value=False)
        with patch.object(DatabaseManager, "initialize", new=init):
            assert await db._try_recover() is False
            assert await db._try_recover() is False

        # Only the first attempt should have reached initialize().
        assert init.await_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_requests_trigger_one_attempt(self):
        """A burst of requests against a down database must not stampede."""
        db = _manager()
        db._init_args = {"base": None, "run_alembic": False, "alembic_ini_path": None}

        init = AsyncMock(return_value=False)
        with patch.object(DatabaseManager, "initialize", new=init):
            await asyncio.gather(*(db._try_recover() for _ in range(10)))

        assert init.await_count == 1
