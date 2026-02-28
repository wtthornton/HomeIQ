"""
Database initialization and connection management

Epic 39, Story 39.1: Training Service Foundation
PostgreSQL connection pooling via homeiq_data shared library.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from homeiq_data.database_pool import create_pg_engine

from ..config import settings

logger = logging.getLogger("ai-training-service")

# PostgreSQL engine via shared library (schema isolation, real connection pool)
_db_url = settings.effective_database_url

engine = create_pg_engine(
    database_url=_db_url,
    schema=settings.database_schema,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.

    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database connection and verify connectivity"""
    try:
        # Import database models to ensure they're registered
        from sqlalchemy import text

        from .models import Base  # noqa: F401

        # Create tables if they don't exist (for shared database, this may already exist)
        # We'll just test connectivity
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
        logger.info(f"Database initialized: {settings.database_path}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
