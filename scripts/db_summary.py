#!/usr/bin/env python3
"""Quick database summary script"""
import os

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

print("=" * 60)
print("DATABASE SUMMARY - HomeIQ")
print("=" * 60)

# PostgreSQL Summary
print("\n📊 PostgreSQL Database (homeiq)")
print("-" * 60)
try:
    conn = psycopg2.connect(POSTGRES_URL)
    cursor = conn.cursor()

    # Get table counts per schema
    cursor.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'monitoring')
        AND table_type = 'BASE TABLE'
        ORDER BY table_schema, table_name
    """)
    tables = cursor.fetchall()

    current_schema = None
    for schema, table in tables:
        if schema != current_schema:
            current_schema = schema
            print(f"\n  Schema: {schema}")
        cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
        count = cursor.fetchone()[0]
        print(f"    {table:30} {count:>8} rows")

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
print("\nPostgreSQL (Relational Metadata):")
print("  - core.devices: Device registry")
print("  - core.entities: Entity registry")
print("  - automation.*: AI automation data")
print("  - patterns.*: Pattern analysis data")
print("  - Purpose: Fast metadata queries (<10ms)")
print("\nInfluxDB (Time-Series Data):")
print("  - home_assistant_events: All HA state changes")
print("  - Purpose: Historical event storage & analytics")
print("  - Retention: 365 days (configurable)")
