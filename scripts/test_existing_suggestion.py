#!/usr/bin/env python3
"""Check existing suggestions from database to verify device names"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

db_path = "services/ai-automation-service/data/ai_automation.db"

if not os.path.exists(db_path):
    print(f"[ERROR] Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 120)
print("CHECKING EXISTING SUGGESTIONS FOR DEVICE NAMES")
print("=" * 120)

# Get recent suggestions
cursor.execute("""
    SELECT query_id, suggestion_id, devices_involved, created_at
    FROM suggestions
    WHERE devices_involved IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 5
""")

suggestions = cursor.fetchall()

if not suggestions:
    print("\n[WARN] No suggestions found in database")
    sys.exit(0)

print(f"\nFound {len(suggestions)} recent suggestion(s):\n")

for row in suggestions:
    query_id = row["query_id"]
    suggestion_id = row["suggestion_id"]
    devices_involved_json = row["devices_involved"]
    created_at = row["created_at"]

    print(f"--- Suggestion {suggestion_id} ---")
    print(f"Query ID: {query_id}")
    print(f"Created: {created_at}")

    if devices_involved_json:
        try:
            devices_involved = json.loads(devices_involved_json) if isinstance(devices_involved_json, str) else devices_involved_json
            print(f"\nDevices Involved ({len(devices_involved)}):")

            friendly_names = 0
            generic_names = 0

            for device in devices_involved:
                print(f"  - {device}")

                # Check if it's a friendly name
                if any(keyword in device for keyword in ["Office", "Back", "Front", "Left", "Right", "Go"]):
                    friendly_names += 1
                    print("    [OK] Friendly name")
                elif any(keyword in device.lower() for keyword in ["hue color downlight", "downlight", "hue_play"]):
                    generic_names += 1
                    print("    [WARN] Generic name")

            print("\nSummary:")
            print(f"  Friendly names: {friendly_names}")
            print(f"  Generic names: {generic_names}")

            if friendly_names > 0:
                print("  [PASS] Found friendly device names!")
            elif generic_names > 0:
                print("  [FAIL] Still showing generic device names")
        except Exception as e:
            print(f"  [ERROR] Failed to parse devices_involved: {e}")

    print()

conn.close()

