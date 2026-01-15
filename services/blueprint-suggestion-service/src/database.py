"""Database connection and session management for Blueprint Suggestion Service."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Create async engine
if "sqlite" in settings.database_url:
    # SQLite-specific configuration
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL or other databases
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def run_alembic_migrations():
    """
    Run Alembic migrations to ensure database schema is up to date.
    
    This should be called on service startup to ensure all migrations are applied.
    """
    try:
        # Get the service directory (parent of src/)
        service_dir = Path(__file__).parent.parent.parent
        alembic_ini_path = service_dir / "alembic.ini"
        
        if not alembic_ini_path.exists():
            logger.warning(f"Alembic config not found at {alembic_ini_path}, skipping migrations")
            return False
        
        # Configure Alembic
        alembic_cfg = Config(str(alembic_ini_path))
        
        # Run migrations
        logger.info("Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Alembic migrations completed")
        return True
    except Exception as e:
        logger.error(f"Failed to run Alembic migrations: {e}", exc_info=True)
        # Don't raise - fallback to manual schema sync
        logger.warning("Will attempt manual schema sync as fallback")
        return False


async def _run_manual_migrations(conn):
    """Fallback: Run manual database migrations to add missing columns."""
    logger.info("Checking for required manual migrations...")
    
    if "sqlite" in settings.database_url:
        # For SQLite, check if table exists and what columns it has
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='blueprint_suggestions'"))
        table_exists = result.fetchone() is not None
        
        if table_exists:
            # Check existing columns
            result = await conn.execute(text("PRAGMA table_info(blueprint_suggestions)"))
            columns = {row[1]: row for row in result.fetchall()}
            
            # Add blueprint_name if missing
            if "blueprint_name" not in columns:
                logger.info("Adding blueprint_name column (manual migration)...")
                await conn.execute(text("ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_name VARCHAR(255)"))
                logger.info("✓ Added blueprint_name column")
            
            # Add blueprint_description if missing
            if "blueprint_description" not in columns:
                logger.info("Adding blueprint_description column (manual migration)...")
                await conn.execute(text("ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_description TEXT"))
                logger.info("✓ Added blueprint_description column")
        else:
            logger.info("Table doesn't exist yet, will be created by create_all()")
    else:
        # For PostgreSQL, use IF NOT EXISTS
        logger.info("Running PostgreSQL manual migrations...")
        await conn.execute(text("""
            ALTER TABLE blueprint_suggestions 
            ADD COLUMN IF NOT EXISTS blueprint_name VARCHAR(255)
        """))
        await conn.execute(text("""
            ALTER TABLE blueprint_suggestions 
            ADD COLUMN IF NOT EXISTS blueprint_description TEXT
        """))
        logger.info("✓ PostgreSQL manual migrations completed")


async def check_schema_version(db: AsyncSession) -> bool:
    """Check if database schema matches the model."""
    try:
        if "sqlite" in settings.database_url:
            result = await db.execute(text("PRAGMA table_info(blueprint_suggestions)"))
            columns = {row[1] for row in result.fetchall()}
            required_columns = {
                "id", "blueprint_id", "blueprint_name", "blueprint_description",
                "suggestion_score", "matched_devices", "use_case", "status",
                "created_at", "updated_at", "accepted_at", "declined_at", "conversation_id"
            }
            return required_columns.issubset(columns)
        else:
            # For PostgreSQL, check using information_schema
            result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'blueprint_suggestions'
            """))
            columns = {row[0] for row in result.fetchall()}
            required_columns = {
                "id", "blueprint_id", "blueprint_name", "blueprint_description",
                "suggestion_score", "matched_devices", "use_case", "status",
                "created_at", "updated_at", "accepted_at", "declined_at", "conversation_id"
            }
            return required_columns.issubset(columns)
    except Exception as e:
        logger.error(f"Failed to check schema version: {e}", exc_info=True)
        return False


async def init_db():
    """
    Initialize database tables and run migrations.
    
    This function:
    1. Runs Alembic migrations to ensure schema is up to date
    2. Creates all tables (if they don't exist)
    3. Performs manual schema sync as fallback (adds missing columns)
    """
    logger.info("Initializing database...")
    
    # Step 1: Try Alembic migrations first
    alembic_success = await run_alembic_migrations()
    
    # Step 2: Create all tables (if they don't exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Step 3: Run manual migrations as fallback if Alembic failed
        if not alembic_success:
            await _run_manual_migrations(conn)
    
    logger.info("Database initialized successfully")


async def close_db():
    """Close database connections."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
