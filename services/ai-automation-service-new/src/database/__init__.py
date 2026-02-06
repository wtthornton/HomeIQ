"""
Database initialization and connection management

Epic 39, Story 39.10: Automation Service Foundation
Database connection pooling for shared SQLite database.
"""

import asyncio
import logging
import os
import sys
from functools import partial
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from ..config import settings

logger = logging.getLogger("ai-automation-service")

# Create async engine with connection pooling
# SQLite doesn't support pool_size/max_overflow - use StaticPool only
if "sqlite" in settings.database_url:
    # SQLite configuration (no pool_size/max_overflow)
    # CRITICAL: Configure PRAGMA settings for optimal performance
    engine = create_async_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0,  # 30 second timeout for database operations
        },
        echo=False,
    )
    
    # Set PRAGMA settings on connection pool initialization
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite PRAGMA settings for optimal performance."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrent reads
        cursor.execute("PRAGMA synchronous=NORMAL")  # Fast writes, survives OS crash
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
        cursor.execute("PRAGMA temp_store=MEMORY")  # Fast temp tables
        cursor.execute("PRAGMA foreign_keys=ON")  # Referential integrity
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s lock wait (vs fail immediately)
        cursor.close()
else:
    # PostgreSQL/MySQL configuration (supports pooling)
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,
    )

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.

    M9 fix: No longer auto-commits. Service methods should manage their own
    transactions explicitly via session.commit(). The session auto-rolls back
    on exception and closes in the finally block.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _run_alembic_upgrade(alembic_ini_path: str) -> None:
    """Run Alembic upgrade synchronously (called from thread executor)."""
    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


async def run_migrations():
    """
    Run Alembic migrations to ensure database schema is up to date.

    M8 fix: Runs the synchronous Alembic command in a thread executor
    to avoid blocking the async event loop.
    """
    try:
        # Get the service directory (parent of src/)
        service_dir = Path(__file__).parent.parent.parent
        alembic_ini_path = service_dir / "alembic.ini"

        if not alembic_ini_path.exists():
            logger.warning(f"Alembic config not found at {alembic_ini_path}, skipping migrations")
            return

        # Run migrations in a thread executor to avoid blocking the event loop
        logger.info("Running Alembic migrations...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_alembic_upgrade, str(alembic_ini_path))
        logger.info("Alembic migrations completed")
    except Exception as e:
        logger.error(f"Failed to run Alembic migrations: {e}", exc_info=True)
        # Don't raise - fallback to manual schema sync
        logger.warning("Will attempt manual schema sync as fallback")


async def init_db():
    """
    Initialize database connection and verify connectivity.
    
    This function:
    1. Runs Alembic migrations to ensure schema is up to date
    2. Tests database connectivity
    3. Performs manual schema sync as fallback (adds missing columns)
    """
    try:
        # Step 1: Run Alembic migrations first
        await run_migrations()
        
        # Step 2: Test connection and perform manual schema sync (fallback)
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
            
            # Check if suggestions table exists and create/add columns if needed
            # This handles schema mismatch between model and existing database
            # (fallback in case migrations didn't run or missed something)
            result = await conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='suggestions'
            """))
            table_exists = result.scalar() is not None
            
            if not table_exists:
                # Create table if it doesn't exist (using Base.metadata)
                logger.info("Creating suggestions table (table doesn't exist)")
                from .models import Base
                # Create all tables defined in Base.metadata
                await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn))
                logger.info("✅ Created suggestions table")
            else:
                # Table exists - check which columns exist and add missing ones
                result = await conn.execute(text("PRAGMA table_info(suggestions)"))
                columns = result.fetchall()
                column_names = [col[1] for col in columns]  # Column name is at index 1
                
                # List of required columns from the model
                # Note: SQLite doesn't have native DATETIME type, uses TEXT for datetime columns
                required_columns = {
                    'description': 'TEXT',
                    'automation_json': 'TEXT',  # JSON stored as TEXT in SQLite
                    'automation_yaml': 'TEXT',
                    'ha_version': 'TEXT',
                    'json_schema_version': 'TEXT',
                    'automation_id': 'TEXT',  # VARCHAR in SQLite is same as TEXT
                    'deployed_at': 'TEXT',  # SQLite stores datetime as TEXT
                    'confidence_score': 'REAL',
                    'safety_score': 'REAL',
                    'user_feedback': 'TEXT',  # VARCHAR in SQLite is same as TEXT
                    'feedback_at': 'TEXT',  # SQLite stores datetime as TEXT
                    # Hybrid Flow Integration columns (Epic 39 - Hybrid Flow)
                    'plan_id': 'TEXT',  # Link to plans table
                    'compiled_id': 'TEXT',  # Link to compiled_artifacts table
                    'deployment_id': 'TEXT'  # Link to deployments table
                }
                
                # Add missing columns
                for col_name, col_type in required_columns.items():
                    if col_name not in column_names:
                        logger.info(f"Adding missing '{col_name}' column to suggestions table")
                        try:
                            await conn.execute(text(f"""
                                ALTER TABLE suggestions 
                                ADD COLUMN {col_name} {col_type}
                            """))
                            logger.info(f"✅ Added '{col_name}' column to suggestions table")
                        except Exception as e:
                            logger.warning(f"Failed to add column '{col_name}': {e}")
            
        logger.info("✅ Database connection initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise  # Re-raise to fail fast on startup

