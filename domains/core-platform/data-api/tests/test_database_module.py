"""
Unit tests for the data-api database module (database.py).

Tests module-level constants, DatabaseManager instantiation, Base metadata,
get_db, init_db, and check_db_health — all with DatabaseManager mocked so no
real PostgreSQL instance is required.

Story: database module unit coverage
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Override the autouse fresh_db fixture from conftest.py so unit tests here
# do not attempt to connect to a real PostgreSQL engine.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def fresh_db():  # noqa: PT004
    """No-op override: unit tests here use mocked DatabaseManager."""
    yield


# ---------------------------------------------------------------------------
# Helpers — fresh module import per test
# ---------------------------------------------------------------------------

def _reload_database_module():
    """Force a clean import of src.database so module-level code re-executes."""
    # Remove cached module so module-level code (DatabaseManager(...)) reruns
    for key in list(sys.modules.keys()):
        if key in ("src.database",):
            del sys.modules[key]


def _make_mock_db_manager():
    """Return a MagicMock shaped like homeiq_data.DatabaseManager."""
    mock_db = MagicMock()
    mock_db.engine = MagicMock()
    mock_db.session_maker = MagicMock()

    # get_db() is an async context manager
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _get_db_ctx():
        yield mock_session

    mock_db.get_db = _get_db_ctx

    # initialize() returns True by default
    mock_db.initialize = AsyncMock(return_value=True)

    # check_health() returns a healthy dict
    mock_db.check_health = AsyncMock(return_value={"status": "healthy", "backend": "postgresql"})

    return mock_db, mock_session


# ---------------------------------------------------------------------------
# 1. Module-level constants
# ---------------------------------------------------------------------------


class TestModuleLevelConstants:
    """Tests for DATABASE_URL and DATABASE_SCHEMA defaults."""

    def test_database_url_default_is_empty_string(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        _reload_database_module()
        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database as db_module
            assert db_module.DATABASE_URL == ""

    def test_database_url_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pw@host/db")
        _reload_database_module()
        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database as db_module
            assert db_module.DATABASE_URL == "postgresql+asyncpg://user:pw@host/db"

    def test_database_schema_default_is_core(self, monkeypatch):
        monkeypatch.delenv("DATABASE_SCHEMA", raising=False)
        _reload_database_module()
        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database as db_module
            assert db_module.DATABASE_SCHEMA == "core"

    def test_database_schema_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_SCHEMA", "myschema")
        _reload_database_module()
        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database as db_module
            assert db_module.DATABASE_SCHEMA == "myschema"


# ---------------------------------------------------------------------------
# 2. DatabaseManager instantiation
# ---------------------------------------------------------------------------


class TestDatabaseManagerInstantiation:
    """Verify DatabaseManager is constructed with the correct keyword args."""

    def test_instantiated_with_correct_params(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test/db")
        monkeypatch.setenv("DATABASE_SCHEMA", "core")
        _reload_database_module()

        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database  # noqa: F401
            call_kwargs = mock_db_cls.call_args.kwargs
            assert call_kwargs["schema"] == "core"
            assert call_kwargs["service_name"] == "data-api"
            assert call_kwargs["database_url"] == "postgresql+asyncpg://test/db"
            assert call_kwargs["pool_size"] == 10
            assert call_kwargs["max_overflow"] == 5
            assert call_kwargs["auto_commit_sessions"] is True

    def test_schema_param_matches_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_SCHEMA", "tenant_schema")
        monkeypatch.setenv("DATABASE_URL", "")
        _reload_database_module()

        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database  # noqa: F401
            call_kwargs = mock_db_cls.call_args.kwargs
            assert call_kwargs["schema"] == "tenant_schema"


# ---------------------------------------------------------------------------
# 3. Base class metadata schema
# ---------------------------------------------------------------------------


class TestBaseMetadata:
    """Base.metadata must use the schema from DATABASE_SCHEMA."""

    def test_base_metadata_schema_matches_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_SCHEMA", "core")
        _reload_database_module()
        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database as db_module
            assert db_module.Base.metadata.schema == "core"

    def test_base_metadata_schema_from_custom_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_SCHEMA", "alt_schema")
        _reload_database_module()
        mock_db_cls = MagicMock(return_value=MagicMock())
        with patch("homeiq_data.DatabaseManager", mock_db_cls):
            import src.database as db_module
            assert db_module.Base.metadata.schema == "alt_schema"


# ---------------------------------------------------------------------------
# 4. get_db — yields a session
# ---------------------------------------------------------------------------


class TestGetDb:
    """get_db must yield the session produced by db.get_db()."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        from src.database import get_db

        mock_db, mock_session = _make_mock_db_manager()

        with patch("src.database.db", mock_db):
            sessions = []
            async for session in get_db():
                sessions.append(session)

        assert len(sessions) == 1
        assert sessions[0] is mock_session

    @pytest.mark.asyncio
    async def test_get_db_exits_context_manager(self):
        """get_db must use the async context manager on db.get_db."""
        from src.database import get_db

        entered = []
        exited = []

        @asynccontextmanager
        async def _tracking_ctx():
            entered.append(True)
            yield AsyncMock()
            exited.append(True)

        mock_db = MagicMock()
        mock_db.get_db = _tracking_ctx

        with patch("src.database.db", mock_db):
            async for _ in get_db():
                pass

        assert entered == [True]
        assert exited == [True]


