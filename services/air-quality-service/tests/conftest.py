"""
Shared test fixtures for air-quality-service
"""

import pytest
from datetime import datetime
from typing import Dict
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession"""
    session = MagicMock()
    session.close = AsyncMock()
    # Don't pre-define session.get - let tests set it up as async context manager
    return session


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client"""
    client = MagicMock()
    client.write = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture
def sample_openweather_response() -> Dict:
    """Sample OpenWeather API response (good air quality)"""
    return {
        'coord': {'lon': -115.1398, 'lat': 36.1699},
        'list': [
            {
                'dt': int(datetime.now().timestamp()),
                'main': {
                    'aqi': 1  # Good
                },
                'components': {
                    'co': 230.31,
                    'no': 0.0,
                    'no2': 1.15,
                    'o3': 68.66,
                    'so2': 0.38,
                    'pm2_5': 3.41,
                    'pm10': 3.78,
                    'nh3': 0.18
                }
            }
        ]
    }


@pytest.fixture
def sample_poor_aqi_response() -> Dict:
    """Sample OpenWeather response with poor AQI"""
    return {
        'list': [
            {
                'dt': int(datetime.now().timestamp()),
                'main': {
                    'aqi': 4  # Poor
                },
                'components': {
                    'co': 450.0,
                    'no2': 45.0,
                    'o3': 150.0,
                    'so2': 25.0,
                    'pm2_5': 75.0,
                    'pm10': 120.0
                }
            }
        ]
    }


@pytest.fixture
def sample_ha_config_response() -> Dict:
    """Sample Home Assistant config response"""
    return {
        'latitude': 36.1699,
        'longitude': -115.1398,
        'elevation': 610,
        'unit_system': {
            'length': 'km',
            'mass': 'g',
            'temperature': 'C',
            'volume': 'L'
        },
        'location_name': 'Home',
        'time_zone': 'America/Los_Angeles'
    }


@pytest.fixture
def sample_aqi_data() -> Dict:
    """Sample processed AQI data"""
    now = datetime.now()
    return {
        'aqi': 25,  # Converted from OpenWeather scale
        'category': 'Good',
        'parameter': 'Combined',
        'pm25': 3,
        'pm10': 4,
        'ozone': 69,
        'co': 230.31,
        'no2': 1.15,
        'so2': 0.38,
        'timestamp': now
    }


@pytest.fixture
async def service_instance():
    """Create service instance for testing"""
    from src.main import AirQualityService

    # Set test environment
    os.environ['WEATHER_API_KEY'] = 'test-api-key'
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
    os.environ['INFLUXDB_ORG'] = 'test-org'
    os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
    os.environ['LATITUDE'] = '36.1699'
    os.environ['LONGITUDE'] = '-115.1398'

    service = AirQualityService()

    yield service

    # Cleanup
    try:
        await service.shutdown()
    except:
        pass
