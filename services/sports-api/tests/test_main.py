"""
Tests for Sports API Service
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

# Mock shared module before importing
sys.modules['shared'] = MagicMock()
sys.modules['shared.logging_config'] = MagicMock()
sys.modules['shared.logging_config'].setup_logging = MagicMock(return_value=MagicMock())

from src.main import SportsService


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv('HA_HTTP_URL', 'http://test-ha:8123')
    monkeypatch.setenv('HA_TOKEN', 'test_token')
    monkeypatch.setenv('INFLUXDB_URL', 'http://test-influxdb:8086')
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test_influx_token')
    monkeypatch.setenv('INFLUXDB_ORG', 'test_org')
    monkeypatch.setenv('INFLUXDB_BUCKET', 'test_bucket')


@pytest.fixture
def sports_service(mock_env_vars):
    """Create SportsService instance"""
    return SportsService()


@pytest.mark.asyncio
async def test_fetch_team_tracker_sensors_success(sports_service):
    """Test successful fetch of Team Tracker sensors"""
    mock_sensors = [
        {
            'entity_id': 'sensor.team_tracker_seahawks',
            'state': 'IN',
            'attributes': {
                'sport': 'football',
                'league': 'NFL',
                'team_abbr': 'SEA',
                'team_name': 'Seahawks',
                'team_score': 14,
                'opponent_score': 7
            },
            'last_updated': '2025-12-29T10:00:00Z',
            'last_changed': '2025-12-29T10:00:00Z'
        }
    ]
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {'entity_id': 'sensor.team_tracker_seahawks', 'state': 'IN', 'attributes': {}, 'last_updated': '', 'last_changed': ''},
            {'entity_id': 'sensor.other_sensor', 'state': 'on', 'attributes': {}}
        ])
        mock_get.return_value.__aenter__.return_value = mock_response
        
        await sports_service.startup()
        sensors = await sports_service.fetch_team_tracker_sensors()
        
        assert len(sensors) == 1
        assert sensors[0]['entity_id'] == 'sensor.team_tracker_seahawks'
        await sports_service.shutdown()


@pytest.mark.asyncio
async def test_fetch_team_tracker_sensors_no_token(sports_service):
    """Test fetch when HA token is not set"""
    sports_service.ha_token = None
    sensors = await sports_service.fetch_team_tracker_sensors()
    assert sensors == []


def test_parse_sensor_data(sports_service):
    """Test parsing sensor data"""
    sensor = {
        'entity_id': 'sensor.team_tracker_seahawks',
        'state': 'IN',
        'attributes': {
            'sport': 'football',
            'league': 'NFL',
            'team_abbr': 'SEA',
            'team_name': 'Seahawks',
            'team_id': '123',
            'opponent_abbr': 'SF',
            'opponent_name': '49ers',
            'team_score': 14,
            'opponent_score': 7,
            'quarter': '2',
            'clock': '5:23',
            'venue': 'Lumen Field',
            'location': 'Seattle, WA'
        },
        'last_updated': '2025-12-29T10:00:00Z',
        'last_changed': '2025-12-29T10:00:00Z'
    }
    
    parsed = sports_service.parse_sensor_data(sensor)
    
    assert parsed['entity_id'] == 'sensor.team_tracker_seahawks'
    assert parsed['state'] == 'IN'
    assert parsed['sport'] == 'football'
    assert parsed['league'] == 'NFL'
    assert parsed['team_abbr'] == 'SEA'
    assert parsed['team_score'] == 14
    assert parsed['opponent_score'] == 7


@pytest.mark.asyncio
async def test_store_in_influxdb_success(sports_service):
    """Test successful storage in InfluxDB"""
    sensors = [
        {
            'entity_id': 'sensor.team_tracker_seahawks',
            'state': 'IN',
            'sport': 'football',
            'league': 'NFL',
            'team_abbr': 'SEA',
            'team_id': '123',
            'team_score': 14,
            'opponent_score': 7,
            'quarter': '2',
            'clock': '5:23'
        }
    ]
    
    mock_client = MagicMock()
    sports_service.influxdb_client = mock_client
    
    await sports_service.store_in_influxdb(sensors)
    
    # Verify write was called
    assert mock_client.write.called


@pytest.mark.asyncio
async def test_store_in_influxdb_no_client(sports_service):
    """Test storage when InfluxDB client is not initialized"""
    sports_service.influxdb_client = None
    sensors = [{'entity_id': 'test', 'state': 'IN'}]
    
    # Should not raise error, just log warning
    await sports_service.store_in_influxdb(sensors)


@pytest.mark.asyncio
async def test_get_current_sports_data(sports_service):
    """Test getting current sports data"""
    mock_sensors = [
        {
            'entity_id': 'sensor.team_tracker_seahawks',
            'state': 'IN',
            'attributes': {'sport': 'football', 'league': 'NFL'},
            'last_updated': '2025-12-29T10:00:00Z',
            'last_changed': '2025-12-29T10:00:00Z'
        }
    ]
    
    with patch.object(sports_service, 'fetch_team_tracker_sensors', return_value=mock_sensors):
        with patch.object(sports_service, 'store_in_influxdb', new_callable=AsyncMock):
            await sports_service.startup()
            data = await sports_service.get_current_sports_data()
            
            assert len(data) == 1
            assert data[0]['entity_id'] == 'sensor.team_tracker_seahawks'
            await sports_service.shutdown()


def test_sports_service_initialization(mock_env_vars):
    """Test SportsService initialization"""
    service = SportsService()
    
    assert service.ha_url == 'http://test-ha:8123'
    assert service.ha_token == 'test_token'
    assert service.influxdb_url == 'http://test-influxdb:8086'
    assert service.poll_interval == 60  # Default


def test_sports_service_initialization_missing_token(monkeypatch):
    """Test SportsService initialization with missing InfluxDB token"""
    monkeypatch.setenv('HA_HTTP_URL', 'http://test-ha:8123')
    monkeypatch.setenv('HA_TOKEN', 'test_token')
    # Remove INFLUXDB_TOKEN if it exists
    monkeypatch.delenv('INFLUXDB_TOKEN', raising=False)
    
    with pytest.raises(ValueError, match="INFLUXDB_TOKEN required"):
        SportsService()

