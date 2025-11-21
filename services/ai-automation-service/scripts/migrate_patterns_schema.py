#!/usr/bin/env python3
"""
Migration Script: Add Phase 1 History Tracking Fields to Patterns Table

This script adds the missing columns to the patterns table:
- updated_at
- first_seen
- last_seen
- confidence_history_count
- trend_direction
- trend_strength

Usage:
    python scripts/migrate_patterns_schema.py
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Database URL - try multiple possible paths
def get_database_url():
    """Get database URL, checking multiple possible locations"""
    # Try root data directory first (most common location)
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
            # Convert to absolute path for SQLite URL (more reliable)
            abs_path = db_path.resolve()
            return f"sqlite+aiosqlite:///{abs_path}"

    # Default fallback - try root data directory
    default_path = root_dir / "data" / "ai_automation.db"
    return f"sqlite+aiosqlite:///{default_path.resolve()}"

DATABASE_URL = get_database_url()

# Columns to add
COLUMNS_TO_ADD = [
    {
        "name": "updated_at",
        "type": "DATETIME",
        "default": "datetime('now')",
        "nullable": True,
    },
    {
        "name": "first_seen",
        "type": "DATETIME",
        "default": "datetime('now')",
        "nullable": False,
    },
    {
        "name": "last_seen",
        "type": "DATETIME",
        "default": "datetime('now')",
        "nullable": False,
    },
    {
        "name": "confidence_history_count",
        "type": "INTEGER",
        "default": "1",
        "nullable": False,
    },
    {
        "name": "trend_direction",
        "type": "VARCHAR(20)",
        "default": "NULL",
        "nullable": True,
    },
    {
        "name": "trend_strength",
        "type": "FLOAT",
        "default": "0.0",
        "nullable": False,
    },
]


async def get_existing_columns(engine):
    """Get list of existing columns in patterns table"""
    async with engine.begin() as conn:
        # Query SQLite schema
        result = await conn.execute(text("""
            SELECT name FROM pragma_table_info('patterns')
        """))
        return [row[0] for row in result.fetchall()]


async def add_column_if_missing(conn, column_def):
    """Add a column to patterns table if it doesn't exist"""
    column_name = column_def["name"]
    column_type = column_def["type"]
    default = column_def.get("default", "NULL")

    # SQLite doesn't support adding NOT NULL columns with defaults easily
    # So we'll add as nullable first, then update existing rows
    "" if column_def["nullable"] else ""

    try:
        # ALTER TABLE ADD COLUMN
        sql = f"ALTER TABLE patterns ADD COLUMN {column_name} {column_type}"
        if default and default != "NULL":
            sql += f" DEFAULT {default}"

        await conn.execute(text(sql))
        logger.info(f"✅ Added column: {column_name}")

        # If column is NOT NULL and has existing rows, update them
        if not column_def["nullable"] and default and default != "NULL":
            await conn.execute(text(f"""
                UPDATE patterns
                SET {column_name} = {default}
                WHERE {column_name} IS NULL
            """))
            logger.info(f"✅ Updated existing rows for {column_name}")

        return True
    except Exception as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            logger.info(f"⏭️  Column {column_name} already exists, skipping")
            return False
        logger.exception(f"❌ Error adding column {column_name}: {e}")
        raise


async def migrate():
    """Run the migration"""
    logger.info("🔄 Starting patterns table migration...")
    logger.info(f"📂 Database URL: {DATABASE_URL}")

    # Create engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        # Get existing columns
        existing_columns = await get_existing_columns(engine)
        logger.info(f"📋 Existing columns: {', '.join(existing_columns)}")

        # Check if patterns table exists
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='patterns'
            """))
            if not result.fetchone():
                logger.warning("⚠️  Patterns table does not exist. Creating it from models...")
                # Import models and create tables
                from database.models import Base
                await conn.run_sync(Base.metadata.create_all, tables=[Base.metadata.tables["patterns"]])
                logger.info("✅ Created patterns table from models")
                # Refresh existing columns after table creation
                existing_columns = await get_existing_columns(engine)

        # Add missing columns
        async with engine.begin() as conn:
            added_count = 0
            for column_def in COLUMNS_TO_ADD:
                if column_def["name"] not in existing_columns:
                    if await add_column_if_missing(conn, column_def):
                        added_count += 1
                else:
                    logger.info(f"⏭️  Column {column_def['name']} already exists, skipping")

        logger.info(f"✅ Migration complete! Added {added_count} columns.")

        # Verify migration
        final_columns = await get_existing_columns(engine)
        logger.info(f"📋 Final columns: {', '.join(final_columns)}")

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(migrate())
    sys.exit(0 if success else 1)
