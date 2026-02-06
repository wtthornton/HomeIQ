"""
Device Intelligence Service - Database Connection

Simple database connection and session management for SQLite.
"""

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import Settings
from ..models.database import Base

logger = logging.getLogger(__name__)

# Global database engine and session factory
_engine = None
_session_factory = None

def get_database_url(settings: Settings) -> str:
    """Get database URL from settings."""
    # Convert SQLite URL to async SQLite URL
    db_url = settings.get_database_url()
    if db_url.startswith("sqlite:///"):
        # Ensure database directory exists
        db_path = db_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Database directory ensured: {db_dir}")
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    return db_url

async def initialize_database(settings: Settings):
    """Initialize database connection and create tables."""
    global _engine, _session_factory

    database_url = get_database_url(settings)
    _engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL logging
        future=True
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Test connection
    async with _engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    logger.info("Database connection initialized and tables created successfully")

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized")

    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_database():
    """Close database connection."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")

async def recreate_tables():
    """Drop all tables and recreate them with new schema."""
    global _engine
    if not _engine:
        raise RuntimeError("Database not initialized")

    logger.info("Recreating database tables")

    # Drop all existing tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, checkfirst=True)

    # Create all tables with updated schema
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    logger.info("Database tables recreated successfully")
