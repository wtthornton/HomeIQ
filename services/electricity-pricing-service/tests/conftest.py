"""
Shared test fixtures for electricity-pricing-service
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory and src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession"""
    session = AsyncMock()
    session.get = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client"""
    client = MagicMock()
    client.write = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture
def sample_pricing_data() -> dict:
    """Sample pricing data from provider"""
    now = datetime.now()
    return {
        'current_price': 0.285,
        'currency': 'EUR',
        'peak_period': True,
        'cheapest_hours': [2, 3, 4, 5],
        'most_expensive_hours': [18, 19, 20],
        'forecast_24h': [
            {'hour': 0, 'price': 0.28, 'timestamp': now},
            {'hour': 1, 'price': 0.25, 'timestamp': now + timedelta(hours=1)},
            {'hour': 2, 'price': 0.22, 'timestamp': now + timedelta(hours=2)},
            {'hour': 3, 'price': 0.21, 'timestamp': now + timedelta(hours=3)},
        ],
        'timestamp': now,
        'provider': 'awattar'
    }


@pytest.fixture
def sample_cheap_pricing() -> dict:
    """Sample cheap pricing (off-peak)"""
    now = datetime.now()
    return {
        'current_price': 0.18,
        'currency': 'EUR',
        'peak_period': False,
        'cheapest_hours': [2, 3, 4, 5],
        'most_expensive_hours': [18, 19, 20],
        'forecast_24h': [],
        'timestamp': now,
        'provider': 'awattar'
    }


@pytest.fixture
def sample_expensive_pricing() -> dict:
    """Sample expensive pricing (peak)"""
    now = datetime.now()
    return {
        'current_price': 0.42,
        'currency': 'EUR',
        'peak_period': True,
        'cheapest_hours': [2, 3, 4, 5],
        'most_expensive_hours': [18, 19, 20],
        'forecast_24h': [],
        'timestamp': now,
        'provider': 'awattar'
    }


@pytest.fixture
async def service_instance():
    """Create service instance for testing"""
    from src.main import ElectricityPricingService

    # Set test environment
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
    os.environ['INFLUXDB_ORG'] = 'test-org'
    os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
    os.environ['PRICING_PROVIDER'] = 'awattar'

    service = ElectricityPricingService()

    yield service

    # Cleanup
    try:
        await service.shutdown()
    except:
        pass
