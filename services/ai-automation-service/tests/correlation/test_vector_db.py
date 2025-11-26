"""
Tests for Correlation Vector Database

Epic 37, Story 37.1: Vector Database Foundation
Tests FAISS-based vector storage and similarity search.
"""

import pytest
import numpy as np
from typing import Optional

from src.correlation.vector_db import CorrelationVectorDatabase, FAISS_AVAILABLE


@pytest.fixture
def vector_db():
    """Create vector database instance for testing."""
    if not FAISS_AVAILABLE:
        pytest.skip("FAISS not available")
    return CorrelationVectorDatabase(vector_dim=32)


@pytest.fixture
def sample_vectors():
    """Create sample feature vectors for testing."""
    return {
        "pair1": np.random.rand(32).astype(np.float32),
        "pair2": np.random.rand(32).astype(np.float32),
        "pair3": np.random.rand(32).astype(np.float32),
    }


class TestVectorDatabaseInitialization:
    """Test vector database initialization."""
    
    def test_init_success(self):
        """Test successful initialization."""
        if not FAISS_AVAILABLE:
            pytest.skip("FAISS not available")
        
        db = CorrelationVectorDatabase(vector_dim=32)
        assert db.vector_dim == 32
        assert db.use_gpu is False
        assert db.get_size() == 0
        assert db.is_trained is True
    
    def test_init_with_gpu(self):
        """Test initialization with GPU flag."""
        if not FAISS_AVAILABLE:
            pytest.skip("FAISS not available")
        
        db = CorrelationVectorDatabase(vector_dim=32, use_gpu=False)
        assert db.use_gpu is False
    
    def test_init_without_faiss(self, monkeypatch):
        """Test initialization fails without FAISS."""
        monkeypatch.setattr("src.correlation.vector_db.FAISS_AVAILABLE", False)
        
        with pytest.raises(ImportError, match="FAISS not available"):
            CorrelationVectorDatabase(vector_dim=32)


class TestVectorDatabaseAdd:
    """Test adding vectors to database."""
    
    def test_add_single_vector(self, vector_db, sample_vectors):
        """Test adding a single vector."""
        vector_db.add_correlation_vector(
            "entity1", "entity2", sample_vectors["pair1"]
        )
        
        assert vector_db.get_size() == 1
        assert len(vector_db.vector_metadata) == 1
        assert vector_db.vector_metadata[0] == ("entity1", "entity2")
    
    def test_add_multiple_vectors(self, vector_db, sample_vectors):
        """Test adding multiple vectors."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        vector_db.add_correlation_vector("e3", "e4", sample_vectors["pair2"])
        vector_db.add_correlation_vector("e5", "e6", sample_vectors["pair3"])
        
        assert vector_db.get_size() == 3
        assert len(vector_db.vector_metadata) == 3
    
    def test_add_wrong_dimension(self, vector_db):
        """Test adding vector with wrong dimension."""
        wrong_vector = np.random.rand(16).astype(np.float32)
        
        with pytest.raises(ValueError, match="Vector dimension mismatch"):
            vector_db.add_correlation_vector("e1", "e2", wrong_vector)


class TestVectorDatabaseSearch:
    """Test similarity search."""
    
    def test_search_empty_database(self, vector_db):
        """Test search on empty database."""
        query = np.random.rand(32).astype(np.float32)
        results = vector_db.search_similar_correlations(query, k=10)
        
        assert results == []
    
    def test_search_single_result(self, vector_db, sample_vectors):
        """Test search with single vector in database."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        
        # Search with same vector (should find itself)
        results = vector_db.search_similar_correlations(
            sample_vectors["pair1"], k=1
        )
        
        assert len(results) == 1
        assert results[0][0] == "e1"
        assert results[0][1] == "e2"
        assert results[0][2] == pytest.approx(0.0, abs=1e-5)  # Distance to self
    
    def test_search_multiple_results(self, vector_db, sample_vectors):
        """Test search with multiple vectors."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        vector_db.add_correlation_vector("e3", "e4", sample_vectors["pair2"])
        vector_db.add_correlation_vector("e5", "e6", sample_vectors["pair3"])
        
        # Search for similar vectors
        query = sample_vectors["pair1"]
        results = vector_db.search_similar_correlations(query, k=3)
        
        assert len(results) <= 3
        assert all(len(r) == 3 for r in results)  # (entity1, entity2, distance)
        assert all(isinstance(r[0], str) for r in results)
        assert all(isinstance(r[1], str) for r in results)
        assert all(isinstance(r[2], float) for r in results)
    
    def test_search_with_min_similarity(self, vector_db, sample_vectors):
        """Test search with minimum similarity threshold."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        vector_db.add_correlation_vector("e3", "e4", sample_vectors["pair2"])
        
        query = sample_vectors["pair1"]
        # Use very high threshold (should filter out most results)
        results = vector_db.search_similar_correlations(
            query, k=10, min_similarity=0.001
        )
        
        # Should only return results with distance <= 0.001
        assert all(r[2] <= 0.001 for r in results)
    
    def test_search_wrong_dimension(self, vector_db, sample_vectors):
        """Test search with wrong dimension query."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        
        wrong_query = np.random.rand(16).astype(np.float32)
        
        with pytest.raises(ValueError, match="Query vector dimension mismatch"):
            vector_db.search_similar_correlations(wrong_query, k=10)


class TestVectorDatabaseRetrieval:
    """Test vector retrieval."""
    
    def test_get_correlation_vector_not_implemented(self, vector_db, sample_vectors):
        """Test that direct retrieval is not implemented (FAISS limitation)."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        
        result = vector_db.get_correlation_vector("e1", "e2")
        
        # Direct retrieval not implemented (FAISS limitation)
        assert result is None


