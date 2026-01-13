"""
Database Session Management

Provides async database session factory and initialization.
Following 2025 patterns: SQLAlchemy async with aiosqlite.
"""

import logging
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from ..config import settings

logger = logging.getLogger(__name__)

# Base class for database models
Base = declarative_base()

# Database URL
database_url = f"sqlite+aiosqlite:///{settings.database_path}"

# Create async engine with StaticPool for SQLite
engine = create_async_engine(
    database_url,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,  # 30 second timeout for database operations
    },
    echo=settings.database_echo,
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
    
    # Ensure database directory exists
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
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
        
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise
