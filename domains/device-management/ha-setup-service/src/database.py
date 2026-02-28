"""Database configuration using SQLAlchemy 2.0 async patterns"""
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from homeiq_data.database_pool import create_pg_engine

from .config import get_settings

settings = get_settings()

# PostgreSQL configuration
_db_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL", "")
_schema = os.getenv("DATABASE_SCHEMA", "devices")

# Create async engine (PostgreSQL only)
engine = create_pg_engine(
    database_url=_db_url,
    schema=_schema,
)

# Create async session factory (Context7 best practice)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints to get database session.

    Context7 Pattern: Async dependency injection with proper exception handling
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise  # CRITICAL: Must re-raise for proper error propagation
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
