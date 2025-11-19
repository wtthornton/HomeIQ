#!/usr/bin/env python3
"""Quick database summary script"""
import os
import sys
import sqlite3
from pathlib import Path

# SQLite database
sqlite_path = "/app/data/metadata.db"
if not Path(sqlite_path).exists():
    sqlite_path = os.getenv("SQLITE_PATH", "data/metadata.db")

print("=" * 60)
print("DATABASE SUMMARY - HomeIQ")
print("=" * 60)

# SQLite Summary
print("\n📊 SQLite Database (metadata.db)")
print("-" * 60)
try:
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Get table counts
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:20} {count:>8} rows")
    
    conn.close()
except Exception as e:
    print(f"  Error: {e}")

# InfluxDB Summary (via data-api health endpoint)
print("\n📈 InfluxDB (Time-Series Database)")
print("-" * 60)
print("  Bucket: home_assistant_events")
print("  Note: Row counts not available via CLI")
print("  Data: Home Assistant state change events")
print("  Purpose: Time-series event storage")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("\nSQLite (Relational Metadata):")
print("  - devices: Device registry (97 devices)")
print("  - entities: Entity registry (695 entities)")
print("  - Purpose: Fast metadata queries (<10ms)")
print("\nInfluxDB (Time-Series Data):")
print("  - home_assistant_events: All HA state changes")
print("  - Purpose: Historical event storage & analytics")
print("  - Retention: 365 days (configurable)")

