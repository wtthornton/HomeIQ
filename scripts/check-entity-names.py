#!/usr/bin/env python3
"""Check entity name fields in PostgreSQL database"""
import os

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

print(f"Checking database: {POSTGRES_URL}")

conn = psycopg2.connect(POSTGRES_URL)
cursor = conn.cursor()

# Check specific entities
entities_to_check = [
    'light.hue_color_downlight_1_5',  # Office Back Left / LR Back Right Ceiling
    'light.hue_color_downlight_1_3',  # Downlight 13
    'light.hue_color_downlight_1_7',  # Downlight 15
    'light.hue_play_1',  # Play 1
]

print("\n" + "=" * 100)
print("ENTITY NAME FIELDS IN DATABASE")
print("=" * 100)

for entity_id in entities_to_check:
    cursor.execute("""
        SELECT entity_id, name, name_by_user, original_name, friendly_name
        FROM core.entities
        WHERE entity_id = %s
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
    FROM core.entities
    WHERE entity_id LIKE '%%hue%%'
    ORDER BY entity_id
    LIMIT 20
""")

rows = cursor.fetchall()
for row in rows:
    eid, name, name_by_user, original_name, friendly_name = row
    print(f"{eid}:")
    print(f"  name={name if name else 'NULL'}, name_by_user={name_by_user if name_by_user else 'NULL'}, original_name={original_name if original_name else 'NULL'}, friendly_name={friendly_name if friendly_name else 'NULL'}")

conn.close()
