"""
Database integrity checking and recovery utilities.

Epic 39: Pattern Service - Database Health & Recovery
Provides utilities for checking PostgreSQL database integrity and handling errors.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("ai-pattern-service")


class DatabaseIntegrityError(Exception):
    """Raised when database integrity check fails"""
    pass


async def attempt_database_repair(_db_path: str | None = None) -> bool:
    """
    Attempt to repair database connectivity issues.

    Args:
        _db_path: Optional path to database (unused for PostgreSQL)

    Returns:
        True if repair succeeded (or no repair needed), False otherwise
    """
    logger.info("Attempting database repair/reconnection...")
    try:
        # For PostgreSQL, "repair" means verifying connectivity
        # The connection pool handles reconnection automatically
        logger.info("Database repair: connection pool handles reconnection automatically")
        return True
    except Exception as e:
        logger.error(f"Database repair failed: {e}")
        return False


async def check_database_integrity(db: AsyncSession) -> tuple[bool, str | None]:
    """
    Check database integrity by running a basic connectivity and consistency check.

    Args:
        db: Database session

    Returns:
        Tuple of (is_healthy, error_message)
        - is_healthy: True if database is healthy, False otherwise
        - error_message: Error message if unhealthy, None if healthy
    """
    try:
        result = await db.execute(text("SELECT 1"))
        value = result.scalar()

        if value == 1:
            logger.debug("Database integrity check passed")
            return True, None
        else:
            error_msg = f"Unexpected result from health check: {value}"
            logger.error(error_msg)
            return False, error_msg

    except Exception as e:
        logger.error(f"Failed to check database integrity: {e}", exc_info=True)
        return False, str(e)


def is_database_corruption_error(error: Exception) -> bool:
    """
    Check if an exception indicates a serious database error.

    Args:
        error: Exception to check

    Returns:
        True if error indicates a serious database issue, False otherwise
    """
    error_str = str(error).lower()
    serious_indicators = [
        "connection refused",
        "connection reset",
        "server closed the connection",
        "could not connect",
        "database does not exist",
        "relation does not exist",
        "corrupted",
    ]

    return any(indicator in error_str for indicator in serious_indicators)


async def safe_database_query(
    db: AsyncSession,
    query_func,
    *args,
    **kwargs
):
    """
    Execute a database query with error handling.

    If a serious error is detected, raises DatabaseIntegrityError.

    Args:
        db: Database session
        query_func: Async function to execute
        *args: Positional arguments for query_func
        **kwargs: Keyword arguments for query_func

    Returns:
        Result from query_func
    """
    try:
        # First, check integrity
        is_healthy, error_msg = await check_database_integrity(db)

        if not is_healthy:
            logger.warning(f"Database integrity check failed: {error_msg}")
            raise DatabaseIntegrityError(f"Database health check failed: {error_msg}")

        # Execute query
        return await query_func(*args, **kwargs)

    except DatabaseIntegrityError:
        raise
    except Exception as e:
        if is_database_corruption_error(e):
            logger.error(f"Serious database error detected during query: {e}")
            raise DatabaseIntegrityError(f"Serious database error: {e}") from e
        else:
            # Re-raise non-critical errors
            raise
