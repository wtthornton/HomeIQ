"""Database connection and session management for Blueprint Index Service."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from homeiq_data.database_pool import create_pg_engine

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# PostgreSQL configuration
_db_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL", "")
_schema = os.getenv("DATABASE_SCHEMA", "blueprints")

# Create async engine (PostgreSQL only)
engine = create_pg_engine(
    database_url=_db_url,
    schema=_schema,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initialize database tables."""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")


async def close_db():
    """Close database connections."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
