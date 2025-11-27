"""
Performance Tests for Epic 38 Advanced Features

Epic 38, Story 38.7: Performance Testing and Optimization
Benchmarks calendar integration, augmented analytics, and presence-aware correlations.

Performance Targets (NUC-optimized):
- Calendar correlation: <10ms per query (cached)
- Augmented Analytics: <100ms per analysis
- Presence-aware correlation: <50ms per analysis
- Memory: <40MB for advanced features (without Wide & Deep)
"""

import pytest
import asyncio
import time
import tracemalloc
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.correlation import (
    CorrelationService,
    CalendarCorrelationIntegration,
    AugmentedCorrelationAnalytics,
    PresenceAwareCorrelationAnalyzer
)


class TestCalendarIntegrationPerformance:
    """Performance tests for calendar integration"""
    
    @pytest.fixture
    async def calendar_integration(self):
        """Create calendar integration instance"""
        integration = CalendarCorrelationIntegration(
            calendar_service_url=None,  # Mock mode
            cache_ttl=timedelta(hours=1),
            max_cache_size=100
        )
        yield integration
        if hasattr(integration, 'session') and integration.session:
            await integration.session.close()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_calendar_query_performance(self, calendar_integration):
        """
        GIVEN: Calendar integration with cache
        WHEN: Querying presence features
        THEN: Should complete in <10ms (cached) or <100ms (uncached)
        """
        timestamp = datetime.now(timezone.utc)
        
        # First query (uncached)
        start = time.perf_counter()
        features = await calendar_integration.get_presence_features(timestamp)
        uncached_time = (time.perf_counter() - start) * 1000  # Convert to ms
        
        # Second query (cached)
        start = time.perf_counter()
        features = await calendar_integration.get_presence_features(timestamp)
        cached_time = (time.perf_counter() - start) * 1000  # Convert to ms
        
        assert uncached_time < 100, f"Uncached query took {uncached_time:.2f}ms (target: <100ms)"
        assert cached_time < 10, f"Cached query took {cached_time:.2f}ms (target: <10ms)"
        assert 'current_presence' in features
        assert 'predicted_presence' in features
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_calendar_memory_usage(self, calendar_integration):
        """
        GIVEN: Calendar integration
        WHEN: Processing multiple queries
        THEN: Memory usage should stay <10MB
        """
        tracemalloc.start()
        
        timestamp = datetime.now(timezone.utc)
        for i in range(100):
            await calendar_integration.get_presence_features(
                timestamp + timedelta(minutes=i)
            )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_mb = peak / (1024 * 1024)
        assert memory_mb < 10, f"Memory usage {memory_mb:.2f}MB exceeds target <10MB"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_calendar_cache_efficiency(self, calendar_integration):
        """
        GIVEN: Calendar integration with cache
        WHEN: Querying same timestamp multiple times
        THEN: Cache hit rate should be >90% after warmup
        """
        timestamp = datetime.now(timezone.utc)
        
        # Warmup
        for _ in range(10):
            await calendar_integration.get_presence_features(timestamp)
        
        # Measure cache hits
        cache_hits = 0
        total_queries = 100
        
        for _ in range(total_queries):
            start = time.perf_counter()
            await calendar_integration.get_presence_features(timestamp)
            query_time = (time.perf_counter() - start) * 1000
            
            # Cached queries should be <10ms
            if query_time < 10:
                cache_hits += 1
        
        hit_rate = (cache_hits / total_queries) * 100
        assert hit_rate > 90, f"Cache hit rate {hit_rate:.1f}% below target >90%"


