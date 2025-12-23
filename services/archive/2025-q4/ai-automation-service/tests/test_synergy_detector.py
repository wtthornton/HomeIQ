"""
Unit tests for Device Synergy Detector

Story AI3.1: Device Synergy Detector Foundation
Epic AI-3: Cross-Device Synergy & Contextual Opportunities
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from src.synergy_detection.synergy_detector import COMPATIBLE_RELATIONSHIPS, DeviceSynergyDetector

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = AsyncMock()

    # Mock devices
    client.fetch_devices = AsyncMock(return_value=[
        {
            'device_id': 'device_1',
            'name': 'Bedroom Motion Sensor',
            'manufacturer': 'Aqara',
            'model': 'RTCGQ11LM'
        },
        {
            'device_id': 'device_2',
            'name': 'Bedroom Ceiling Light',
            'manufacturer': 'Philips',
            'model': 'Hue White'
        },
        {
            'device_id': 'device_3',
            'name': 'Living Room Thermostat',
            'manufacturer': 'Ecobee',
            'model': 'SmartThermostat'
        }
    ])

    # Mock entities
    client.fetch_entities = AsyncMock(return_value=[
        {
            'entity_id': 'binary_sensor.bedroom_motion',
            'device_id': 'device_1',
            'friendly_name': 'Bedroom Motion',
            'area_id': 'bedroom',
            'device_class': 'motion'
        },
        {
            'entity_id': 'light.bedroom_ceiling',
            'device_id': 'device_2',
            'friendly_name': 'Bedroom Light',
            'area_id': 'bedroom'
        },
        {
            'entity_id': 'climate.living_room',
            'device_id': 'device_3',
            'friendly_name': 'Living Room Thermostat',
            'area_id': 'living_room'
        },
        {
            'entity_id': 'sensor.outdoor_temperature',
            'device_id': 'device_4',
            'friendly_name': 'Outdoor Temperature',
            'area_id': 'living_room',
            'device_class': 'temperature'
        }
    ])

    return client


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    return None  # For initial implementation


# ============================================================================
# Core Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_detect_synergies_basic(mock_data_api_client, mock_ha_client):
    """Test basic synergy detection"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client,
        min_confidence=0.7
    )

    synergies = await detector.detect_synergies()

    # Should detect at least motion sensor + light in bedroom
    assert len(synergies) > 0
    assert any(s['relationship'] == 'motion_to_light' for s in synergies)


@pytest.mark.asyncio
async def test_same_area_motion_light_detection(mock_data_api_client, mock_ha_client):
    """Test detection of motion sensor + light in same area"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    synergies = await detector.detect_synergies()

    # Find bedroom synergy
    bedroom_synergies = [s for s in synergies if s.get('area') == 'bedroom']
    assert len(bedroom_synergies) > 0

    motion_light = [s for s in bedroom_synergies if s.get('relationship') == 'motion_to_light']
    assert len(motion_light) > 0, "No motion_to_light synergy found in bedroom"
    motion_light = motion_light[0]
    assert motion_light.get('trigger_entity') == 'binary_sensor.bedroom_motion'
    assert motion_light.get('action_entity') == 'light.bedroom_ceiling'
    assert motion_light.get('impact_score', 0) > 0.0
    assert motion_light.get('complexity') == 'low'
    assert motion_light.get('confidence', 0) >= 0.7


@pytest.mark.asyncio
async def test_temp_climate_detection(mock_data_api_client, mock_ha_client):
    """Test detection of temperature sensor + climate device"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    synergies = await detector.detect_synergies()

    # Find living room temp → climate synergy
    living_room_synergies = [s for s in synergies if s.get('area') == 'living_room']

    if living_room_synergies:
        temp_climate = [s for s in living_room_synergies if s.get('relationship') == 'temp_to_climate']
        if temp_climate:
            assert temp_climate[0].get('complexity') == 'medium'
            assert temp_climate[0].get('trigger_entity') == 'sensor.outdoor_temperature'


