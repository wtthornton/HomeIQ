"""
Cleanup Script for Pattern and Synergy Data
NUCLEAR OPTION: Deletes all patterns, synergies, and related data
"""
import sqlite3
import sys
from datetime import datetime

DB_PATH = '/app/data/ai_automation.db'

def backup_database():
    """Create a backup before cleanup"""
    import shutil
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"/app/data/ai_automation.backup.{timestamp}"
    
    print(f"Creating backup: {backup_path}")
    try:
        shutil.copy2(DB_PATH, backup_path)
        print("✅ Backup created successfully")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def get_stats_before(conn):
    """Get statistics before cleanup"""
    cursor = conn.cursor()
    
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM patterns")
    stats['patterns'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM synergy_opportunities")
    stats['synergies'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM pattern_history")
    stats['history'] = cursor.fetchone()[0]
    
    return stats

def cleanup_all_data(conn, dry_run=True):
    """Delete all pattern and synergy data"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    if dry_run:
        print("DRY RUN - NO DATA WILL BE DELETED")
    else:
        print("EXECUTING CLEANUP - DATA WILL BE DELETED")
    print("="*80)
    
    # SQL statements
    cleanup_sql = [
        ("pattern_history", "DELETE FROM pattern_history"),
        ("patterns", "DELETE FROM patterns"),
        ("synergy_opportunities", "DELETE FROM synergy_opportunities"),
        ("discovered_synergies", "DELETE FROM discovered_synergies"),
    ]
    
    results = {}
    
    for table, sql in cleanup_sql:
        print(f"\n{table}:")
        print(f"  SQL: {sql}")
        
        if not dry_run:
            try:
                cursor.execute(sql)
                deleted = cursor.rowcount
                print(f"  ✅ Deleted {deleted} rows")
                results[table] = deleted
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results[table] = 0
        else:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  Would delete {count} rows")
            results[table] = count
    
    if not dry_run:
        print("\nVacuuming database...")
        cursor.execute("VACUUM")
        print("✅ Database vacuumed")
    
    return results

def main():
    """Main cleanup function"""
    print("="*80)
    print("PATTERN & SYNERGY DATA CLEANUP")
    print("="*80)
    print(f"Database: {DB_PATH}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Check for dry-run flag
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - Use --execute flag to actually delete data")
    else:
        print("\n🔥 EXECUTE MODE - DATA WILL BE DELETED")
        response = input("Are you sure? Type 'DELETE ALL' to confirm: ")
        if response != "DELETE ALL":
            print("❌ Aborted")
            return
    
    # Create backup (only in execute mode)
    if not dry_run:
        if not backup_database():
            print("❌ Backup failed, aborting cleanup")
            return
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Get stats before
        print("\n" + "="*80)
        print("BEFORE CLEANUP")
        print("="*80)
        stats_before = get_stats_before(conn)
        for table, count in stats_before.items():
            print(f"  {table}: {count} rows")
        
        # Execute cleanup
        results = cleanup_all_data(conn, dry_run=dry_run)
        
        if not dry_run:
            conn.commit()
            print("\n✅ Changes committed")
            
            # Get stats after
            print("\n" + "="*80)
            print("AFTER CLEANUP")
            print("="*80)
            stats_after = get_stats_before(conn)
            for table, count in stats_after.items():
                print(f"  {table}: {count} rows")
        
        print("\n" + "="*80)
        print("CLEANUP COMPLETE")
        print("="*80)
        
        if dry_run:
            print("\n💡 To execute cleanup, run:")
            print("   docker exec ai-pattern-service python3 /tmp/cleanup.py --execute")
        else:
            print("\n✅ All pattern and synergy data has been deleted")
            print("💡 Restart the service to regenerate fresh patterns:")
            print("   docker compose restart ai-pattern-service")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if not dry_run:
            conn.rollback()
            print("Changes rolled back")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
