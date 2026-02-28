#!/usr/bin/env python3
"""Check what devices are in Device Intelligence database"""
import os
import sys

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

try:
    conn = psycopg2.connect(POSTGRES_URL)
    cursor = conn.cursor()

    # Get Office devices
    cursor.execute("SELECT name, manufacturer, model, integration, area_name FROM devices.devices WHERE area_name ILIKE '%%office%%' LIMIT 20")
    rows = cursor.fetchall()

    print(f"Found {len(rows)} devices in office area:")
    print("-" * 80)
    for row in rows:
        print(f"Name: {row[0]}")
        print(f"  Manufacturer: {row[1]}")
        print(f"  Model: {row[2]}")
        print(f"  Integration: {row[3]}")
        print(f"  Area: {row[4]}")
        print()

    # Check all manufacturers
    cursor.execute("SELECT DISTINCT manufacturer FROM devices.devices WHERE manufacturer IS NOT NULL")
    manufacturers = cursor.fetchall()
    print(f"\nAll manufacturers in database ({len(manufacturers)} total):")
    for mfr in manufacturers:
        print(f"  - {mfr[0]}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
