"""Database configuration using SQLAlchemy 2.0 async patterns

PostgreSQL via homeiq_data DatabaseManager (standardized lifecycle).
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from homeiq_data import DatabaseManager

from .config import get_settings

settings = get_settings()

# Schema configuration
_schema = os.getenv("DATABASE_SCHEMA", "devices")

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=_schema,
    service_name="ha-setup-service",
    auto_commit_sessions=False,
)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


# Module-level aliases for backwards compatibility
engine = None
async_session_maker = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI endpoints to get database session."""
    async with db.get_db() as session:
        yield session


async def init_db() -> bool:
    """
    Initialize database tables.

    Returns True if successful, False if degraded. Never raises.
    """
    global engine, async_session_maker
    result = await db.initialize(base=Base)
    engine = db.engine
    async_session_maker = db.session_maker
    return result