class TestVectorDatabaseRemoval:
    """Test vector removal."""
    
    def test_remove_existing(self, vector_db, sample_vectors):
        """Test removing existing vector."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        
        result = vector_db.remove_correlation("e1", "e2")
        
        # FAISS flat index doesn't support removal, but metadata is marked
        assert result is True
    
    def test_remove_nonexistent(self, vector_db):
        """Test removing non-existent vector."""
        result = vector_db.remove_correlation("e1", "e2")
        
        assert result is False


class TestVectorDatabaseManagement:
    """Test database management operations."""
    
    def test_clear(self, vector_db, sample_vectors):
        """Test clearing database."""
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        vector_db.add_correlation_vector("e3", "e4", sample_vectors["pair2"])
        
        assert vector_db.get_size() == 2
        
        vector_db.clear()
        
        assert vector_db.get_size() == 0
        assert len(vector_db.vector_metadata) == 0
    
    def test_get_size(self, vector_db, sample_vectors):
        """Test getting database size."""
        assert vector_db.get_size() == 0
        
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        assert vector_db.get_size() == 1
        
        vector_db.add_correlation_vector("e3", "e4", sample_vectors["pair2"])
        assert vector_db.get_size() == 2
    
    def test_get_memory_usage(self, vector_db, sample_vectors):
        """Test memory usage estimation."""
        # Empty database
        memory_empty = vector_db.get_memory_usage_mb()
        assert memory_empty >= 0
        
        # Add vectors
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        vector_db.add_correlation_vector("e3", "e4", sample_vectors["pair2"])
        
        memory_with_vectors = vector_db.get_memory_usage_mb()
        assert memory_with_vectors > memory_empty
        assert memory_with_vectors < 1.0  # Should be <1MB for 2 vectors


class TestVectorDatabasePersistence:
    """Test save/load operations."""
    
    def test_save_and_load(self, vector_db, sample_vectors, tmp_path):
        """Test saving and loading index."""
        # Add vectors
        vector_db.add_correlation_vector("e1", "e2", sample_vectors["pair1"])
        vector_db.add_correlation_vector("e3", "e4", sample_vectors["pair2"])
        
        # Save
        filepath = tmp_path / "test_index.faiss"
        vector_db.save(str(filepath))
        
        # Create new database and load
        new_db = CorrelationVectorDatabase(vector_dim=32)
        new_db.load(str(filepath))
        
        # Index should be loaded (but metadata not, as noted in warning)
        assert new_db.get_size() == 2
        
        # Note: Metadata is not saved/loaded (FAISS limitation)
        # In production, metadata would need to be saved separately


class TestVectorDatabasePerformance:
    """Test performance characteristics."""
    
    def test_search_performance(self, vector_db):
        """Test that search is reasonably fast."""
        import time
        
        # Add 100 vectors
        vectors = [np.random.rand(32).astype(np.float32) for _ in range(100)]
        for i in range(100):
            vector_db.add_correlation_vector(f"e{i*2}", f"e{i*2+1}", vectors[i])
        
        # Search
        query = np.random.rand(32).astype(np.float32)
        start = time.time()
        results = vector_db.search_similar_correlations(query, k=10)
        elapsed = time.time() - start
        
        # Should be fast (<100ms for 100 vectors with flat index)
        assert elapsed < 0.1
        assert len(results) <= 10

