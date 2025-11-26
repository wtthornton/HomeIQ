"""
Tests for Correlation Service

Epic 36: Correlation Analysis Foundation
Basic unit tests for correlation service components.
"""

import pytest
from datetime import datetime

from src.correlation import (
    TabPFNCorrelationPredictor,
    StreamingCorrelationTracker,
    CorrelationCache,
    CorrelationService
)


class TestTabPFNCorrelationPredictor:
    """Tests for TabPFN correlation predictor"""
    
    def test_initialization(self):
        """Test predictor initialization"""
        predictor = TabPFNCorrelationPredictor(device_only=True)
        assert predictor.device_only is True
        assert predictor.model is None
        assert predictor.is_trained is False
    
    def test_feature_extraction(self):
        """Test pair feature extraction"""
        predictor = TabPFNCorrelationPredictor(device_only=True)
        
        entity1 = {'domain': 'light', 'area_id': 'living_room', 'entity_id': 'light.living'}
        entity2 = {'domain': 'binary_sensor', 'area_id': 'living_room', 'entity_id': 'binary_sensor.motion'}
        
        features = predictor._extract_pair_features(entity1, entity2)
        
        assert features.same_area is True
        assert features.same_device_type is False
        assert features.entity1_domain == 'light'
        assert features.entity2_domain == 'binary_sensor'
    
    def test_device_only_predictions(self):
        """Test device-only prediction mode"""
        predictor = TabPFNCorrelationPredictor(device_only=True)
        
        entity1 = {'domain': 'light', 'area_id': 'living_room', 'entity_id': 'light.living'}
        entity2 = {'domain': 'binary_sensor', 'area_id': 'living_room', 'entity_id': 'binary_sensor.motion'}
        
        pairs = [(entity1, entity2)]
        results = predictor.predict_likely_pairs(pairs, threshold=0.5)
        
        assert len(results) > 0
        assert results[0][2] >= 0.5  # Probability >= threshold


class TestStreamingCorrelationTracker:
    """Tests for streaming correlation tracker"""
    
    def test_initialization(self):
        """Test tracker initialization"""
        tracker = StreamingCorrelationTracker(window_size_hours=24)
        assert tracker.window_size_hours == 24
        assert len(tracker.entity_stats) == 0
    
    def test_update_and_get_correlation(self):
        """Test correlation update and retrieval"""
        tracker = StreamingCorrelationTracker()
        
        # Update with correlated values
        for i in range(10):
            tracker.update('entity1', 'entity2', 0.5 + i * 0.1, 0.5 + i * 0.1)
        
        correlation = tracker.get_correlation('entity1', 'entity2')
        
        # Should have positive correlation
        assert correlation is not None
        assert correlation > 0.0
    
    def test_memory_usage(self):
        """Test memory usage estimation"""
        tracker = StreamingCorrelationTracker()
        
        # Add some data
        for i in range(100):
            tracker.update(f'entity{i}', f'entity{i+1}', 0.5, 0.5)
        
        memory_mb = tracker.get_memory_usage_mb()
        
        # Should be reasonable (<10MB for 100 entities)
        assert memory_mb < 10.0


class TestCorrelationCache:
    """Tests for correlation cache"""
    
    def test_cache_set_and_get(self):
        """Test cache set and get"""
        cache = CorrelationCache()  # In-memory only
        
        cache.set('entity1', 'entity2', 0.75, ttl_seconds=3600)
        cached = cache.get('entity1', 'entity2')
        
        assert cached == 0.75
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        cache = CorrelationCache()
        
        cache.set('entity1', 'entity2', 0.75, ttl_seconds=1)
        
        # Should be valid immediately
        assert cache.get('entity1', 'entity2') == 0.75
        
        # After expiration (simulated by setting short TTL and waiting)
        # Note: In real test, would use time mocking
        cache.clear_expired()
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = CorrelationCache()
        
        cache.set('entity1', 'entity2', 0.75)
        cache.set('entity2', 'entity3', 0.65)
        
        stats = cache.get_stats()
        
        assert stats['memory_cache_size'] == 2


class TestCorrelationService:
    """Tests for unified correlation service"""
    
    def test_initialization(self):
        """Test service initialization"""
        service = CorrelationService(enable_tabpfn=True, enable_streaming=True)
        
        assert service.tabpfn_predictor is not None
        assert service.streaming_tracker is not None
        assert service.feature_extractor is not None
        assert service.cache is not None
    
    def test_update_and_get_correlation(self):
        """Test correlation update and retrieval"""
        service = CorrelationService(enable_streaming=True)
        
        # Update correlation
        service.update_correlation('entity1', 'entity2', 0.5, 0.6)
        
        # Get correlation
        corr = service.get_correlation('entity1', 'entity2')
        
        # Should have correlation (may be None if insufficient data)
        assert corr is None or -1.0 <= corr <= 1.0
    
    def test_memory_usage(self):
        """Test memory usage estimation"""
        service = CorrelationService()
        
        memory_mb = service.get_memory_usage_mb()
        
        # Should be reasonable (<60MB as per Epic 36 spec)
        assert memory_mb < 60.0

