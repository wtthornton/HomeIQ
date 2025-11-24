#!/usr/bin/env python3
"""Verify database optimization deployment"""
import sqlite3
from pathlib import Path

DB_PATH = Path("/app/data/ai_automation.db")

# Expected new indexes
EXPECTED_INDEXES = [
    'idx_suggestions_pattern_id',
    'idx_user_feedback_suggestion_id',
    'idx_suggestions_status_created',
    'idx_patterns_type_confidence',
    'idx_ask_ai_queries_user_created',
    'idx_clarification_sessions_status_created',
    'idx_patterns_active_confidence',
    'idx_suggestions_active_status_created',
    'idx_patterns_active_type_device_confidence'
]

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name")
all_indexes = [row[0] for row in cursor.fetchall()]

print("=" * 80)
print("DEPLOYMENT VERIFICATION")
print("=" * 80)
print()
print(f"Total indexes found: {len(all_indexes)}")
print()
print("Expected optimization indexes:")
found = 0
for idx in EXPECTED_INDEXES:
    if idx in all_indexes:
        print(f"  ✅ {idx}")
        found += 1
    else:
        print(f"  ❌ {idx} - MISSING")

print()
print(f"Found: {found}/{len(EXPECTED_INDEXES)} expected indexes")
print()

if found == len(EXPECTED_INDEXES):
    print("✅ All optimization indexes deployed successfully!")
else:
    print(f"⚠️  {len(EXPECTED_INDEXES) - found} indexes missing")

conn.close()

