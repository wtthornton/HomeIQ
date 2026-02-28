#!/usr/bin/env python3
"""
Add partial indexes for filtered queries in PostgreSQL.

Partial indexes only index rows that match a WHERE clause, making them
more efficient for filtered queries.
"""
import os
import sys

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

# Partial indexes to create
PARTIAL_INDEXES = [
    {
        "table": "automation.suggestions",
        "columns": ["status", "created_at"],
        "where_clause": "status IN ('draft', 'refining')",
        "index_name": "idx_suggestions_active_status_created",
        "description": "Active suggestions only (draft, refining) with date sorting",
        "order": "DESC"
    },
    {
        "table": "automation.patterns",
        "columns": ["pattern_type", "device_id", "confidence"],
        "where_clause": "deprecated = 0",
        "index_name": "idx_patterns_active_type_device_confidence",
        "description": "Active patterns (deprecated=0) with type, device, and confidence",
        "order": "DESC"
    }
]

def index_exists(conn, index_name):
    """Check if an index exists"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT indexname FROM pg_catalog.pg_indexes
        WHERE indexname = %s
    """, (index_name,))
    return cursor.fetchone() is not None

def create_partial_index(conn, index_def):
    """Create a partial index if it doesn't exist"""
    table = index_def["table"]
    columns = index_def["columns"]
    where_clause = index_def["where_clause"]
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

        # Create partial index with WHERE clause
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table}({columns_sql})
            WHERE {where_clause}
        """)
        conn.commit()
        print(f"  ✅ Created partial index '{index_name}' on {table}({', '.join(columns)}) WHERE {where_clause}")
        print(f"     {description}")
        return True
    except psycopg2.Error as e:
        print(f"  ❌ Error creating index '{index_name}': {e}")
        conn.rollback()
        return False

def verify_index(conn, index_name):
    """Verify an index exists and get its column info"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.attname
        FROM pg_catalog.pg_index i
        JOIN pg_catalog.pg_class c ON c.oid = i.indexrelid
        JOIN pg_catalog.pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE c.relname = %s
    """, (index_name,))
    return cursor.fetchall()

def main():
    """Main entry point"""
    print("=" * 80)
    print("ADDING PARTIAL INDEXES FOR FILTERED QUERIES")
    print("=" * 80)
    print()
    print(f"Database: {POSTGRES_URL}")
    print()

    try:
        conn = psycopg2.connect(POSTGRES_URL)

        indexes_created = 0
        indexes_existing = 0

        print("Creating partial indexes for filtered queries...")
        print("-" * 80)

        for index_def in PARTIAL_INDEXES:
            table = index_def["table"]
            columns = index_def["columns"]
            where_clause = index_def["where_clause"]
            index_name = index_def["index_name"]

            print(f"\n{table}.({', '.join(columns)}) WHERE {where_clause}:")

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
                if create_partial_index(conn, index_def):
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
        print(f"📊 Total partial indexes: {len(PARTIAL_INDEXES)}")
        print()

        # Performance note
        print("Performance Impact:")
        print("  - Queries filtering active suggestions (draft/refining) will be faster")
        print("  - Queries filtering active patterns (deprecated=0) will be faster")
        print("  - Partial indexes use less storage than full indexes")
        print()
        print("Note: Run ANALYZE after creating indexes to update query planner statistics")

        conn.close()
        return indexes_created > 0 or indexes_existing == len(PARTIAL_INDEXES)

    except psycopg2.Error as e:
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
