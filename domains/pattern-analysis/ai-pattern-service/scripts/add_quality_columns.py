#!/usr/bin/env python3
"""
Add Quality Columns to Synergy Opportunities Table

2025 Enhancement: Adds quality_score, quality_tier, last_validated_at, and filter_reason columns
to the synergy_opportunities table.

Usage:
    python scripts/add_quality_columns.py [--db-path /path/to/database.db]
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def add_quality_columns(db_path: str, dry_run: bool = False) -> None:
    """
    Add quality columns to synergy_opportunities table.
    
    Args:
        db_path: Path to SQLite database file
        dry_run: If True, only show what would be done without making changes
    """
    print(f"{'[DRY RUN] ' if dry_run else ''}Adding quality columns to synergy_opportunities table...")
    print(f"Database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='synergy_opportunities'
        """)
        if not cursor.fetchone():
            print("ERROR: synergy_opportunities table does not exist!")
            sys.exit(1)
        
        # Check which columns already exist
        cursor.execute("PRAGMA table_info(synergy_opportunities)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        columns_to_add = [
            ('quality_score', 'FLOAT', 'NULL', 'Quality score (0.0-1.0)'),
            ('quality_tier', 'VARCHAR(20)', 'NULL', "Quality tier ('high', 'medium', 'low', 'poor')"),
            ('last_validated_at', 'TIMESTAMP', 'NULL', 'Last quality validation timestamp'),
            ('filter_reason', 'VARCHAR(200)', 'NULL', 'Reason if filtered (for audit)')
        ]
        
        columns_added = []
        for col_name, col_type, nullable, description in columns_to_add:
            if col_name in existing_columns:
                print(f"  ✓ Column '{col_name}' already exists (skipping)")
            else:
                if dry_run:
                    print(f"  [WOULD ADD] {col_name} ({col_type}, {nullable}) - {description}")
                else:
                    # SQLite doesn't support adding columns with specific types directly
                    # We need to use ALTER TABLE ADD COLUMN
                    alter_sql = f"ALTER TABLE synergy_opportunities ADD COLUMN {col_name} {col_type}"
                    if nullable == 'NULL':
                        alter_sql += " NULL"
                    cursor.execute(alter_sql)
                    print(f"  ✓ Added column '{col_name}' ({col_type})")
                    columns_added.append(col_name)
        
        if not dry_run and columns_added:
            conn.commit()
            print(f"\n✅ Successfully added {len(columns_added)} column(s) to synergy_opportunities table")
        elif dry_run:
            print(f"\n[DRY RUN] Would add {len([c for c, _, _, _ in columns_to_add if c not in existing_columns])} column(s)")
        else:
            print("\n✅ All columns already exist (no changes needed)")
        
        # Show final schema
        if not dry_run:
            print("\nCurrent columns in synergy_opportunities:")
            cursor.execute("PRAGMA table_info(synergy_opportunities)")
            for row in cursor.fetchall():
                col_id, col_name, col_type, not_null, default_val, pk = row
                nullable = "NOT NULL" if not_null else "NULL"
                print(f"  - {col_name}: {col_type} ({nullable})")
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Add quality columns to synergy_opportunities table'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='/app/data/ai_automation.db',
        help='Path to SQLite database file (default: /app/data/ai_automation.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    
    args = parser.parse_args()
    
    # Check if database file exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERROR: Database file does not exist: {db_path}")
        print("Hint: Use --db-path to specify the correct path")
        sys.exit(1)
    
    add_quality_columns(str(db_path), dry_run=args.dry_run)


if __name__ == '__main__':
    main()
