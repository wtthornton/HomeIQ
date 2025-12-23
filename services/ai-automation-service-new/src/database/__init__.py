"""
Database initialization and connection management

Epic 39, Story 39.10: Automation Service Foundation
Database connection pooling for shared SQLite database.
"""

import logging
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from ..config import settings

logger = logging.getLogger("ai-automation-service")

# Create async engine with connection pooling
# SQLite doesn't support pool_size/max_overflow - use StaticPool only
if "sqlite" in settings.database_url:
    # SQLite configuration (no pool_size/max_overflow)
    # CRITICAL: Configure PRAGMA settings for optimal performance
    engine = create_async_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0,  # 30 second timeout for database operations
        },
        echo=False,
    )
    
    # Set PRAGMA settings on connection pool initialization
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite PRAGMA settings for optimal performance."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrent reads
        cursor.execute("PRAGMA synchronous=NORMAL")  # Fast writes, survives OS crash
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
        cursor.execute("PRAGMA temp_store=MEMORY")  # Fast temp tables
        cursor.execute("PRAGMA foreign_keys=ON")  # Referential integrity
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s lock wait (vs fail immediately)
        cursor.close()
else:
    # PostgreSQL/MySQL configuration (supports pooling)
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,
    )

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.
    
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
        finally:
            await session.close()


async def init_db():
    """Initialize database connection and verify connectivity."""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
            
            # Check if suggestions table exists and add missing description column if needed
            # This handles schema mismatch between model and existing database
            result = await conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='suggestions'
            """))
            table_exists = result.scalar() is not None
            
            if table_exists:
                # Check if description column exists
                result = await conn.execute(text("PRAGMA table_info(suggestions)"))
                columns = result.fetchall()
                column_names = [col[1] for col in columns]  # Column name is at index 1
                
                if 'description' not in column_names:
                    logger.info("Adding missing 'description' column to suggestions table")
                    await conn.execute(text("""
                        ALTER TABLE suggestions 
                        ADD COLUMN description TEXT
                    """))
                    logger.info("✅ Added 'description' column to suggestions table")
            
        logger.info("✅ Database connection initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise  # Re-raise to fail fast on startup

