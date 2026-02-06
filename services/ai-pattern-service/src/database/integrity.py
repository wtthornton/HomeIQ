"""
Database integrity checking and recovery utilities.

Epic 39: Pattern Service - Database Health & Recovery
Provides utilities for checking SQLite database integrity and handling corruption.
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..config import settings

logger = logging.getLogger("ai-pattern-service")


class DatabaseIntegrityError(Exception):
    """Raised when database integrity check fails"""
    pass


async def check_database_integrity(db: AsyncSession) -> Tuple[bool, Optional[str]]:
    """
    Check database integrity using PRAGMA integrity_check.
    
    Args:
        db: Database session
        
    Returns:
        Tuple of (is_healthy, error_message)
        - is_healthy: True if database is healthy, False otherwise
        - error_message: Error message if unhealthy, None if healthy
    """
    try:
        # Use quick_check for faster verification (checks for corruption)
        result = await db.execute(text("PRAGMA quick_check"))
        integrity_result = result.scalar()
        
        # SQLite returns "ok" for healthy database, or error message string for corruption
        if integrity_result == "ok":
            logger.debug("Database integrity check passed")
            return True, None
        else:
            # Check if result indicates corruption (contains "***" or specific error patterns)
            error_msg = str(integrity_result)
            is_corrupted = (
                "***" in error_msg or
                "rowid out of order" in error_msg.lower() or
                "page never used" in error_msg.lower() or
                "tree" in error_msg.lower()
            )
            
            if is_corrupted:
                logger.error(f"Database corruption detected: {error_msg[:500]}")  # Truncate long messages
                return False, error_msg
            else:
                # Unexpected result but not clearly corruption
                logger.warning(f"Database integrity check returned unexpected result: {error_msg[:200]}")
                return False, error_msg
            
    except Exception as e:
        logger.error(f"Failed to check database integrity: {e}", exc_info=True)
        # If we can't even run the check, assume corruption
        return False, str(e)


async def attempt_database_repair(db_path: Optional[Path] = None) -> bool:
    """
    Attempt to repair a corrupted SQLite database.
    
    This uses SQLite's built-in recovery mechanism:
    1. Attempts to dump and recreate the database
    2. Uses .dump to extract data
    3. Recreates database from dump
    
    Args:
        db_path: Path to database file. If None, uses settings.database_path
        
    Returns:
        True if repair was successful, False otherwise
    """
    import asyncio
    
    if db_path is None:
        db_path = Path(settings.database_path)
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return False
    
    def _repair_sync():
        """Synchronous repair function to run in executor"""
        try:
            import tempfile
            import shutil
            import subprocess
            
            # Create backup before attempting repair
            backup_path = db_path.with_suffix(f".backup.{int(time.time())}")
            logger.info(f"Creating backup before repair: {backup_path}")
            shutil.copy2(db_path, backup_path)
            
            # Method 1: Try SQLite's .recover command (SQLite 3.29+)
            # This is more robust for severe corruption
            try:
                logger.info("Attempting repair using SQLite .recover command")
                recovered_path = db_path.with_suffix(".recovered")

                # Use sqlite3 command-line tool to recover (safe: no shell=True)
                sqlite3_path = shutil.which("sqlite3")
                if not sqlite3_path:
                    raise FileNotFoundError("sqlite3 not found on PATH")

                recover_proc = subprocess.run(
                    [sqlite3_path, str(db_path), ".recover"],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                if recover_proc.returncode == 0:
                    result = subprocess.run(
                        [sqlite3_path, str(recovered_path)],
                        input=recover_proc.stdout,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                else:
                    result = recover_proc
                
                if result.returncode == 0 and recovered_path.exists():
                    # Verify recovered database
                    verify_conn = sqlite3.connect(str(recovered_path))
                    verify_result = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
                    verify_conn.close()
                    
                    if verify_result == "ok":
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
                else:
                    logger.warning(f".recover command failed: {result.stderr}")
            except Exception as recover_error:
                logger.warning(f"SQLite .recover method failed: {recover_error}, trying dump method")
            
            # Method 2: Fallback to dump method (for older SQLite or if .recover fails)
            logger.info("Attempting repair using dump method")
            dump_path = db_path.with_suffix(".dump")
            
            # Try to dump with error handling
            source_conn = sqlite3.connect(str(db_path))
            source_conn.execute("PRAGMA integrity_check")  # This will fail if too corrupted
            
            try:
                with open(dump_path, 'w', encoding='utf-8') as f:
                    for line in source_conn.iterdump():
                        f.write(f"{line}\n")
            except sqlite3.DatabaseError as dump_error:
                logger.warning(f"Could not dump database: {dump_error}")
                source_conn.close()
                # If dump fails, try VACUUM INTO (SQLite 3.27+)
                try:
                    logger.info("Attempting repair using VACUUM INTO")
                    vacuum_path = db_path.with_suffix(".vacuum")
                    source_conn = sqlite3.connect(str(db_path))
                    source_conn.execute(f"VACUUM INTO '{vacuum_path}'")
                    source_conn.close()
                    
                    # Verify vacuumed database
                    verify_conn = sqlite3.connect(str(vacuum_path))
                    verify_result = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
                    verify_conn.close()
                    
                    if verify_result == "ok":
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
                except Exception as vacuum_error:
                    logger.error(f"VACUUM INTO failed: {vacuum_error}")
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
                verify_conn = sqlite3.connect(str(new_db_path))
                verify_result = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
                verify_conn.close()
                
                if verify_result == "ok":
                    # Replace old database with new one
                    logger.info("Repair successful, replacing database")
                    old_db_path = db_path.with_suffix(".old")
                    if old_db_path.exists():
                        old_db_path.unlink()
                    db_path.rename(old_db_path)
                    new_db_path.rename(db_path)
                    dump_path.unlink()  # Clean up dump file
                    logger.info("Database repair completed successfully")
                    return True
                else:
                    logger.error(f"Repaired database still has integrity issues: {verify_result[:200]}")
                    new_db_path.unlink()  # Clean up failed repair
                    dump_path.unlink()
                    return False
            else:
                logger.error("Dump file is empty or missing, repair failed")
                if dump_path.exists():
                    dump_path.unlink()
                return False
                
        except Exception as e:
            logger.error(f"Database repair failed: {e}", exc_info=True)
            return False
    
    # Run synchronous repair in executor
    return await asyncio.to_thread(_repair_sync)


def is_database_corruption_error(error: Exception) -> bool:
    """
    Check if an exception indicates database corruption.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error indicates corruption, False otherwise
    """
    error_str = str(error).lower()
    corruption_indicators = [
        "database disk image is malformed",
        "database is corrupted",
        "file is encrypted or is not a database",
        "database schema is corrupted",
        "malformed",
        "corrupted",
        "rowid out of order",  # SQLite integrity_check error
        "page never used",  # SQLite integrity_check error
        "*** in database",  # SQLite integrity_check error prefix
        "tree",  # SQLite B-tree corruption
        "cell",  # SQLite cell corruption
    ]
    
    return any(indicator in error_str for indicator in corruption_indicators)


async def safe_database_query(
    db: AsyncSession,
    query_func,
    *args,
    **kwargs
):
    """
    Execute a database query with corruption error handling.
    
    If corruption is detected, attempts recovery and retries.
    If recovery fails, returns a safe fallback response.
    
    Args:
        db: Database session
        query_func: Async function to execute
        *args: Positional arguments for query_func
        **kwargs: Keyword arguments for query_func
        
    Returns:
        Result from query_func, or fallback value if corruption cannot be recovered
    """
    try:
        # First, check integrity
        is_healthy, error_msg = await check_database_integrity(db)
        
        if not is_healthy:
            logger.warning(f"Database integrity check failed: {error_msg}")
            # Attempt repair
            db_path = Path(settings.database_path)
            if await attempt_database_repair(db_path):
                logger.info("Database repair successful, retrying query")
                # Retry after repair
                is_healthy, _ = await check_database_integrity(db)
                if not is_healthy:
                    logger.error("Database still unhealthy after repair")
                    raise DatabaseIntegrityError("Database corruption could not be repaired")
            else:
                logger.error("Database repair failed")
                raise DatabaseIntegrityError(f"Database corruption detected and repair failed: {error_msg}")
        
        # Execute query
        return await query_func(*args, **kwargs)
        
    except Exception as e:
        if is_database_corruption_error(e):
            logger.error(f"Database corruption detected during query: {e}")
            # Attempt repair
            db_path = Path(settings.database_path)
            if await attempt_database_repair(db_path):
                logger.info("Database repair successful after corruption error, retrying query")
                try:
                    return await query_func(*args, **kwargs)
                except Exception as retry_error:
                    logger.error(f"Query failed after repair: {retry_error}")
                    raise DatabaseIntegrityError("Query failed after database repair") from retry_error
            else:
                raise DatabaseIntegrityError(f"Database corruption detected and repair failed: {e}") from e
        else:
            # Re-raise non-corruption errors
            raise
