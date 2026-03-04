"""Database connection and session management for Blueprint Index Service.

PostgreSQL via homeiq_data DatabaseManager (standardized lifecycle).
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from homeiq_data import DatabaseManager
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Schema configuration
_schema = os.getenv("DATABASE_SCHEMA", "blueprints")

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=_schema,
    service_name="blueprint-index",
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    auto_commit_sessions=True,
)

# Module-level aliases for backwards compatibility
engine = None
async_session_maker = None


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


async def close_db():
    """Close database connections."""
    await db.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with db.get_db() as session:
        yield session


@asynccontextmanager
async def get_db_context():
    """Context manager for database sessions."""
    async with db.get_db_context() as session:
        yield session
