"""
Database Configuration for Data API Service

PostgreSQL (asyncpg) with schema isolation via homeiq_data shared library.
"""

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from homeiq_data.database_pool import create_pg_engine

logger = logging.getLogger(__name__)

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "core")

# Create async engine (PostgreSQL only)
async_engine: AsyncEngine = create_pg_engine(
    database_url=DATABASE_URL,
    schema=DATABASE_SCHEMA,
    pool_size=10,
    max_overflow=5,
)

# Session factory for creating async sessions
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Schema-aware metadata for PostgreSQL
_metadata = MetaData(schema=DATABASE_SCHEMA)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = _metadata


# FastAPI dependency for database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Automatically handles:
    - Session creation
    - Transaction commit on success
    - Transaction rollback on error
    - Session cleanup
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database by creating all tables.

    Ensures the target schema exists first.
    Called during application startup.
    Note: In production, use Alembic migrations instead.
    """
    async with async_engine.begin() as conn:
        await conn.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {DATABASE_SCHEMA}")
        )
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def check_db_health() -> dict:
    """
    Check database health and return status information.

    Returns PostgreSQL pool stats, schema, and server version.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            version_result = await session.execute(text("SELECT version()"))
            pg_version = version_result.scalar()

            pool = async_engine.pool
            return {
                "status": "healthy",
                "backend": "postgresql",
                "schema": DATABASE_SCHEMA,
                "server_version": pg_version,
                "pool_size": pool.size(),
                "pool_checked_in": pool.checkedin(),
                "pool_checked_out": pool.checkedout(),
                "pool_overflow": pool.overflow(),
                "connection": "ok",
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "backend": "postgresql",
            "connection": str(e),
        }


# Log database configuration on module import
logger.info(f"PostgreSQL database configured: schema={DATABASE_SCHEMA}")
