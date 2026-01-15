#!/usr/bin/env python3
"""
Delete all suggestions from the ai-automation-service database.

This script:
1. Connects to the SQLite database
2. Counts existing suggestions
3. Deletes all suggestions
4. Verifies deletion

Usage:
    python scripts/delete_all_suggestions.py
    OR
    docker exec homeiq-ai-automation-service-new python /app/scripts/delete_all_suggestions.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 - use environment variable only
        pass

# Add /app/src to path for imports (works both locally and in Docker)
script_dir = Path(__file__).parent
if (script_dir.parent / "services" / "ai-automation-service-new" / "src").exists():
    # Running locally
    sys.path.insert(0, str(script_dir.parent / "services" / "ai-automation-service-new" / "src"))
else:
    # Running in Docker container
    sys.path.insert(0, "/app/src")

# Use direct SQLAlchemy imports to avoid complex dependency chains
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

async def delete_all_suggestions():
    """Delete all suggestions from the database"""
    print("=" * 60)
    print("DELETING ALL SUGGESTIONS FROM DATABASE")
    print("=" * 60)
    print()
    
    # Database path - works in both local and Docker
    if Path("/app/data/ai_automation.db").exists():
        db_path = "/app/data/ai_automation.db"
    elif (script_dir.parent / "services" / "ai-automation-service-new" / "data" / "ai_automation.db").exists():
        db_path = str(script_dir.parent / "services" / "ai-automation-service-new" / "data" / "ai_automation.db")
    else:
        print("[ERROR] Database not found")
        print("   Checked paths:")
        print(f"   - /app/data/ai_automation.db")
        print(f"   - {script_dir.parent / 'services' / 'ai-automation-service-new' / 'data' / 'ai_automation.db'}")
        return -1
    
    # Create async engine
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Count existing suggestions using raw SQL
        result = await db.execute(text("SELECT COUNT(*) FROM suggestions"))
        count = result.scalar()
        
        if count == 0:
            print("[OK] No suggestions found in database. Nothing to delete.")
            await engine.dispose()
            return 0
        
        print(f"Found {count} suggestion(s) in database")
        print()
        
        # Show some details about what will be deleted
        result = await db.execute(text("SELECT id, title, status FROM suggestions LIMIT 5"))
        rows = result.fetchall()
        print("Sample suggestions to be deleted:")
        for i, row in enumerate(rows, 1):
            print(f"  {i}. ID: {row[0]}, Title: {row[1]}, Status: {row[2]}")
        if count > 5:
            print(f"  ... and {count - 5} more")
        print()
        
        # Delete all suggestions
        print(f"[DELETE] Deleting {count} suggestions...")
        await db.execute(text("DELETE FROM suggestions"))
        await db.commit()
        
        print(f"[OK] Successfully deleted {count} suggestions")
        print()
        
        # Verify deletion
        print("Verifying deletion...")
        result = await db.execute(text("SELECT COUNT(*) FROM suggestions"))
        remaining_count = result.scalar()
        
        if remaining_count == 0:
            print("✅ Verification successful: All suggestions deleted")
        else:
            print(f"⚠️  WARNING: {remaining_count} suggestions still remain!")
            result = await db.execute(text("SELECT id, title FROM suggestions"))
            for row in result.fetchall():
                print(f"  - ID: {row[0]}, Title: {row[1]}")
        
        print()
        print("=" * 60)
        print(f"COMPLETE: Deleted {count} suggestions")
        print("=" * 60)
        
        await engine.dispose()
        return count

async def main():
    """Main entry point"""
    try:
        count = await delete_all_suggestions()
        sys.exit(0 if count >= 0 else 1)
    except Exception as e:
        print(f"[ERROR] Failed to delete suggestions: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
