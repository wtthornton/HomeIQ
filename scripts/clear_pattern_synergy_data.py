#!/usr/bin/env python3
"""Clear pattern and synergy data from database for fresh analysis"""
import sqlite3
import sys
import os
from pathlib import Path

# Try to find the database in common locations
possible_paths = [
    '/app/data/ai_automation.db',  # Docker path
    'data/ai_automation.db',  # Root data directory
    'services/ai-automation-service/data/ai_automation.db',  # Local dev path
    './data/ai_automation.db',  # Relative to script location
    str(Path(__file__).parent.parent / 'data' / 'ai_automation.db'),  # Absolute from script root
    str(Path(__file__).parent.parent / 'services' / 'ai-automation-service' / 'data' / 'ai_automation.db'),  # Absolute from script
]

db_path = None
for path in possible_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("❌ Error: Could not find ai_automation.db database")
    print("   Searched in:")
    for path in possible_paths:
        print(f"     - {path}")
    sys.exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("CLEARING PATTERN AND SYNERGY DATA")
    print("=" * 70)
    
    # Check which tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    # Get counts before deletion (only for existing tables)
    pattern_count = 0
    synergy_count = 0
    ml_synergy_count = 0
    history_count = 0
    
    if 'patterns' in existing_tables:
        cursor.execute('SELECT COUNT(*) FROM patterns')
        pattern_count = cursor.fetchone()[0]
    
    if 'synergy_opportunities' in existing_tables:
        cursor.execute('SELECT COUNT(*) FROM synergy_opportunities')
        synergy_count = cursor.fetchone()[0]
    
    if 'discovered_synergies' in existing_tables:
        cursor.execute('SELECT COUNT(*) FROM discovered_synergies')
        ml_synergy_count = cursor.fetchone()[0]
    
    if 'pattern_history' in existing_tables:
        cursor.execute('SELECT COUNT(*) FROM pattern_history')
        history_count = cursor.fetchone()[0]
    
    print(f"\n📊 Current Data Counts:")
    print(f"   Patterns: {pattern_count}")
    print(f"   Pattern History: {history_count}")
    print(f"   Synergy Opportunities: {synergy_count}")
    print(f"   Discovered Synergies (ML): {ml_synergy_count}")
    
    # Delete in order (respecting foreign keys if any)
    print(f"\n🗑️  Deleting data...")
    
    # Delete pattern_history first (if exists)
    if history_count > 0:
        cursor.execute('DELETE FROM pattern_history')
        print(f"   ✅ Deleted {history_count} pattern history records")
    
    # Delete discovered_synergies
    if ml_synergy_count > 0:
        cursor.execute('DELETE FROM discovered_synergies')
        print(f"   ✅ Deleted {ml_synergy_count} ML-discovered synergies")
    
    # Delete synergy_opportunities
    if synergy_count > 0:
        cursor.execute('DELETE FROM synergy_opportunities')
        print(f"   ✅ Deleted {synergy_count} synergy opportunities")
    
    # Delete patterns last
    if pattern_count > 0:
        cursor.execute('DELETE FROM patterns')
        print(f"   ✅ Deleted {pattern_count} patterns")
    
    # Commit changes
    conn.commit()
    
    # Verify deletion
    remaining_patterns = 0
    remaining_synergies = 0
    remaining_ml_synergies = 0
    
    if 'patterns' in existing_tables:
        cursor.execute('SELECT COUNT(*) FROM patterns')
        remaining_patterns = cursor.fetchone()[0]
    
    if 'synergy_opportunities' in existing_tables:
        cursor.execute('SELECT COUNT(*) FROM synergy_opportunities')
        remaining_synergies = cursor.fetchone()[0]
    
    if 'discovered_synergies' in existing_tables:
        cursor.execute('SELECT COUNT(*) FROM discovered_synergies')
        remaining_ml_synergies = cursor.fetchone()[0]
    
    print(f"\n✅ Verification:")
    print(f"   Remaining Patterns: {remaining_patterns}")
    print(f"   Remaining Synergies: {remaining_synergies}")
    print(f"   Remaining ML Synergies: {remaining_ml_synergies}")
    
    if remaining_patterns == 0 and remaining_synergies == 0 and remaining_ml_synergies == 0:
        print(f"\n✅ All pattern and synergy data cleared successfully!")
    else:
        print(f"\n⚠️  Warning: Some data remains")
    
    print("=" * 70)
    
    conn.close()
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