# ---------------------------------------------------------------------------
# 5. init_db — success path
# ---------------------------------------------------------------------------


class TestInitDbSuccess:
    """init_db must call db.initialize, assign module globals, and return True."""

    @pytest.mark.asyncio
    async def test_init_db_returns_true_on_success(self):
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        fake_engine = MagicMock()
        fake_session_maker = MagicMock()
        mock_db.engine = fake_engine
        mock_db.session_maker = fake_session_maker

        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=None)))
        fake_engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            result = await init_db()

        assert result is True

    @pytest.mark.asyncio
    async def test_init_db_calls_db_initialize_with_base(self):
        from src.database import Base, init_db

        mock_db, _ = _make_mock_db_manager()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=None)))
        mock_db.engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        mock_db.initialize.assert_awaited_once_with(base=Base)

    @pytest.mark.asyncio
    async def test_init_db_assigns_async_engine_global(self):
        import src.database as db_module
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        fake_engine = MagicMock()
        mock_db.engine = fake_engine
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=None)))
        fake_engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        assert db_module.async_engine is fake_engine

    @pytest.mark.asyncio
    async def test_init_db_assigns_async_session_local_global(self):
        import src.database as db_module
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        fake_session_maker = MagicMock()
        mock_db.session_maker = fake_session_maker
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=None)))
        mock_db.engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        assert db_module.AsyncSessionLocal is fake_session_maker


# ---------------------------------------------------------------------------
# 6. init_db — failure path
# ---------------------------------------------------------------------------


class TestInitDbFailure:
    """init_db must return False when db.initialize() returns False."""

    @pytest.mark.asyncio
    async def test_init_db_returns_false_when_initialize_fails(self):
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        mock_db.initialize = AsyncMock(return_value=False)
        mock_db.engine = None  # engine is None on failure

        with patch("src.database.db", mock_db):
            result = await init_db()

        assert result is False

    @pytest.mark.asyncio
    async def test_init_db_skips_schema_creation_when_result_false(self):
        """When initialize returns False, schema CREATE SCHEMA must not be called."""
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        mock_db.initialize = AsyncMock(return_value=False)
        mock_db.engine = None

        with patch("src.database.db", mock_db):
            await init_db()

        # engine is None so .begin() should never have been called
        # (no AttributeError because we short-circuit on `if result and db.engine`)


# ---------------------------------------------------------------------------
# 7. init_db — creates schema
# ---------------------------------------------------------------------------


class TestInitDbCreatesSchema:
    """init_db must execute CREATE SCHEMA IF NOT EXISTS when engine is ready."""

    @pytest.mark.asyncio
    async def test_init_db_executes_create_schema(self, monkeypatch):
        monkeypatch.setenv("DATABASE_SCHEMA", "core")
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        conn = AsyncMock()
        executed_sqls: list[str] = []

        async def _capture_execute(stmt):
            executed_sqls.append(str(stmt))
            return MagicMock(scalar=MagicMock(return_value=None))

        conn.execute = _capture_execute
        mock_db.engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        create_schema_calls = [s for s in executed_sqls if "CREATE SCHEMA" in s.upper()]
        assert len(create_schema_calls) >= 1

    @pytest.mark.asyncio
    async def test_init_db_schema_creation_error_does_not_raise(self):
        """A failure in CREATE SCHEMA must be swallowed (not re-raised)."""
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()

        call_count = [0]

        @asynccontextmanager
        async def _failing_begin():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("schema creation failed")
            # Second call (migration check) succeeds
            conn = AsyncMock()
            conn.execute = AsyncMock(
                return_value=MagicMock(scalar=MagicMock(return_value=None))
            )
            yield conn

        mock_db.engine.begin = _failing_begin

        with patch("src.database.db", mock_db):
            result = await init_db()  # must not raise

        assert result is True


