#!/usr/bin/env python3
"""Check entity name fields in database"""
import os
import sqlite3
import sys

# Find database
db_paths = [
    "services/data-api/data/metadata.db",
    "services/data-api/data/homeiq.db",
    "/app/data/metadata.db",  # Docker path
]

db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("ERROR: Database not found")
    sys.exit(1)

print(f"Checking database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check specific entities
entities_to_check = [
    "light.hue_color_downlight_1_5",  # Office Back Left / LR Back Right Ceiling
    "light.hue_color_downlight_1_3",  # Downlight 13
    "light.hue_color_downlight_1_7",  # Downlight 15
    "light.hue_play_1",  # Play 1
]

print("\n" + "=" * 100)
print("ENTITY NAME FIELDS IN DATABASE")
print("=" * 100)

for entity_id in entities_to_check:
    cursor.execute("""
        SELECT entity_id, name, name_by_user, original_name, friendly_name
        FROM entities
        WHERE entity_id = ?
    """, (entity_id,))

    row = cursor.fetchone()
    if row:
        eid, name, name_by_user, original_name, friendly_name = row
        print(f"\n{entity_id}:")
        print(f"  name: {name if name else 'NULL'}")
        print(f"  name_by_user: {name_by_user if name_by_user else 'NULL'}")
        print(f"  original_name: {original_name if original_name else 'NULL'}")
        print(f"  friendly_name: {friendly_name if friendly_name else 'NULL'}")
    else:
        print(f"\n{entity_id}: NOT FOUND IN DATABASE")

# Check all Hue entities
print("\n" + "=" * 100)
print("ALL HUE ENTITIES WITH NAME FIELDS")
print("=" * 100)

cursor.execute("""
    SELECT entity_id, name, name_by_user, original_name, friendly_name
    FROM entities
    WHERE entity_id LIKE '%hue%'
    ORDER BY entity_id
    LIMIT 20
""")

rows = cursor.fetchall()
for row in rows:
    eid, name, name_by_user, original_name, friendly_name = row
    print(f"{eid}:")
    print(f"  name={name if name else 'NULL'}, name_by_user={name_by_user if name_by_user else 'NULL'}, original_name={original_name if original_name else 'NULL'}, friendly_name={friendly_name if friendly_name else 'NULL'}")

conn.close()

