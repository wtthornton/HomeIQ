"""
Shared test fixtures for energy-correlator service
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client for testing"""
    client = MagicMock()
    client.query = AsyncMock(return_value=[])
    client.write_points = AsyncMock()
    client.connect = MagicMock()
    client.close = MagicMock()

    return client


@pytest.fixture
def sample_events() -> list[dict]:
    """Sample HA events for testing"""
    now = datetime.utcnow()

    return [
        {
            'time': now - timedelta(seconds=30),
            'entity_id': 'switch.living_room_lamp',
            'domain': 'switch',
            'state': 'on',
            'previous_state': 'off'
        },
        {
            'time': now - timedelta(seconds=60),
            'entity_id': 'climate.living_room',
            'domain': 'climate',
            'state': 'heating',
            'previous_state': 'idle'
        },
        {
            'time': now - timedelta(seconds=90),
            'entity_id': 'light.bedroom',
            'domain': 'light',
            'state': 'off',
            'previous_state': 'on'
        },
        {
            'time': now - timedelta(seconds=120),
            'entity_id': 'fan.ceiling_fan',
            'domain': 'fan',
            'state': 'high',
            'previous_state': 'low'
        },
        {
            'time': now - timedelta(seconds=150),
            'entity_id': 'cover.living_room_blinds',
            'domain': 'cover',
            'state': 'closed',
            'previous_state': 'open'
        }
    ]


@pytest.fixture
def sample_power_data() -> dict:
    """Sample power readings for testing"""
    return {
        'before': 2450.0,
        'after': 2510.0,
        'delta': 60.0,
        'delta_pct': 2.45
    }


@pytest.fixture
def sample_large_power_change() -> dict:
    """Sample HVAC power change (large delta)"""
    return {
        'before': 1850.0,
        'after': 4350.0,
        'delta': 2500.0,
        'delta_pct': 135.14
    }


@pytest.fixture
def sample_negative_power_change() -> dict:
    """Sample light turning off (negative delta)"""
    return {
        'before': 2150.0,
        'after': 2030.0,
        'delta': -120.0,
        'delta_pct': -5.58
    }


@pytest.fixture
def sample_small_power_change() -> dict:
    """Sample small power change (below threshold)"""
    return {
        'before': 2450.0,
        'after': 2455.0,
        'delta': 5.0,
        'delta_pct': 0.20
    }


@pytest.fixture
def correlator_instance(mock_influxdb_client):
    """Create correlator instance with mocked dependencies"""
    from src.correlator import EnergyEventCorrelator

    correlator = EnergyEventCorrelator(
        influxdb_url='http://test-influxdb:8086',
        influxdb_token='test-token',
        influxdb_org='test-org',
        influxdb_bucket='test-bucket'
    )

    # Inject mock client
    correlator.client = mock_influxdb_client

    return correlator


@pytest.fixture
async def service_instance():
    """Create service instance for integration testing"""
    from src.main import EnergyCorrelatorService

    # Set test environment
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
    os.environ['INFLUXDB_ORG'] = 'test-org'
    os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
    os.environ['PROCESSING_INTERVAL'] = '10'  # Faster for tests
    os.environ['LOOKBACK_MINUTES'] = '5'

    service = EnergyCorrelatorService()

    yield service

    # Cleanup
    try:
        await service.shutdown()
    except:
        pass


@pytest.fixture
def mock_influx_query_results():
    """Mock InfluxDB query results in Flux format"""
    now = datetime.utcnow()

    return [
        {
            'time': now - timedelta(seconds=30),
            'entity_id': 'switch.living_room_lamp',
            'domain': 'switch',
            '_value': 'on',
            'previous_state': 'off',
            '_measurement': 'home_assistant_events',
            '_field': 'state_value'
        },
        {
            'time': now - timedelta(seconds=60),
            'entity_id': 'climate.living_room',
            'domain': 'climate',
            '_value': 'heating',
            'previous_state': 'idle',
            '_measurement': 'home_assistant_events',
            '_field': 'state_value'
        }
    ]


@pytest.fixture
def mock_power_query_result():
    """Mock power reading query result"""
    return [
        {
            '_measurement': 'smart_meter',
            '_field': 'total_power_w',
            '_value': 2450.0,
            '_time': datetime.now(timezone.utc)
        }
    ]
