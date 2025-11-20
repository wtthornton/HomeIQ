#!/usr/bin/env python3
"""Fix metadata column name in discovered_synergies table"""
import sqlite3
import sys

db_path = '/app/data/ai_automation.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if metadata column exists
    cursor.execute('PRAGMA table_info(discovered_synergies)')
    cols = [col[1] for col in cursor.fetchall()]

    if 'metadata' in cols and 'synergy_metadata' not in cols:
        print("Renaming 'metadata' column to 'synergy_metadata'...")

        # SQLite 3.25.0+ supports RENAME COLUMN
        try:
            cursor.execute('ALTER TABLE discovered_synergies RENAME COLUMN metadata TO synergy_metadata')
            conn.commit()
            print("✅ Column renamed successfully using RENAME COLUMN")
        except sqlite3.OperationalError as e:
            if 'RENAME COLUMN' in str(e):
                print("SQLite version doesn't support RENAME COLUMN, using table recreation method...")
                # Fallback: recreate table
                # Get all data
                cursor.execute('SELECT * FROM discovered_synergies')
                rows = cursor.fetchall()

                # Get column names
                cursor.execute('PRAGMA table_info(discovered_synergies)')
                old_cols = [col[1] for col in cursor.fetchall()]
                metadata_idx = old_cols.index('metadata')

                # Drop old table
                cursor.execute('DROP TABLE discovered_synergies')

                # Recreate with new column name
                cursor.execute('''
                    CREATE TABLE discovered_synergies (
                        id INTEGER PRIMARY KEY,
                        synergy_id VARCHAR(36) NOT NULL UNIQUE,
                        trigger_entity VARCHAR(255) NOT NULL,
                        action_entity VARCHAR(255) NOT NULL,
                        source VARCHAR(20) NOT NULL DEFAULT 'mined',
                        support FLOAT NOT NULL,
                        confidence FLOAT NOT NULL,
                        lift FLOAT NOT NULL,
                        frequency INTEGER NOT NULL,
                        consistency FLOAT NOT NULL,
                        time_window_seconds INTEGER NOT NULL,
                        discovered_at DATETIME NOT NULL,
                        last_validated DATETIME,
                        validation_count INTEGER NOT NULL DEFAULT 0,
                        validation_passed BOOLEAN,
                        synergy_metadata JSON,
                        status VARCHAR(20) NOT NULL DEFAULT 'discovered',
                        rejection_reason TEXT
                    )
                ''')

                # Recreate indexes
                cursor.execute('CREATE UNIQUE INDEX ix_discovered_synergies_synergy_id ON discovered_synergies(synergy_id)')
                cursor.execute('CREATE INDEX ix_discovered_synergies_trigger ON discovered_synergies(trigger_entity)')
                cursor.execute('CREATE INDEX ix_discovered_synergies_action ON discovered_synergies(action_entity)')
                cursor.execute('CREATE INDEX ix_discovered_synergies_source ON discovered_synergies(source)')
                cursor.execute('CREATE INDEX ix_discovered_synergies_status ON discovered_synergies(status)')
                cursor.execute('CREATE INDEX ix_discovered_synergies_confidence ON discovered_synergies(confidence)')
                cursor.execute('CREATE INDEX ix_discovered_synergies_trigger_action ON discovered_synergies(trigger_entity, action_entity)')

                # Reinsert data (adjusting for renamed column)
                if rows:
                    placeholders = ','.join(['?' for _ in old_cols])
                    # Replace metadata column name in placeholders
                    old_cols_str = ','.join(old_cols)
                    old_cols_str = old_cols_str.replace('metadata', 'synergy_metadata')

                    # Insert rows
                    for row in rows:
                        cursor.execute(f'INSERT INTO discovered_synergies ({old_cols_str}) VALUES ({placeholders})', row)

                conn.commit()
                print("✅ Table recreated with renamed column")
            else:
                raise

    elif 'synergy_metadata' in cols:
        print("✅ Column already renamed to 'synergy_metadata'")
    else:
        print("⚠️ Neither 'metadata' nor 'synergy_metadata' column found")

    conn.close()
    sys.exit(0)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

