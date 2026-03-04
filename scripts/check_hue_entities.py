#!/usr/bin/env python3
"""Check Hue entities in database"""
import os

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

conn = psycopg2.connect(POSTGRES_URL)
cursor = conn.cursor()

# Check total entities
cursor.execute('SELECT COUNT(*) FROM core.entities')
total = cursor.fetchone()[0]
print(f"Total entities in database: {total}\n")

# Check Hue entities
cursor.execute("""
    SELECT entity_id, name, name_by_user, original_name, friendly_name
    FROM core.entities
    WHERE entity_id LIKE '%%hue%%'
    ORDER BY entity_id
    LIMIT 20
""")
rows = cursor.fetchall()

print(f"Found {len(rows)} Hue entities:\n")
for row in rows:
    entity_id, name, name_by_user, original_name, friendly_name = row
    print(f"{entity_id}:")
    print(f"  name: {name}")
    print(f"  name_by_user: {name_by_user}")
    print(f"  original_name: {original_name}")
    print(f"  friendly_name: {friendly_name}")
    print()

# Check specific devices
specific = [
    'light.hue_color_downlight_1_5',
    'light.hue_color_downlight_1_3',
    'light.hue_color_downlight_1_7',
    'light.hue_play_1',
]

print("\nChecking specific devices:")
for entity_id in specific:
    cursor.execute("""
        SELECT entity_id, name, name_by_user, original_name, friendly_name
        FROM core.entities
        WHERE entity_id = %s
    """, (entity_id,))
    row = cursor.fetchone()
    if row:
        eid, name, name_by_user, original_name, friendly_name = row
        print(f"\n{entity_id}:")
        print(f"  name: {name}")
        print(f"  name_by_user: {name_by_user}")
        print(f"  original_name: {original_name}")
        print(f"  friendly_name: {friendly_name}")
    else:
        print(f"\n{entity_id}: NOT FOUND")

conn.close()
