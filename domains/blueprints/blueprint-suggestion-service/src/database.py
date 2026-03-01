"""Database connection and session management for Blueprint Suggestion Service.

PostgreSQL via homeiq_data DatabaseManager (standardized lifecycle).
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from homeiq_data import DatabaseManager

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Schema configuration
_schema = os.getenv("DATABASE_SCHEMA", "blueprints")

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=_schema,
    service_name="blueprint-suggestion-service",
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    auto_commit_sessions=True,
)

# Module-level aliases for backwards compatibility
engine = None
async_session_maker = None


async def run_alembic_migrations():
    """Run Alembic migrations to ensure database schema is up to date."""
    try:
        container_path = Path("/app/alembic.ini")
        calculated_path = Path(__file__).parent.parent.parent / "alembic.ini"

        alembic_ini_path = None
        if container_path.exists():
            alembic_ini_path = container_path
        elif calculated_path.exists():
            alembic_ini_path = calculated_path
        else:
            logger.warning("Alembic config not found, skipping migrations")
            return False

        logger.info("Running Alembic migrations...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_alembic_sync, str(alembic_ini_path))
        logger.info("Alembic migrations completed")
        return True
    except Exception as e:
        logger.error("Failed to run Alembic migrations: %s", e, exc_info=True)
        logger.warning("Will attempt manual schema sync as fallback")
        return False


def _run_alembic_sync(alembic_ini_path: str) -> None:
    """Run Alembic upgrade synchronously."""
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


async def _run_manual_migrations(conn):
    """Fallback: Run manual database migrations to add missing columns."""
    logger.info("Running PostgreSQL manual migrations...")
    await conn.execute(text("""
        ALTER TABLE blueprint_suggestions
        ADD COLUMN IF NOT EXISTS blueprint_name VARCHAR(255)
    """))
    await conn.execute(text("""
        ALTER TABLE blueprint_suggestions
        ADD COLUMN IF NOT EXISTS blueprint_description TEXT
    """))
    logger.info("PostgreSQL manual migrations completed")


async def check_schema_version(db_session: AsyncSession) -> bool:
    """Check if database schema matches the model."""
    try:
        result = await db_session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'blueprint_suggestions'
        """))
        columns = {row[0] for row in result.fetchall()}
        required_columns = {
            "id", "blueprint_id", "blueprint_name", "blueprint_description",
            "suggestion_score", "matched_devices", "use_case", "status",
            "created_at", "updated_at", "accepted_at", "declined_at", "conversation_id"
        }
        return required_columns.issubset(columns)
    except Exception as e:
        logger.error("Failed to check schema version: %s", e, exc_info=True)
        return False


async def init_db() -> bool:
    """
    Initialize database tables and run migrations.

    Returns True if successful, False if degraded. Never raises.
    """
    global engine, async_session_maker

    # Step 1: Try Alembic migrations first
    alembic_success = await run_alembic_migrations()

    # Step 2: Initialize via DatabaseManager (creates engine, tests connection, creates tables)
    result = await db.initialize(base=Base)
    engine = db.engine
    async_session_maker = db.session_maker

    # Step 3: Run manual migrations as fallback if Alembic failed
    if result and not alembic_success and db.engine is not None:
        try:
            async with db.engine.begin() as conn:
                await _run_manual_migrations(conn)
        except Exception as e:
            logger.error("Manual migrations failed: %s", e, exc_info=True)

    return result


async def close_db():
    """Close database connections."""
    await db.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with db.get_db() as session:
        yield session


async def get_db_context():
    """Context manager for database sessions."""
    async with db.get_db_context() as session:
        yield session
