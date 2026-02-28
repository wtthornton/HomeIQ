"""
Database Session Management

Provides async database session factory and initialization.
PostgreSQL via homeiq_data shared library.
"""

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from homeiq_data.database_pool import create_pg_engine

from ..config import settings

logger = logging.getLogger(__name__)

# Base class for database models
Base = declarative_base()

# PostgreSQL configuration
_pg_url = os.getenv("POSTGRES_URL") or ""
_schema = os.getenv("DATABASE_SCHEMA", "rag")

engine = create_pg_engine(
    database_url=_pg_url,
    schema=_schema,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.

    Usage in FastAPI:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...

    Returns:
        AsyncSession: Database session
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database (create tables).

    Called on service startup to ensure database tables exist.

    Raises:
        Exception: If database initialization fails
    """
    logger.info(f"Initializing database: {settings.database_path}")

    try:
        from sqlalchemy import text

        # Test connection first
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        # Import models to ensure they're registered with Base
        from .models import RAGKnowledge  # noqa: F401

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn))

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
