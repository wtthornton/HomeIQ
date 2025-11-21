#!/usr/bin/env python3
"""Check device names in devices table"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

db_path = "services/data-api/data/metadata.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 120)
print("DEVICES TABLE - Hue Devices")
print("=" * 120)

# Check if devices table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
if not cursor.fetchone():
    print("devices table does not exist")
    conn.close()
    sys.exit(1)

# Get schema
cursor.execute("PRAGMA table_info(devices)")
columns = cursor.fetchall()
print("Devices table columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print("\n" + "=" * 120)
print("Hue Devices in devices table:")
print("=" * 120)

query = """
SELECT device_id, name, name_by_user, manufacturer, model, area_id
FROM devices
WHERE manufacturer LIKE '%hue%' OR manufacturer LIKE '%philips%' OR name LIKE '%hue%' OR name LIKE '%Office%'
ORDER BY name
LIMIT 50
"""

cursor.execute(query)
rows = cursor.fetchall()

if rows:
    print(f"{'device_id':<50} {'name':<40} {'name_by_user':<40} {'area_id':<20}")
    print("-" * 150)
    for row in rows:
        device_id, name, name_by_user, manufacturer, model, area_id = row
        print(f"{device_id or ''!s:<50} {name or ''!s:<40} {name_by_user or ''!s:<40} {area_id or ''!s:<20}")
else:
    print("No Hue devices found in devices table")

print("\n" + "=" * 120)
print("Entities linked to Hue devices:")
print("=" * 120)

# Get entities that link to Hue devices
query = """
SELECT e.entity_id, e.device_id, e.friendly_name, e.name, e.name_by_user, d.name as device_name, d.name_by_user as device_name_by_user
FROM entities e
LEFT JOIN devices d ON e.device_id = d.device_id
WHERE e.entity_id LIKE '%hue%' AND e.device_id IS NOT NULL
ORDER BY d.name, e.entity_id
LIMIT 20
"""

cursor.execute(query)
rows = cursor.fetchall()

if rows:
    print(f"{'entity_id':<40} {'device_id':<50} {'entity_friendly_name':<30} {'device_name':<40} {'device_name_by_user':<40}")
    print("-" * 200)
    for row in rows:
        entity_id, device_id, entity_friendly_name, entity_name, entity_name_by_user, device_name, device_name_by_user = row
        print(f"{entity_id or ''!s:<40} {device_id or ''!s:<50} {entity_friendly_name or ''!s:<30} {device_name or ''!s:<40} {device_name_by_user or ''!s:<40}")

conn.close()

