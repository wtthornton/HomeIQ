"""
Database initialization and connection management

Epic 39, Story 39.5: Pattern Service Foundation
PostgreSQL connection pooling via homeiq_data DatabaseManager.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from homeiq_data import DatabaseManager

from ..config import settings

logger = logging.getLogger("ai-pattern-service")

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=settings.database_schema,
    service_name="ai-pattern-service",
    database_url=settings.effective_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    auto_commit_sessions=True,
)

# Module-level aliases for backwards compatibility
engine = None
AsyncSessionLocal = None


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
    global engine, AsyncSessionLocal
    from .models import Base  # noqa: F401 - imported for side-effect registration

    result = await db.initialize(base=Base)
    engine = db.engine
    AsyncSessionLocal = db.session_maker
    return result
