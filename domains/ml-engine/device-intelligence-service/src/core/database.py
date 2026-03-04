"""
Device Intelligence Service - Database Connection

PostgreSQL database connection and session management
via homeiq_data DatabaseManager (standardized lifecycle).
"""

import logging
import os
from collections.abc import AsyncGenerator

from homeiq_data import DatabaseManager
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.database import Base

logger = logging.getLogger(__name__)

# Schema configuration
_schema = os.getenv("DATABASE_SCHEMA", "devices")

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=_schema,
    service_name="device-intelligence-service",
    auto_commit_sessions=False,
)

# Module-level aliases for backwards compatibility
engine = None
_session_factory = None


async def initialize_database(_settings: Settings) -> bool:
    """
    Initialize database connection and create tables.

    Returns True if successful, False if degraded. Never raises.
    """
    global engine, _session_factory
    result = await db.initialize(base=Base)
    engine = db.engine
    _session_factory = db.session_maker
    return result


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with db.get_db() as session:
        yield session


async def close_database():
    """Close database connection."""
    await db.close()


async def recreate_tables():
    """Drop all tables and recreate them with new schema."""
    if not db.available or db.engine is None:
        raise RuntimeError("Database not initialized")

    logger.info("Recreating database tables")

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, checkfirst=True)

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    logger.info("Database tables recreated successfully")