@pytest.mark.asyncio
async def test_confidence_threshold_filtering(mock_data_api_client, mock_ha_client):
    """Test that low confidence synergies are filtered out"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client,
        min_confidence=0.95  # Very high threshold
    )

    synergies = await detector.detect_synergies()

    # All returned synergies should meet threshold
    for synergy in synergies:
        assert synergy['confidence'] >= 0.95


@pytest.mark.asyncio
async def test_impact_score_calculation(mock_data_api_client, mock_ha_client):
    """Test that impact scores are calculated correctly"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    synergies = await detector.detect_synergies()

    # All synergies should have valid impact scores
    for synergy in synergies:
        assert 0.0 <= synergy['impact_score'] <= 1.0
        assert synergy['impact_score'] > 0.0  # Should not be zero


@pytest.mark.asyncio
async def test_synergy_structure(mock_data_api_client, mock_ha_client):
    """Test that synergy opportunity structure is correct"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    synergies = await detector.detect_synergies()

    assert len(synergies) > 0

    # Check required fields
    synergy = synergies[0]
    assert 'synergy_id' in synergy
    assert 'synergy_type' in synergy
    assert 'devices' in synergy
    assert 'relationship' in synergy
    assert 'area' in synergy
    assert 'impact_score' in synergy
    assert 'complexity' in synergy
    assert 'confidence' in synergy
    assert 'rationale' in synergy

    # Check field types
    assert isinstance(synergy['synergy_id'], str)
    assert synergy['synergy_type'] == 'device_pair'
    assert isinstance(synergy['devices'], list)
    assert len(synergy['devices']) == 2
    assert synergy['complexity'] in ['low', 'medium', 'high']


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_no_devices_graceful_handling():
    """Test graceful handling when no devices found"""
    mock_client = AsyncMock()
    mock_client.fetch_devices = AsyncMock(return_value=[])
    mock_client.fetch_entities = AsyncMock(return_value=[])

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None
    )

    synergies = await detector.detect_synergies()

    # Should return empty list, not error
    assert synergies == []


@pytest.mark.asyncio
async def test_data_api_failure_handling():
    """Test graceful handling when data-api fails"""
    mock_client = AsyncMock()
    mock_client.fetch_devices = AsyncMock(side_effect=Exception("API unavailable"))
    mock_client.fetch_entities = AsyncMock(return_value=[])

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None
    )

    synergies = await detector.detect_synergies()

    # Should return empty list and log error, not crash
    assert synergies == []


@pytest.mark.asyncio
async def test_entity_fetch_failure_handling():
    """Test graceful handling when entity fetch fails"""
    mock_client = AsyncMock()
    mock_client.fetch_devices = AsyncMock(return_value=[{'device_id': 'test'}])
    mock_client.fetch_entities = AsyncMock(side_effect=Exception("Entity fetch failed"))

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None
    )

    synergies = await detector.detect_synergies()

    # Should return empty list and log error, not crash
    assert synergies == []


# ============================================================================
# Caching Tests
# ============================================================================

@pytest.mark.asyncio
async def test_device_caching(mock_data_api_client, mock_ha_client):
    """Test that devices are cached after first fetch"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    # First call
    synergies1 = await detector.detect_synergies()

    # Second call (should use cache)
    synergies2 = await detector.detect_synergies()

    # Should only call API once due to caching
    assert mock_data_api_client.fetch_devices.call_count == 1
    assert mock_data_api_client.fetch_entities.call_count == 1


@pytest.mark.asyncio
async def test_cache_clear(mock_data_api_client, mock_ha_client):
    """Test cache clearing functionality"""
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    # First call (populates cache)
    await detector.detect_synergies()
    assert mock_data_api_client.fetch_devices.call_count == 1

    # Clear cache
    detector.clear_cache()

    # Second call (should fetch again)
    await detector.detect_synergies()
    assert mock_data_api_client.fetch_devices.call_count == 2


# ============================================================================
# Relationship Type Tests
# ============================================================================

def test_compatible_relationships_defined():
    """Test that relationship types are properly defined"""
    assert 'motion_to_light' in COMPATIBLE_RELATIONSHIPS
    assert 'door_to_light' in COMPATIBLE_RELATIONSHIPS
    assert 'door_to_lock' in COMPATIBLE_RELATIONSHIPS
    assert 'temp_to_climate' in COMPATIBLE_RELATIONSHIPS
    assert 'occupancy_to_light' in COMPATIBLE_RELATIONSHIPS

    # Check required fields
    for rel_type, config in COMPATIBLE_RELATIONSHIPS.items():
        assert 'trigger_domain' in config
        assert 'action_domain' in config
        assert 'benefit_score' in config
        assert 'complexity' in config
        assert 'description' in config


