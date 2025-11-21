#!/usr/bin/env python3
"""Query patterns and synergies from ai-automation-service database"""
import sqlite3

db_path = "/app/data/ai_automation.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 70)
    print("PATTERNS & SYNERGIES DATABASE SUMMARY")
    print("=" * 70)

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("\n📊 Database: ai_automation.db")
    print("   Location: ai-automation-service:/app/data/ai_automation.db")
    print(f"   Tables: {len(tables)}")

    # Patterns
    print("\n" + "-" * 70)
    print("PATTERNS (patterns table)")
    print("-" * 70)
    try:
        cursor.execute("SELECT COUNT(*) FROM patterns")
        pattern_count = cursor.fetchone()[0]
        print(f"  Total Patterns: {pattern_count}")

        if pattern_count > 0:
            cursor.execute("SELECT pattern_type, COUNT(*) FROM patterns GROUP BY pattern_type")
            by_type = cursor.fetchall()
            print("  By Type:")
            for ptype, count in by_type:
                print(f"    - {ptype}: {count}")

            cursor.execute("SELECT AVG(confidence), MIN(confidence), MAX(confidence) FROM patterns")
            avg_conf, min_conf, max_conf = cursor.fetchone()
            print(f"  Confidence: avg={avg_conf:.2f}, min={min_conf:.2f}, max={max_conf:.2f}")
    except Exception as e:
        print(f"  Error: {e}")

    # Pattern History
    print("\n" + "-" * 70)
    print("PATTERN HISTORY (pattern_history table)")
    print("-" * 70)
    try:
        cursor.execute("SELECT COUNT(*) FROM pattern_history")
        history_count = cursor.fetchone()[0]
        print(f"  Total History Records: {history_count}")
    except Exception as e:
        print(f"  Table not found or error: {e}")

    # Synergy Opportunities
    print("\n" + "-" * 70)
    print("SYNERGY OPPORTUNITIES (synergy_opportunities table)")
    print("-" * 70)
    try:
        cursor.execute("SELECT COUNT(*) FROM synergy_opportunities")
        synergy_count = cursor.fetchone()[0]
        print(f"  Total Synergies: {synergy_count}")

        if synergy_count > 0:
            cursor.execute("SELECT synergy_type, COUNT(*) FROM synergy_opportunities GROUP BY synergy_type")
            by_type = cursor.fetchall()
            print("  By Type:")
            for stype, count in by_type:
                print(f"    - {stype}: {count}")

            cursor.execute("SELECT COUNT(*) FROM synergy_opportunities WHERE validated_by_patterns = 1")
            validated = cursor.fetchone()[0]
            print(f"  Pattern-Validated: {validated} ({validated/synergy_count*100:.1f}%)")

            cursor.execute("SELECT AVG(impact_score), AVG(confidence) FROM synergy_opportunities")
            avg_impact, avg_conf = cursor.fetchone()
            print(f"  Avg Impact Score: {avg_impact:.2f}")
            print(f"  Avg Confidence: {avg_conf:.2f}")
    except Exception as e:
        print(f"  Error: {e}")

    # Discovered Synergies
    print("\n" + "-" * 70)
    print("DISCOVERED SYNERGIES (discovered_synergies table)")
    print("-" * 70)
    try:
        cursor.execute("SELECT COUNT(*) FROM discovered_synergies")
        discovered_count = cursor.fetchone()[0]
        print(f"  Total Discovered: {discovered_count}")

        if discovered_count > 0:
            cursor.execute("SELECT COUNT(*) FROM discovered_synergies WHERE status = 'validated'")
            validated = cursor.fetchone()[0]
            print(f"  Validated: {validated}")
    except Exception as e:
        print(f"  Table not found or error: {e}")

    print("\n" + "=" * 70)
    print("STORAGE LOCATION SUMMARY")
    print("=" * 70)
    print("\n✅ Patterns:")
    print("   - Table: patterns")
    print("   - Database: ai-automation-service:/app/data/ai_automation.db")
    print("   - Purpose: Detected automation patterns (time_of_day, co_occurrence, anomaly)")
    print("   - History: pattern_history table for time-series snapshots")

    print("\n✅ Synergies:")
    print("   - Table: synergy_opportunities")
    print("   - Database: ai-automation-service:/app/data/ai_automation.db")
    print("   - Purpose: Cross-device synergy opportunities for automation")
    print("   - Additional: discovered_synergies table for ML-mined relationships")

    print("\n📦 Docker Volume:")
    print("   - Volume: ai_automation_data")
    print("   - Mount: /app/data in ai-automation-service container")
    print("   - Persistence: Data persists across container restarts")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

