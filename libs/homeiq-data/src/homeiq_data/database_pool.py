"""
Shared Database Connection Pool Utilities

Epic 39, Story 39.11: Shared Infrastructure Setup
Utilities for managing shared database connections across microservices.
Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

import os

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from .logging_config import get_logger

logger = get_logger(__name__)


# Global engine instances (one per database path)
_engines: dict[str, AsyncEngine] = {}
_session_makers: dict[str, async_sessionmaker] = {}


def _is_postgres_url(url: str) -> bool:
    """Check if a database URL is for PostgreSQL."""
    return url.startswith("postgresql") or url.startswith("postgres")


def create_shared_db_engine(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 5,
    database_path: str | None = None,
) -> AsyncEngine:
    """
    Create or get a shared database engine for connection pooling.

    Uses singleton pattern to ensure one engine per database URL.
    This prevents connection pool exhaustion when multiple services
    access the same shared database.

    Supports both PostgreSQL and SQLite URLs:
    - PostgreSQL: uses real connection pool with pool_recycle
    - SQLite: uses StaticPool for thread safety (backward compat)

    Args:
        database_url: SQLAlchemy database URL
        pool_size: Connection pool size (default: 10, max: 20 per service)
        max_overflow: Max overflow connections (default: 5)
        database_path: Optional database path for logging

    Returns:
        Shared AsyncEngine instance
    """
    if database_url not in _engines:
        connect_args: dict = {}
        poolclass = None
        extra_kwargs: dict = {}

        if _is_postgres_url(database_url):
            # PostgreSQL: use real connection pool
            extra_kwargs = {
                "pool_recycle": 3600,
            }
        elif "sqlite" in database_url:
            # SQLite: use StaticPool for thread safety
            connect_args = {"check_same_thread": False}
            poolclass = StaticPool

        engine_kwargs: dict = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_pre_ping": True,
            "connect_args": connect_args,
            "echo": False,
            **extra_kwargs,
        }
        if poolclass is not None:
            engine_kwargs["poolclass"] = poolclass

        _engines[database_url] = create_async_engine(
            database_url,
            **engine_kwargs,
        )

        logger.info(
            f"Created shared database engine: {database_path or database_url} "
            f"(pool_size={pool_size}, max_overflow={max_overflow})"
        )

    return _engines[database_url]


def create_shared_session_maker(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 5,
    database_path: str | None = None,
) -> async_sessionmaker:
    """
    Create or get a shared session maker for database sessions.

    Args:
        database_url: SQLAlchemy database URL
        pool_size: Connection pool size
        max_overflow: Max overflow connections
        database_path: Optional database path for logging

    Returns:
        Shared async_sessionmaker instance
    """
    if database_url not in _session_makers:
        engine = create_shared_db_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            database_path=database_path,
        )

        _session_makers[database_url] = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info(
            f"Created shared session maker: {database_path or database_url}"
        )

    return _session_makers[database_url]


async def get_shared_db_session(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 5,
) -> AsyncSession:
    """
    Get a database session from the shared pool.

    Args:
        database_url: SQLAlchemy database URL
        pool_size: Connection pool size
        max_overflow: Max overflow connections

    Returns:
        AsyncSession instance
    """
    session_maker = create_shared_session_maker(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )

    return session_maker()


def get_pool_stats(database_url: str) -> dict:
    """
    Get connection pool statistics for a database.

    Args:
        database_url: Database URL to get stats for

    Returns:
        Dictionary with pool statistics
    """
    if database_url not in _engines:
        return {"error": "Engine not found for database URL"}

    engine = _engines[database_url]
    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
    }


def close_all_engines():
    """Close all shared database engines (synchronous, for backward compat)."""
    global _engines, _session_makers

    _engines.clear()
    _session_makers.clear()
    logger.info("All shared database engines closed")


async def close_all_engines_async():
    """Close all shared database engines asynchronously."""
    global _engines, _session_makers
    for url, engine in _engines.items():
        await engine.dispose()
        logger.info(f"Disposed engine: {url}")
    _engines.clear()
    _session_makers.clear()
    logger.info("All shared database engines disposed")


def create_pg_engine(
    database_url: str,
    schema: str,
    pool_size: int = 10,
    max_overflow: int = 5,
    pool_recycle: int = 3600,
) -> AsyncEngine:
    """
    Create a PostgreSQL async engine with schema isolation.

    Each call creates a NEW engine (not singleton) because different
    schemas need different search_path settings.

    Args:
        database_url: PostgreSQL connection URL
        schema: PostgreSQL schema name for search_path isolation
        pool_size: Connection pool size (default: 10)
        max_overflow: Max overflow connections (default: 5)
        pool_recycle: Recycle connections after N seconds (default: 3600)

    Returns:
        AsyncEngine configured for the specified schema
    """
    engine = create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET search_path TO {schema}, public")
        cursor.close()

    logger.info(
        f"Created PostgreSQL engine: schema={schema} "
        f"(pool_size={pool_size}, max_overflow={max_overflow})"
    )

    return engine


def get_database_url(service_name: str = "") -> str:
    """
    Build DATABASE_URL from environment variables with fallback.

    Checks POSTGRES_URL first, then DATABASE_URL, then falls back
    to a SQLite URL for backward compatibility.

    Args:
        service_name: Optional service name for logging

    Returns:
        Database URL string
    """
    url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL", "")
    if url:
        return url

    # Fallback to SQLite
    sqlite_path = os.environ.get(
        "SQLITE_PATH", f"./data/{service_name or 'app'}.db"
    )
    return f"sqlite+aiosqlite:///{sqlite_path}"


async def check_pg_connection(engine: AsyncEngine) -> bool:
    """
    Check if a PostgreSQL connection is healthy.

    Args:
        engine: AsyncEngine to check

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False
