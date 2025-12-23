#!/usr/bin/env python3
"""Quick script to add training_type column to training_runs table"""
import sqlite3
import sys

db_path = 'data/ai_automation.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute('PRAGMA table_info(training_runs)')
    cols = [c[1] for c in cursor.fetchall()]
    
    if 'training_type' in cols:
        print('Column training_type already exists')
        sys.exit(0)
    
    # Add column
    cursor.execute("ALTER TABLE training_runs ADD COLUMN training_type VARCHAR(20) NOT NULL DEFAULT 'soft_prompt'")
    conn.commit()
    
    # Verify
    cursor.execute('PRAGMA table_info(training_runs)')
    cols = [c[1] for c in cursor.fetchall()]
    if 'training_type' in cols:
        print('SUCCESS: Column training_type added')
    else:
        print('ERROR: Column was not added')
        sys.exit(1)
        
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    conn.close()

