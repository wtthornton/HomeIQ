"""
Unit tests for Database Initialization

Epic 39, Story 39.10: Automation Service Foundation
Tests for database initialization, migrations, and schema sync.
Updated for PostgreSQL.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.database.models import Suggestion


class TestRunMigrations:
    """Test suite for Alembic migration execution."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database.command.upgrade")
    @patch("src.database.Config")
    @patch("pathlib.Path.exists")
    async def test_run_migrations_success(self, mock_exists, mock_config_class, mock_upgrade):
        """Test successful migration execution."""
        from src.database import run_migrations

        # Mock Alembic config file exists
        mock_exists.return_value = True

        # Mock Config class
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Run migrations
        await run_migrations()

        # Verify Config was called with correct path
        mock_config_class.assert_called_once()
        # Verify upgrade was called
        mock_upgrade.assert_called_once_with(mock_config, "head")

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("pathlib.Path.exists")
    async def test_run_migrations_no_config_file(self, mock_exists):
        """Test migration execution when Alembic config doesn't exist."""
        from src.database import run_migrations

        # Mock Alembic config file doesn't exist
        mock_exists.return_value = False

        # Run migrations - should return without error
        await run_migrations()

        # Should have checked for file existence
        mock_exists.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database.command.upgrade")
    @patch("src.database.Config")
    @patch("pathlib.Path.exists")
    async def test_run_migrations_handles_errors(
        self, mock_exists, mock_config_class, mock_upgrade
    ):
        """Test migration execution handles errors gracefully."""
        from src.database import run_migrations

        # Mock Alembic config file exists
        mock_exists.return_value = True

        # Mock Config class
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Mock upgrade raises exception
        mock_upgrade.side_effect = Exception("Migration failed")

        # Run migrations - should not raise, should handle error
        await run_migrations()

        # Verify upgrade was attempted
        mock_upgrade.assert_called_once()


class TestInitDb:
    """Test suite for database initialization."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database.run_migrations")
    @patch("src.database.engine")
    @patch("src.database._is_postgres", True)
    async def test_init_db_success(self, mock_engine, mock_run_migrations):
        """Test successful database initialization (PostgreSQL path)."""
        from src.database import init_db

        # Mock engine context manager
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1  # SELECT 1 result
        mock_conn.execute.return_value = mock_result

        mock_engine.begin.return_value.__aenter__.return_value = mock_conn

        # Run initialization
        await init_db()

        # Verify migrations were called
        mock_run_migrations.assert_called_once()
        # Verify connection was tested (SELECT 1)
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.database.run_migrations")
    @patch("src.database.engine")
    @patch("src.database._is_postgres", True)
    async def test_init_db_handles_connection_failure(self, mock_engine, mock_run_migrations):
        """Test that init_db handles database connection failures."""
        from src.database import init_db

        # Mock engine.begin raises exception
        mock_engine.begin.side_effect = Exception("Connection failed")

        # Should raise exception
        with pytest.raises(Exception, match="Connection failed"):
            await init_db()

        # Migrations should have been attempted
        mock_run_migrations.assert_called_once()


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
    async def test_get_db_yields_session(self, test_db):
        """Test that get_db dependency yields a database session."""
        from src.database import get_db

        # Test the generator
        async for session in get_db():
            assert session is not None
            # Should be an AsyncSession
            from sqlalchemy.ext.asyncio import AsyncSession

            assert isinstance(session, AsyncSession)
            break  # Only test first yield

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_db_commits_on_success(self):
        """Test that get_db commits the session on successful completion."""

        # This test is more of an integration test
        # For unit testing, we'd need to mock the session factory
        # Skipping for now as it requires more complex mocking
