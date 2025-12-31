#!/usr/bin/env python3
"""
Verify Database Schema Fix

This script verifies that the database schema fix is working correctly:
1. Checks if suggestions table exists
2. Verifies automation_json column exists
3. Tests that the init_db() function works correctly
"""

import asyncio
import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add service directory to path
service_dir = Path(__file__).parent.parent / "services" / "ai-automation-service-new"
sys.path.insert(0, str(service_dir))

async def verify_schema():
    """Verify database schema is correct."""
    from src.database import init_db, engine
    from sqlalchemy import text
    
    print("=" * 60)
    print("Database Schema Verification")
    print("=" * 60)
    
    try:
        # Initialize database (this should create table if missing)
        print("\n1. Running init_db()...")
        await init_db()
        print("   ✅ init_db() completed")
        
        # Verify table exists and has required columns
        print("\n2. Verifying table schema...")
        async with engine.begin() as conn:
            # Check if table exists
            result = await conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='suggestions'
            """))
            table_exists = result.scalar() is not None
            
            if not table_exists:
                print("   ❌ ERROR: suggestions table does not exist!")
                return False
            
            print("   ✅ suggestions table exists")
            
            # Check columns
            result = await conn.execute(text("PRAGMA table_info(suggestions)"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            
            required_columns = [
                'id', 'pattern_id', 'title', 'description',
                'automation_json', 'automation_yaml', 'ha_version', 'json_schema_version',
                'status', 'created_at', 'updated_at', 'automation_id', 'deployed_at',
                'confidence_score', 'safety_score', 'user_feedback', 'feedback_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                print(f"   ❌ ERROR: Missing columns: {missing_columns}")
                return False
            
            print(f"   ✅ All required columns exist ({len(column_names)} total)")
            
            # Specifically verify automation_json
            if 'automation_json' in column_names:
                print("   ✅ automation_json column exists")
            else:
                print("   ❌ ERROR: automation_json column missing!")
                return False
        
        print("\n" + "=" * 60)
        print("✅ Schema verification PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_schema())
    sys.exit(0 if success else 1)