# ---------------------------------------------------------------------------
# 8. init_db — timestamp migration runs when columns are naive
# ---------------------------------------------------------------------------


class TestInitDbTimestampMigration:
    """init_db must ALTER columns when last_seen type contains 'without'."""

    @pytest.mark.asyncio
    async def test_migration_runs_when_columns_naive(self):
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()

        executed_sqls: list[str] = []

        async def _execute(stmt):
            sql_text = str(stmt)
            executed_sqls.append(sql_text)
            # SELECT data_type check — signal naive column
            if "data_type" in sql_text.lower():
                return MagicMock(scalar=MagicMock(return_value="timestamp without time zone"))
            return MagicMock(scalar=MagicMock(return_value=None))

        conn = AsyncMock()
        conn.execute = _execute
        # engine.begin() is called twice: schema create + migration block
        mock_db.engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        alter_calls = [s for s in executed_sqls if "ALTER TABLE" in s.upper()]
        assert len(alter_calls) == 5, f"Expected 5 ALTER TABLE calls, got {len(alter_calls)}"

    @pytest.mark.asyncio
    async def test_migration_alters_correct_tables_and_columns(self):
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        executed_sqls: list[str] = []

        async def _execute(stmt):
            sql_text = str(stmt)
            executed_sqls.append(sql_text)
            if "data_type" in sql_text.lower():
                return MagicMock(scalar=MagicMock(return_value="timestamp without time zone"))
            return MagicMock(scalar=MagicMock(return_value=None))

        conn = AsyncMock()
        conn.execute = _execute
        mock_db.engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        alter_calls = [s for s in executed_sqls if "ALTER TABLE" in s.upper()]
        expected_pairs = [
            ("devices", "last_seen"),
            ("devices", "created_at"),
            ("devices", "last_capability_sync"),
            ("entities", "created_at"),
            ("entities", "updated_at"),
        ]
        for tbl, col in expected_pairs:
            match = any(tbl in s and col in s for s in alter_calls)
            assert match, f"Expected ALTER for {tbl}.{col} not found in: {alter_calls}"


# ---------------------------------------------------------------------------
# 9. init_db — skips migration when columns already timezone-aware
# ---------------------------------------------------------------------------


class TestInitDbMigrationSkipped:
    """init_db must not ALTER columns when data_type has no 'without'."""

    @pytest.mark.asyncio
    async def test_migration_skipped_when_columns_already_aware(self):
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        executed_sqls: list[str] = []

        async def _execute(stmt):
            sql_text = str(stmt)
            executed_sqls.append(sql_text)
            if "data_type" in sql_text.lower():
                # Already timezone-aware — no "without" in type name
                return MagicMock(
                    scalar=MagicMock(return_value="timestamp with time zone")
                )
            return MagicMock(scalar=MagicMock(return_value=None))

        conn = AsyncMock()
        conn.execute = _execute
        mock_db.engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        alter_calls = [s for s in executed_sqls if "ALTER TABLE" in s.upper()]
        assert alter_calls == [], f"No ALTER should run, got: {alter_calls}"

    @pytest.mark.asyncio
    async def test_migration_skipped_when_col_type_is_none(self):
        """If the column doesn't exist, scalar() returns None — skip migration."""
        from src.database import init_db

        mock_db, _ = _make_mock_db_manager()
        executed_sqls: list[str] = []

        async def _execute(stmt):
            sql_text = str(stmt)
            executed_sqls.append(sql_text)
            if "data_type" in sql_text.lower():
                return MagicMock(scalar=MagicMock(return_value=None))
            return MagicMock(scalar=MagicMock(return_value=None))

        conn = AsyncMock()
        conn.execute = _execute
        mock_db.engine.begin = _make_begin_factory(conn)

        with patch("src.database.db", mock_db):
            await init_db()

        alter_calls = [s for s in executed_sqls if "ALTER TABLE" in s.upper()]
        assert alter_calls == []


