"""
Database initialization for Proactive Agent Service

SQLAlchemy 2.0 async patterns for suggestion storage.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import Settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for database models"""
    pass


# Global engine and session factory
_engine = None
_async_session_maker = None


async def init_database(settings: Settings):
    """
    Initialize database connection and create tables.

    Args:
        settings: Application settings
    """
    global _engine, _async_session_maker

    # Ensure data directory exists
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = Path(db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create async engine
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.log_level == "DEBUG",
        future=True,
    )

    # SQLite-specific optimizations
    @event.listens_for(_engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite pragmas for better performance"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

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

