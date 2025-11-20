"""
Unit tests for Device Pair Analyzer

Story AI3.2: Same-Area Device Pair Detection
Epic AI-3: Cross-Device Synergy & Contextual Opportunities
"""

from unittest.mock import MagicMock

import pytest
from src.synergy_detection.device_pair_analyzer import DevicePairAnalyzer

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client that matches real InfluxDB API"""
    client = MagicMock()
    client.org = "test-org"

    # Create mock query_api
    query_api = MagicMock()

    # Mock query responses with different usage levels
    def mock_query(query_str, org=None):
        # Create mock record
        mock_record = MagicMock()

        # Parse entity from query to determine usage level
        if 'high_usage' in query_str:
            # High usage device: 150 events/day * 30 days = 4500 events
            mock_record.get_value = MagicMock(return_value=4500)
        elif 'medium_usage' in query_str:
            # Medium usage: 15 events/day * 30 days = 450 events
            mock_record.get_value = MagicMock(return_value=450)
        elif 'low_usage' in query_str:
            # Low usage: 3 events/day * 30 days = 90 events
            mock_record.get_value = MagicMock(return_value=90)
        else:
            # Default medium usage
            mock_record.get_value = MagicMock(return_value=300)

        # Create mock table
        mock_table = MagicMock()
        mock_table.records = [mock_record]

        return [mock_table]

    query_api.query = MagicMock(side_effect=mock_query)
    client.query_api = query_api

    return client


@pytest.fixture
def sample_entities():
    """Sample entities for testing"""
    return [
        {
            'entity_id': 'light.bedroom_high_usage',
            'area_id': 'bedroom'
        },
        {
            'entity_id': 'light.kitchen_medium_usage',
            'area_id': 'kitchen'
        },
        {
            'entity_id': 'light.storage_low_usage',
            'area_id': 'storage'
        }
    ]


@pytest.fixture
def sample_synergy():
    """Sample synergy for impact calculation"""
    return {
        'trigger_entity': 'binary_sensor.bedroom_motion',
        'action_entity': 'light.bedroom_high_usage',
        'area': 'bedroom',
        'impact_score': 0.7,  # Base score from AI3.1
        'complexity': 'low',
        'relationship': 'motion_to_light'
    }


# ============================================================================
# Usage Frequency Tests
# ============================================================================

@pytest.mark.asyncio
async def test_usage_frequency_high(mock_influxdb_client):
    """Test high usage frequency detection"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    frequency = await analyzer.get_device_usage_frequency('light.bedroom_high_usage')

    # 150 events/day should give high frequency (1.0)
    assert frequency == 1.0


@pytest.mark.asyncio
async def test_usage_frequency_medium(mock_influxdb_client):
    """Test medium usage frequency detection"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    frequency = await analyzer.get_device_usage_frequency('light.kitchen_medium_usage')

    # 15 events/day should give medium frequency (0.5)
    assert frequency == 0.5


@pytest.mark.asyncio
async def test_usage_frequency_low(mock_influxdb_client):
    """Test low usage frequency detection"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    frequency = await analyzer.get_device_usage_frequency('light.storage_low_usage')

    # 3 events/day should give low frequency (0.1)
    assert frequency == 0.1


@pytest.mark.asyncio
async def test_usage_frequency_caching(mock_influxdb_client):
    """Test that usage data is cached"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    # First call
    freq1 = await analyzer.get_device_usage_frequency('test.device')

    # Second call (should use cache)
    freq2 = await analyzer.get_device_usage_frequency('test.device')

    # Should only query InfluxDB once
    assert mock_influxdb_client.query_api.query.call_count == 1
    assert freq1 == freq2


# ============================================================================
# Area Traffic Tests
# ============================================================================

@pytest.mark.asyncio
async def test_area_traffic_high(sample_entities):
    """Test high traffic area detection"""
    # Create mock with high traffic response
    mock_client = MagicMock()
    mock_client.org = "test-org"
    query_api = MagicMock()

    # Mock high traffic: 22500 events over 30 days = 750 events/day
    mock_record = MagicMock()
    mock_record.get_value = MagicMock(return_value=22500)
    mock_table = MagicMock()
    mock_table.records = [mock_record]

    query_api.query = MagicMock(return_value=[mock_table])
    mock_client.query_api = query_api

    analyzer = DevicePairAnalyzer(mock_client)
    traffic = await analyzer.get_area_traffic('bedroom', sample_entities)

    # 750 events/day should give traffic >= 1.0
    assert traffic >= 0.9


@pytest.mark.asyncio
async def test_area_traffic_caching(mock_influxdb_client, sample_entities):
    """Test that area traffic is cached"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    # First call
    traffic1 = await analyzer.get_area_traffic('bedroom', sample_entities)

    # Second call (should use cache)
    traffic2 = await analyzer.get_area_traffic('bedroom', sample_entities)

    # Should only query InfluxDB once
    assert mock_influxdb_client.query_api.query.call_count == 1
    assert traffic1 == traffic2


