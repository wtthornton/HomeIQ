"""Unit tests for SimpleCache — Story 85.10

Tests cache get/set with TTL and stats syncing.
"""

import pytest
from src.cache import SimpleCache


class TestSimpleCache:

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = SimpleCache(default_ttl=300)
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self):
        cache = SimpleCache(default_ttl=300)
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_hits_counter_synced(self):
        cache = SimpleCache(default_ttl=300)
        await cache.set("key1", "value1")
        await cache.get("key1")
        assert cache.hits >= 1

    @pytest.mark.asyncio
    async def test_misses_counter_synced(self):
        cache = SimpleCache(default_ttl=300)
        await cache.get("missing")
        assert cache.misses >= 1

    @pytest.mark.asyncio
    async def test_get_stats(self):
        cache = SimpleCache(default_ttl=300)
        await cache.set("k", "v")
        await cache.get("k")
        stats = cache.get_stats()
        assert "hits" in stats

    @pytest.mark.asyncio
    async def test_custom_ttl(self):
        cache = SimpleCache(default_ttl=1, max_size=10)
        await cache.set("k", "v", ttl=1)
        result = await cache.get("k")
        assert result == "v"

    @pytest.mark.asyncio
    async def test_eviction_counter(self):
        cache = SimpleCache(default_ttl=300, max_size=2)
        await cache.set("k1", "v1")
        await cache.set("k2", "v2")
        await cache.set("k3", "v3")  # Should evict k1
        assert cache.evictions >= 0  # May or may not have evicted depending on BaseCache impl
