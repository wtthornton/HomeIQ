"""Migration script to add blueprint_name and blueprint_description columns."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration():
    """Add blueprint_name and blueprint_description columns to blueprint_suggestions table."""
    logger.info("Starting migration: Add blueprint_name and blueprint_description columns")
    
    # Create engine
    if "sqlite" in settings.database_url:
        from sqlalchemy.pool import StaticPool
        engine = create_async_engine(
            settings.database_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_async_engine(
            settings.database_url,
            echo=False,
        )
    
    try:
        async with engine.begin() as conn:
            # SQLite doesn't support "IF NOT EXISTS" in ALTER TABLE, so check first
            # For SQLite, we'll use a try/except approach or check if column exists
            logger.info("Checking if columns already exist...")
            
            # Check if blueprint_name column exists
            if "sqlite" in settings.database_url:
                # For SQLite, check pragma table_info
                result = await conn.execute(text("PRAGMA table_info(blueprint_suggestions)"))
                columns = [row[1] for row in result.fetchall()]
                
                if "blueprint_name" not in columns:
                    logger.info("Adding blueprint_name column...")
                    await conn.execute(text("ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_name VARCHAR(255)"))
                    logger.info("✓ Added blueprint_name column")
                else:
                    logger.info("blueprint_name column already exists")
                
                if "blueprint_description" not in columns:
                    logger.info("Adding blueprint_description column...")
                    await conn.execute(text("ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_description TEXT"))
                    logger.info("✓ Added blueprint_description column")
                else:
                    logger.info("blueprint_description column already exists")
            else:
                # For PostgreSQL, use IF NOT EXISTS equivalent
                logger.info("Adding columns (PostgreSQL)...")
                await conn.execute(text("""
                    ALTER TABLE blueprint_suggestions 
                    ADD COLUMN IF NOT EXISTS blueprint_name VARCHAR(255)
                """))
                await conn.execute(text("""
                    ALTER TABLE blueprint_suggestions 
                    ADD COLUMN IF NOT EXISTS blueprint_description TEXT
                """))
                logger.info("✓ Added columns (PostgreSQL)")
            
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())
