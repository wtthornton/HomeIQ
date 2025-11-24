#!/usr/bin/env python3
"""
Add composite indexes for common SQLite query patterns.

This script analyzes query patterns and adds composite indexes to improve
query performance for common WHERE + ORDER BY combinations.
"""
import sqlite3
import sys
from pathlib import Path

# Database path (Docker container path)
DB_PATH = Path("/app/data/ai_automation.db")

# Composite indexes to create based on query pattern analysis
COMPOSITE_INDEXES = [
    {
        "table": "suggestions",
        "columns": ["status", "created_at"],
        "index_name": "idx_suggestions_status_created",
        "description": "Status filtering with date sorting (common in suggestion queries)",
        "order": "DESC"  # Most queries order by created_at DESC
    },
    {
        "table": "patterns",
        "columns": ["pattern_type", "confidence"],
        "index_name": "idx_patterns_type_confidence",
        "description": "Pattern type with confidence sorting",
        "order": "DESC"
    },
    {
        "table": "ask_ai_queries",
        "columns": ["user_id", "created_at"],
        "index_name": "idx_ask_ai_queries_user_created",
        "description": "User query history with date sorting",
        "order": "DESC"
    },
    {
        "table": "clarification_sessions",
        "columns": ["status", "created_at"],
        "index_name": "idx_clarification_sessions_status_created",
        "description": "Session status queries with date sorting",
        "order": "DESC"
    },
    {
        "table": "patterns",
        "columns": ["deprecated", "confidence"],
        "index_name": "idx_patterns_active_confidence",
        "description": "Active patterns (deprecated=0) with confidence sorting",
        "order": "DESC"
    }
]

def index_exists(conn, index_name):
    """Check if an index exists"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' 
        AND name=?
    """, (index_name,))
    return cursor.fetchone() is not None

def create_composite_index(conn, index_def):
    """Create a composite index if it doesn't exist"""
    table = index_def["table"]
    columns = index_def["columns"]
    index_name = index_def["index_name"]
    description = index_def["description"]
    order = index_def.get("order", "")
    
    if index_exists(conn, index_name):
        print(f"  ✓ Index '{index_name}' already exists")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Build column list with ordering
        column_list = []
        for i, col in enumerate(columns):
            if i == len(columns) - 1 and order:
                # Apply ordering to last column
                column_list.append(f"{col} {order}")
            else:
                column_list.append(col)
        
        columns_sql = ", ".join(column_list)
        
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name} 
            ON {table}({columns_sql})
        """)
        conn.commit()
        print(f"  ✅ Created index '{index_name}' on {table}({', '.join(columns)})")
        print(f"     {description}")
        return True
    except sqlite3.Error as e:
        print(f"  ❌ Error creating index '{index_name}': {e}")
        return False

def verify_index(conn, index_name):
    """Verify an index exists and get its info"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA index_info({index_name})")
    return cursor.fetchall()

def main():
    """Main entry point"""
    print("=" * 80)
    print("ADDING COMPOSITE INDEXES FOR COMMON QUERY PATTERNS")
    print("=" * 80)
    print()
    print(f"Database: {DB_PATH}")
    print()
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("   Make sure you're running this script inside the Docker container")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA foreign_keys=ON")
        
        indexes_created = 0
        indexes_existing = 0
        
        print("Analyzing query patterns and creating composite indexes...")
        print("-" * 80)
        
        for index_def in COMPOSITE_INDEXES:
            table = index_def["table"]
            columns = index_def["columns"]
            index_name = index_def["index_name"]
            
            print(f"\n{table}.({', '.join(columns)}):")
            
            # Check if index already exists
            if index_exists(conn, index_name):
                indexes_existing += 1
                print(f"  ✓ Index '{index_name}' already exists")
                # Verify it
                info = verify_index(conn, index_name)
                if info:
                    print(f"    Verified: {len(info)} column(s) indexed")
            else:
                # Create the index
                if create_composite_index(conn, index_def):
                    indexes_created += 1
                    # Verify it
                    info = verify_index(conn, index_name)
                    if info:
                        print(f"    Verified: {len(info)} column(s) indexed")
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        print(f"✅ Indexes created: {indexes_created}")
        print(f"✓ Indexes already existing: {indexes_existing}")
        print(f"📊 Total composite indexes: {len(COMPOSITE_INDEXES)}")
        print()
        
        # Performance note
        print("Performance Impact:")
        print("  - Queries filtering by status + ordering by created_at will be faster")
        print("  - Pattern type + confidence queries will benefit from composite index")
        print("  - User query history lookups will be optimized")
        print()
        print("Note: Run ANALYZE after creating indexes to update query planner statistics")
        
        conn.close()
        return indexes_created > 0 or indexes_existing == len(COMPOSITE_INDEXES)
        
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

