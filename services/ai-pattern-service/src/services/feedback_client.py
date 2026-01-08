"""
Feedback Client Service

Retrieves user feedback on synergies and devices to influence pattern detection.
Implements Recommendation 2.1: Integrate Feedback into Pattern Detection.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md

Refactored: January 2026
- Added cache TTL with expiration
- Added bounded cache size with LRU eviction
- Added async lock for thread-safe cache access
- Added cache statistics for monitoring
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class DeviceFeedbackStats:
    """Statistics for device feedback."""
    
    avg_rating: float = 3.0  # Neutral default
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    acceptance_rate: float = 0.5
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'avg_rating': self.avg_rating,
            'total_feedback': self.total_feedback,
            'positive_count': self.positive_count,
            'negative_count': self.negative_count,
            'acceptance_rate': self.acceptance_rate
        }


@dataclass
class CachedFeedback:
    """Cached feedback entry with expiration."""
    
    data: dict[str, Any]
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() >= self.expires_at
    
    def touch(self) -> None:
        """Update access tracking for LRU eviction."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


@dataclass
class CacheStatistics:
    """Statistics for cache monitoring."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'expirations': self.expirations,
            'current_size': self.current_size,
            'max_size': self.max_size,
            'hit_rate': round(self.hit_rate, 3)
        }


@dataclass
class FeedbackAggregator:
    """Aggregates feedback data for a device."""
    
    ratings: list[float] = field(default_factory=list)
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    accepted_count: int = 0
    total_synergies: int = 0
    
    def add_rating(self, rating: float) -> None:
        """Add a rating to the aggregator."""
        if 0.0 <= rating <= 5.0:
            self.ratings.append(rating)
            self.total_feedback += 1
            
            if rating >= 4.0:
                self.positive_count += 1
            elif rating < 2.0:
                self.negative_count += 1
    
    def add_acceptance(self, accepted: bool) -> None:
        """Track acceptance of a synergy."""
        if accepted:
            self.accepted_count += 1
    
    def increment_synergy_count(self) -> None:
        """Increment total synergy count."""
        self.total_synergies += 1
    
    def calculate_stats(self) -> DeviceFeedbackStats:
        """Calculate final statistics."""
        avg_rating = sum(self.ratings) / len(self.ratings) if self.ratings else 3.0
        acceptance_rate = self.accepted_count / self.total_synergies if self.total_synergies > 0 else 0.5
        
        return DeviceFeedbackStats(
            avg_rating=float(avg_rating),
            total_feedback=self.total_feedback,
            positive_count=self.positive_count,
            negative_count=self.negative_count,
            acceptance_rate=float(acceptance_rate)
        )


class FeedbackClient:
    """
    Client for retrieving user feedback on synergies and devices.
    
    Aggregates feedback from synergy_feedback table to provide device-level
    feedback statistics for pattern detection enhancement.
    
    Features:
    - Cache with TTL expiration
    - Bounded cache size with LRU eviction
    - Thread-safe async access
    - Cache statistics for monitoring
    """
    
    # SQL query for fetching feedback data
    _FEEDBACK_QUERY = text("""
        SELECT 
            sf.feedback_type,
            sf.feedback_data,
            so.device_ids
        FROM synergy_feedback sf
        JOIN synergy_opportunities so ON sf.synergy_id = so.synergy_id
        WHERE sf.feedback_data IS NOT NULL
    """)
    
    # Default configuration
    DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes
    DEFAULT_MAX_CACHE_SIZE = 1000
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        max_cache_size: int = DEFAULT_MAX_CACHE_SIZE
    ):
        """
        Initialize feedback client.
        
        Args:
            db: Optional database session for querying feedback
            cache_ttl_seconds: Time-to-live for cache entries in seconds
            max_cache_size: Maximum number of entries in cache
        """
        self.db = db
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._max_cache_size = max_cache_size
        self._feedback_cache: dict[str, CachedFeedback] = {}
        self._cache_lock = asyncio.Lock()
        self._stats = CacheStatistics(max_size=max_cache_size)
        
        logger.info(
            f"FeedbackClient initialized: cache_ttl={cache_ttl_seconds}s, "
            f"max_cache_size={max_cache_size}"
        )
    
    async def get_device_feedback(
        self,
        device_id: str,
        db: Optional[AsyncSession] = None
    ) -> dict[str, Any]:
        """
        Get aggregated feedback for a device.
        
        Aggregates feedback from synergies that involve this device.
        Uses cache with TTL and LRU eviction.
        
        Args:
            device_id: Device identifier (e.g., "light.bedroom")
            db: Optional database session (uses self.db if not provided)
        
        Returns:
            Dictionary with keys:
                - avg_rating: Average rating (0.0-5.0)
                - total_feedback: Total number of feedback entries
                - positive_count: Number of positive feedbacks (rating >= 4.0)
                - negative_count: Number of negative feedbacks (rating < 2.0)
                - acceptance_rate: Rate of accepted synergies (0.0-1.0)
        """
        # Check cache first (with lock)
        cached_result = await self._get_from_cache(device_id)
        if cached_result is not None:
            return cached_result
        
        # Cache miss - fetch from database
        session = db or self.db
        if not session:
            logger.debug(f"No database session available for device feedback: {device_id}")
            return DeviceFeedbackStats().to_dict()
        
        try:
            feedback_stats = await self._fetch_and_aggregate_feedback(session, device_id)
            await self._add_to_cache(device_id, feedback_stats)
            return feedback_stats
        except Exception as e:
            logger.warning(f"Failed to get device feedback for {device_id}: {e}")
            return DeviceFeedbackStats().to_dict()
    
    async def _get_from_cache(self, device_id: str) -> Optional[dict[str, Any]]:
        """
        Get entry from cache if valid.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Cached data or None if not found/expired
        """
        async with self._cache_lock:
            if device_id in self._feedback_cache:
                entry = self._feedback_cache[device_id]
                
                if entry.is_expired:
                    # Remove expired entry
                    del self._feedback_cache[device_id]
                    self._stats.expirations += 1
                    self._stats.misses += 1
                    self._stats.current_size = len(self._feedback_cache)
                    logger.debug(f"Cache entry expired for {device_id}")
                    return None
                
                # Valid cache hit
                entry.touch()
                self._stats.hits += 1
                return entry.data
            
            # Cache miss
            self._stats.misses += 1
            return None
    
    async def _add_to_cache(self, device_id: str, data: dict[str, Any]) -> None:
        """
        Add entry to cache with TTL.
        
        Args:
            device_id: Device identifier
            data: Data to cache
        """
        async with self._cache_lock:
            # Evict if cache is full
            if len(self._feedback_cache) >= self._max_cache_size:
                await self._evict_lru_entry()
            
            # Add new entry
            self._feedback_cache[device_id] = CachedFeedback(
                data=data,
                expires_at=datetime.utcnow() + self._cache_ttl
            )
            self._stats.current_size = len(self._feedback_cache)
    
    async def _evict_lru_entry(self) -> None:
        """
        Evict least recently used cache entry.
        
        Must be called while holding _cache_lock.
        """
        if not self._feedback_cache:
            return
        
        # Find LRU entry (oldest last_accessed)
        lru_key = min(
            self._feedback_cache,
            key=lambda k: self._feedback_cache[k].last_accessed
        )
        
        del self._feedback_cache[lru_key]
        self._stats.evictions += 1
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    async def _fetch_and_aggregate_feedback(
        self,
        session: AsyncSession,
        device_id: str
    ) -> dict[str, Any]:
        """
        Fetch feedback from database and aggregate for device.
        
        Args:
            session: Database session
            device_id: Device identifier
            
        Returns:
            Aggregated feedback statistics
        """
        result = await session.execute(self._FEEDBACK_QUERY)
        rows = result.fetchall()
        
        aggregator = FeedbackAggregator()
        
        for row in rows:
            self._process_feedback_row(row, device_id, aggregator)
        
        stats = aggregator.calculate_stats()
        
        logger.debug(
            f"Device feedback for {device_id}: "
            f"avg_rating={stats.avg_rating:.2f}, total={stats.total_feedback}, "
            f"acceptance_rate={stats.acceptance_rate:.2f}"
        )
        
        return stats.to_dict()
    
    def _process_feedback_row(
        self,
        row: tuple[Any, ...],
        device_id: str,
        aggregator: FeedbackAggregator
    ) -> None:
        """
        Process a single feedback row.
        
        Args:
            row: Database row (feedback_type, feedback_data, device_ids)
            device_id: Device identifier to filter by
            aggregator: Aggregator to collect statistics
        """
        if len(row) < 3:
            logger.warning(f"Invalid row format: expected 3 columns, got {len(row)}")
            return
        
        feedback_type, feedback_data_json, device_ids = row[0], row[1], row[2]
        
        # Check if this synergy involves the device
        # device_ids should be a list/set; handle both None and empty cases
        if not device_ids or not isinstance(device_ids, (list, set, tuple)):
            return
        
        if device_id not in device_ids:
            return
        
        aggregator.increment_synergy_count()
        feedback_data = self._parse_feedback_data(feedback_data_json)
        
        if feedback_data is None:
            return
        
        # Extract and add rating
        rating = self._extract_rating(feedback_data)
        if rating is not None:
            aggregator.add_rating(rating)
        
        # Track acceptance
        is_accepted = feedback_data.get('accepted', False) or feedback_type == 'accept'
        aggregator.add_acceptance(is_accepted)
    
    def _parse_feedback_data(self, feedback_data_json: Any) -> Optional[dict[str, Any]]:
        """
        Parse feedback data from JSON.
        
        Args:
            feedback_data_json: JSON string or dict
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            if isinstance(feedback_data_json, str):
                return json.loads(feedback_data_json)
            return feedback_data_json
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug(f"Failed to parse feedback data: {e}")
            return None
    
    def _extract_rating(self, feedback_data: dict[str, Any]) -> Optional[float]:
        """
        Extract rating from feedback data.
        
        Args:
            feedback_data: Parsed feedback dictionary
            
        Returns:
            Rating value (0.0-5.0) or None if not available
        """
        rating = feedback_data.get('rating') or feedback_data.get('user_rating')
        if rating is None:
            return None
        
        try:
            rating_float = float(rating)
            if 0.0 <= rating_float <= 5.0:
                return rating_float
        except (ValueError, TypeError):
            pass
        
        return None
    
    def clear_cache(self) -> None:
        """Clear the feedback cache synchronously."""
        self._feedback_cache.clear()
        self._stats.current_size = 0
        logger.debug("Feedback cache cleared")
    
    async def clear_cache_async(self) -> None:
        """Clear the feedback cache with async lock."""
        async with self._cache_lock:
            self._feedback_cache.clear()
            self._stats.current_size = 0
            logger.debug("Feedback cache cleared (async)")
    
    async def invalidate_device(self, device_id: str) -> bool:
        """
        Invalidate cache entry for a specific device.
        
        Args:
            device_id: Device identifier to invalidate
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        async with self._cache_lock:
            if device_id in self._feedback_cache:
                del self._feedback_cache[device_id]
                self._stats.current_size = len(self._feedback_cache)
                logger.debug(f"Invalidated cache for device: {device_id}")
                return True
            return False
    
    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dictionary with cache statistics
        """
        async with self._cache_lock:
            self._stats.current_size = len(self._feedback_cache)
            return self._stats.to_dict()
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.
        
        Returns:
            Number of entries removed
        """
        async with self._cache_lock:
            expired_keys = [
                key for key, entry in self._feedback_cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self._feedback_cache[key]
            
            self._stats.expirations += len(expired_keys)
            self._stats.current_size = len(self._feedback_cache)
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    async def get_multiple_device_feedback(
        self,
        device_ids: list[str],
        db: Optional[AsyncSession] = None
    ) -> dict[str, dict[str, Any]]:
        """
        Get feedback for multiple devices efficiently.
        
        Args:
            device_ids: List of device identifiers
            db: Optional database session
            
        Returns:
            Dictionary mapping device_id to feedback stats
        """
        results: dict[str, dict[str, Any]] = {}
        
        # Gather all feedback requests concurrently
        tasks = [
            self.get_device_feedback(device_id, db)
            for device_id in device_ids
        ]
        
        feedback_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for device_id, result in zip(device_ids, feedback_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get feedback for {device_id}: {result}")
                results[device_id] = DeviceFeedbackStats().to_dict()
            else:
                results[device_id] = result
        
        return results