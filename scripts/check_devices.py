#!/usr/bin/env python3
"""Check what devices are in Device Intelligence database"""
import sqlite3
import sys

import os
# Try different possible paths
possible_paths = [
    "../data/device_intelligence.db",
    "./data/device_intelligence.db",
    "data/device_intelligence.db",
    os.path.join(os.path.expanduser("~"), ".homeiq/data/device_intelligence.db")
]

db_path = None
for path in possible_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("Could not find database file. Trying to list what's available:")
    print("Searching for device_intelligence.db...")
    import subprocess
    subprocess.run(["find", ".", "-name", "device_intelligence.db", "-type", "f"], shell=True)
    sys.exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get Office devices
    cursor.execute("SELECT name, manufacturer, model, integration, area_name FROM devices WHERE area_name LIKE '%office%' LIMIT 20")
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
    cursor.execute("SELECT DISTINCT manufacturer FROM devices WHERE manufacturer IS NOT NULL")
    manufacturers = cursor.fetchall()
    print(f"\nAll manufacturers in database ({len(manufacturers)} total):")
    for mfr in manufacturers:
        print(f"  - {mfr[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

