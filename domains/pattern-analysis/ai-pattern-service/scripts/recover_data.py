#!/usr/bin/env python3
"""
Recover data from a PostgreSQL database backup.

This script attempts to extract pattern data from a backup and insert it into
the current database.
"""

import logging
import os
import sys

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def recover_patterns(source_url: str, target_url: str):
    """Recover patterns from source database to target database."""
    try:
        source_conn = psycopg2.connect(source_url)
        source_conn.set_session(readonly=True)
        source_cursor = source_conn.cursor()

        target_conn = psycopg2.connect(target_url)
        target_cursor = target_conn.cursor()

        # Ensure target table exists
        target_cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id SERIAL PRIMARY KEY,
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
        target_conn.commit()

        # Try to recover patterns
        recovered_count = 0
        error_count = 0

        try:
            source_cursor.execute("SELECT * FROM patterns LIMIT 10000")
            columns = [desc[0] for desc in source_cursor.description]
            for row in source_cursor:
                row_dict = dict(zip(columns, row))
                try:
                    target_cursor.execute("""
                        INSERT INTO patterns
                        (pattern_type, device_id, pattern_metadata, confidence, occurrences,
                         created_at, first_seen, last_seen, trend_direction, trend_strength, confidence_history_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        row_dict.get('pattern_type'),
                        row_dict.get('device_id'),
                        row_dict.get('pattern_metadata'),
                        row_dict.get('confidence'),
                        row_dict.get('occurrences', 0),
                        row_dict.get('created_at'),
                        row_dict.get('first_seen'),
                        row_dict.get('last_seen'),
                        row_dict.get('trend_direction'),
                        row_dict.get('trend_strength'),
                        row_dict.get('confidence_history_count', 0)
                    ))
                    recovered_count += 1
                except Exception as e:
                    error_count += 1
                    if error_count < 10:
                        logger.warning(f"Failed to recover pattern row: {e}")
        except Exception as e:
            logger.error(f"Failed to query patterns table: {e}")

        target_conn.commit()
        source_conn.close()
        target_conn.close()

        logger.info(f"Recovered {recovered_count} patterns, {error_count} errors")
        return recovered_count > 0

    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        return False


def main():
    source_url = os.environ.get("SOURCE_DATABASE_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq_backup")
    target_url = os.environ.get("POSTGRES_URL", os.environ.get("DATABASE_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq"))

    logger.info(f"Attempting to recover data from {source_url}")

    if recover_patterns(source_url, target_url):
        logger.info("Recovery successful.")
        logger.info("Data has been inserted into the target database.")
        return 0
    else:
        logger.error("Recovery failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
