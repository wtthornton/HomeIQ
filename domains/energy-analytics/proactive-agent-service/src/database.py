"""
Database initialization for Proactive Agent Service

SQLAlchemy 2.0 async patterns for suggestion storage.
PostgreSQL via homeiq_data shared library.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from .config import Settings

logger = logging.getLogger(__name__)

# PostgreSQL configuration
_pg_url = os.getenv("POSTGRES_URL") or ""
_schema = os.getenv("DATABASE_SCHEMA", "energy")


class Base(DeclarativeBase):
    """Base class for database models"""
    pass


# Global engine and session factory
_engine = None
_async_session_maker = None


def get_async_session_maker():
    """
    Get the async session maker.

    Returns:
        The async_sessionmaker instance, or None if not initialized.

    Note:
        This function allows callers to get the current session maker
        even after database initialization, avoiding import-time binding issues.
    """
    return _async_session_maker


async def init_database(settings: Settings):
    """
    Initialize database connection and create tables.

    Args:
        settings: Application settings
    """
    global _engine, _async_session_maker

    from homeiq_data.database_pool import create_pg_engine
    _engine = create_pg_engine(
        database_url=_pg_url,
        schema=_schema,
    )
    logger.info(f"Using PostgreSQL with schema '{_schema}'")

    # Create async session factory
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def get_db() -> AsyncSession:
    """
    Get database session.

    Yields:
        AsyncSession: Database session
    """
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with _async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_database():
    """Close database connections"""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database connections closed")
