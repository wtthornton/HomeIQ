#!/usr/bin/env python3
"""Add training_type column to training_runs table"""
import sqlite3
import sys
from pathlib import Path

db_path = Path('data/ai_automation.db')
if not db_path.exists():
    print(f'Database not found at {db_path}')
    sys.exit(1)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute('PRAGMA table_info(training_runs)')
    cols = [c[1] for c in cursor.fetchall()]
    
    if 'training_type' in cols:
        print('✓ Column training_type already exists')
        sys.exit(0)
    
    # Add column
    cursor.execute("ALTER TABLE training_runs ADD COLUMN training_type VARCHAR(20) NOT NULL DEFAULT 'soft_prompt'")
    conn.commit()
    
    # Verify
    cursor.execute('PRAGMA table_info(training_runs)')
    cols = [c[1] for c in cursor.fetchall()]
    if 'training_type' in cols:
        print('✓ SUCCESS: Column training_type added successfully')
    else:
        print('✗ ERROR: Column was not added')
        sys.exit(1)
        
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
        print('✓ Column training_type already exists')
    else:
        print(f'✗ ERROR: {e}')
        sys.exit(1)
except Exception as e:
    print(f'✗ ERROR: {e}')
    sys.exit(1)
finally:
    conn.close()