class TestAugmentedAnalyticsPerformance:
    """Performance tests for augmented analytics"""
    
    @pytest.fixture
    def correlation_service(self):
        """Create correlation service instance"""
        return CorrelationService(
            enable_tabpfn=True,
            enable_streaming=True,
            enable_vector_db=False  # Disable for performance tests
        )
    
    @pytest.fixture
    def augmented_analytics(self, correlation_service):
        """Create augmented analytics instance"""
        return AugmentedCorrelationAnalytics(correlation_service)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_pattern_detection_performance(self, augmented_analytics):
        """
        GIVEN: Augmented analytics with sample entities
        WHEN: Detecting patterns
        THEN: Should complete in <100ms
        """
        entities = [
            {'entity_id': f'light.living_{i}', 'domain': 'light', 'area_id': 'living_room'}
            for i in range(20)
        ]
        
        correlations = [
            {
                'entity1_id': 'light.living_1',
                'entity2_id': 'binary_sensor.motion',
                'correlation': 0.85,
                'confidence': 0.9
            }
            for _ in range(10)
        ]
        
        start = time.perf_counter()
        patterns = await augmented_analytics.detect_patterns(entities, correlations)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        assert elapsed < 100, f"Pattern detection took {elapsed:.2f}ms (target: <100ms)"
        assert isinstance(patterns, list)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_explanation_generation_performance(self, augmented_analytics):
        """
        GIVEN: Augmented analytics with correlation data
        WHEN: Generating explanation
        THEN: Should complete in <100ms
        """
        correlation_data = {
            'entity1_id': 'light.living',
            'entity2_id': 'binary_sensor.motion',
            'correlation': 0.85,
            'confidence': 0.9,
            'features': {
                'same_area': True,
                'temporal_proximity': 0.8
            }
        }
        
        start = time.perf_counter()
        explanation = await augmented_analytics.explain_correlation(correlation_data)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        assert elapsed < 100, f"Explanation generation took {elapsed:.2f}ms (target: <100ms)"
        assert isinstance(explanation, str)
        assert len(explanation) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_augmented_analytics_memory_usage(self, augmented_analytics):
        """
        GIVEN: Augmented analytics
        WHEN: Processing multiple analyses
        THEN: Memory usage should stay <20MB
        """
        tracemalloc.start()
        
        entities = [
            {'entity_id': f'light.living_{i}', 'domain': 'light', 'area_id': 'living_room'}
            for i in range(50)
        ]
        
        correlations = [
            {
                'entity1_id': f'light.living_{i}',
                'entity2_id': 'binary_sensor.motion',
                'correlation': 0.85,
                'confidence': 0.9
            }
            for i in range(50)
        ]
        
        for _ in range(10):
            await augmented_analytics.detect_patterns(entities, correlations)
            correlation_data = {
                'entity1_id': 'light.living_1',
                'entity2_id': 'binary_sensor.motion',
                'correlation': 0.85,
                'confidence': 0.9
            }
            await augmented_analytics.explain_correlation(correlation_data)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_mb = peak / (1024 * 1024)
        assert memory_mb < 20, f"Memory usage {memory_mb:.2f}MB exceeds target <20MB"


class TestPresenceAwareCorrelationPerformance:
    """Performance tests for presence-aware correlations"""
    
    @pytest.fixture
    async def calendar_integration(self):
        """Create calendar integration instance"""
        integration = CalendarCorrelationIntegration(
            calendar_service_url=None,  # Mock mode
            cache_ttl=timedelta(hours=1)
        )
        yield integration
        if hasattr(integration, 'session') and integration.session:
            await integration.session.close()
    
    @pytest.fixture
    def correlation_service(self):
        """Create correlation service instance"""
        return CorrelationService(
            enable_tabpfn=True,
            enable_streaming=True,
            enable_vector_db=False
        )
    
    @pytest.fixture
    async def presence_analyzer(self, correlation_service, calendar_integration):
        """Create presence-aware analyzer instance"""
        return PresenceAwareCorrelationAnalyzer(correlation_service, calendar_integration)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_presence_aware_analysis_performance(self, presence_analyzer):
        """
        GIVEN: Presence-aware analyzer
        WHEN: Analyzing presence correlation
        THEN: Should complete in <50ms
        """
        entity_id = 'light.living'
        timestamp = datetime.now(timezone.utc)
        
        start = time.perf_counter()
        result = await presence_analyzer.analyze_presence_correlation(
            entity_id,
            timestamp,
            time_window=timedelta(hours=24)
        )
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        assert elapsed < 50, f"Presence-aware analysis took {elapsed:.2f}ms (target: <50ms)"
        # Result may be None if no correlations found, which is acceptable


