"""
Performance Optimization Utilities

Epic 39, Story 39.15: Performance Optimization
Utilities for query optimization, caching, and performance monitoring.
"""

import logging
import time
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Optional

from shared.correlation_cache import CorrelationCache

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Performance monitoring utility for tracking query times, cache hits, etc.
    
    Usage:
        monitor = PerformanceMonitor()
        with monitor.track("query_name"):
            # Your code here
        stats = monitor.get_stats()
    """
    
    def __init__(self):
        self._operations: dict[str, list[float]] = {}
        self._cache_hits: dict[str, int] = {}
        self._cache_misses: dict[str, int] = {}
    
    @asynccontextmanager
    async def track(self, operation_name: str):
        """Track execution time of an operation."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation_name not in self._operations:
                self._operations[operation_name] = []
            self._operations[operation_name].append(duration)
    
    def record_cache_hit(self, cache_name: str):
        """Record a cache hit."""
        self._cache_hits[cache_name] = self._cache_hits.get(cache_name, 0) + 1
    
    def record_cache_miss(self, cache_name: str):
        """Record a cache miss."""
        self._cache_misses[cache_name] = self._cache_misses.get(cache_name, 0) + 1
    
    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        stats = {
            "operations": {},
            "cache_stats": {}
        }
        
        # Calculate operation statistics
        for op_name, durations in self._operations.items():
            if durations:
                stats["operations"][op_name] = {
                    "count": len(durations),
                    "total_time": sum(durations),
                    "avg_time": sum(durations) / len(durations),
                    "min_time": min(durations),
                    "max_time": max(durations),
                    "p50": sorted(durations)[len(durations) // 2],
                    "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
                }
        
        # Calculate cache statistics
        for cache_name in set(list(self._cache_hits.keys()) + list(self._cache_misses.keys())):
            hits = self._cache_hits.get(cache_name, 0)
            misses = self._cache_misses.get(cache_name, 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0.0
            
            stats["cache_stats"][cache_name] = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": round(hit_rate, 2)
            }
        
        return stats
    
    def reset(self):
        """Reset all statistics."""
        self._operations.clear()
        self._cache_hits.clear()
        self._cache_misses.clear()


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def track_performance(operation_name: str):
    """
    Decorator to track function execution time.
    
    Usage:
        @track_performance("database_query")
        async def my_query():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            async with monitor.track(operation_name):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if operation_name not in monitor._operations:
                    monitor._operations[operation_name] = []
                monitor._operations[operation_name].append(duration)
        
        # Return appropriate wrapper based on whether function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def batch_database_operations(operations: list[Callable], batch_size: int = 100):
    """
    Batch database operations to reduce round trips.
    
    Args:
        operations: List of async functions that perform database operations
        batch_size: Number of operations per batch
    
    Returns:
        List of results from all operations
    """
    import asyncio
    
    async def _batch_execute():
        results = []
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            batch_results = await asyncio.gather(*[op() for op in batch], return_exceptions=True)
            results.extend(batch_results)
        return results
    
    return _batch_execute()


def optimize_query(query_str: str, params: Optional[dict] = None) -> tuple[str, dict]:
    """
    Optimize SQL query by adding hints and optimizing parameters.
    
    Note: For SQLite, this is mostly about ensuring proper indexing.
    For production databases (PostgreSQL, etc.), could add EXPLAIN hints.
    
    Args:
        query_str: SQL query string
        params: Query parameters
    
    Returns:
        Tuple of (optimized_query, optimized_params)
    """
    # SQLite-specific optimizations
    optimized_query = query_str
    
    # Add PRAGMA optimizations for SQLite (if applicable)
    # Note: These should be set at connection level, not query level
    
    # Return optimized query (for now, just pass through)
    # Future: Could add query analysis, index hints, etc.
    return optimized_query, params or {}

