#!/usr/bin/env python3
"""
Script to directly clear devices and entities from SQLite database
"""

import asyncio
import sqlite3
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Database path - matches data-api configuration
DB_PATH = os.getenv('DATABASE_URL', 'sqlite:///./data/metadata.db').replace('sqlite+aiosqlite:///', 'sqlite:///').replace('sqlite:///', '').replace('/./', './')
if not DB_PATH:
    DB_PATH = './data/metadata.db'

async def clear_database():
    """Clear all devices and entities from database"""
    try:
        # Ensure database file exists
        db_path = Path(DB_PATH)
        if not db_path.exists():
            print(f"⚠️  Database file not found at {DB_PATH}")
            print("   Creating database...")
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"📂 Opening database: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get counts before deletion
        cursor.execute("SELECT COUNT(*) FROM entities")
        entities_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM devices")
        devices_count = cursor.fetchone()[0]
        
        print(f"📊 Found {devices_count} devices and {entities_count} entities")
        
        if devices_count == 0 and entities_count == 0:
            print("✅ Database is already empty")
            conn.close()
            return True
        
        # Delete entities first (foreign key constraint)
        print("\n🗑️  Deleting entities...")
        cursor.execute("DELETE FROM entities")
        entities_deleted = cursor.rowcount
        
        # Delete devices
        print("🗑️  Deleting devices...")
        cursor.execute("DELETE FROM devices")
        devices_deleted = cursor.rowcount
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"\n✅ Successfully cleared database:")
        print(f"   - {devices_deleted} devices deleted")
        print(f"   - {entities_deleted} entities deleted")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("🗑️  Device Database Clear Script")
    print("=" * 80)
    
    success = asyncio.run(clear_database())
    
    if success:
        print("\n" + "=" * 80)
        print("✅ Database cleared successfully!")
        print("=" * 80)
        print("\n💡 Next step: Trigger device discovery to reload devices")
        print("   You can do this by:")
        print("   1. Restarting the websocket-ingestion service")
        print("   2. Or calling: curl -X POST http://localhost:8001/api/v1/discovery/trigger")
    else:
        print("\n" + "=" * 80)
        print("❌ Failed to clear database")
        print("=" * 80)
        sys.exit(1)

