"""
Unit tests for air quality service logic
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestLocationFetching:
    """Test location fetching from Home Assistant"""

    @pytest.mark.asyncio
    async def test_fetch_location_from_ha_success(self, service_instance, mock_aiohttp_session, sample_ha_config_response):
        """GIVEN: HA configured | WHEN: Fetch location | THEN: Return lat/lon"""
        service_instance.session = mock_aiohttp_session
        service_instance.ha_url = 'http://homeassistant:8123'
        service_instance.ha_token = 'test-token'

        # Mock the response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_ha_config_response)

        # Properly mock async context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        location = await service_instance.fetch_location_from_ha()

        assert location is not None
        assert location['latitude'] == 36.1699
        assert location['longitude'] == -115.1398

    @pytest.mark.asyncio
    async def test_fetch_location_no_ha_config(self, service_instance):
        """GIVEN: No HA configured | WHEN: Fetch location | THEN: Return None"""
        service_instance.ha_url = None
        service_instance.ha_token = None

        location = await service_instance.fetch_location_from_ha()

        assert location is None

    @pytest.mark.asyncio
    async def test_fetch_location_ha_error(self, service_instance, mock_aiohttp_session):
        """GIVEN: HA returns error | WHEN: Fetch location | THEN: Return None"""
        service_instance.session = mock_aiohttp_session
        service_instance.ha_url = 'http://homeassistant:8123'
        service_instance.ha_token = 'test-token'

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        location = await service_instance.fetch_location_from_ha()

        assert location is None


class TestDataFetching:
    """Test AQI data fetching and parsing"""

    @pytest.mark.asyncio
    async def test_fetch_aqi_success(self, service_instance, mock_aiohttp_session, sample_openweather_response):
        """GIVEN: Valid API response | WHEN: Fetch AQI | THEN: Return parsed data"""
        service_instance.session = mock_aiohttp_session

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_openweather_response)

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        data = await service_instance.fetch_air_quality()

        assert data is not None
        assert data['aqi'] == 25  # Converted from OpenWeather AQI 1
        assert data['category'] == 'Good'
        assert data['parameter'] == 'Combined'
        assert 'pm25' in data
        assert 'pm10' in data
        assert 'ozone' in data

    @pytest.mark.asyncio
    async def test_fetch_aqi_scale_conversion(self, service_instance, mock_aiohttp_session):
        """GIVEN: Different OpenWeather AQI values | WHEN: Convert | THEN: Map to 0-500 scale"""
        service_instance.session = mock_aiohttp_session

        # Test all 5 AQI levels
        test_cases = [
            (1, 25, 'Good'),
            (2, 75, 'Fair'),
            (3, 125, 'Moderate'),
            (4, 175, 'Poor'),
            (5, 250, 'Very Poor')
        ]

        for ow_aqi, expected_aqi, expected_category in test_cases:
            response = {
                'list': [{
                    'dt': int(datetime.now().timestamp()),
                    'main': {'aqi': ow_aqi},
                    'components': {'pm2_5': 10, 'pm10': 15, 'o3': 50, 'co': 200, 'no2': 5, 'so2': 2}
                }]
            }

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=response)

            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_response
            mock_cm.__aexit__.return_value = None
            mock_aiohttp_session.get.return_value = mock_cm

            data = await service_instance.fetch_air_quality()

            assert data['aqi'] == expected_aqi
            assert data['category'] == expected_category

    @pytest.mark.asyncio
    async def test_fetch_aqi_updates_cache(self, service_instance, mock_aiohttp_session, sample_openweather_response):
        """GIVEN: Successful fetch | WHEN: Complete | THEN: Update cache"""
        service_instance.session = mock_aiohttp_session

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_openweather_response)

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        await service_instance.fetch_air_quality()

        assert service_instance.cached_data is not None
        assert service_instance.last_fetch_time is not None

    @pytest.mark.asyncio
    async def test_fetch_aqi_error_returns_cached(self, service_instance, mock_aiohttp_session, sample_aqi_data):
        """GIVEN: API error but cache exists | WHEN: Fetch | THEN: Return cached data"""
        service_instance.session = mock_aiohttp_session
        service_instance.cached_data = sample_aqi_data.copy()

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        data = await service_instance.fetch_air_quality()

        assert data is not None
        assert data == service_instance.cached_data

    @pytest.mark.asyncio
    async def test_fetch_aqi_empty_response(self, service_instance, mock_aiohttp_session, sample_aqi_data):
        """GIVEN: Empty API response | WHEN: Fetch | THEN: Return cached data"""
        service_instance.session = mock_aiohttp_session
        service_instance.cached_data = sample_aqi_data.copy()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'list': []})

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        data = await service_instance.fetch_air_quality()

        assert data == service_instance.cached_data


class TestCategoryTracking:
    """Test AQI category change tracking"""

    @pytest.mark.asyncio
    async def test_category_change_logged(self, service_instance, mock_aiohttp_session):
        """GIVEN: Category changes | WHEN: Fetch | THEN: Log change"""
        service_instance.session = mock_aiohttp_session
        service_instance.last_category = 'Good'

        response = {
            'list': [{
                'dt': int(datetime.now().timestamp()),
                'main': {'aqi': 4},  # Poor
                'components': {'pm2_5': 75, 'pm10': 120, 'o3': 150, 'co': 450, 'no2': 45, 'so2': 25}
            }]
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=response)

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        data = await service_instance.fetch_air_quality()

        assert data['category'] == 'Poor'
        assert service_instance.last_category == 'Poor'


class TestInfluxDBStorage:
    """Test InfluxDB data storage"""

    @pytest.mark.asyncio
    async def test_store_aqi_data(self, service_instance, sample_aqi_data, mock_influxdb_client):
        """GIVEN: AQI data | WHEN: Store | THEN: Write to InfluxDB"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(sample_aqi_data)

        assert mock_influxdb_client.write.called

    @pytest.mark.asyncio
    async def test_store_skips_empty_data(self, service_instance, mock_influxdb_client):
        """GIVEN: None data | WHEN: Store | THEN: Skip"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(None)

        assert not mock_influxdb_client.write.called

    @pytest.mark.asyncio
    async def test_store_handles_error(self, service_instance, sample_aqi_data, mock_influxdb_client):
        """GIVEN: InfluxDB write fails | WHEN: Store | THEN: Handle gracefully"""
        service_instance.influxdb_client = mock_influxdb_client
        mock_influxdb_client.write.side_effect = Exception("InfluxDB write failed")

        # Should not raise exception
        await service_instance.store_in_influxdb(sample_aqi_data)


class TestAPIEndpoints:
    """Test API endpoints"""

    @pytest.mark.asyncio
    async def test_get_current_aqi_with_data(self, service_instance, sample_aqi_data):
        """GIVEN: Cached data exists | WHEN: GET /current-aqi | THEN: Return data"""
        service_instance.cached_data = sample_aqi_data.copy()
        service_instance.last_fetch_time = datetime.now()

        mock_request = MagicMock()
        response = await service_instance.get_current_aqi(mock_request)

        assert response.status == 200
        body = response.body
        assert b'aqi' in body
        assert b'category' in body

    @pytest.mark.asyncio
    async def test_get_current_aqi_no_data(self, service_instance):
        """GIVEN: No cached data | WHEN: GET /current-aqi | THEN: Return 503"""
        service_instance.cached_data = None

        mock_request = MagicMock()
        response = await service_instance.get_current_aqi(mock_request)

        assert response.status == 503


class TestServiceLifecycle:
    """Test service startup and shutdown"""

    @pytest.mark.asyncio
    async def test_startup_creates_session(self, service_instance):
        """GIVEN: Service | WHEN: Startup | THEN: Create session"""
        await service_instance.startup()
        assert service_instance.session is not None

    @pytest.mark.asyncio
    async def test_startup_creates_influxdb_client(self, service_instance):
        """GIVEN: Service | WHEN: Startup | THEN: Create InfluxDB client"""
        await service_instance.startup()
        assert service_instance.influxdb_client is not None

    @pytest.mark.asyncio
    async def test_shutdown_closes_session(self, service_instance):
        """GIVEN: Running service | WHEN: Shutdown | THEN: Close session"""
        await service_instance.startup()
        session_close = AsyncMock()
        service_instance.session.close = session_close

        await service_instance.shutdown()

        assert session_close.called

    @pytest.mark.asyncio
    async def test_shutdown_closes_influxdb_client(self, service_instance):
        """GIVEN: Running service | WHEN: Shutdown | THEN: Close InfluxDB client"""
        await service_instance.startup()
        client_close = MagicMock()
        service_instance.influxdb_client.close = client_close

        await service_instance.shutdown()

        assert client_close.called


class TestHealthTracking:
    """Test health tracking"""

    @pytest.mark.asyncio
    async def test_successful_fetch_updates_health(self, service_instance, mock_aiohttp_session, sample_openweather_response):
        """GIVEN: Successful fetch | WHEN: Complete | THEN: Update health stats"""
        service_instance.session = mock_aiohttp_session
        initial_fetches = service_instance.health_handler.total_fetches

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_openweather_response)

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        await service_instance.fetch_air_quality()

        assert service_instance.health_handler.total_fetches == initial_fetches + 1
        assert service_instance.health_handler.last_successful_fetch is not None

    @pytest.mark.asyncio
    async def test_failed_fetch_updates_health(self, service_instance, mock_aiohttp_session):
        """GIVEN: Failed fetch | WHEN: Error | THEN: Update failed count"""
        service_instance.session = mock_aiohttp_session
        initial_failed = service_instance.health_handler.failed_fetches

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_cm.__aexit__.return_value = None
        mock_aiohttp_session.get.return_value = mock_cm

        await service_instance.fetch_air_quality()

        assert service_instance.health_handler.failed_fetches == initial_failed + 1
