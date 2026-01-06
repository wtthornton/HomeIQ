#!/usr/bin/env python3
"""
Recover data from corrupted SQLite database.

This script attempts to extract as much data as possible from a corrupted database
and create a new clean database.
"""

import sqlite3
import sys
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def recover_patterns(corrupted_db: str, new_db: str):
    """Recover patterns from corrupted database."""
    try:
        # Connect to corrupted database (read-only if possible)
        corrupted_conn = sqlite3.connect(f"file:{corrupted_db}?mode=ro", uri=True)
        corrupted_conn.row_factory = sqlite3.Row
        
        # Create new database
        new_conn = sqlite3.connect(new_db)
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                device_id TEXT,
                pattern_metadata TEXT,
                confidence REAL NOT NULL,
                occurrences INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                trend_direction TEXT,
                trend_strength REAL,
                confidence_history_count INTEGER DEFAULT 0
            )
        """)
        
        # Try to recover patterns
        recovered_count = 0
        error_count = 0
        
        try:
            cursor = corrupted_conn.execute("SELECT * FROM patterns LIMIT 10000")
            for row in cursor:
                try:
                    new_conn.execute("""
                        INSERT INTO patterns 
                        (pattern_type, device_id, pattern_metadata, confidence, occurrences,
                         created_at, first_seen, last_seen, trend_direction, trend_strength, confidence_history_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('pattern_type'),
                        row.get('device_id'),
                        row.get('pattern_metadata'),
                        row.get('confidence'),
                        row.get('occurrences', 0),
                        row.get('created_at'),
                        row.get('first_seen'),
                        row.get('last_seen'),
                        row.get('trend_direction'),
                        row.get('trend_strength'),
                        row.get('confidence_history_count', 0)
                    ))
                    recovered_count += 1
                except Exception as e:
                    error_count += 1
                    if error_count < 10:  # Log first 10 errors
                        logger.warning(f"Failed to recover pattern row: {e}")
        except Exception as e:
            logger.error(f"Failed to query patterns table: {e}")
        
        new_conn.commit()
        corrupted_conn.close()
        new_conn.close()
        
        logger.info(f"Recovered {recovered_count} patterns, {error_count} errors")
        return recovered_count > 0
        
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        return False


def main():
    corrupted_db = "/app/data/ai_automation.db"
    new_db = "/app/data/ai_automation_recovered.db"
    
    logger.info(f"Attempting to recover data from {corrupted_db}")
    
    if recover_patterns(corrupted_db, new_db):
        logger.info(f"Recovery successful. New database: {new_db}")
        logger.info("You can now replace the old database with the recovered one.")
        return 0
    else:
        logger.error("Recovery failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
