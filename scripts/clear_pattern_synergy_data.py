#!/usr/bin/env python3
"""Clear pattern and synergy data from database for fresh analysis"""
import sqlite3
import sys

db_path = "/app/data/ai_automation.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 70)
    print("CLEARING PATTERN AND SYNERGY DATA")
    print("=" * 70)

    # Get counts before deletion
    cursor.execute("SELECT COUNT(*) FROM patterns")
    pattern_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM synergy_opportunities")
    synergy_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM discovered_synergies")
    ml_synergy_count = cursor.fetchone()[0]

    # Check if pattern_history table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_history'")
    history_table_exists = cursor.fetchone() is not None
    history_count = 0
    if history_table_exists:
        cursor.execute("SELECT COUNT(*) FROM pattern_history")
        history_count = cursor.fetchone()[0]

    print("\n📊 Current Data Counts:")
    print(f"   Patterns: {pattern_count}")
    print(f"   Pattern History: {history_count}")
    print(f"   Synergy Opportunities: {synergy_count}")
    print(f"   Discovered Synergies (ML): {ml_synergy_count}")

    # Delete in order (respecting foreign keys if any)
    print("\n🗑️  Deleting data...")

    # Delete pattern_history first (if exists)
    if history_count > 0:
        cursor.execute("DELETE FROM pattern_history")
        print(f"   ✅ Deleted {history_count} pattern history records")

    # Delete discovered_synergies
    if ml_synergy_count > 0:
        cursor.execute("DELETE FROM discovered_synergies")
        print(f"   ✅ Deleted {ml_synergy_count} ML-discovered synergies")

    # Delete synergy_opportunities
    if synergy_count > 0:
        cursor.execute("DELETE FROM synergy_opportunities")
        print(f"   ✅ Deleted {synergy_count} synergy opportunities")

    # Delete patterns last
    if pattern_count > 0:
        cursor.execute("DELETE FROM patterns")
        print(f"   ✅ Deleted {pattern_count} patterns")

    # Commit changes
    conn.commit()

    # Verify deletion
    cursor.execute("SELECT COUNT(*) FROM patterns")
    remaining_patterns = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM synergy_opportunities")
    remaining_synergies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM discovered_synergies")
    remaining_ml_synergies = cursor.fetchone()[0]

    print("\n✅ Verification:")
    print(f"   Remaining Patterns: {remaining_patterns}")
    print(f"   Remaining Synergies: {remaining_synergies}")
    print(f"   Remaining ML Synergies: {remaining_ml_synergies}")

    if remaining_patterns == 0 and remaining_synergies == 0 and remaining_ml_synergies == 0:
        print("\n✅ All pattern and synergy data cleared successfully!")
    else:
        print("\n⚠️  Warning: Some data remains")

    print("=" * 70)

    conn.close()
    sys.exit(0)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

