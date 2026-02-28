"""
Database initialization and session management for AI Query Service

Epic 39, Story 39.9: Query Service Foundation
PostgreSQL connection pooling via homeiq_data shared library.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from homeiq_data.database_pool import create_pg_engine

from ..config import settings

logger = logging.getLogger(__name__)

# PostgreSQL engine via shared library (schema isolation, real connection pool)
_db_url = settings.effective_database_url

engine = create_pg_engine(
    database_url=_db_url,
    schema=settings.database_schema,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
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

    Commits on success, rolls back on exception.  The ``async with``
    context manager already closes the session when exiting.

    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database connection and verify connectivity."""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise  # Re-raise to fail fast on startup
