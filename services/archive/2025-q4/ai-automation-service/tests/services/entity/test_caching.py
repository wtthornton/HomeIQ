"""
Unit tests for caching functionality

Epic AI-12, Story AI12.10: Performance Optimization & Caching
Tests for EmbeddingCache, IndexCache, and QueryCache.
"""

import pytest
from datetime import datetime, timedelta
import time

from src.services.entity.embedding_cache import EmbeddingCache
from src.services.entity.index_cache import IndexCache
from src.services.entity.query_cache import QueryCache
from src.services.entity.personalized_index import PersonalizedEntityIndex


class TestEmbeddingCache:
    """Tests for EmbeddingCache"""
    
    def test_put_and_get(self):
        """Test basic put/get operations"""
        cache = EmbeddingCache(max_size=10)
        
        embedding = [0.1, 0.2, 0.3]
        cache.put("test text", embedding)
        
        result = cache.get("test text")
        assert result == embedding
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = EmbeddingCache(max_size=10)
        
        result = cache.get("nonexistent")
        assert result is None
    
    def test_case_insensitive(self):
        """Test that cache is case-insensitive"""
        cache = EmbeddingCache(max_size=10)
        
        embedding = [0.1, 0.2, 0.3]
        cache.put("Test Text", embedding)
        
        # Should find with different case
        result = cache.get("test text")
        assert result == embedding
        
        result = cache.get("TEST TEXT")
        assert result == embedding
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = EmbeddingCache(max_size=3)
        
        # Add 3 items
        cache.put("text1", [1.0])
        cache.put("text2", [2.0])
        cache.put("text3", [3.0])
        
        # All should be in cache
        assert cache.get("text1") == [1.0]
        assert cache.get("text2") == [2.0]
        assert cache.get("text3") == [3.0]
        
        # Add 4th item - should evict least recently used (text1)
        cache.put("text4", [4.0])
        
        # text1 should be evicted
        assert cache.get("text1") is None
        assert cache.get("text2") == [2.0]
        assert cache.get("text3") == [3.0]
        assert cache.get("text4") == [4.0]
    
    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = EmbeddingCache(max_size=10, ttl_seconds=1)
        
        embedding = [0.1, 0.2, 0.3]
        cache.put("test", embedding)
        
        # Should be in cache
        assert cache.get("test") == embedding
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("test") is None
    
    def test_cleanup_expired(self):
        """Test cleanup_expired removes expired entries"""
        cache = EmbeddingCache(max_size=10, ttl_seconds=1)
        
        cache.put("text1", [1.0])
        cache.put("text2", [2.0])
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup should remove expired entries
        removed = cache.cleanup_expired()
        assert removed == 2
        assert cache.get("text1") is None
        assert cache.get("text2") is None
    
    def test_stats(self):
        """Test cache statistics"""
        cache = EmbeddingCache(max_size=10)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        
        # Add and retrieve
        cache.put("text1", [1.0])
        cache.get("text1")  # Hit
        cache.get("text2")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 50.0
    
    def test_clear(self):
        """Test clearing cache"""
        cache = EmbeddingCache(max_size=10)
        
        cache.put("text1", [1.0])
        cache.put("text2", [2.0])
        
        cache.clear()
        
        assert cache.get("text1") is None
        assert cache.get("text2") is None
        stats = cache.get_stats()
        assert stats["size"] == 0


class TestIndexCache:
    """Tests for IndexCache"""
    
    def test_singleton(self):
        """Test singleton pattern"""
        cache1 = IndexCache.get_instance()
        cache2 = IndexCache.get_instance()
        
        assert cache1 is cache2
    
    def test_put_and_get(self):
        """Test basic put/get operations"""
        cache = IndexCache(ttl_seconds=None)
        
        index = PersonalizedEntityIndex()
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        cache.put(index, user_id="test_user")
        
        result = cache.get(user_id="test_user")
        assert result is not None
        assert result.get_entity("light.test") is not None
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = IndexCache(ttl_seconds=None)
        
        result = cache.get(user_id="nonexistent")
        assert result is None
    
    def test_force_rebuild(self):
        """Test force_rebuild ignores cache"""
        cache = IndexCache(ttl_seconds=None)
        
        index = PersonalizedEntityIndex()
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        cache.put(index, user_id="test_user")
        
        # Should return None with force_rebuild=True
        result = cache.get(user_id="test_user", force_rebuild=True)
        assert result is None
    
    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = IndexCache(ttl_seconds=1)
        
        index = PersonalizedEntityIndex()
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        cache.put(index, user_id="test_user")
        
        # Should be in cache
        assert cache.get(user_id="test_user") is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get(user_id="test_user") is None
    
    def test_invalidate(self):
        """Test invalidate removes entry"""
        cache = IndexCache(ttl_seconds=None)
        
        index = PersonalizedEntityIndex()
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        cache.put(index, user_id="test_user")
        cache.invalidate(user_id="test_user")
        
        assert cache.get(user_id="test_user") is None
    
    def test_stats(self):
        """Test cache statistics"""
        cache = IndexCache(ttl_seconds=None)
        
        index = PersonalizedEntityIndex()
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["builds"] == 0
        
        # Build and retrieve
        cache.put(index, user_id="test_user")
        cache.get(user_id="test_user")  # Hit
        cache.get(user_id="nonexistent")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["builds"] == 1
        assert stats["cached_users"] == 1
    
    def test_clear(self):
        """Test clearing cache"""
        cache = IndexCache(ttl_seconds=None)
        
        index = PersonalizedEntityIndex()
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        cache.put(index, user_id="test_user")
        cache.clear()
        
        assert cache.get(user_id="test_user") is None
        stats = cache.get_stats()
        assert stats["cached_users"] == 0


