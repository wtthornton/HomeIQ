"""
Huey Configuration

Initialize Huey with SQLite backend for task queue.
"""

import logging
import os
from pathlib import Path

from huey.contrib.sqlitedb import SqliteHuey

from ..config import settings

logger = logging.getLogger(__name__)


def get_huey_instance() -> SqliteHuey:
    """
    Get or create Huey instance with SQLite backend.
    
    Returns:
        SqliteHuey instance configured for automation queue
    """
    # Ensure data directory exists
    db_path = Path(settings.huey_database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert relative path to absolute for consistency
    if not db_path.is_absolute():
        # Default to ./data/ directory
        base_dir = Path.cwd()
        if os.path.exists('/app'):  # Docker container
            base_dir = Path('/app')
        db_path = base_dir / db_path
    
    logger.info(f"Initializing Huey with SQLite database: {db_path}")
    
    huey = SqliteHuey(
        'automation-queue',
        filename=str(db_path),
        results=True,
        result_ttl=settings.huey_result_ttl,
        consumer={
            'workers': settings.huey_workers,
            'worker_type': 'thread',
            'scheduler_interval': settings.huey_scheduler_interval,
        }
    )
    
    return huey


# Global Huey instance
huey = get_huey_instance()
