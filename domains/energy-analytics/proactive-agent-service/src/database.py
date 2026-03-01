"""
Database initialization for Proactive Agent Service

PostgreSQL via homeiq_data DatabaseManager (standardized lifecycle).
"""

from __future__ import annotations

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from homeiq_data import DatabaseManager

from .config import Settings

logger = logging.getLogger(__name__)

# Schema configuration
_schema = os.getenv("DATABASE_SCHEMA", "energy")


class Base(DeclarativeBase):
    """Base class for database models"""
    pass


# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=_schema,
    service_name="proactive-agent-service",
    auto_commit_sessions=False,
)

# Module-level aliases for backwards compatibility
engine = None
_async_session_maker = None


def get_async_session_maker():
    """Get the async session maker."""
    return db.session_maker


async def init_database(settings: Settings) -> bool:
    """
    Initialize database connection and create tables.

    Returns True if successful, False if degraded. Never raises.
    """
    global engine, _async_session_maker
    result = await db.initialize(base=Base)
    engine = db.engine
    _async_session_maker = db.session_maker
    logger.info("Using PostgreSQL with schema '%s'", _schema)
    return result


async def get_db() -> AsyncSession:
    """Get database session (FastAPI dependency)."""
    async with db.get_db() as session:
        yield session


async def close_database():
    """Close database connections."""
    await db.close()
