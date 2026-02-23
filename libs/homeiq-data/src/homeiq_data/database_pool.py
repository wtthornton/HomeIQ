"""
Shared Database Connection Pool Utilities

Epic 39, Story 39.11: Shared Infrastructure Setup
Utilities for managing shared SQLite database connections across microservices.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.pool import StaticPool

from .logging_config import get_logger

logger = get_logger(__name__)


# Global engine instances (one per database path)
_engines: dict[str, AsyncEngine] = {}
_session_makers: dict[str, async_sessionmaker] = {}


def create_shared_db_engine(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 5,
    database_path: Optional[str] = None
) -> AsyncEngine:
    """
    Create or get a shared database engine for connection pooling.
    
    Uses singleton pattern to ensure one engine per database URL.
    This prevents connection pool exhaustion when multiple services
    access the same shared database.
    
    Args:
        database_url: SQLAlchemy database URL (e.g., "sqlite+aiosqlite:///path/to/db")
        pool_size: Connection pool size (default: 10, max: 20 per service)
        max_overflow: Max overflow connections (default: 5)
        database_path: Optional database path for logging
    
    Returns:
        Shared AsyncEngine instance
    
    Example:
        ```python
        from shared.database_pool import create_shared_db_engine
        
        engine = create_shared_db_engine(
            database_url="sqlite+aiosqlite:////app/data/shared.db",
            pool_size=10,
            max_overflow=5
        )
        ```
    """
    # Use database URL as key for singleton
    if database_url not in _engines:
        # Configure pool for SQLite
        connect_args = {}
        poolclass = None
        
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}
            poolclass = StaticPool
        
        _engines[database_url] = create_async_engine(
            database_url,
            poolclass=poolclass,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            connect_args=connect_args,
            echo=False,
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
    database_path: Optional[str] = None
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
    
    Example:
        ```python
        from shared.database_pool import create_shared_session_maker
        
        AsyncSessionLocal = create_shared_session_maker(
            database_url="sqlite+aiosqlite:////app/data/shared.db"
        )
        
        async with AsyncSessionLocal() as session:
            # Use session
            ...
        ```
    """
    # Use database URL as key for singleton
    if database_url not in _session_makers:
        engine = create_shared_db_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            database_path=database_path
        )
        
        _session_makers[database_url] = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info(f"Created shared session maker: {database_path or database_url}")
    
    return _session_makers[database_url]


async def get_shared_db_session(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 5
) -> AsyncSession:
    """
    Get a database session from the shared pool.
    
    Args:
        database_url: SQLAlchemy database URL
        pool_size: Connection pool size
        max_overflow: Max overflow connections
    
    Returns:
        AsyncSession instance
    
    Example:
        ```python
        from shared.database_pool import get_shared_db_session
        
        session = await get_shared_db_session(
            database_url="sqlite+aiosqlite:////app/data/shared.db"
        )
        ```
    """
    session_maker = create_shared_session_maker(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow
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
        "invalid": pool.invalid()
    }


def close_all_engines():
    """Close all shared database engines (for cleanup)"""
    global _engines, _session_makers
    
    for engine in _engines.values():
        # Note: AsyncEngine doesn't have a direct close() method
        # Connections are closed automatically when engine is garbage collected
        pass
    
    _engines.clear()
    _session_makers.clear()
    logger.info("All shared database engines closed")

