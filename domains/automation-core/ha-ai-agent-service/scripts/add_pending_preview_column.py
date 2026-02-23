#!/usr/bin/env python3
"""
Migration script to add pending_preview column to conversations table
Run this script to fix the "no such column: conversations.pending_preview" error
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def migrate():
    """Add pending_preview column if it doesn't exist"""
    # Database path (matches config default)
    database_url = "sqlite+aiosqlite:///./data/ha_ai_agent.db"
    
    # If running in Docker, use absolute path
    if Path("/app/data/ha_ai_agent.db").exists():
        database_url = "sqlite+aiosqlite:////app/data/ha_ai_agent.db"
    
    print(f"🔍 Connecting to database: {database_url}")
    
    engine = create_async_engine(database_url, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Check if table exists
            table_result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            )
            table_exists = table_result.fetchone() is not None
            
            if not table_exists:
                print("❌ Conversations table doesn't exist. Run database initialization first.")
                return False
            
            # Check if column exists
            column_result = await conn.execute(
                text("SELECT COUNT(*) FROM pragma_table_info('conversations') WHERE name = 'pending_preview'")
            )
            column_count = column_result.scalar()
            column_exists = column_count > 0
            
            if column_exists:
                print("✅ Column pending_preview already exists. No migration needed.")
                return True
            
            # Add column
            print("🔄 Adding pending_preview column...")
            await conn.execute(
                text("ALTER TABLE conversations ADD COLUMN pending_preview JSON")
            )
            print("✅ Successfully added pending_preview column to conversations table")
            return True
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(migrate())
    sys.exit(0 if success else 1)