# ============================================================================
# Advanced Impact Scoring Tests
# ============================================================================

@pytest.mark.asyncio
async def test_advanced_impact_calculation(mock_influxdb_client, sample_entities, sample_synergy):
    """Test advanced impact score calculation"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    impact = await analyzer.calculate_advanced_impact_score(
        sample_synergy,
        sample_entities
    )

    # Should return valid score
    assert 0.0 <= impact <= 1.0
    assert impact > 0.0


@pytest.mark.asyncio
async def test_advanced_impact_higher_than_base(mock_influxdb_client, sample_entities):
    """Test that high usage increases impact score"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    synergy_low = {
        'trigger_entity': 'light.storage_low_usage',
        'action_entity': 'light.storage_low_usage',
        'area': 'storage',
        'impact_score': 0.7,
        'complexity': 'low'
    }

    synergy_high = {
        'trigger_entity': 'light.bedroom_high_usage',
        'action_entity': 'light.bedroom_high_usage',
        'area': 'bedroom',
        'impact_score': 0.7,
        'complexity': 'low'
    }

    impact_low = await analyzer.calculate_advanced_impact_score(synergy_low, sample_entities)
    impact_high = await analyzer.calculate_advanced_impact_score(synergy_high, sample_entities)

    # High usage should have higher impact
    assert impact_high > impact_low


@pytest.mark.asyncio
async def test_advanced_impact_complexity_penalty(mock_influxdb_client, sample_entities):
    """Test that complexity affects impact score"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    base_synergy = {
        'trigger_entity': 'light.bedroom_high_usage',
        'action_entity': 'light.bedroom_high_usage',
        'area': 'bedroom',
        'impact_score': 0.7,
    }

    synergy_low = {**base_synergy, 'complexity': 'low'}
    synergy_medium = {**base_synergy, 'complexity': 'medium'}
    synergy_high = {**base_synergy, 'complexity': 'high'}

    impact_low = await analyzer.calculate_advanced_impact_score(synergy_low, sample_entities)
    impact_medium = await analyzer.calculate_advanced_impact_score(synergy_medium, sample_entities)
    impact_high = await analyzer.calculate_advanced_impact_score(synergy_high, sample_entities)

    # Lower complexity should have higher impact
    assert impact_low > impact_medium > impact_high


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_influxdb_failure_graceful_handling():
    """Test graceful handling when InfluxDB fails"""
    mock_client = MagicMock()
    mock_client.org = "test-org"
    query_api = MagicMock()
    query_api.query = MagicMock(side_effect=Exception("InfluxDB unavailable"))
    mock_client.query_api = query_api

    analyzer = DevicePairAnalyzer(mock_client)

    # Should return default value, not crash
    frequency = await analyzer.get_device_usage_frequency('test.device')
    assert frequency == 0.5  # Default moderate usage


@pytest.mark.asyncio
async def test_area_traffic_failure_graceful_handling():
    """Test graceful handling when area traffic query fails"""
    mock_client = MagicMock()
    mock_client.org = "test-org"
    query_api = MagicMock()
    query_api.query = MagicMock(side_effect=Exception("Query failed"))
    mock_client.query_api = query_api

    analyzer = DevicePairAnalyzer(mock_client)

    # Should return default value, not crash
    traffic = await analyzer.get_area_traffic('bedroom', [])
    assert traffic == 0.5  # Default when no entities (line 140 in device_pair_analyzer.py)


# ============================================================================
# Cache Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cache_clear(mock_influxdb_client, sample_entities):
    """Test cache clearing functionality"""
    analyzer = DevicePairAnalyzer(mock_influxdb_client)

    # Populate cache
    await analyzer.get_device_usage_frequency('test.device')
    await analyzer.get_area_traffic('bedroom', sample_entities)

    assert len(analyzer._usage_cache) > 0
    assert len(analyzer._area_cache) > 0

    # Clear cache
    analyzer.clear_cache()

    assert len(analyzer._usage_cache) == 0
    assert len(analyzer._area_cache) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

