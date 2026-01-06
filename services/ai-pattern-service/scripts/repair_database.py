#!/usr/bin/env python3
"""
Manual database repair script for SQLite corruption.

This script attempts to repair a corrupted SQLite database using multiple methods:
1. SQLite .recover command (if available)
2. VACUUM INTO (SQLite 3.27+)
3. Dump and recreate method

Usage:
    python repair_database.py [database_path]
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path
import shutil
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_integrity(db_path: Path) -> tuple[bool, str]:
    """Check database integrity."""
    try:
        conn = sqlite3.connect(str(db_path))
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        
        if result == "ok":
            return True, "ok"
        else:
            return False, result
    except Exception as e:
        return False, str(e)


def repair_with_recover(db_path: Path) -> bool:
    """Attempt repair using SQLite .recover command."""
    try:
        logger.info("Attempting repair using SQLite .recover command")
        recovered_path = db_path.with_suffix(".recovered")
        
        # Use sqlite3 command-line tool to recover
        recover_cmd = f'sqlite3 "{db_path}" ".recover" | sqlite3 "{recovered_path}"'
        result = subprocess.run(
            recover_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and recovered_path.exists():
            # Verify recovered database
            is_healthy, verify_result = check_integrity(recovered_path)
            
            if is_healthy:
                logger.info("Recovery successful using .recover command")
                # Replace old database
                old_db_path = db_path.with_suffix(".old")
                if old_db_path.exists():
                    old_db_path.unlink()
                db_path.rename(old_db_path)
                recovered_path.rename(db_path)
                logger.info("Database repair completed successfully using .recover")
                return True
            else:
                logger.warning(f"Recovered database still has issues: {verify_result[:200]}")
                recovered_path.unlink()
                return False
        else:
            logger.warning(f".recover command failed: {result.stderr}")
            return False
    except Exception as e:
        logger.warning(f"SQLite .recover method failed: {e}")
        return False


def repair_with_vacuum(db_path: Path) -> bool:
    """Attempt repair using VACUUM INTO."""
    try:
        logger.info("Attempting repair using VACUUM INTO")
        vacuum_path = db_path.with_suffix(".vacuum")
        
        source_conn = sqlite3.connect(str(db_path))
        source_conn.execute(f"VACUUM INTO '{vacuum_path}'")
        source_conn.close()
        
        # Verify vacuumed database
        is_healthy, verify_result = check_integrity(vacuum_path)
        
        if is_healthy:
            logger.info("VACUUM INTO repair successful")
            old_db_path = db_path.with_suffix(".old")
            if old_db_path.exists():
                old_db_path.unlink()
            db_path.rename(old_db_path)
            vacuum_path.rename(db_path)
            logger.info("Database repair completed successfully using VACUUM INTO")
            return True
        else:
            logger.error(f"VACUUM INTO database still has issues: {verify_result[:200]}")
            vacuum_path.unlink()
            return False
    except Exception as e:
        logger.error(f"VACUUM INTO failed: {e}")
        return False


def repair_with_dump(db_path: Path) -> bool:
    """Attempt repair using dump and recreate method."""
    try:
        logger.info("Attempting repair using dump method")
        dump_path = db_path.with_suffix(".dump")
        
        # Try to dump
        source_conn = sqlite3.connect(str(db_path))
        try:
            with open(dump_path, 'w', encoding='utf-8') as f:
                for line in source_conn.iterdump():
                    f.write(f"{line}\n")
        except sqlite3.DatabaseError as dump_error:
            logger.warning(f"Could not dump database: {dump_error}")
            source_conn.close()
            return False
        
        source_conn.close()
        
        # Create new database from dump
        if dump_path.exists() and dump_path.stat().st_size > 0:
            logger.info("Recreating database from dump")
            new_db_path = db_path.with_suffix(".new")
            new_conn = sqlite3.connect(str(new_db_path))
            
            with open(dump_path, 'r', encoding='utf-8') as f:
                new_conn.executescript(f.read())
            new_conn.close()
            
            # Verify new database
            is_healthy, verify_result = check_integrity(new_db_path)
            
            if is_healthy:
                # Replace old database with new one
                logger.info("Repair successful, replacing database")
                old_db_path = db_path.with_suffix(".old")
                if old_db_path.exists():
                    old_db_path.unlink()
                db_path.rename(old_db_path)
                new_db_path.rename(db_path)
                dump_path.unlink()
                logger.info("Database repair completed successfully")
                return True
            else:
                logger.error(f"Repaired database still has integrity issues: {verify_result[:200]}")
                new_db_path.unlink()
                dump_path.unlink()
                return False
        else:
            logger.error("Dump file is empty or missing, repair failed")
            if dump_path.exists():
                dump_path.unlink()
            return False
    except Exception as e:
        logger.error(f"Dump method failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Repair corrupted SQLite database")
    parser.add_argument("database_path", nargs="?", default="/app/data/ai_automation.db",
                       help="Path to database file (default: /app/data/ai_automation.db)")
    args = parser.parse_args()
    
    db_path = Path(args.database_path)
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
    
    # Create backup
    backup_path = db_path.with_suffix(f".backup.{int(time.time())}")
    logger.info(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    # Check current integrity
    logger.info("Checking database integrity...")
    is_healthy, error_msg = check_integrity(db_path)
    
    if is_healthy:
        logger.info("Database is healthy, no repair needed")
        return 0
    
    logger.error(f"Database corruption detected: {error_msg[:500]}")
    
    # Try repair methods in order
    methods = [
        ("SQLite .recover", repair_with_recover),
        ("VACUUM INTO", repair_with_vacuum),
        ("Dump and recreate", repair_with_dump),
    ]
    
    for method_name, repair_func in methods:
        logger.info(f"Trying {method_name}...")
        if repair_func(db_path):
            logger.info(f"Repair successful using {method_name}")
            # Verify final integrity
            is_healthy, verify_result = check_integrity(db_path)
            if is_healthy:
                logger.info("Database integrity verified after repair")
                return 0
            else:
                logger.error(f"Database still has issues after repair: {verify_result[:200]}")
                return 1
        else:
            logger.warning(f"{method_name} failed, trying next method...")
    
    logger.error("All repair methods failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