class TestQueryCache:
    """Tests for QueryCache"""
    
    def test_put_and_get(self):
        """Test basic put/get operations"""
        cache = QueryCache(max_size=10)
        
        results = [("light.test", 0.9), ("light.other", 0.8)]
        cache.put("test query", results)
        
        result = cache.get("test query")
        assert result == results
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = QueryCache(max_size=10)
        
        result = cache.get("nonexistent query")
        assert result is None
    
    def test_cache_key_includes_filters(self):
        """Test that cache key includes domain and area filters"""
        cache = QueryCache(max_size=10)
        
        results1 = [("light.test", 0.9)]
        results2 = [("switch.test", 0.8)]
        
        cache.put("test", results1, domain="light")
        cache.put("test", results2, domain="switch")
        
        # Should return different results based on domain
        assert cache.get("test", domain="light") == results1
        assert cache.get("test", domain="switch") == results2
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = QueryCache(max_size=3)
        
        # Add 3 queries
        cache.put("query1", [("entity1", 0.9)])
        cache.put("query2", [("entity2", 0.8)])
        cache.put("query3", [("entity3", 0.7)])
        
        # All should be in cache
        assert cache.get("query1") is not None
        assert cache.get("query2") is not None
        assert cache.get("query3") is not None
        
        # Add 4th query - should evict least recently used (query1)
        cache.put("query4", [("entity4", 0.6)])
        
        # query1 should be evicted
        assert cache.get("query1") is None
        assert cache.get("query2") is not None
        assert cache.get("query3") is not None
        assert cache.get("query4") is not None
    
    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = QueryCache(max_size=10, ttl_seconds=1)
        
        results = [("light.test", 0.9)]
        cache.put("test query", results)
        
        # Should be in cache
        assert cache.get("test query") == results
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("test query") is None
    
    def test_invalidate(self):
        """Test invalidate removes entries"""
        cache = QueryCache(max_size=10)
        
        cache.put("test query", [("entity1", 0.9)])
        cache.put("other query", [("entity2", 0.8)])
        
        # Invalidate all
        removed = cache.invalidate()
        assert removed == 2
        assert cache.get("test query") is None
        assert cache.get("other query") is None
    
    def test_invalidate_specific_query(self):
        """Test invalidate for specific query"""
        cache = QueryCache(max_size=10)
        
        cache.put("test query", [("entity1", 0.9)])
        cache.put("other query", [("entity2", 0.8)])
        
        # Invalidate specific query
        removed = cache.invalidate("test")
        assert removed >= 1
        assert cache.get("test query") is None
        # Other query might still be there (depends on implementation)
    
    def test_stats(self):
        """Test cache statistics"""
        cache = QueryCache(max_size=10)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        
        # Add and retrieve
        cache.put("query1", [("entity1", 0.9)])
        cache.get("query1")  # Hit
        cache.get("query2")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 50.0
    
    def test_clear(self):
        """Test clearing cache"""
        cache = QueryCache(max_size=10)
        
        cache.put("query1", [("entity1", 0.9)])
        cache.put("query2", [("entity2", 0.8)])
        
        cache.clear()
        
        assert cache.get("query1") is None
        assert cache.get("query2") is None
        stats = cache.get_stats()
        assert stats["size"] == 0


class TestCachingIntegration:
    """Integration tests for caching in PersonalizedEntityIndex"""
    
    def test_embedding_cache_in_index(self):
        """Test that PersonalizedEntityIndex uses EmbeddingCache"""
        index = PersonalizedEntityIndex()
        
        # Add entity - should generate embedding
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        # Search - should use cached embedding
        results1 = index.search_by_name("test light")
        
        # Search again - should use cached embedding (faster)
        results2 = index.search_by_name("test light")
        
        # Results should be the same
        assert results1 == results2
        
        # Check cache stats
        stats = index.get_stats()
        assert "embedding_cache" in stats
        assert stats["embedding_cache"]["hits"] > 0
    
    def test_query_cache_in_index(self):
        """Test that PersonalizedEntityIndex uses QueryCache"""
        index = PersonalizedEntityIndex()
        
        # Add entity
        index.add_entity("light.test", "light", {"name": "Test Light"})
        
        # Search - should cache query result
        results1 = index.search_by_name("test light")
        
        # Search again - should use cached result
        results2 = index.search_by_name("test light")
        
        # Results should be the same
        assert results1 == results2
        
        # Check cache stats
        stats = index.get_stats()
        assert "query_cache" in stats
        assert stats["query_cache"]["hits"] > 0

