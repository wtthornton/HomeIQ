#!/usr/bin/env python3
"""Check device names in devices table"""
import os
import sys

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

conn = psycopg2.connect(POSTGRES_URL)
cursor = conn.cursor()

print("=" * 120)
print("DEVICES TABLE - Hue Devices")
print("=" * 120)

# Check if devices table exists
cursor.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'core' AND table_name = 'devices'
""")
if not cursor.fetchone():
    print("devices table does not exist in core schema")
    conn.close()
    sys.exit(1)

# Get schema
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'core' AND table_name = 'devices'
    ORDER BY ordinal_position
""")
columns = cursor.fetchall()
print("Devices table columns:")
for col in columns:
    print(f"  {col[0]} ({col[1]})")

print("\n" + "=" * 120)
print("Hue Devices in devices table:")
print("=" * 120)

query = """
SELECT device_id, name, name_by_user, manufacturer, model, area_id
FROM core.devices
WHERE manufacturer ILIKE '%%hue%%' OR manufacturer ILIKE '%%philips%%' OR name ILIKE '%%hue%%' OR name ILIKE '%%Office%%'
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
        print(f"{str(device_id or ''):<50} {str(name or ''):<40} {str(name_by_user or ''):<40} {str(area_id or ''):<20}")
else:
    print("No Hue devices found in devices table")

print("\n" + "=" * 120)
print("Entities linked to Hue devices:")
print("=" * 120)

# Get entities that link to Hue devices
query = """
SELECT e.entity_id, e.device_id, e.friendly_name, e.name, e.name_by_user, d.name as device_name, d.name_by_user as device_name_by_user
FROM core.entities e
LEFT JOIN core.devices d ON e.device_id = d.device_id
WHERE e.entity_id LIKE '%%hue%%' AND e.device_id IS NOT NULL
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
        print(f"{str(entity_id or ''):<40} {str(device_id or ''):<50} {str(entity_friendly_name or ''):<30} {str(device_name or ''):<40} {str(device_name_by_user or ''):<40}")

conn.close()
