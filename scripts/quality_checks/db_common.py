"""
Common utilities for SQLite database operations.
"""
from pathlib import Path
from typing import Optional

from .config import DATABASE_CONFIGS, PROJECT_ROOT

# Script directory for path resolution
SCRIPT_DIR = Path(__file__).parent.parent


def find_database_path(db_key: str) -> Optional[Path]:
    """Find database file path using multiple possible locations."""
    config = DATABASE_CONFIGS.get(db_key)
    if not config:
        return None
    
    for path_str in config['paths']:
        path = Path(path_str)
        # Handle absolute paths
        if path.is_absolute():
            if path.exists():
                return path
        # Handle relative paths from script directory
        else:
            # Try from script directory
            full_path = SCRIPT_DIR.parent / path
            if full_path.exists():
                return full_path
            # Try from current directory
            if path.exists():
                return path
    
    return None


def get_database_config(db_key: str) -> Optional[dict]:
    """Get database configuration by key."""
    return DATABASE_CONFIGS.get(db_key)


def list_all_databases() -> list[str]:
    """List all available database keys."""
    return list(DATABASE_CONFIGS.keys())

