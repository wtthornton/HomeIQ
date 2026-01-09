"""
Migration Script: Update Suggestions Status from 'pending' to 'draft'

Epic 39, Story 39.10: Automation Service Foundation
Fixes status mapping issue - updates existing suggestions with status='pending' to status='draft'
to align with frontend expectations.

Usage:
    python scripts/migrate_status_pending_to_draft.py

This script:
- Connects to the ai-automation-service-new database
- Finds all suggestions with status='pending'
- Updates them to status='draft'
- Reports how many suggestions were updated
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.config import settings
from src.database.models import Suggestion

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_suggestion_status():
    """
    Migrate existing suggestions from status='pending' to status='draft'.
    
    This fixes the status mapping issue where the API was using 'pending'
    but the frontend expects 'draft'.
    """
    logger.info("=" * 60)
    logger.info("Migration: Update suggestions status from 'pending' to 'draft'")
    logger.info("=" * 60)
    logger.info(f"Database: {settings.database_path}")
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
    )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    try:
        async with async_session_maker() as session:
            # Count suggestions with status='pending'
            stmt = select(Suggestion).where(Suggestion.status == "pending")
            result = await session.execute(stmt)
            pending_suggestions = result.scalars().all()
            pending_count = len(pending_suggestions)
            
            logger.info(f"Found {pending_count} suggestions with status='pending'")
            
            if pending_count == 0:
                logger.info("No suggestions to migrate. Migration complete.")
                return
            
            # Update all suggestions with status='pending' to status='draft'
            update_stmt = (
                update(Suggestion)
                .where(Suggestion.status == "pending")
                .values(status="draft")
            )
            result = await session.execute(update_stmt)
            updated_count = result.rowcount
            
            # Commit the changes
            await session.commit()
            
            logger.info(f"✅ Successfully updated {updated_count} suggestions from 'pending' to 'draft'")
            logger.info("=" * 60)
            logger.info("Migration complete!")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


def main():
    """Run the migration script."""
    try:
        asyncio.run(migrate_suggestion_status())
        return True
    except Exception as e:
        logger.error(f"Migration script failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
