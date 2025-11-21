"""
Database Migration: Add Learning Tables

Adds Q&A learning tables to existing database:
- qa_outcomes
- user_preferences
- question_quality_metrics

Also adds learning configuration settings to SystemSettings.

Created: January 2025
Story: Q&A Learning Enhancement Plan
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from ..config import settings
from ..database.models import Base, SystemSettings

logger = logging.getLogger(__name__)


async def add_learning_tables():
    """
    Add learning tables to database.
    
    This migration:
    1. Creates qa_outcomes table
    2. Creates user_preferences table
    3. Creates question_quality_metrics table
    4. Adds learning settings to SystemSettings (if not exists)
    """
    # Create async engine
    database_url = settings.database_url
    engine = create_async_engine(database_url, echo=False)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with engine.begin() as conn:
            # Create tables using SQLAlchemy metadata
            # This will only create tables that don't exist
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Learning tables created (or already exist)")
        
        # Update SystemSettings with new learning fields
        async with async_session() as session:
            try:
                from sqlalchemy import select
                
                # Get existing settings
                result = await session.execute(select(SystemSettings).limit(1))
                system_settings = result.scalar_one_or_none()
                
                if system_settings:
                    # Add new fields if they don't exist (for existing records)
                    if not hasattr(system_settings, 'enable_qa_learning'):
                        # Use raw SQL to add columns if they don't exist
                        async with engine.begin() as conn:
                            # Check if columns exist and add if not
                            await conn.execute(text("""
                                ALTER TABLE system_settings 
                                ADD COLUMN IF NOT EXISTS enable_qa_learning BOOLEAN DEFAULT TRUE
                            """))
                            await conn.execute(text("""
                                ALTER TABLE system_settings 
                                ADD COLUMN IF NOT EXISTS preference_consistency_threshold REAL DEFAULT 0.9
                            """))
                            await conn.execute(text("""
                                ALTER TABLE system_settings 
                                ADD COLUMN IF NOT EXISTS min_questions_for_preference INTEGER DEFAULT 3
                            """))
                            await conn.execute(text("""
                                ALTER TABLE system_settings 
                                ADD COLUMN IF NOT EXISTS learning_retrain_frequency VARCHAR DEFAULT 'weekly'
                            """))
                            logger.info("✅ Added learning settings columns to SystemSettings")
                    else:
                        logger.info("✅ Learning settings already exist in SystemSettings")
                else:
                    # Settings don't exist, will be created on first access
                    logger.info("ℹ️ SystemSettings will be created with defaults on first access")
                
                await session.commit()
                
            except Exception as e:
                logger.warning(f"⚠️ Could not update SystemSettings: {e}")
                # Non-critical, continue
        
        logger.info("✅ Migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


async def main():
    """Run migration."""
    logging.basicConfig(level=logging.INFO)
    logger.info("🚀 Starting learning tables migration...")
    await add_learning_tables()
    logger.info("✅ Migration complete")


if __name__ == "__main__":
    asyncio.run(main())


