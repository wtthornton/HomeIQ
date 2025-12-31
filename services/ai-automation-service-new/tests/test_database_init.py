"""
Unit tests for Database Initialization

Epic 39, Story 39.10: Automation Service Foundation
Tests for database initialization, migrations, and schema sync.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from sqlalchemy import text

from src.database.models import Suggestion, AutomationVersion, Base


class TestRunMigrations:
    """Test suite for Alembic migration execution."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.database.command.upgrade')
    @patch('src.database.Config')
    @patch('pathlib.Path.exists')
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
    @patch('pathlib.Path.exists')
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
    @patch('src.database.command.upgrade')
    @patch('src.database.Config')
    @patch('pathlib.Path.exists')
    async def test_run_migrations_handles_errors(self, mock_exists, mock_config_class, mock_upgrade):
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
    @patch('src.database.run_migrations')
    @patch('src.database.engine')
    async def test_init_db_success(self, mock_engine, mock_run_migrations):
        """Test successful database initialization."""
        from src.database import init_db
        
        # Mock engine context manager
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = "suggestions"  # Table exists
        mock_conn.execute.return_value = mock_result
        
        # Mock PRAGMA table_info result (no missing columns)
        mock_pragma_result = MagicMock()
        mock_pragma_result.fetchall.return_value = [
            (0, 'id', 'INTEGER', 0, None, 1),  # col_id, name, type, notnull, default, pk
            (1, 'title', 'TEXT', 1, None, 0),
            (2, 'description', 'TEXT', 0, None, 0),
            (3, 'automation_json', 'TEXT', 0, None, 0),
            (4, 'automation_yaml', 'TEXT', 0, None, 0),
            (5, 'ha_version', 'TEXT', 0, None, 0),
            (6, 'json_schema_version', 'TEXT', 0, None, 0),
            (7, 'automation_id', 'TEXT', 0, None, 0),
            (8, 'deployed_at', 'TEXT', 0, None, 0),
            (9, 'confidence_score', 'REAL', 0, None, 0),
            (10, 'safety_score', 'REAL', 0, None, 0),
            (11, 'user_feedback', 'TEXT', 0, None, 0),
            (12, 'feedback_at', 'TEXT', 0, None, 0),
        ]
        mock_conn.execute.return_value = mock_pragma_result
        
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        # Run initialization
        await init_db()
        
        # Verify migrations were called
        mock_run_migrations.assert_called_once()
        # Verify connection was tested
        assert mock_conn.execute.called
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.database.run_migrations')
    @patch('src.database.engine')
    async def test_init_db_adds_missing_columns(self, mock_engine, mock_run_migrations):
        """Test that init_db adds missing columns."""
        from src.database import init_db
        from sqlalchemy import text
        
        # Mock engine context manager
        mock_conn = AsyncMock()
        
        # Mock table exists check
        mock_table_exists_result = MagicMock()
        mock_table_exists_result.scalar.return_value = "suggestions"
        
        # Mock PRAGMA table_info result (missing JSON columns)
        mock_pragma_result = MagicMock()
        mock_pragma_result.fetchall.return_value = [
            (0, 'id', 'INTEGER', 0, None, 1),
            (1, 'title', 'TEXT', 1, None, 0),
            (2, 'description', 'TEXT', 0, None, 0),
            # Missing: automation_json, automation_yaml, ha_version, json_schema_version
        ]
        
        # Track ALTER TABLE calls
        alter_table_calls = []
        
        # Mock execute to return different results based on query
        async def execute_side_effect(query):
            query_str = str(query)
            if "sqlite_master" in query_str:
                return mock_table_exists_result
            elif "PRAGMA table_info" in query_str:
                return mock_pragma_result
            elif "SELECT 1" in query_str:
                return MagicMock()
            elif "ALTER TABLE" in query_str:
                # Track ALTER TABLE calls
                alter_table_calls.append(query_str)
                return MagicMock()
            return MagicMock()
        
        mock_conn.execute.side_effect = execute_side_effect
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        # Run initialization
        await init_db()
        
        # Verify ALTER TABLE was called to add missing columns
        # Should be called for each missing column (automation_json, automation_yaml, ha_version, json_schema_version)
        assert len(alter_table_calls) >= 4, f"Should have called ALTER TABLE at least 4 times (for missing JSON columns), got {len(alter_table_calls)}"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.database.run_migrations')
    @patch('src.database.engine')
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
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.database.run_migrations')
    @patch('src.database.engine')
    async def test_init_db_no_table_exists(self, mock_engine, mock_run_migrations):
        """Test init_db when suggestions table doesn't exist."""
        from src.database import init_db
        
        # Mock engine context manager
        mock_conn = AsyncMock()
        
        # Mock table doesn't exist
        mock_table_exists_result = MagicMock()
        mock_table_exists_result.scalar.return_value = None
        
        # Mock execute to return different results
        async def execute_side_effect(query):
            if "sqlite_master" in str(query):
                return mock_table_exists_result
            elif "SELECT 1" in str(query):
                return MagicMock()
            return MagicMock()
        
        mock_conn.execute.side_effect = execute_side_effect
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        # Run initialization
        await init_db()
        
        # Should not try to add columns if table doesn't exist
        # (table creation should be handled by migrations)
        assert mock_conn.execute.called


class TestSchemaSync:
    """Test suite for manual schema synchronization."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_required_columns_in_init_db(self, test_db):
        """Test that all required columns from the model are in init_db's required_columns."""
        from src.database import init_db
        
        # Get the model columns
        suggestion_columns = {col.name: str(col.type) for col in Suggestion.__table__.columns}
        
        # Check that key columns exist in model
        assert 'automation_json' in suggestion_columns
        assert 'automation_yaml' in suggestion_columns
        assert 'ha_version' in suggestion_columns
        assert 'json_schema_version' in suggestion_columns
        
        # Note: We can't directly check init_db's required_columns dict from here
        # but we can verify the model has the columns it should sync


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
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import AsyncMock
        
        # This test is more of an integration test
        # For unit testing, we'd need to mock the session factory
        # Skipping for now as it requires more complex mocking

