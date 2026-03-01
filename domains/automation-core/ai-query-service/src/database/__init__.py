"""
Database initialization and session management for AI Query Service

Epic 39, Story 39.9: Query Service Foundation
PostgreSQL connection pooling via homeiq_data DatabaseManager.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from homeiq_data import DatabaseManager

from ..config import settings

logger = logging.getLogger(__name__)

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=settings.database_schema,
    service_name="ai-query-service",
    database_url=settings.effective_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    auto_commit_sessions=True,
)

# Module-level aliases for backwards compatibility
engine = None
async_session_maker = None


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.

    Commits on success, rolls back on exception.
    """
    async with db.get_db() as session:
        yield session


async def init_db() -> bool:
    """
    Initialize database connection and verify connectivity.

    Returns True if successful, False if degraded. Never raises.
    """
    global engine, async_session_maker
    result = await db.initialize()
    engine = db.engine
    async_session_maker = db.session_maker
    return result
