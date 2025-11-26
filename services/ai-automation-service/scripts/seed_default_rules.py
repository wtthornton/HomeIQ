#!/usr/bin/env python3
"""
Seed Default Rules Script

Loads default rules from real_world_rules.py and inserts them into the
home_layout_rules table with source='system_default'.

Phase 2: Real-World Rules Database

Usage:
    python scripts/seed_default_rules.py [--force]
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from database.models import HomeLayoutRule, Base
from synergy_detection.rules_manager import RulesManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Database URL - try multiple possible paths
def get_database_url():
    """Get database URL, checking multiple possible locations"""
    root_dir = Path(__file__).parent.parent.parent.parent  # Go up to project root
    script_dir = Path(__file__).parent.parent

    db_paths = [
        root_dir / "data" / "ai_automation.db",  # Root data directory
        Path("data") / "ai_automation.db",  # Current directory
        script_dir / "data" / "ai_automation.db",  # Service data directory
        Path("/app/data/ai_automation.db"),  # Docker container path
    ]

    for db_path in db_paths:
        if db_path.exists():
            abs_path = db_path.resolve()
            return f"sqlite+aiosqlite:///{abs_path}"

    # Default fallback - try root data directory
    default_path = root_dir / "data" / "ai_automation.db"
    return f"sqlite+aiosqlite:///{default_path.resolve()}"


DATABASE_URL = get_database_url()


async def table_exists(conn, table_name: str) -> bool:
    """Check if table exists"""
    result = await conn.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=:table_name
    """), {"table_name": table_name})
    return result.fetchone() is not None


async def rule_exists(session, rule_dict: dict) -> bool:
    """
    Check if a rule already exists in the database.
    
    Args:
        session: Database session
        rule_dict: Rule dictionary to check
        
    Returns:
        True if rule exists, False otherwise
    """
    query = select(HomeLayoutRule).where(
        HomeLayoutRule.home_id == rule_dict['home_id'],
        HomeLayoutRule.device1_pattern == rule_dict['device1_pattern'],
        HomeLayoutRule.device2_pattern == rule_dict['device2_pattern'],
        HomeLayoutRule.relationship == rule_dict['relationship'],
        HomeLayoutRule.source == rule_dict['source']
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def seed_default_rules(force: bool = False):
    """
    Seed default rules into the database.
    
    Args:
        force: If True, delete existing default rules before seeding
    """
    logger.info("🌱 Starting default rules seeding...")
    logger.info(f"📂 Database URL: {DATABASE_URL}")

    # Create engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        # Check if table exists
        async with engine.begin() as conn:
            if not await table_exists(conn, 'home_layout_rules'):
                logger.error("❌ home_layout_rules table does not exist. Run migration first.")
                return False

        # Create rules manager
        async with async_session() as session:
            rules_manager = RulesManager(session)
            
            # Load default rules
            logger.info("📋 Loading default rules from real_world_rules.py...")
            default_rules = await rules_manager.load_default_rules()
            logger.info(f"   → Found {len(default_rules)} default rules")
            
            if force:
                # Delete existing default rules
                logger.info("🗑️  Deleting existing default rules (--force)...")
                delete_query = select(HomeLayoutRule).where(
                    HomeLayoutRule.home_id == 'default',
                    HomeLayoutRule.source == 'system_default'
                )
                result = await session.execute(delete_query)
                existing_rules = result.scalars().all()
                for rule in existing_rules:
                    await session.delete(rule)
                await session.commit()
                logger.info(f"   → Deleted {len(existing_rules)} existing rules")
            
            # Insert rules (idempotent - skip if exists)
            inserted_count = 0
            skipped_count = 0
            
            for rule_dict in default_rules:
                # Check if rule already exists
                if await rule_exists(session, rule_dict):
                    skipped_count += 1
                    continue
                
                # Create rule object
                rule = HomeLayoutRule(**rule_dict)
                session.add(rule)
                inserted_count += 1
            
            await session.commit()
            
            logger.info(f"✅ Seeding complete!")
            logger.info(f"   → Inserted: {inserted_count} rules")
            logger.info(f"   → Skipped (already exist): {skipped_count} rules")
            logger.info(f"   → Total: {len(default_rules)} rules")
            
            # Verify
            verify_query = select(HomeLayoutRule).where(
                HomeLayoutRule.home_id == 'default',
                HomeLayoutRule.source == 'system_default'
            )
            result = await session.execute(verify_query)
            total_rules = len(result.scalars().all())
            logger.info(f"   → Total default rules in database: {total_rules}")
            
            return True

    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}", exc_info=True)
        return False

    finally:
        await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed default rules into database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing default rules before seeding"
    )
    args = parser.parse_args()

    success = asyncio.run(seed_default_rules(force=args.force))
    sys.exit(0 if success else 1)

