"""
Database initialization and connection management

Epic 39, Story 39.5: Pattern Service Foundation
Database connection pooling for shared SQLite database.
"""

import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import settings

logger = logging.getLogger("ai-pattern-service")

# Create async engine with connection pooling
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
        from sqlalchemy import text
        
        # Test connectivity (tables may already exist in shared database)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info(f"Database initialized: {settings.database_path}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise

