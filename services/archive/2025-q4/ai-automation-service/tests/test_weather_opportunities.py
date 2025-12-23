"""
Unit tests for Weather Opportunity Detector

Story AI3.5: Weather Context Integration
Epic AI-3: Cross-Device Synergy & Contextual Opportunities
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.contextual_patterns.weather_opportunities import WeatherOpportunityDetector

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client with weather data"""
    client = MagicMock()
    client.org = "test-org"
    query_api = MagicMock()

    def mock_query(query_str, org=None):
        # Create mock weather records
        records = []

        if 'forecast_low' in query_str or 'temperature' in query_str:
            # Frost risk scenario: Low temp 28°F
            record_low = MagicMock()
            record_low.get_time = MagicMock(return_value=datetime.now(timezone.utc))
            record_low.get_value = MagicMock(return_value=28.0)  # Below freezing
            record_low.values = {'_field': 'forecast_low', 'location': 'home'}
            records.append(record_low)

            # High temp for precooling: 90°F
            record_high = MagicMock()
            record_high.get_time = MagicMock(return_value=datetime.now(timezone.utc))
            record_high.get_value = MagicMock(return_value=90.0)  # Hot day
            record_high.values = {'_field': 'forecast_high', 'location': 'home'}
            records.append(record_high)

        mock_table = MagicMock()
        mock_table.records = records

        return [mock_table]

    query_api.query = MagicMock(side_effect=mock_query)
    client.query_api = query_api

    return client


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = AsyncMock()

    client.fetch_devices = AsyncMock(return_value=[
        {'device_id': 'device_1', 'name': 'Thermostat'},
    ])

    client.fetch_entities = AsyncMock(return_value=[
        {
            'entity_id': 'climate.living_room',
            'friendly_name': 'Living Room Thermostat',
            'area_id': 'living_room'
        },
        {
            'entity_id': 'climate.bedroom',
            'friendly_name': 'Bedroom Thermostat',
            'area_id': 'bedroom'
        }
    ])

    return client


# ============================================================================
# Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_frost_protection_detection(mock_influxdb_client, mock_data_api_client):
    """Test frost protection opportunity detection"""
    detector = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb_client,
        data_api_client=mock_data_api_client,
        frost_threshold_f=32.0
    )

    opportunities = await detector.detect_opportunities()

    # Should find frost protection opportunities
    frost_opps = [o for o in opportunities if o['relationship'] == 'frost_protection']
    assert len(frost_opps) > 0

    # Check structure
    opp = frost_opps[0]
    assert opp['synergy_type'] == 'weather_context'
    assert opp['impact_score'] >= 0.8  # High impact
    assert opp['complexity'] == 'medium'


@pytest.mark.asyncio
async def test_precooling_detection(mock_influxdb_client, mock_data_api_client):
    """Test pre-cooling opportunity detection"""
    detector = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb_client,
        data_api_client=mock_data_api_client,
        heat_threshold_f=85.0
    )

    opportunities = await detector.detect_opportunities()

    # Should find pre-cooling opportunities
    cooling_opps = [o for o in opportunities if o['relationship'] == 'precooling']
    assert len(cooling_opps) > 0

    # Check structure
    opp = cooling_opps[0]
    assert opp['synergy_type'] == 'weather_context'
    assert 'energy' in opp['opportunity_metadata']['suggested_action'].lower() or 'cool' in opp['opportunity_metadata']['suggested_action'].lower()


@pytest.mark.asyncio
async def test_no_weather_data_handling(mock_data_api_client):
    """Test graceful handling when no weather data available"""
    # Mock InfluxDB with no data
    mock_influxdb = MagicMock()
    mock_influxdb.org = "test-org"
    query_api = MagicMock()
    query_api.query = MagicMock(return_value=[])  # Empty result
    mock_influxdb.query_api = query_api

    detector = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb,
        data_api_client=mock_data_api_client
    )

    opportunities = await detector.detect_opportunities()

    # Should return empty list, not crash
    assert opportunities == []


