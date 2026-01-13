"""
Metrics Tracking for RAG Service

Tracks RAG operation metrics (calls, latency, cache hits, errors).
Thread-safe in-memory counters for RAG Status Monitor integration.
"""

import logging
import threading
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)


class RAGMetrics:
    """
    Thread-safe metrics tracker for RAG operations.
    
    Tracks:
    - Total calls (store, retrieve)
    - Cache hits/misses
    - Latency (avg, min, max)
    - Errors
    - Success scores (avg)
    """

    def __init__(self):
        """Initialize metrics tracker."""
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        """Reset all metrics (called with lock)."""
        # Counters
        self.total_calls = 0
        self.store_calls = 0
        self.retrieve_calls = 0
        self.search_calls = 0
        
        # Cache metrics
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Latency tracking (using deque for rolling window)
        self._latencies: deque[float] = deque(maxlen=1000)  # Keep last 1000 latencies
        self.total_latency_ms = 0.0
        
        # Errors
        self.errors = 0
        self.embedding_errors = 0
        self.storage_errors = 0
        
        # Success scores (for tracking quality)
        self._success_scores: deque[float] = deque(maxlen=1000)
        self.total_success_score = 0.0

    def record_call(self, operation: str, latency_ms: float, cache_hit: bool = False) -> None:
        """
        Record a RAG operation call.
        
        Args:
            operation: Operation type ('store', 'retrieve', 'search')
            latency_ms: Operation latency in milliseconds
            cache_hit: Whether this was a cache hit
        """
        with self._lock:
            self.total_calls += 1
            
            if operation == 'store':
                self.store_calls += 1
            elif operation == 'retrieve':
                self.retrieve_calls += 1
            elif operation == 'search':
                self.search_calls += 1
            
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            
            self._latencies.append(latency_ms)
            self.total_latency_ms += latency_ms

    def record_error(self, error_type: str) -> None:
        """
        Record an error.
        
        Args:
            error_type: Error type ('embedding', 'storage', 'other')
        """
        with self._lock:
            self.errors += 1
            if error_type == 'embedding':
                self.embedding_errors += 1
            elif error_type == 'storage':
                self.storage_errors += 1

    def record_success_score(self, score: float) -> None:
        """
        Record a success score.
        
        Args:
            score: Success score (0.0-1.0)
        """
        with self._lock:
            self._success_scores.append(score)
            self.total_success_score += score

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current metrics snapshot.
        
        Returns:
            Dictionary with all metrics
        """
        with self._lock:
            latencies_list = list(self._latencies)
            avg_latency_ms = (
                sum(latencies_list) / len(latencies_list)
                if latencies_list else 0.0
            )
            min_latency_ms = min(latencies_list) if latencies_list else 0.0
            max_latency_ms = max(latencies_list) if latencies_list else 0.0
            
            cache_hit_rate = (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0 else 0.0
            )
            
            avg_success_score = (
                sum(self._success_scores) / len(self._success_scores)
                if self._success_scores else 0.5
            )
            
            error_rate = (
                self.errors / self.total_calls
                if self.total_calls > 0 else 0.0
            )
            
            return {
                'total_calls': self.total_calls,
                'store_calls': self.store_calls,
                'retrieve_calls': self.retrieve_calls,
                'search_calls': self.search_calls,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'cache_hit_rate': cache_hit_rate,
                'avg_latency_ms': avg_latency_ms,
                'min_latency_ms': min_latency_ms,
                'max_latency_ms': max_latency_ms,
                'total_latency_ms': self.total_latency_ms,
                'errors': self.errors,
                'embedding_errors': self.embedding_errors,
                'storage_errors': self.storage_errors,
                'error_rate': error_rate,
                'avg_success_score': avg_success_score,
                'total_success_scores': len(self._success_scores),
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._reset()
        logger.info("RAG metrics reset")


# Global metrics instance (singleton)
_metrics_instance: RAGMetrics | None = None
_metrics_lock = threading.Lock()


def get_metrics() -> RAGMetrics:
    """Get global metrics instance (singleton)."""
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = RAGMetrics()
    return _metrics_instance