class TestOverallSystemPerformance:
    """Performance tests for overall Epic 38 system"""
    
    @pytest.fixture
    async def full_system(self):
        """Create full Epic 38 system with all components"""
        calendar_integration = CalendarCorrelationIntegration(
            calendar_service_url=None,  # Mock mode
            cache_ttl=timedelta(hours=1)
        )
        
        correlation_service = CorrelationService(
            calendar_integration=calendar_integration,
            enable_tabpfn=True,
            enable_streaming=True,
            enable_vector_db=False
        )
        
        augmented_analytics = AugmentedCorrelationAnalytics(correlation_service)
        
        yield {
            'calendar_integration': calendar_integration,
            'correlation_service': correlation_service,
            'augmented_analytics': augmented_analytics
        }
        
        if hasattr(calendar_integration, 'session') and calendar_integration.session:
            await calendar_integration.session.close()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_end_to_end_performance(self, full_system):
        """
        GIVEN: Full Epic 38 system
        WHEN: Processing end-to-end correlation analysis
        THEN: Should complete in <200ms
        """
        calendar_integration = full_system['calendar_integration']
        correlation_service = full_system['correlation_service']
        augmented_analytics = full_system['augmented_analytics']
        
        entity1 = {'entity_id': 'light.living', 'domain': 'light', 'area_id': 'living_room'}
        entity2 = {'entity_id': 'binary_sensor.motion', 'domain': 'binary_sensor', 'area_id': 'living_room'}
        timestamp = datetime.now(timezone.utc)
        
        start = time.perf_counter()
        
        # Get presence features
        presence_features = await calendar_integration.get_presence_features(timestamp)
        
        # Compute correlation
        correlation = await correlation_service.compute_correlation(
            entity1, entity2, timestamp=timestamp
        )
        
        # Generate explanation
        if correlation:
            explanation = await augmented_analytics.explain_correlation(correlation)
        
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        assert elapsed < 200, f"End-to-end processing took {elapsed:.2f}ms (target: <200ms)"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_system_memory_usage(self, full_system):
        """
        GIVEN: Full Epic 38 system
        WHEN: Processing multiple analyses
        THEN: Memory usage should stay <40MB (without Wide & Deep)
        """
        tracemalloc.start()
        
        calendar_integration = full_system['calendar_integration']
        correlation_service = full_system['correlation_service']
        augmented_analytics = full_system['augmented_analytics']
        
        entities = [
            {'entity_id': f'light.living_{i}', 'domain': 'light', 'area_id': 'living_room'}
            for i in range(20)
        ]
        
        timestamp = datetime.now(timezone.utc)
        
        for i in range(10):
            # Calendar integration
            await calendar_integration.get_presence_features(timestamp)
            
            # Correlation computation
            if i < len(entities) - 1:
                await correlation_service.compute_correlation(
                    entities[i], entities[i+1], timestamp=timestamp
                )
            
            # Augmented analytics
            correlations = [
                {
                    'entity1_id': entities[j]['entity_id'],
                    'entity2_id': entities[j+1]['entity_id'],
                    'correlation': 0.85,
                    'confidence': 0.9
                }
                for j in range(min(5, len(entities)-1))
            ]
            await augmented_analytics.detect_patterns(entities[:10], correlations)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_mb = peak / (1024 * 1024)
        assert memory_mb < 40, f"System memory usage {memory_mb:.2f}MB exceeds target <40MB (without Wide & Deep)"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_requests_performance(self, full_system):
        """
        GIVEN: Full Epic 38 system
        WHEN: Processing concurrent requests
        THEN: Should handle 10 concurrent requests in <500ms
        """
        calendar_integration = full_system['calendar_integration']
        timestamp = datetime.now(timezone.utc)
        
        async def process_request(i: int):
            """Process a single request"""
            return await calendar_integration.get_presence_features(
                timestamp + timedelta(minutes=i)
            )
        
        start = time.perf_counter()
        
        # Process 10 concurrent requests
        tasks = [process_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        assert elapsed < 500, f"10 concurrent requests took {elapsed:.2f}ms (target: <500ms)"
        assert len(results) == 10
        assert all('current_presence' in r for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'performance'])

