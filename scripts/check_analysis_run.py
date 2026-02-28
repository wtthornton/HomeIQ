#!/usr/bin/env python3
"""Check if daily analysis ran and what it did"""
import os

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

try:
    conn = psycopg2.connect(POSTGRES_URL)
    cursor = conn.cursor()

    print("=" * 70)
    print("DAILY ANALYSIS RUN CHECK")
    print("=" * 70)

    # Check recent patterns
    cursor.execute('''
        SELECT COUNT(*) FROM patterns.patterns
        WHERE created_at > NOW() - INTERVAL '24 hours'
    ''')
    new_patterns = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM patterns.patterns')
    total_patterns = cursor.fetchone()[0]

    # Check recent synergies
    cursor.execute('''
        SELECT COUNT(*) FROM patterns.synergy_opportunities
        WHERE created_at > NOW() - INTERVAL '24 hours'
    ''')
    new_synergies = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM patterns.synergy_opportunities')
    total_synergies = cursor.fetchone()[0]

    # Check ML synergies
    cursor.execute('''
        SELECT COUNT(*) FROM patterns.discovered_synergies
        WHERE discovered_at > NOW() - INTERVAL '24 hours'
    ''')
    new_ml_synergies = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM patterns.discovered_synergies')
    total_ml_synergies = cursor.fetchone()[0]

    # Check calibrated patterns
    cursor.execute('SELECT COUNT(*) FROM patterns.patterns WHERE calibrated = true')
    calibrated_patterns = cursor.fetchone()[0]

    # Check pattern statistics
    cursor.execute('''
        SELECT pattern_type, COUNT(*) as count,
               AVG(confidence) as avg_conf,
               AVG(raw_confidence) as avg_raw_conf,
               SUM(CASE WHEN calibrated = true THEN 1 ELSE 0 END) as calibrated_count
        FROM patterns.patterns
        GROUP BY pattern_type
    ''')
    pattern_stats = cursor.fetchall()

    # Get most recent pattern
    cursor.execute('''
        SELECT created_at, pattern_type, device_id, confidence, calibrated, raw_confidence
        FROM patterns.patterns
        ORDER BY created_at DESC
        LIMIT 1
    ''')
    latest_pattern = cursor.fetchone()

    # Get most recent synergy
    cursor.execute('''
        SELECT created_at, synergy_type, device_ids, confidence, validated_by_patterns
        FROM patterns.synergy_opportunities
        ORDER BY created_at DESC
        LIMIT 1
    ''')
    latest_synergy = cursor.fetchone()

    print(f"\n📊 PATTERNS:")
    print(f"   Total: {total_patterns}")
    print(f"   Created in last 24h: {new_patterns}")
    print(f"   Calibrated: {calibrated_patterns}")

    print(f"\n📊 SYNERGIES:")
    print(f"   Total: {total_synergies}")
    print(f"   Created in last 24h: {new_synergies}")

    print(f"\n📊 ML-DISCOVERED SYNERGIES:")
    print(f"   Total: {total_ml_synergies}")
    print(f"   Discovered in last 24h: {new_ml_synergies}")

    print(f"\n📊 PATTERN STATISTICS BY TYPE:")
    print("-" * 70)
    for row in pattern_stats:
        ptype, count, avg_conf, avg_raw_conf, calibrated = row
        avg_conf_str = f"{avg_conf:.3f}" if avg_conf else "N/A"
        avg_raw_str = f"{avg_raw_conf:.3f}" if avg_raw_conf else "N/A"
        print(f"   {ptype:20} Count: {count:5}  Avg Conf: {avg_conf_str:>6}  "
              f"Raw: {avg_raw_str:>6}  Calibrated: {calibrated}")

    if latest_pattern:
        print(f"\n📅 MOST RECENT PATTERN:")
        created_at, ptype, device_id, conf, calibrated, raw_conf = latest_pattern
        print(f"   Created: {created_at}")
        print(f"   Type: {ptype}")
        print(f"   Device: {device_id}")
        print(f"   Confidence: {conf:.3f}")
        print(f"   Calibrated: {calibrated}")
        print(f"   Raw Confidence: {raw_conf if raw_conf else 'N/A'}")

    if latest_synergy:
        print(f"\n📅 MOST RECENT SYNERGY:")
        created_at, stype, devices, conf, validated = latest_synergy
        print(f"   Created: {created_at}")
        print(f"   Type: {stype}")
        print(f"   Devices: {devices}")
        print(f"   Confidence: {conf:.3f}")
        print(f"   Validated: {validated}")

    print("\n" + "=" * 70)

    # Analysis conclusion
    if new_patterns > 0 or new_synergies > 0 or new_ml_synergies > 0:
        print("✅ ANALYSIS RAN: New patterns/synergies were created in the last 24 hours")
    else:
        print("⚠️  ANALYSIS DID NOT RUN: No new patterns/synergies in the last 24 hours")
        print("   This could mean:")
        print("   - No events were available for analysis")
        print("   - Analysis hasn't been triggered yet")
        print("   - Analysis is scheduled for later (default: 03:00 daily)")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
