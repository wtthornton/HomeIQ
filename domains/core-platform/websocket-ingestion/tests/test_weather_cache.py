"""
Tests for Weather Cache
"""

import asyncio
from datetime import datetime

import pytest

from src.weather_cache import WeatherCache


class TestWeatherCache:
    """Test cases for WeatherCache class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.cache = WeatherCache(max_size=3, default_ttl=60)

    def teardown_method(self):
        """Clean up after tests"""
        if self.cache.is_running:
            asyncio.run(self.cache.stop())

    def test_initialization(self):
        """Test cache initialization"""
        assert self.cache.max_size == 3
        assert self.cache.default_ttl == 60
        assert len(self.cache.cache) == 0
        assert self.cache.hits == 0
        assert self.cache.misses == 0
        assert self.cache.evictions == 0
        assert not self.cache.is_running

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the cache"""
        # Start cache
        await self.cache.start()
        assert self.cache.is_running
        assert self.cache.cleanup_task is not None

        # Stop cache
        await self.cache.stop()
        assert not self.cache.is_running

    @pytest.mark.asyncio
    async def test_put_get(self):
        """Test putting and getting data from cache"""
        await self.cache.start()

        # Put data in cache
        weather_data = {"temperature": 20.5, "humidity": 65}
        success = await self.cache.put("London", weather_data)
        assert success

        # Get data from cache
        retrieved_data = await self.cache.get("London")
        assert retrieved_data == weather_data
        assert self.cache.hits == 1
        assert self.cache.misses == 0

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss scenario"""
        await self.cache.start()

        # Try to get non-existent data
        retrieved_data = await self.cache.get("NonExistent")
        assert retrieved_data is None
        assert self.cache.hits == 0
        assert self.cache.misses == 1

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache expiration"""
        await self.cache.start()

        # Put data with short TTL
        weather_data = {"temperature": 20.5}
        await self.cache.put("London", weather_data, ttl=1)  # 1 second TTL

        # Should be available immediately
        retrieved_data = await self.cache.get("London")
        assert retrieved_data == weather_data

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired now
        retrieved_data = await self.cache.get("London")
        assert retrieved_data is None
        assert self.cache.misses == 1

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        await self.cache.start()

        # Fill cache to max size
        await self.cache.put("London", {"temp": 20})
        await self.cache.put("Paris", {"temp": 18})
        await self.cache.put("Berlin", {"temp": 15})

        assert len(self.cache.cache) == 3

        # Add one more item (should evict least recently used)
        await self.cache.put("Madrid", {"temp": 25})

        assert len(self.cache.cache) == 3
        assert self.cache.evictions == 1

        # London should be evicted (first added)
        london_data = await self.cache.get("London")
        assert london_data is None

        # Madrid should be available (most recently added)
        madrid_data = await self.cache.get("Madrid")
        assert madrid_data == {"temp": 25}

    @pytest.mark.asyncio
    async def test_custom_ttl(self):
        """Test custom TTL for cache entries"""
        await self.cache.start()

        # Put data with custom TTL
        weather_data = {"temperature": 20.5}
        await self.cache.put("London", weather_data, ttl=120)  # 2 minutes

        # Check that custom TTL is stored
        entry = self.cache.cache["London"]
        assert entry["ttl"] == 120

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing all cache entries"""
        await self.cache.start()

        # Add some data
        await self.cache.put("London", {"temp": 20})
        await self.cache.put("Paris", {"temp": 18})

        assert len(self.cache.cache) == 2

        # Clear cache
        await self.cache.clear()

        assert len(self.cache.cache) == 0

    @pytest.mark.asyncio
    async def test_clear_expired(self):
        """Test clearing only expired entries"""
        await self.cache.start()

        # Add data with different TTLs
        await self.cache.put("London", {"temp": 20}, ttl=1)  # Expires quickly
        await self.cache.put("Paris", {"temp": 18}, ttl=300)  # Long TTL

        # Wait for London to expire
        await asyncio.sleep(1.1)

        # Clear expired entries
        await self.cache.clear_expired()

        # London should be removed, Paris should remain
        assert "London" not in self.cache.cache
        assert "Paris" in self.cache.cache

    def test_get_cache_statistics(self):
        """Test getting cache statistics"""
        # Set some statistics
        self.cache.hits = 10
        self.cache.misses = 5
        self.cache.evictions = 2
        self.cache.total_requests = 15

        stats = self.cache.get_cache_statistics()

        assert stats["max_size"] == 3
        assert stats["current_size"] == 0
        assert stats["default_ttl"] == 60
        assert stats["total_requests"] == 15
        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert stats["evictions"] == 2
        assert stats["hit_rate"] == 66.67  # 10/15 * 100
        assert stats["cleanup_interval"] == 60

    def test_get_cache_keys(self):
        """Test getting cache keys"""
        # Add some data
        self.cache.cache["London"] = {"data": {"temp": 20}, "timestamp": datetime.now().isoformat(), "ttl": 60}
        self.cache.cache["Paris"] = {"data": {"temp": 18}, "timestamp": datetime.now().isoformat(), "ttl": 60}

        keys = self.cache.get_cache_keys()
        assert "London" in keys
        assert "Paris" in keys
        assert len(keys) == 2

    def test_configure_max_size(self):
        """Test configuring maximum cache size"""
        self.cache.configure_max_size(100)
        assert self.cache.max_size == 100

        # Test invalid max size
        with pytest.raises(ValueError):
            self.cache.configure_max_size(0)

    def test_configure_ttl(self):
        """Test configuring default TTL"""
        self.cache.configure_ttl(300)
        assert self.cache.default_ttl == 300

        # Test invalid TTL
        with pytest.raises(ValueError):
            self.cache.configure_ttl(0)

    def test_configure_cleanup_interval(self):
        """Test configuring cleanup interval"""
        self.cache.configure_cleanup_interval(120)
        assert self.cache.cleanup_interval == 120

        # Test invalid interval
        with pytest.raises(ValueError):
            self.cache.configure_cleanup_interval(0)

    def test_reset_statistics(self):
        """Test resetting statistics"""
        # Set some statistics
        self.cache.hits = 10
        self.cache.misses = 5
        self.cache.evictions = 2
        self.cache.total_requests = 15

        # Reset statistics
        self.cache.reset_statistics()

        assert self.cache.hits == 0
        assert self.cache.misses == 0
        assert self.cache.evictions == 0
        assert self.cache.total_requests == 0