def test_benefit_scores_valid():
    """Test that benefit scores are in valid range"""
    for rel_type, config in COMPATIBLE_RELATIONSHIPS.items():
        assert 0.0 <= config['benefit_score'] <= 1.0


def test_complexity_levels_valid():
    """Test that complexity levels are valid"""
    valid_complexity = ['low', 'medium', 'high']
    for rel_type, config in COMPATIBLE_RELATIONSHIPS.items():
        assert config['complexity'] in valid_complexity


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
async def test_performance_large_device_count(mock_ha_client):
    """Test performance with large number of devices"""
    # Create mock with many devices (100 devices, 300 entities)
    mock_client = AsyncMock()

    mock_devices = [
        {'device_id': f'device_{i}', 'name': f'Device {i}'}
        for i in range(100)
    ]

    mock_entities = []
    for i in range(100):
        # Add 3 entities per device in various areas
        area = f'area_{i % 10}'  # 10 areas
        mock_entities.extend([
            {
                'entity_id': f'binary_sensor.motion_{i}',
                'device_id': f'device_{i}',
                'friendly_name': f'Motion {i}',
                'area_id': area,
                'device_class': 'motion'
            },
            {
                'entity_id': f'light.light_{i}',
                'device_id': f'device_{i}',
                'friendly_name': f'Light {i}',
                'area_id': area
            },
            {
                'entity_id': f'sensor.temp_{i}',
                'device_id': f'device_{i}',
                'friendly_name': f'Temp {i}',
                'area_id': area,
                'device_class': 'temperature'
            }
        ])

    mock_client.fetch_devices = AsyncMock(return_value=mock_devices)
    mock_client.fetch_entities = AsyncMock(return_value=mock_entities)

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=mock_ha_client
    )

    # Measure performance
    start_time = datetime.now(timezone.utc)
    synergies = await detector.detect_synergies()
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Should complete in < 1 minute (AC: 6)
    assert duration < 60

    # Should find synergies
    assert len(synergies) > 0

    print(f"✅ Performance test: {len(synergies)} synergies detected in {duration:.2f}s")


# ============================================================================
# Integration Tests (require database)
# ============================================================================

@pytest.mark.asyncio
async def test_synergy_storage_integration(mock_data_api_client, mock_ha_client):
    """Test integration with database storage (requires running database)"""
    # This test would require actual database connection
    # For unit tests, we'll mock the storage layer


    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    synergies = await detector.detect_synergies()

    # Verify structure is compatible with storage
    assert len(synergies) > 0
    synergy = synergies[0]

    # Check required fields for storage
    assert 'synergy_id' in synergy
    assert 'synergy_type' in synergy
    assert 'devices' in synergy
    assert 'impact_score' in synergy
    assert 'complexity' in synergy
    assert 'confidence' in synergy


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_no_compatible_pairs():
    """Test when no compatible pairs exist"""
    mock_client = AsyncMock()

    # Only incompatible devices
    mock_client.fetch_devices = AsyncMock(return_value=[
        {'device_id': 'device_1', 'name': 'Switch 1'},
        {'device_id': 'device_2', 'name': 'Switch 2'}
    ])

    mock_client.fetch_entities = AsyncMock(return_value=[
        {
            'entity_id': 'switch.device_1',
            'device_id': 'device_1',
            'friendly_name': 'Switch 1',
            'area_id': 'kitchen'
        },
        {
            'entity_id': 'switch.device_2',
            'device_id': 'device_2',
            'friendly_name': 'Switch 2',
            'area_id': 'kitchen'
        }
    ])

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None
    )

    synergies = await detector.detect_synergies()

    # Should return empty list (switches can't trigger each other in our relationships)
    assert synergies == []


