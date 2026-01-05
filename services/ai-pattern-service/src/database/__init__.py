"""
Database initialization and connection management

Epic 39, Story 39.5: Pattern Service Foundation
Database connection pooling for shared SQLite database.
"""

import logging
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import settings

logger = logging.getLogger("ai-pattern-service")

# Create async engine with connection pooling
# For SQLite, configure PRAGMA settings for better reliability
if "sqlite" in settings.database_url:
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,  # Set to True for SQL query logging
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0,  # 30 second timeout for database operations
        },
    )
    
    # Set SQLite PRAGMA settings on connection
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite PRAGMA settings for optimal performance and reliability."""
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrent reads
            cursor.execute("PRAGMA synchronous=NORMAL")  # Fast writes, survives OS crash
            cursor.execute("PRAGMA foreign_keys=ON")  # Referential integrity
            cursor.execute("PRAGMA busy_timeout=30000")  # 30s lock wait (vs fail immediately)
            # Enable integrity checking on connection
            cursor.execute("PRAGMA quick_check")  # Quick integrity check
        except Exception as e:
            logger.warning(f"Failed to set SQLite PRAGMA settings: {e}")
        finally:
            cursor.close()
else:
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,  # Set to True for SQL query logging
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
        from .models import Base
        from .integrity import check_database_integrity
        from sqlalchemy import text
        
        # Test connectivity (tables may already exist in shared database)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Check database integrity on initialization
        async with AsyncSessionLocal() as session:
            is_healthy, error_msg = await check_database_integrity(session)
            if not is_healthy:
                logger.warning(f"Database integrity check failed on initialization: {error_msg}")
                logger.warning("Database may be corrupted. Consider running repair.")
            else:
                logger.info("Database integrity check passed on initialization")
        
        logger.info(f"Database initialized: {settings.database_path}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise

