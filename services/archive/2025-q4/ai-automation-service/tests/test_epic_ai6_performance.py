"""
Performance Tests for Epic AI-6: Blueprint-Enhanced Suggestion Intelligence

Performance benchmarks to ensure all services meet latency targets:
- Blueprint discovery: <50ms latency
- Pattern validation: <30ms latency
- Preference ranking: <10ms latency

Story AI6.13: Comprehensive Testing Suite
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.blueprint_discovery.blueprint_ranker import BlueprintRanker
from src.blueprint_discovery.blueprint_validator import BlueprintValidator
from src.blueprint_discovery.creativity_filter import CreativityFilter
from src.blueprint_discovery.opportunity_finder import BlueprintOpportunityFinder
from src.blueprint_discovery.preference_aware_ranker import PreferenceAwareRanker
from src.blueprint_discovery.preference_manager import PreferenceManager


@pytest.fixture
def mock_device_inventory():
    """Mock device inventory for testing."""
    return [
        {
            "device_id": "test_device_1",
            "name": "Test Device 1",
            "domain": "light",
            "platform": "hue",
            "area_id": "living_room",
        },
        {
            "device_id": "test_device_2",
            "name": "Test Device 2",
            "domain": "sensor",
            "platform": "hue",
            "area_id": "living_room",
        },
    ]


@pytest.fixture
def mock_blueprint_results():
    """Mock blueprint search results."""
    return [
        {
            "blueprint_id": "test_bp_1",
            "title": "Test Blueprint 1",
            "domain": "light",
            "fit_score": 0.85,
        },
        {
            "blueprint_id": "test_bp_2",
            "title": "Test Blueprint 2",
            "domain": "sensor",
            "fit_score": 0.75,
        },
    ]


@pytest.fixture
def sample_patterns():
    """Sample patterns for validation testing."""
    return [
        {
            "pattern_id": "pattern_1",
            "type": "time_of_day",
            "confidence": 0.85,
            "entities": ["light.office_light"],
            "trigger_time": "08:00:00",
        },
        {
            "pattern_id": "pattern_2",
            "type": "co_occurrence",
            "confidence": 0.75,
            "entities": ["sensor.motion", "light.office_light"],
        },
    ]


@pytest.fixture
def sample_suggestions():
    """Sample suggestions for ranking tests."""
    return [
        {
            "title": "High Confidence Pattern",
            "confidence": 0.90,
            "type": "pattern_based",
            "blueprint_validated": False,
        },
        {
            "title": "Blueprint Opportunity",
            "confidence": 0.80,
            "type": "blueprint_opportunity",
            "source": "Epic-AI-6",
        },
        {
            "title": "Medium Confidence Pattern",
            "confidence": 0.70,
            "type": "pattern_based",
            "blueprint_validated": True,
            "blueprint_confidence_boost": 0.05,
        },
        {
            "title": "Low Confidence Pattern",
            "confidence": 0.60,
            "type": "pattern_based",
            "blueprint_validated": False,
        },
    ]


class TestBlueprintDiscoveryPerformance:
    """Performance tests for BlueprintOpportunityFinder."""

    @pytest.mark.asyncio
    async def test_blueprint_discovery_latency(self, mock_device_inventory, mock_blueprint_results):
        """
        Test blueprint discovery meets <50ms latency target.
        
        Target: <50ms for discovering blueprint opportunities from device inventory.
        """
        with patch("src.blueprint_discovery.opportunity_finder.MinerIntegration") as MockMiner, \
             patch("src.blueprint_discovery.opportunity_finder.DataAPIClient") as MockDataAPI:

            # Mock miner to return results quickly
            mock_miner = MagicMock()
            mock_miner.is_available.return_value = True
            mock_miner.search_blueprints.return_value = mock_blueprint_results
            MockMiner.return_value = mock_miner

            # Mock data API client
            mock_data_api = AsyncMock()
            mock_data_api.get_devices.return_value = mock_device_inventory
            mock_data_api.get_entities.return_value = []
            MockDataAPI.return_value = mock_data_api

            finder = BlueprintOpportunityFinder()

            # Measure performance
            start_time = time.perf_counter()
            opportunities = await finder.find_opportunities()
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Assert latency target
            assert duration_ms < 50.0, f"Blueprint discovery took {duration_ms:.2f}ms, exceeds 50ms target"
            assert opportunities is not None

    @pytest.mark.asyncio
    async def test_blueprint_discovery_with_cache(self, mock_device_inventory, mock_blueprint_results):
        """Test blueprint discovery performance with caching enabled."""
        with patch("src.blueprint_discovery.opportunity_finder.MinerIntegration") as MockMiner, \
             patch("src.blueprint_discovery.opportunity_finder.DataAPIClient") as MockDataAPI:

            mock_miner = MagicMock()
            mock_miner.is_available.return_value = True
            mock_miner.search_blueprints.return_value = mock_blueprint_results
            MockMiner.return_value = mock_miner

            mock_data_api = AsyncMock()
            mock_data_api.get_devices.return_value = mock_device_inventory
            mock_data_api.get_entities.return_value = []
            MockDataAPI.return_value = mock_data_api

            finder = BlueprintOpportunityFinder()

            # First call (populates cache)
            await finder.find_opportunities()

            # Second call (uses cache) - should be faster
            start_time = time.perf_counter()
            opportunities = await finder.find_opportunities()
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Cached calls should be very fast (<10ms)
            assert duration_ms < 10.0, f"Cached blueprint discovery took {duration_ms:.2f}ms"
            assert opportunities is not None


class TestPatternValidationPerformance:
    """Performance tests for BlueprintValidator."""

    @pytest.mark.asyncio
    async def test_pattern_validation_latency(self, sample_patterns, mock_blueprint_results):
        """
        Test pattern validation meets <30ms latency target.
        
        Target: <30ms for validating patterns against blueprints.
        """
        with patch("src.blueprint_discovery.blueprint_validator.MinerIntegration") as MockMiner:

            mock_miner = MagicMock()
            mock_miner.is_available.return_value = True
            mock_miner.search_blueprints.return_value = mock_blueprint_results
            MockMiner.return_value = mock_miner

            validator = BlueprintValidator()

            # Measure performance for validating all patterns
            start_time = time.perf_counter()
            
            for pattern in sample_patterns:
                await validator.validate_pattern(pattern)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            avg_latency_ms = duration_ms / len(sample_patterns)

            # Assert latency target (average per pattern)
            assert avg_latency_ms < 30.0, f"Pattern validation took {avg_latency_ms:.2f}ms per pattern, exceeds 30ms target"
            assert duration_ms < 100.0, f"Total validation time {duration_ms:.2f}ms for {len(sample_patterns)} patterns"

    @pytest.mark.asyncio
    async def test_pattern_validation_batch_performance(self, sample_patterns, mock_blueprint_results):
        """Test batch pattern validation performance."""
        with patch("src.blueprint_discovery.blueprint_validator.MinerIntegration") as MockMiner:

            mock_miner = MagicMock()
            mock_miner.is_available.return_value = True
            mock_miner.search_blueprints.return_value = mock_blueprint_results
            MockMiner.return_value = mock_miner

            validator = BlueprintValidator()

            # Measure performance for batch validation
            start_time = time.perf_counter()
            
            validated_patterns = []
            for pattern in sample_patterns:
                validated = await validator.validate_pattern(pattern)
                validated_patterns.append(validated)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            avg_latency_ms = duration_ms / len(sample_patterns)

            # Batch should be efficient (<30ms per pattern)
            assert avg_latency_ms < 30.0, f"Batch validation took {avg_latency_ms:.2f}ms per pattern"
            assert len(validated_patterns) == len(sample_patterns)


class TestPreferenceRankingPerformance:
    """Performance tests for preference-based ranking services."""

    @pytest.mark.asyncio
    async def test_preference_ranking_latency(self, sample_suggestions):
        """
        Test preference-aware ranking meets <10ms latency target.
        
        Target: <10ms for ranking suggestions with all preferences applied.
        """
        with patch("src.blueprint_discovery.preference_aware_ranker.PreferenceManager") as MockPrefMgr:

            mock_pref_mgr = MagicMock()
            mock_pref_mgr.get_max_suggestions.return_value = 10
            mock_pref_mgr.get_creativity_level.return_value = "balanced"
            mock_pref_mgr.get_blueprint_preference.return_value = "medium"
            MockPrefMgr.return_value = mock_pref_mgr

            ranker = PreferenceAwareRanker(user_id="test_user")

            # Measure performance
            start_time = time.perf_counter()
            ranked_suggestions = await ranker.rank_suggestions(sample_suggestions)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Assert latency target
            assert duration_ms < 10.0, f"Preference ranking took {duration_ms:.2f}ms, exceeds 10ms target"
            assert ranked_suggestions is not None
            assert len(ranked_suggestions) <= len(sample_suggestions)

    @pytest.mark.asyncio
    async def test_creativity_filter_performance(self, sample_suggestions):
        """Test creativity filter performance."""
        with patch("src.blueprint_discovery.creativity_filter.PreferenceManager") as MockPrefMgr:

            mock_pref_mgr = MagicMock()
            mock_pref_mgr.get_creativity_level.return_value = "balanced"
            MockPrefMgr.return_value = mock_pref_mgr

            filter_service = CreativityFilter(user_id="test_user")

            # Measure performance
            start_time = time.perf_counter()
            filtered_suggestions = await filter_service.filter_suggestions(sample_suggestions)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Filtering should be very fast (<10ms)
            assert duration_ms < 10.0, f"Creativity filtering took {duration_ms:.2f}ms"
            assert filtered_suggestions is not None

    @pytest.mark.asyncio
    async def test_blueprint_ranker_performance(self, sample_suggestions):
        """Test blueprint ranker performance."""
        with patch("src.blueprint_discovery.blueprint_ranker.PreferenceManager") as MockPrefMgr:

            mock_pref_mgr = MagicMock()
            mock_pref_mgr.get_blueprint_preference.return_value = "medium"
            MockPrefMgr.return_value = mock_pref_mgr

            ranker = BlueprintRanker(user_id="test_user")

            # Measure performance
            start_time = time.perf_counter()
            ranked_suggestions = await ranker.apply_blueprint_preference_weighting(sample_suggestions)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Ranking should be very fast (<5ms)
            assert duration_ms < 5.0, f"Blueprint ranking took {duration_ms:.2f}ms"
            assert ranked_suggestions is not None

    @pytest.mark.asyncio
    async def test_preference_manager_performance(self):
        """Test preference manager lookup performance."""
        with patch("src.blueprint_discovery.preference_manager.get_db_session") as MockDB:

            # Mock database session
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # Returns default values
            mock_session.execute.return_value = mock_result
            MockDB.return_value.__aenter__.return_value = mock_session

            manager = PreferenceManager(user_id="test_user")

            # Measure performance for getting all preferences
            start_time = time.perf_counter()
            
            max_suggestions = await manager.get_max_suggestions()
            creativity_level = await manager.get_creativity_level()
            blueprint_preference = await manager.get_blueprint_preference()
            
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Preference lookups should be fast (<10ms total for 3 lookups)
            assert duration_ms < 10.0, f"Preference lookups took {duration_ms:.2f}ms"
            assert max_suggestions is not None
            assert creativity_level is not None
            assert blueprint_preference is not None


class TestEndToEndPerformance:
    """End-to-end performance tests for the complete preference ranking flow."""

    @pytest.mark.asyncio
    async def test_full_preference_ranking_flow(self, sample_suggestions):
        """Test end-to-end preference ranking flow performance."""
        with patch("src.blueprint_discovery.preference_aware_ranker.PreferenceManager") as MockPrefMgr:

            mock_pref_mgr = MagicMock()
            mock_pref_mgr.get_max_suggestions.return_value = 10
            mock_pref_mgr.get_creativity_level.return_value = "balanced"
            mock_pref_mgr.get_blueprint_preference.return_value = "medium"
            MockPrefMgr.return_value = mock_pref_mgr

            ranker = PreferenceAwareRanker(user_id="test_user")

            # Measure full flow: creativity filter + blueprint ranker + max suggestions
            start_time = time.perf_counter()
            
            ranked_suggestions = await ranker.rank_suggestions(
                sample_suggestions,
                apply_creativity_filter=True,
                apply_blueprint_weighting=True,
                apply_max_suggestions_limit=True
            )
            
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Full flow should still be fast (<15ms)
            assert duration_ms < 15.0, f"Full preference ranking flow took {duration_ms:.2f}ms"
            assert ranked_suggestions is not None
            assert len(ranked_suggestions) <= 10  # Max suggestions limit applied