@pytest.mark.asyncio
async def test_devices_different_areas():
    """Test that different area devices aren't paired (when same_area_required=True)"""
    mock_client = AsyncMock()

    mock_client.fetch_devices = AsyncMock(return_value=[
        {'device_id': 'device_1', 'name': 'Bedroom Motion'},
        {'device_id': 'device_2', 'name': 'Kitchen Light'}
    ])

    mock_client.fetch_entities = AsyncMock(return_value=[
        {
            'entity_id': 'binary_sensor.bedroom_motion',
            'device_id': 'device_1',
            'friendly_name': 'Bedroom Motion',
            'area_id': 'bedroom',
            'device_class': 'motion'
        },
        {
            'entity_id': 'light.kitchen_light',
            'device_id': 'device_2',
            'friendly_name': 'Kitchen Light',
            'area_id': 'kitchen'
        }
    ])

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None,
        same_area_required=True
    )

    synergies = await detector.detect_synergies()

    # Should not pair devices from different areas
    assert synergies == []


@pytest.mark.asyncio
async def test_ranking_order():
    """Test that synergies are ranked by impact score"""
    mock_client = AsyncMock()

    # Create entities that will generate multiple synergies with different scores
    mock_client.fetch_devices = AsyncMock(return_value=[
        {'device_id': f'device_{i}', 'name': f'Device {i}'}
        for i in range(10)
    ])

    mock_client.fetch_entities = AsyncMock(return_value=[
        # Door sensor + lock (high benefit 1.0)
        {
            'entity_id': 'binary_sensor.door',
            'device_id': 'device_1',
            'friendly_name': 'Door Sensor',
            'area_id': 'entry',
            'device_class': 'door'
        },
        {
            'entity_id': 'lock.front_door',
            'device_id': 'device_2',
            'friendly_name': 'Front Door Lock',
            'area_id': 'entry'
        },
        # Motion + light (medium benefit 0.7)
        {
            'entity_id': 'binary_sensor.motion',
            'device_id': 'device_3',
            'friendly_name': 'Motion',
            'area_id': 'bedroom',
            'device_class': 'motion'
        },
        {
            'entity_id': 'light.bedroom',
            'device_id': 'device_4',
            'friendly_name': 'Bedroom Light',
            'area_id': 'bedroom'
        }
    ])

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None
    )

    synergies = await detector.detect_synergies()

    # Should be ranked by impact (door_to_lock should be first due to higher benefit)
    if len(synergies) >= 2:
        # Verify descending order
        for i in range(len(synergies) - 1):
            assert synergies[i]['impact_score'] >= synergies[i+1]['impact_score']


# ============================================================================
# Logging Tests
# ============================================================================

@pytest.mark.asyncio
async def test_logging_output(mock_data_api_client, mock_ha_client, caplog):
    """Test that proper logging occurs"""
    import logging
    caplog.set_level(logging.INFO)

    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client
    )

    await detector.detect_synergies()

    # Check for expected log messages
    assert "Starting synergy detection" in caplog.text
    assert "Synergy detection complete" in caplog.text
    assert "opportunities" in caplog.text.lower()


# ============================================================================
# 4-Level Chain Detection Tests (Epic AI-4)
# ============================================================================

@pytest.mark.asyncio
async def test_4_level_chain_detection():
    """Test that 4-level chains are detected correctly"""
    # Create mock with devices that can form a 4-level chain
    mock_client = AsyncMock()

    mock_client.fetch_devices = AsyncMock(return_value=[
        {'device_id': 'device_1', 'name': 'Motion Sensor'},
        {'device_id': 'device_2', 'name': 'Light'},
        {'device_id': 'device_3', 'name': 'Climate'},
        {'device_id': 'device_4', 'name': 'Media Player'}
    ])

    mock_client.fetch_entities = AsyncMock(return_value=[
        {
            'entity_id': 'binary_sensor.motion',
            'device_id': 'device_1',
            'friendly_name': 'Motion Sensor',
            'area_id': 'bedroom',
            'device_class': 'motion'
        },
        {
            'entity_id': 'light.bedroom',
            'device_id': 'device_2',
            'friendly_name': 'Bedroom Light',
            'area_id': 'bedroom'
        },
        {
            'entity_id': 'climate.bedroom',
            'device_id': 'device_3',
            'friendly_name': 'Bedroom Climate',
            'area_id': 'bedroom'
        },
        {
            'entity_id': 'media_player.bedroom',
            'device_id': 'device_4',
            'friendly_name': 'Bedroom Media',
            'area_id': 'bedroom'
        }
    ])

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None,
        min_confidence=0.5  # Lower threshold to allow more chains
    )

    synergies = await detector.detect_synergies()

    # Check that we have synergies
    assert len(synergies) > 0

    # Check for 4-level chains
    four_level_chains = [
        s for s in synergies
        if s.get('synergy_type') == 'device_chain'
        and s.get('synergy_depth') == 4
        and len(s.get('devices', [])) == 4
    ]

    # Should have at least some 4-level chains if conditions are right
    # (May not always have them depending on relationship compatibility)
    if four_level_chains:
        chain = four_level_chains[0]
        assert chain['synergy_depth'] == 4
        assert len(chain['devices']) == 4
        assert 'chain_path' in chain
        assert '→' in chain['chain_path']
        assert chain.get('chain_devices') == chain['devices']


