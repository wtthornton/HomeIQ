#!/usr/bin/env python3
"""Check time-of-day patterns in the database."""

import json
import os
import sys

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

def main():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        cursor = conn.cursor()

        # Get time-of-day patterns
        cursor.execute("""
            SELECT id, pattern_type, device_id, pattern_metadata, confidence
            FROM patterns.patterns
            WHERE pattern_type = 'time_of_day'
            LIMIT 20
        """)
        patterns = cursor.fetchall()

        print(f"Time-of-day patterns: {len(patterns)}")
        print("\nSample patterns:")

        time_groups = {}

        for p in patterns:
            pattern_id, pattern_type, device_id, metadata_str, confidence = p

            # Parse metadata
            try:
                metadata = json.loads(metadata_str) if isinstance(metadata_str, str) and metadata_str else (metadata_str if isinstance(metadata_str, dict) else {})
            except (json.JSONDecodeError, TypeError, ValueError):
                metadata = {}

            hour = metadata.get('hour')
            minute = metadata.get('minute')
            cluster = metadata.get('cluster')

            print(f"  ID: {pattern_id}, Device: {device_id}")
            print(f"    Hour: {hour}, Minute: {minute}, Cluster: {cluster}")
            print(f"    Metadata keys: {list(metadata.keys())}")

            # Group by time
            if hour is not None:
                # Use hour only for grouping (more lenient)
                time_key = f"{hour:02d}:00" if isinstance(hour, int) else str(hour)
                if time_key not in time_groups:
                    time_groups[time_key] = []
                time_groups[time_key].append(device_id)

        print(f"\n\nTime groups (hour only):")
        for time_key, devices in sorted(time_groups.items()):
            print(f"  {time_key}: {len(devices)} devices")
            if len(devices) >= 2:
                print(f"    → Could create schedule_based synergy!")
                print(f"    Devices: {devices[:5]}...")

        # Count total time patterns
        cursor.execute("SELECT COUNT(*) FROM patterns.patterns WHERE pattern_type = 'time_of_day'")
        total = cursor.fetchone()[0]
        print(f"\nTotal time-of-day patterns: {total}")

        # Check if any have hour/minute
        cursor.execute("""
            SELECT COUNT(*) FROM patterns.patterns
            WHERE pattern_type = 'time_of_day'
            AND pattern_metadata::text LIKE '%%hour%%'
        """)
        with_hour = cursor.fetchone()[0]
        print(f"Patterns with 'hour' in metadata: {with_hour}")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