@pytest.mark.asyncio
async def test_no_climate_devices_handling(mock_influxdb_client):
    """Test graceful handling when no climate devices found"""
    # Mock data API with no climate devices
    mock_data_api = AsyncMock()
    mock_data_api.fetch_devices = AsyncMock(return_value=[])
    mock_data_api.fetch_entities = AsyncMock(return_value=[])

    detector = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb_client,
        data_api_client=mock_data_api
    )

    opportunities = await detector.detect_opportunities()

    # Should return empty list, not crash
    assert opportunities == []


# ============================================================================
# Threshold Tests
# ============================================================================

@pytest.mark.asyncio
async def test_custom_frost_threshold():
    """Test custom frost threshold"""
    mock_influxdb = MagicMock()
    mock_influxdb.org = "test-org"
    query_api = MagicMock()

    # Mock temp of 30°F
    record = MagicMock()
    record.get_time = MagicMock(return_value=datetime.now(timezone.utc))
    record.get_value = MagicMock(return_value=30.0)
    record.values = {'_field': 'temperature', 'location': 'home'}

    mock_table = MagicMock()
    mock_table.records = [record]
    query_api.query = MagicMock(return_value=[mock_table])
    mock_influxdb.query_api = query_api

    mock_data_api = AsyncMock()
    mock_data_api.fetch_devices = AsyncMock(return_value=[])
    mock_data_api.fetch_entities = AsyncMock(return_value=[
        {'entity_id': 'climate.test', 'friendly_name': 'Test'}
    ])

    # With threshold of 28°F, should NOT trigger (30°F > 28°F)
    detector1 = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb,
        data_api_client=mock_data_api,
        frost_threshold_f=28.0
    )

    opps1 = await detector1.detect_opportunities()
    frost_opps1 = [o for o in opps1 if o['relationship'] == 'frost_protection']
    assert len(frost_opps1) == 0

    # With threshold of 32°F, should trigger (30°F < 32°F)
    detector2 = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb,
        data_api_client=mock_data_api,
        frost_threshold_f=32.0
    )

    # Clear cache
    detector2._weather_cache = detector1._weather_cache
    detector2._climate_devices_cache = detector1._climate_devices_cache

    opps2 = await detector2._detect_frost_protection(
        detector2._weather_cache,
        detector2._climate_devices_cache
    )
    assert len(opps2) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_influxdb_query_failure_handling(mock_data_api_client):
    """Test graceful handling when InfluxDB query fails"""
    mock_influxdb = MagicMock()
    mock_influxdb.org = "test-org"
    query_api = MagicMock()
    query_api.query = MagicMock(side_effect=Exception("InfluxDB error"))
    mock_influxdb.query_api = query_api

    detector = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb,
        data_api_client=mock_data_api_client
    )

    # Should return empty list and log error, not crash
    opportunities = await detector.detect_opportunities()
    assert opportunities == []


# ============================================================================
# Cache Tests
# ============================================================================

@pytest.mark.asyncio
async def test_weather_data_caching(mock_influxdb_client, mock_data_api_client):
    """Test that weather data is cached"""
    detector = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb_client,
        data_api_client=mock_data_api_client
    )

    # First call
    opps1 = await detector.detect_opportunities()

    # Second call (should use cache)
    opps2 = await detector.detect_opportunities()

    # Should only query InfluxDB once
    assert mock_influxdb_client.query_api.query.call_count == 1


@pytest.mark.asyncio
async def test_cache_clear(mock_influxdb_client, mock_data_api_client):
    """Test cache clearing"""
    detector = WeatherOpportunityDetector(
        influxdb_client=mock_influxdb_client,
        data_api_client=mock_data_api_client
    )

    # Populate cache
    await detector.detect_opportunities()
    assert detector._weather_cache is not None

    # Clear cache
    detector.clear_cache()
    assert detector._weather_cache is None
    assert detector._climate_devices_cache is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

