#!/usr/bin/env python3
"""
Migration Script: Create home_layout_rules Table

This script creates the home_layout_rules table for storing per-home spatial rules
and device relationships.

Phase 2: Real-World Rules Database

Usage:
    python scripts/migrate_home_layout_rules.py
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

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


async def index_exists(conn, index_name: str) -> bool:
    """Check if index exists"""
    result = await conn.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name=:index_name
    """), {"index_name": index_name})
    return result.fetchone() is not None


async def migrate():
    """Run the migration"""
    logger.info("🔄 Starting home_layout_rules table migration...")
    logger.info(f"📂 Database URL: {DATABASE_URL}")

    # Create engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # Check if table already exists
            if await table_exists(conn, 'home_layout_rules'):
                logger.info("⏭️  home_layout_rules table already exists, skipping creation")
            else:
                # Create table
                logger.info("📋 Creating home_layout_rules table...")
                await conn.execute(text("""
                    CREATE TABLE home_layout_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        home_id VARCHAR NOT NULL,
                        rule_type VARCHAR NOT NULL,
                        device1_pattern VARCHAR NOT NULL,
                        device2_pattern VARCHAR NOT NULL,
                        relationship VARCHAR NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        source VARCHAR,
                        metadata_json TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                logger.info("✅ Created home_layout_rules table")

            # Create indexes
            indexes = [
                ('idx_home_layout_home_id', 'home_id'),
                ('idx_home_layout_rule_type', 'rule_type'),
            ]

            for index_name, column in indexes:
                if await index_exists(conn, index_name):
                    logger.info(f"⏭️  Index {index_name} already exists, skipping")
                else:
                    logger.info(f"📋 Creating index {index_name} on {column}...")
                    await conn.execute(text(f"""
                        CREATE INDEX {index_name} ON home_layout_rules({column})
                    """))
                    logger.info(f"✅ Created index {index_name}")

        # Verify migration
        async with engine.begin() as conn:
            if await table_exists(conn, 'home_layout_rules'):
                # Check columns
                result = await conn.execute(text("PRAGMA table_info(home_layout_rules)"))
                columns = [row[1] for row in result.fetchall()]
                logger.info(f"📋 Table columns: {', '.join(columns)}")
                
                # Check indexes
                result = await conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND tbl_name='home_layout_rules'
                """))
                indexes = [row[0] for row in result.fetchall()]
                logger.info(f"📋 Table indexes: {', '.join(indexes)}")

        logger.info("✅ Migration complete!")

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False

    finally:
        await engine.dispose()


async def rollback():
    """Rollback migration (drop table)"""
    logger.warning("⚠️  Rolling back home_layout_rules migration...")
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            if await table_exists(conn, 'home_layout_rules'):
                await conn.execute(text("DROP TABLE IF EXISTS home_layout_rules"))
                logger.info("✅ Dropped home_layout_rules table")
            else:
                logger.info("⏭️  Table doesn't exist, nothing to rollback")

        return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}", exc_info=True)
        return False

    finally:
        await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate home_layout_rules table")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration")
    args = parser.parse_args()

    if args.rollback:
        asyncio.run(rollback())
    else:
        success = asyncio.run(migrate())
        sys.exit(0 if success else 1)

