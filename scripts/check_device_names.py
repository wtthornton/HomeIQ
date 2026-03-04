#!/usr/bin/env python3
"""Check device names in database"""
import os

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

conn = psycopg2.connect(POSTGRES_URL)
cursor = conn.cursor()

# Search for devices
print("=" * 120)
print("DEVICE NAME FIELDS IN DATABASE")
print("=" * 120)
print(f"{'Entity ID':<40} {'name':<30} {'name_by_user':<30} {'original_name':<30} {'friendly_name':<30}")
print("-" * 120)

query = """
SELECT entity_id, name, name_by_user, original_name, friendly_name
FROM core.entities
WHERE entity_id LIKE '%%hue%%'
   OR friendly_name ILIKE '%%Office%%'
   OR friendly_name ILIKE '%%Downlight%%'
   OR friendly_name ILIKE '%%Play%%'
   OR friendly_name ILIKE '%%LR%%'
   OR name ILIKE '%%Office%%'
   OR name_by_user ILIKE '%%Office%%'
ORDER BY friendly_name
LIMIT 30
"""

cursor.execute(query)
rows = cursor.fetchall()

for row in rows:
    entity_id, name, name_by_user, original_name, friendly_name = row
    print(f"{entity_id:<40} {str(name or ''):<30} {str(name_by_user or ''):<30} {str(original_name or ''):<30} {str(friendly_name or ''):<30}")

print("\n" + "=" * 120)
print("SPECIFIC DEVICES CHECK")
print("=" * 120)

# Check specific devices mentioned
specific_devices = [
    ('light.hue_color_downlight_1_5', 'Office Back Left / LR Back Right Ceiling'),
    ('light.hue_color_downlight_1_3', 'Downlight 13'),
    ('light.hue_color_downlight_1_7', 'Downlight 15'),
    ('light.hue_play_1', 'Play 1'),
]

for entity_id_pattern, description in specific_devices:
    query = """
    SELECT entity_id, name, name_by_user, original_name, friendly_name
    FROM core.entities
    WHERE entity_id LIKE %s
    LIMIT 5
    """
    cursor.execute(query, (f'%{entity_id_pattern.split(".")[-1]}%',))
    rows = cursor.fetchall()
    if rows:
        print(f"\n{description} ({entity_id_pattern}):")
        for row in rows:
            eid, name, name_by_user, original_name, friendly_name = row
            print(f"  Entity ID: {eid}")
            print(f"  name: {name}")
            print(f"  name_by_user: {name_by_user}")
            print(f"  original_name: {original_name}")
            print(f"  friendly_name: {friendly_name}")
    else:
        print(f"\n{description} ({entity_id_pattern}): NOT FOUND")

conn.close()
