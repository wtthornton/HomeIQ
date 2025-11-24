#!/usr/bin/env python3
"""
SQLite database maintenance script.

This script checks database health and runs maintenance operations:
- Checks freelist_count (recommends VACUUM if >100)
- Runs VACUUM if needed
- Runs ANALYZE to update query planner statistics
- Runs PRAGMA optimize (SQLite 3.38+)
"""
import sqlite3
import sys
import os
from pathlib import Path

# Database path (Docker container path)
DB_PATH = Path("/app/data/ai_automation.db")

def get_database_size(db_path):
    """Get database file size in MB"""
    if db_path.exists():
        return db_path.stat().st_size / (1024 * 1024)
    return 0

def check_freelist_count(conn):
    """Check freelist count (fragmented pages)"""
    cursor = conn.cursor()
    cursor.execute("PRAGMA freelist_count")
    return cursor.fetchone()[0]

def check_page_count(conn):
    """Get total page count"""
    cursor = conn.cursor()
    cursor.execute("PRAGMA page_count")
    return cursor.fetchone()[0]

def check_integrity(conn):
    """Check database integrity"""
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]
    return result == "ok"

def run_vacuum(conn):
    """Run VACUUM to reclaim space"""
    try:
        print("  Running VACUUM...")
        conn.execute("VACUUM")
        conn.commit()
        print("  ✅ VACUUM completed successfully")
        return True
    except sqlite3.Error as e:
        print(f"  ❌ VACUUM failed: {e}")
        return False

def run_analyze(conn):
    """Run ANALYZE to update query planner statistics"""
    try:
        print("  Running ANALYZE...")
        conn.execute("ANALYZE")
        conn.commit()
        print("  ✅ ANALYZE completed successfully")
        return True
    except sqlite3.Error as e:
        print(f"  ❌ ANALYZE failed: {e}")
        return False

def run_optimize(conn):
    """Run PRAGMA optimize (SQLite 3.38+)"""
    try:
        print("  Running PRAGMA optimize...")
        cursor = conn.cursor()
        cursor.execute("PRAGMA optimize")
        result = cursor.fetchall()
        if result:
            print(f"  ✅ PRAGMA optimize completed ({len(result)} recommendations)")
            for row in result:
                print(f"     {row[0]}: {row[1]}")
        else:
            print("  ✅ PRAGMA optimize completed (no recommendations)")
        return True
    except sqlite3.Error as e:
        # PRAGMA optimize might not be available in older SQLite versions
        if "no such function" in str(e).lower() or "syntax error" in str(e).lower():
            print(f"  ⚠️  PRAGMA optimize not available (SQLite 3.38+ required)")
            return False
        print(f"  ❌ PRAGMA optimize failed: {e}")
        return False

def get_sqlite_version(conn):
    """Get SQLite version"""
    cursor = conn.cursor()
    cursor.execute("SELECT sqlite_version()")
    return cursor.fetchone()[0]

def main():
    """Main entry point"""
    print("=" * 80)
    print("SQLITE DATABASE MAINTENANCE")
    print("=" * 80)
    print()
    print(f"Database: {DB_PATH}")
    print()
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("   Make sure you're running this script inside the Docker container")
        return False
    
    try:
        # Get initial database size
        size_before = get_database_size(DB_PATH)
        print(f"Database size before: {size_before:.2f} MB")
        print()
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Get SQLite version
        sqlite_version = get_sqlite_version(conn)
        print(f"SQLite version: {sqlite_version}")
        print()
        
        # Check integrity
        print("Checking database integrity...")
        print("-" * 80)
        if check_integrity(conn):
            print("  ✅ Database integrity check passed")
        else:
            print("  ❌ Database integrity check failed!")
            conn.close()
            return False
        print()
        
        # Check freelist count
        print("Checking database fragmentation...")
        print("-" * 80)
        freelist_count = check_freelist_count(conn)
        page_count = check_page_count(conn)
        fragmentation_pct = (freelist_count / page_count * 100) if page_count > 0 else 0
        
        print(f"  Total pages: {page_count:,}")
        print(f"  Freelist pages: {freelist_count:,}")
        print(f"  Fragmentation: {fragmentation_pct:.2f}%")
        
        vacuum_needed = freelist_count > 100
        if vacuum_needed:
            print(f"  ⚠️  VACUUM recommended (freelist_count > 100)")
        else:
            print(f"  ✅ Fragmentation is low (freelist_count ≤ 100)")
        print()
        
        # Run maintenance operations
        maintenance_performed = False
        
        if vacuum_needed:
            print("Running maintenance operations...")
            print("-" * 80)
            
            if run_vacuum(conn):
                maintenance_performed = True
                # Recheck after VACUUM
                new_freelist = check_freelist_count(conn)
                new_page_count = check_page_count(conn)
                print(f"  After VACUUM: {new_freelist:,} freelist pages, {new_page_count:,} total pages")
                print()
        else:
            print("Maintenance operations...")
            print("-" * 80)
            print("  ℹ️  VACUUM not needed (fragmentation is low)")
            print()
        
        # Always run ANALYZE
        print("Updating query planner statistics...")
        print("-" * 80)
        if run_analyze(conn):
            maintenance_performed = True
        print()
        
        # Try PRAGMA optimize (SQLite 3.38+)
        print("Running query optimizer...")
        print("-" * 80)
        run_optimize(conn)
        print()
        
        # Get final database size
        size_after = get_database_size(DB_PATH)
        size_change = size_after - size_before
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        print(f"Database size before: {size_before:.2f} MB")
        print(f"Database size after:  {size_after:.2f} MB")
        if size_change != 0:
            print(f"Size change: {size_change:+.2f} MB")
        print()
        print(f"Fragmentation: {fragmentation_pct:.2f}% ({freelist_count:,} freelist pages)")
        print()
        
        if maintenance_performed:
            print("✅ Maintenance operations completed")
        else:
            print("ℹ️  No maintenance operations were needed")
        
        print()
        print("Recommendation: Run this script monthly or when fragmentation > 10%")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

