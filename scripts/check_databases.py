#!/usr/bin/env python3
"""Check both database files for entities"""
import os
import sqlite3

dbs = [
    "services/data-api/data/metadata.db",
    "data/metadata.db",
]

for db_path in dbs:
    print(f"\n=== {db_path} ===")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if entities table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM entities")
                count = cursor.fetchone()[0]
                print(f"Entities table exists: {count} entities")

                # Check Hue entities
                cursor.execute("SELECT COUNT(*) FROM entities WHERE entity_id LIKE '%hue%'")
                hue_count = cursor.fetchone()[0]
                print(f"Hue entities: {hue_count}")

                # Sample entities
                cursor.execute("SELECT entity_id, name, name_by_user FROM entities LIMIT 3")
                rows = cursor.fetchall()
                if rows:
                    print("Sample entities:")
                    for row in rows:
                        print(f"  {row[0]}: name={row[1]}, name_by_user={row[2]}")
            else:
                print("Entities table does not exist")

            conn.close()
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Database file does not exist")

