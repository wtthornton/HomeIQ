#!/usr/bin/env python3
"""Check entity table schema and name fields"""
import sqlite3
import os

db_path = 'services/data-api/data/metadata.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check table schema
print("Entity table columns:")
cursor.execute('PRAGMA table_info(entities)')
cols = cursor.fetchall()
for col in cols:
    print(f"  {col[1]} ({col[2]})")

# Check if name columns exist
name_cols = [c[1] for c in cols if 'name' in c[1].lower()]
print(f"\nName-related columns: {name_cols}")

# Check Hue entity with name fields
print("\nChecking light.hue_color_downlight_1_5:")
cursor.execute("""
    SELECT entity_id, name, name_by_user, original_name, friendly_name 
    FROM entities 
    WHERE entity_id = 'light.hue_color_downlight_1_5'
""")
row = cursor.fetchone()
if row:
    print(f"  entity_id: {row[0]}")
    print(f"  name: {row[1]}")
    print(f"  name_by_user: {row[2]}")
    print(f"  original_name: {row[3]}")
    print(f"  friendly_name: {row[4]}")
else:
    print("  Entity not found")

# Count entities with NULL name fields
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN name IS NULL THEN 1 ELSE 0 END) as null_name,
        SUM(CASE WHEN name_by_user IS NULL THEN 1 ELSE 0 END) as null_name_by_user,
        SUM(CASE WHEN original_name IS NULL THEN 1 ELSE 0 END) as null_original_name,
        SUM(CASE WHEN friendly_name IS NULL THEN 1 ELSE 0 END) as null_friendly_name
    FROM entities
    WHERE entity_id LIKE '%hue%'
""")
stats = cursor.fetchone()
if stats:
    total, null_name, null_name_by_user, null_original_name, null_friendly_name = stats
    print(f"\nHue entity name field statistics:")
    print(f"  Total Hue entities: {total}")
    print(f"  NULL name: {null_name}")
    print(f"  NULL name_by_user: {null_name_by_user}")
    print(f"  NULL original_name: {null_original_name}")
    print(f"  NULL friendly_name: {null_friendly_name}")

conn.close()

