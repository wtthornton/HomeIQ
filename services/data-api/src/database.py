"""
SQLite Database Configuration for Data API Service
Implements async SQLAlchemy 2.0 with WAL mode for optimal concurrency.

Based on Context7 KB best practices for FastAPI + SQLite.
"""

import os
import logging
from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/metadata.db")
SQLITE_TIMEOUT = int(os.getenv("SQLITE_TIMEOUT", "30"))
SQLITE_CACHE_SIZE = int(os.getenv("SQLITE_CACHE_SIZE", "-64000"))  # 64MB

# Create async engine
async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging during development
    pool_pre_ping=True,  # Verify connections before using
    connect_args={
        "timeout": SQLITE_TIMEOUT,
    }
)

# Configure SQLite pragmas for optimal performance
@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
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
        # Enable WAL mode for concurrent access
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Synchronous mode: NORMAL is faster and still safe
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Cache size (negative = KB, positive = pages)
        cursor.execute(f"PRAGMA cache_size={SQLITE_CACHE_SIZE}")
        
        # Use memory for temp tables
        cursor.execute("PRAGMA temp_store=MEMORY")
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Busy timeout (milliseconds)
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
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False
)


# Declarative Base for SQLAlchemy models
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Usage:
        class Device(Base):
            __tablename__ = "devices"
            device_id = Column(String, primary_key=True)
            ...
    """
    pass


# FastAPI dependency for database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Automatically handles:
    - Session creation
    - Transaction commit on success
    - Transaction rollback on error
    - Session cleanup
    
    Usage:
        @app.get("/devices")
        async def list_devices(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Device))
            return result.scalars().all()
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
    
    Called during application startup.
    Note: In production, use Alembic migrations instead.
    """
    async with async_engine.begin() as conn:
        # Create all tables defined in Base metadata
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def check_db_health() -> dict:
    """
    Check database health and return status information.
    
    Returns:
        dict: Database health status including:
            - status: "healthy" or "unhealthy"
            - journal_mode: Current journal mode (should be "wal")
            - database_size_mb: Size of database file
            - connection: "ok" or error message
    """
    try:
        async with AsyncSessionLocal() as session:
            # Test connection with simple query
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            
            # Get journal mode
            journal_result = await session.execute(text("PRAGMA journal_mode"))
            journal_mode = journal_result.scalar()
            
            # Get database size
            page_count_result = await session.execute(text("PRAGMA page_count"))
            page_count = page_count_result.scalar() or 0
            
            page_size_result = await session.execute(text("PRAGMA page_size"))
            page_size = page_size_result.scalar() or 4096
            
            db_size_mb = (page_count * page_size) / (1024 * 1024)
            
            return {
                "status": "healthy",
                "journal_mode": journal_mode,
                "database_size_mb": round(db_size_mb, 2),
                "wal_enabled": journal_mode == "wal",
                "connection": "ok"
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connection": str(e)
        }


# Log database configuration on module import
logger.info(f"SQLite database configured: {DATABASE_URL}")
logger.info(f"Cache size: {abs(SQLITE_CACHE_SIZE) // 1024}MB, Timeout: {SQLITE_TIMEOUT}s")

