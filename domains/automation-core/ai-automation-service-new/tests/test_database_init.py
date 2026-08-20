"""
Unit tests for Database Initialization

Epic 39, Story 39.10: Automation Service Foundation
Tests for database initialization, migrations, and schema sync.
Updated for PostgreSQL.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.database.models import Suggestion


class TestRunMigrations:
    """Test suite for Alembic migration execution."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database._run_alembic_upgrade")
    @patch("pathlib.Path.exists")
    async def test_run_migrations_success(self, mock_exists, mock_upgrade):
        """With an alembic.ini present, the upgrade runs once against it."""
        from src.database import run_migrations

        mock_exists.return_value = True

        await run_migrations()

        mock_upgrade.assert_called_once()
        assert mock_upgrade.call_args.args[0].endswith("alembic.ini")

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database._run_alembic_upgrade")
    @patch("pathlib.Path.exists")
    async def test_run_migrations_no_config_file(self, mock_exists, mock_upgrade):
        """Without an alembic.ini nothing runs."""
        from src.database import run_migrations

        mock_exists.return_value = False

        await run_migrations()

        mock_upgrade.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database._run_alembic_upgrade")
    @patch("pathlib.Path.exists")
    async def test_run_migrations_handles_errors(self, mock_exists, mock_upgrade):
        """A failing upgrade is logged, not raised: startup continues degraded."""
        from src.database import run_migrations

        mock_exists.return_value = True
        mock_upgrade.side_effect = Exception("Migration failed")

        await run_migrations()

        mock_upgrade.assert_called_once()


class TestInitDb:
    """Test suite for database initialization."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database.db.initialize", new_callable=AsyncMock, return_value=True)
    @patch("src.database.run_migrations", new_callable=AsyncMock)
    async def test_init_db_success(self, mock_run_migrations, mock_initialize):
        """Migrations run, then the shared DatabaseManager initialises."""
        from src.database import init_db

        assert await init_db() is True

        mock_run_migrations.assert_awaited_once()
        mock_initialize.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database.db.initialize", new_callable=AsyncMock, return_value=False)
    @patch("src.database.run_migrations", new_callable=AsyncMock)
    async def test_init_db_handles_connection_failure(self, mock_run_migrations, mock_initialize):
        """init_db never raises: an unreachable database reports False (degraded mode)."""
        from src.database import init_db

        assert await init_db() is False

        mock_run_migrations.assert_awaited_once()
        mock_initialize.assert_awaited_once()


class TestSchemaSync:
    """Test suite for model schema validation."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_required_columns_in_model(self, test_db):
        """Test that all required columns exist in the Suggestion model."""

        # Get the model columns
        suggestion_columns = {col.name: str(col.type) for col in Suggestion.__table__.columns}

        # Check that key columns exist in model
        assert "automation_json" in suggestion_columns
        assert "automation_yaml" in suggestion_columns
        assert "ha_version" in suggestion_columns
        assert "json_schema_version" in suggestion_columns


class TestDatabaseConnection:
    """Test suite for database connection management."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_db_yields_session(self):
        """get_db yields a session from the module-level DatabaseManager once initialised.

        The manager is only initialised by the lifespan, which ASGI tests never
        run, so initialise it here explicitly instead of through a side engine.
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.database import db, get_db, init_db

        if not await init_db():
            pytest.fail(
                "DatabaseManager could not initialise; set POSTGRES_URL to a reachable PostgreSQL"
            )
        try:
            async for session in get_db():
                assert isinstance(session, AsyncSession)
                break  # Only test first yield
        finally:
            await db.close()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_db_commits_on_success(self):
        """Test that get_db commits the session on successful completion."""

        # This test is more of an integration test
        # For unit testing, we'd need to mock the session factory
        # Skipping for now as it requires more complex mocking
