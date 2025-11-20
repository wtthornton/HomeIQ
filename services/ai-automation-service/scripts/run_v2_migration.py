#!/usr/bin/env python3
"""
Run v2 database migration script.

This script creates the new v2 schema tables for the conversation system.
It does NOT migrate existing data - use import_to_v2.py for that.

Usage:
    python scripts/run_v2_migration.py [--dry-run]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration(dry_run: bool = False):
    """Run v2 schema migration"""

    # Read SQL file
    sql_file = Path(__file__).parent.parent / "database" / "migrations" / "v2_schema.sql"

    if not sql_file.exists():
        logger.error(f"SQL file not found: {sql_file}")
        return False

    sql_content = sql_file.read_text()

    # Database path
    db_path = Path(__file__).parent.parent / "data" / "ai_automation.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Database path: {db_path}")

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info(f"Would execute SQL from: {sql_file}")
        logger.info("SQL Preview (first 500 chars):")
        print(sql_content[:500])
        return True

    # Connect to database
    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Execute SQL statements
            logger.info("Creating v2 schema tables...")

            # Split SQL by semicolons and execute each statement
            # Remove comments (both line comments and inline comments)
            lines = []
            for line in sql_content.split('\n'):
                # Remove inline comments (everything after --)
                if '--' in line:
                    line = line[:line.index('--')]
                line = line.strip()
                if line:
                    lines.append(line)

            # Join lines and split by semicolon
            full_sql = ' '.join(lines)
            statements = [s.strip() for s in full_sql.split(';') if s.strip()]

            for i, statement in enumerate(statements, 1):
                if statement:
                    logger.debug(f"Executing statement {i}/{len(statements)}: {statement[:50]}...")
                    try:
                        await conn.execute(text(statement))
                    except Exception as e:
                        # If it's an index that already exists or table already exists, that's OK
                        error_str = str(e).lower()
                        if "already exists" in error_str or "duplicate" in error_str:
                            logger.debug(f"Statement {i} already applied, skipping")
                        else:
                            raise

            logger.info("✅ v2 schema migration completed successfully")

            # Verify tables were created
            result = await conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name IN ('conversations', 'conversation_turns', 'confidence_factors', 
                            'function_calls', 'automation_suggestions')
                ORDER BY name
            """))
            tables = [row[0] for row in result.fetchall()]

            logger.info(f"✅ Created tables: {', '.join(tables)}")

            if len(tables) < 5:
                logger.warning(f"⚠️ Expected 5 tables, found {len(tables)}")
                return False

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False
    finally:
        await engine.dispose()


async def main():
    parser = argparse.ArgumentParser(description="Run v2 database migration")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    args = parser.parse_args()

    success = await run_migration(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

