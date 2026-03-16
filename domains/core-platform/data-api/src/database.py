"""
Database Configuration for Data API Service

PostgreSQL (asyncpg) with schema isolation via homeiq_data DatabaseManager.
"""

import logging
import os
from collections.abc import AsyncGenerator

from homeiq_data import DatabaseManager
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "core")

# Schema-aware metadata for PostgreSQL
_metadata = MetaData(schema=DATABASE_SCHEMA)

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=DATABASE_SCHEMA,
    service_name="data-api",
    database_url=DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    auto_commit_sessions=True,
)


from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = _metadata


# Module-level aliases for backwards compatibility
async_engine = None
AsyncSessionLocal = None


# FastAPI dependency for database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Automatically handles:
    - Session creation
    - Transaction commit on success
    - Transaction rollback on error
    - Session cleanup
    """
    async with db.get_db() as session:
        yield session


async def init_db() -> bool:
    """
    Initialize database by creating all tables.

    Ensures the target schema exists first.
    Returns True if successful, False if degraded. Never raises.
    """
    global async_engine, AsyncSessionLocal

    result = await db.initialize(base=Base)
    async_engine = db.engine
    AsyncSessionLocal = db.session_maker

    # Create schema if it doesn't exist (data-api specific)
    if result and db.engine is not None:
        try:
            async with db.engine.begin() as conn:
                await conn.execute(
                    text(f"CREATE SCHEMA IF NOT EXISTS {DATABASE_SCHEMA}")
                )
        except Exception as e:
            logger.error("Failed to create schema: %s", e)

        # Migrate timestamp columns to TIMESTAMP WITH TIME ZONE (migration 010)
        # Fixes: asyncpg DataError mixing offset-aware datetimes with naive columns
        try:
            async with db.engine.begin() as conn:
                # Check if migration is needed (only run if columns are still naive)
                row = await conn.execute(text(
                    "SELECT data_type FROM information_schema.columns "
                    f"WHERE table_schema='{DATABASE_SCHEMA}' "
                    "AND table_name='devices' AND column_name='last_seen'"
                ))
                col_type = row.scalar()
                if col_type and "without" in col_type.lower():
                    logger.info("Running migration 010: converting timestamp columns to timezone-aware")
                    for tbl, col in [
                        ("devices", "last_seen"),
                        ("devices", "created_at"),
                        ("devices", "last_capability_sync"),
                        ("entities", "created_at"),
                        ("entities", "updated_at"),
                    ]:
                        await conn.execute(text(
                            f"ALTER TABLE {DATABASE_SCHEMA}.{tbl} "
                            f"ALTER COLUMN {col} TYPE TIMESTAMP WITH TIME ZONE "
                            f"USING {col} AT TIME ZONE 'UTC'"
                        ))
                    logger.info("Migration 010 complete: all timestamp columns are now timezone-aware")
        except Exception as e:
            logger.warning("Timestamp timezone migration skipped: %s", e)

    return result


async def check_db_health() -> dict:
    """Check database health and return status information."""
    health = await db.check_health()
    # Add data-api specific fields
    if health.get("status") == "healthy" and db.engine is not None:
        try:
            async with db.session_maker() as session:
                version_result = await session.execute(text("SELECT version()"))
                health["server_version"] = version_result.scalar()
        except Exception:
            pass
    return health


# Log database configuration on module import
logger.info("PostgreSQL database configured: schema=%s", DATABASE_SCHEMA)
