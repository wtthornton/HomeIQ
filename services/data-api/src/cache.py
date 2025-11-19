"""
Simple in-memory cache for frequently accessed data
Provides TTL-based caching to reduce database queries

Uses shared cache base class from shared/cache.py
"""

import sys
import os
from pathlib import Path
from typing import Any, Optional, Dict

# Add shared directory to path for imports
shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')
try:
    app_root = Path(__file__).resolve().parents[3]  # Go up to project root
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
    Path(__file__).parent.parent.parent.parent / "shared",  # Fallback for local dev
])

shared_path = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from cache import BaseCache

import logging

logger = logging.getLogger(__name__)


class SimpleCache(BaseCache):
    """
    Simple in-memory cache with TTL support

    Features:
    - TTL-based expiration
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - LRU eviction when max size reached
    
    Inherits from shared BaseCache for consistency.
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache

        Args:
            default_ttl: Default TTL in seconds (default: 5 minutes)
            max_size: Maximum cache entries before eviction
        """
        super().__init__(default_ttl=default_ttl, max_size=max_size)
        
        # Backward compatibility: expose stats as instance variables
        # These will be kept in sync with self.stats
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (overrides to sync instance variables)"""
        result = await super().get(key)
        # Sync instance variables for backward compatibility
        self.hits = self.stats.hits
        self.misses = self.stats.misses
        return result
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache (overrides to sync instance variables)"""
        result = await super().set(key, value, ttl)
        # Sync instance variables for backward compatibility
        self.evictions = self.stats.evictions
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics (backward compatibility method)

        Returns:
            Dictionary with cache stats
        """
        return super().get_stats()


# Global cache instance (5 minute TTL, 1000 entries max)
cache = SimpleCache(default_ttl=300, max_size=1000)
