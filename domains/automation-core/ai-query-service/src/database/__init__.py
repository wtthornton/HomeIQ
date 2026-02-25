"""
Database initialization and session management for AI Query Service

Epic 39, Story 39.9: Query Service Foundation
Epics 3-4: Dual-mode PostgreSQL/SQLite support.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

logger = logging.getLogger(__name__)

# Determine effective database URL and backend type
_db_url = settings.effective_database_url
_is_postgres = _db_url.startswith("postgresql") or _db_url.startswith("postgres")

if _is_postgres:
    # PostgreSQL via shared library (schema isolation, real connection pool)
    from homeiq_data.database_pool import create_pg_engine

    engine = create_pg_engine(
        database_url=_db_url,
        schema=settings.database_schema,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
else:
    # SQLite configuration (backward compatible - original code preserved)
    from sqlalchemy import event
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        _db_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0,  # 30 second timeout for database operations
        },
        echo=False,
    )

    # Set PRAGMA settings on connection pool initialization
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        """Set SQLite PRAGMA settings for optimal performance."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrent reads
        cursor.execute("PRAGMA synchronous=NORMAL")  # Fast writes, survives OS crash
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
        cursor.execute("PRAGMA temp_store=MEMORY")  # Fast temp tables
        cursor.execute("PRAGMA foreign_keys=ON")  # Referential integrity
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s lock wait (vs fail immediately)
        cursor.close()

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
        logger.info("✅ Database connection initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise  # Re-raise to fail fast on startup

