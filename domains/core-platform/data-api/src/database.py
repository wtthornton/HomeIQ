"""
Database Configuration for Data API Service

Supports dual-mode operation:
- PostgreSQL (asyncpg) with schema isolation via homeiq_data shared library
- SQLite (aiosqlite) with WAL mode for local/dev fallback

Mode is auto-detected from DATABASE_URL prefix.
"""

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/metadata.db")
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "core")
SQLITE_TIMEOUT = int(os.getenv("SQLITE_TIMEOUT", "30"))
SQLITE_CACHE_SIZE = int(os.getenv("SQLITE_CACHE_SIZE", "-64000"))  # 64MB

# Detect database backend
_is_postgres = DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith(
    "postgres"
)

# Create async engine based on backend
if _is_postgres:
    from homeiq_data.database_pool import create_pg_engine

    async_engine: AsyncEngine = create_pg_engine(
        database_url=DATABASE_URL,
        schema=DATABASE_SCHEMA,
        pool_size=10,
        max_overflow=5,
    )
else:
    async_engine: AsyncEngine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={
            "timeout": SQLITE_TIMEOUT,
        },
    )

    @event.listens_for(async_engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        """
        Set SQLite pragmas on each connection for optimal performance.

        Pragmas configured:
        - WAL mode: Better concurrency (multiple readers, one writer)
        - NORMAL sync: Faster writes, still safe (survives OS crash)
        - 64MB cache: Improves query performance
        - Memory temp tables: Faster temporary operations
        - Foreign keys ON: Enforce referential integrity
        - 30s busy timeout: Wait for locks instead of immediate fail
        """
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute(f"PRAGMA cache_size={SQLITE_CACHE_SIZE}")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_TIMEOUT * 1000}")
            logger.debug("SQLite pragmas configured successfully")
        except Exception as e:
            logger.error(f"Failed to set SQLite pragmas: {e}")
            raise
        finally:
            cursor.close()


# Session factory for creating async sessions
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Schema-aware metadata for PostgreSQL; plain metadata for SQLite
_metadata = MetaData(schema=DATABASE_SCHEMA) if _is_postgres else MetaData()


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

    For PostgreSQL, ensures the target schema exists first.
    Called during application startup.
    Note: In production, use Alembic migrations instead.
    """
    async with async_engine.begin() as conn:
        if _is_postgres:
            await conn.execute(
                text(f"CREATE SCHEMA IF NOT EXISTS {DATABASE_SCHEMA}")
            )
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def check_db_health() -> dict:
    """
    Check database health and return status information.

    Returns backend-appropriate metrics:
    - PostgreSQL: pool stats, schema, server version
    - SQLite: journal mode, WAL status, database size
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            if _is_postgres:
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

            # SQLite health checks
            journal_result = await session.execute(text("PRAGMA journal_mode"))
            journal_mode = journal_result.scalar()

            page_count_result = await session.execute(text("PRAGMA page_count"))
            page_count = page_count_result.scalar() or 0

            page_size_result = await session.execute(text("PRAGMA page_size"))
            page_size = page_size_result.scalar() or 4096

            db_size_mb = (page_count * page_size) / (1024 * 1024)

            return {
                "status": "healthy",
                "backend": "sqlite",
                "journal_mode": journal_mode,
                "database_size_mb": round(db_size_mb, 2),
                "wal_enabled": journal_mode == "wal",
                "connection": "ok",
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "backend": "postgresql" if _is_postgres else "sqlite",
            "connection": str(e),
        }


# Log database configuration on module import
if _is_postgres:
    logger.info(f"PostgreSQL database configured: schema={DATABASE_SCHEMA}")
else:
    logger.info(f"SQLite database configured: {DATABASE_URL}")
    logger.info(
        f"Cache size: {abs(SQLITE_CACHE_SIZE) // 1024}MB, Timeout: {SQLITE_TIMEOUT}s"
    )
