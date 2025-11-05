#!/usr/bin/env python3
"""Add Phase 2 columns to synergy_opportunities table if they don't exist"""
import sqlite3
import sys

db_path = '/app/data/ai_automation.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities') WHERE name = 'pattern_support_score'")
    has_pattern_support = cursor.fetchone()[0] > 0
    
    cursor.execute("SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities') WHERE name = 'validated_by_patterns'")
    has_validated = cursor.fetchone()[0] > 0
    
    cursor.execute("SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities') WHERE name = 'supporting_pattern_ids'")
    has_supporting = cursor.fetchone()[0] > 0
    
    print(f"pattern_support_score exists: {has_pattern_support}")
    print(f"validated_by_patterns exists: {has_validated}")
    print(f"supporting_pattern_ids exists: {has_supporting}")
    
    if not has_pattern_support:
        print("Adding pattern_support_score column...")
        cursor.execute("ALTER TABLE synergy_opportunities ADD COLUMN pattern_support_score FLOAT DEFAULT 0.0")
        cursor.execute("UPDATE synergy_opportunities SET pattern_support_score = 0.0 WHERE pattern_support_score IS NULL")
    
    if not has_validated:
        print("Adding validated_by_patterns column...")
        cursor.execute("ALTER TABLE synergy_opportunities ADD COLUMN validated_by_patterns BOOLEAN DEFAULT 0")
        cursor.execute("UPDATE synergy_opportunities SET validated_by_patterns = 0 WHERE validated_by_patterns IS NULL")
    
    if not has_supporting:
        print("Adding supporting_pattern_ids column...")
        cursor.execute("ALTER TABLE synergy_opportunities ADD COLUMN supporting_pattern_ids TEXT")
    
    conn.commit()
    print("✅ Columns added successfully!")
    
    conn.close()
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)