# ---------------------------------------------------------------------------
# 10. check_db_health — healthy path
# ---------------------------------------------------------------------------


class TestCheckDbHealthHealthy:
    """check_db_health returns health dict with server_version when healthy."""

    @pytest.mark.asyncio
    async def test_returns_status_healthy_with_server_version(self):
        from src.database import check_db_health

        mock_db, _ = _make_mock_db_manager()
        mock_db.check_health = AsyncMock(
            return_value={"status": "healthy", "backend": "postgresql"}
        )
        mock_db.engine = MagicMock()

        version_result = MagicMock()
        version_result.scalar = MagicMock(return_value="PostgreSQL 15.1")

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=version_result)

        mock_db.session_maker = MagicMock(
            return_value=_async_cm_session(mock_session)
        )

        with patch("src.database.db", mock_db):
            health = await check_db_health()

        assert health["status"] == "healthy"
        assert health["server_version"] == "PostgreSQL 15.1"

    @pytest.mark.asyncio
    async def test_server_version_key_absent_when_session_execute_raises(self):
        """If the SELECT version() fails, server_version is simply omitted."""
        from src.database import check_db_health

        mock_db, _ = _make_mock_db_manager()
        mock_db.check_health = AsyncMock(
            return_value={"status": "healthy", "backend": "postgresql"}
        )
        mock_db.engine = MagicMock()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))

        mock_db.session_maker = MagicMock(
            return_value=_async_cm_session(mock_session)
        )

        with patch("src.database.db", mock_db):
            health = await check_db_health()

        assert health["status"] == "healthy"
        assert "server_version" not in health


# ---------------------------------------------------------------------------
# 11. check_db_health — unhealthy path
# ---------------------------------------------------------------------------


class TestCheckDbHealthUnhealthy:
    """check_db_health returns health dict without server_version when unhealthy."""

    @pytest.mark.asyncio
    async def test_returns_unhealthy_dict_without_server_version(self):
        from src.database import check_db_health

        mock_db, _ = _make_mock_db_manager()
        mock_db.check_health = AsyncMock(
            return_value={"status": "unhealthy", "error": "connection refused"}
        )
        mock_db.engine = MagicMock()

        with patch("src.database.db", mock_db):
            health = await check_db_health()

        assert health["status"] == "unhealthy"
        assert "server_version" not in health

    @pytest.mark.asyncio
    async def test_returns_dict_when_engine_is_none(self):
        """With engine=None, server_version block is skipped entirely."""
        from src.database import check_db_health

        mock_db, _ = _make_mock_db_manager()
        mock_db.check_health = AsyncMock(
            return_value={"status": "healthy", "backend": "postgresql"}
        )
        mock_db.engine = None  # no engine

        with patch("src.database.db", mock_db):
            health = await check_db_health()

        assert isinstance(health, dict)
        assert "server_version" not in health

    @pytest.mark.asyncio
    async def test_always_returns_a_dict(self):
        from src.database import check_db_health

        mock_db, _ = _make_mock_db_manager()
        mock_db.check_health = AsyncMock(return_value={"status": "degraded"})
        mock_db.engine = None

        with patch("src.database.db", mock_db):
            result = await check_db_health()

        assert isinstance(result, dict)
        assert "status" in result


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _async_cm(conn_mock):
    """Return an async context manager that yields conn_mock (single-use)."""

    @asynccontextmanager
    async def _cm():
        yield conn_mock

    return _cm()


def _make_begin_factory(conn_mock):
    """
    Return a callable that produces a fresh async CM each time it is called.

    database.py calls ``async with db.engine.begin() as conn`` twice (once for
    CREATE SCHEMA, once for the migration block), so ``engine.begin`` must be a
    callable, not a pre-built single-use context manager.
    """

    def _begin():
        @asynccontextmanager
        async def _cm():
            yield conn_mock

        return _cm()

    return _begin


def _async_cm_session(session_mock):
    """Return a callable that, when called, returns an async context manager."""

    class _AsyncCMFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return session_mock

        async def __aexit__(self, *_):
            pass

    return _AsyncCMFactory()
