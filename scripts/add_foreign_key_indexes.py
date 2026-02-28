#!/usr/bin/env python3
"""
Add indexes on foreign key columns in PostgreSQL database.

This script checks for existing indexes on foreign key columns and adds
missing indexes to improve JOIN performance.
"""
import os
import sys

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

# Foreign keys that need indexes
FK_INDEXES = [
    {
        "table": "automation.suggestions",
        "column": "pattern_id",
        "index_name": "idx_suggestions_pattern_id",
        "description": "Index on suggestions.pattern_id (FK to patterns.id)"
    },
    {
        "table": "automation.user_feedback",
        "column": "suggestion_id",
        "index_name": "idx_user_feedback_suggestion_id",
        "description": "Index on user_feedback.suggestion_id (FK to suggestions.id)"
    }
]

def get_existing_indexes(conn, table_name):
    """Get list of existing indexes for a table"""
    # Split schema.table if present
    parts = table_name.split(".")
    if len(parts) == 2:
        schema_name, tbl_name = parts
    else:
        schema_name, tbl_name = "public", parts[0]

    cursor = conn.cursor()
    cursor.execute("""
        SELECT indexname FROM pg_catalog.pg_indexes
        WHERE schemaname = %s AND tablename = %s
    """, (schema_name, tbl_name))
    return [row[0] for row in cursor.fetchall()]

def index_exists(conn, index_name):
    """Check if an index exists"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT indexname FROM pg_catalog.pg_indexes
        WHERE indexname = %s
    """, (index_name,))
    return cursor.fetchone() is not None

def create_index(conn, index_def):
    """Create an index if it doesn't exist"""
    table = index_def["table"]
    column = index_def["column"]
    index_name = index_def["index_name"]
    description = index_def["description"]

    if index_exists(conn, index_name):
        print(f"  ✓ Index '{index_name}' already exists")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table}({column})
        """)
        conn.commit()
        print(f"  ✅ Created index '{index_name}' on {table}.{column}")
        print(f"     {description}")
        return True
    except psycopg2.Error as e:
        print(f"  ❌ Error creating index '{index_name}': {e}")
        conn.rollback()
        return False

def main():
    """Main entry point"""
    print("=" * 80)
    print("ADDING FOREIGN KEY INDEXES")
    print("=" * 80)
    print()
    print(f"Database: {POSTGRES_URL}")
    print()

    try:
        conn = psycopg2.connect(POSTGRES_URL)

        indexes_created = 0
        indexes_existing = 0

        print("Checking existing indexes...")
        print("-" * 80)

        for index_def in FK_INDEXES:
            table = index_def["table"]
            column = index_def["column"]
            index_name = index_def["index_name"]

            print(f"\n{table}.{column}:")

            # Check if index already exists
            if index_exists(conn, index_name):
                indexes_existing += 1
                print(f"  ✓ Index '{index_name}' already exists")
            else:
                # Check existing indexes on the table
                existing = get_existing_indexes(conn, table)
                if existing:
                    print(f"  Existing indexes on {table}: {', '.join(existing)}")

                # Create the index
                if create_index(conn, index_def):
                    indexes_created += 1

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        print(f"✅ Indexes created: {indexes_created}")
        print(f"✓ Indexes already existing: {indexes_existing}")
        print(f"📊 Total foreign keys checked: {len(FK_INDEXES)}")
        print()

        # Verify indexes
        print("Verifying indexes...")
        print("-" * 80)
        for index_def in FK_INDEXES:
            index_name = index_def["index_name"]
            if index_exists(conn, index_name):
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.attname
                    FROM pg_catalog.pg_index i
                    JOIN pg_catalog.pg_class c ON c.oid = i.indexrelid
                    JOIN pg_catalog.pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE c.relname = %s
                """, (index_name,))
                info = cursor.fetchall()
                if info:
                    print(f"  ✓ {index_name}: {len(info)} column(s) indexed")

        conn.close()
        return indexes_created > 0 or indexes_existing == len(FK_INDEXES)

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