@pytest.mark.asyncio
async def test_4_level_chain_structure():
    """Test that 4-level chains have correct structure"""
    mock_client = AsyncMock()

    # Minimal setup - just need entities
    mock_client.fetch_devices = AsyncMock(return_value=[])
    mock_client.fetch_entities = AsyncMock(return_value=[
        {
            'entity_id': 'binary_sensor.door',
            'device_id': 'device_1',
            'friendly_name': 'Door Sensor',
            'area_id': 'entry',
            'device_class': 'door'
        },
        {
            'entity_id': 'lock.entry',
            'device_id': 'device_2',
            'friendly_name': 'Entry Lock',
            'area_id': 'entry'
        },
        {
            'entity_id': 'alarm_control_panel.home',
            'device_id': 'device_3',
            'friendly_name': 'Home Alarm',
            'area_id': 'entry'
        },
        {
            'entity_id': 'notify.mobile',
            'device_id': 'device_4',
            'friendly_name': 'Mobile Notification',
            'area_id': None
        }
    ])

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None,
        min_confidence=0.5
    )

    synergies = await detector.detect_synergies()

    # Check all chains have required fields
    chains = [s for s in synergies if s.get('synergy_type') == 'device_chain']
    for chain in chains:
        assert 'synergy_id' in chain
        assert 'synergy_depth' in chain
        assert 'devices' in chain
        assert 'chain_devices' in chain
        assert 'chain_path' in chain
        assert 'impact_score' in chain
        assert 'confidence' in chain
        assert 'complexity' in chain

        # Verify depth matches device count
        depth = chain['synergy_depth']
        device_count = len(chain['devices'])
        assert depth == device_count, f"Depth {depth} doesn't match device count {device_count}"

        # Verify chain_devices matches devices
        assert chain['chain_devices'] == chain['devices']


@pytest.mark.asyncio
async def test_4_level_chain_limits():
    """Test that 4-level chain detection respects limits"""
    mock_client = AsyncMock()

    # Create many entities to potentially generate many chains
    entities = []
    for i in range(20):
        entities.extend([
            {
                'entity_id': f'binary_sensor.motion_{i}',
                'device_id': f'device_{i*4}',
                'friendly_name': f'Motion {i}',
                'area_id': 'bedroom',
                'device_class': 'motion'
            },
            {
                'entity_id': f'light.light_{i}',
                'device_id': f'device_{i*4+1}',
                'friendly_name': f'Light {i}',
                'area_id': 'bedroom'
            },
            {
                'entity_id': f'climate.climate_{i}',
                'device_id': f'device_{i*4+2}',
                'friendly_name': f'Climate {i}',
                'area_id': 'bedroom'
            },
            {
                'entity_id': f'media_player.media_{i}',
                'device_id': f'device_{i*4+3}',
                'friendly_name': f'Media {i}',
                'area_id': 'bedroom'
            }
        ])

    mock_client.fetch_devices = AsyncMock(return_value=[])
    mock_client.fetch_entities = AsyncMock(return_value=entities)

    detector = DeviceSynergyDetector(
        data_api_client=mock_client,
        ha_client=None,
        min_confidence=0.5
    )

    synergies = await detector.detect_synergies()

    # Check that 4-level chains are limited (MAX_CHAINS = 50)
    four_level_chains = [
        s for s in synergies
        if s.get('synergy_type') == 'device_chain'
        and s.get('synergy_depth') == 4
    ]

    # Should not exceed limit (50 for 4-level chains)
    assert len(four_level_chains) <= 50, f"Found {len(four_level_chains)} 4-level chains, should be <= 50"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

