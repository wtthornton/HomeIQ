"""
Unit tests for air quality service configuration and validation
"""

import pytest
import os
from unittest.mock import patch


class TestServiceConfiguration:
    """Test service configuration parsing"""

    def test_missing_weather_api_key(self):
        """
        GIVEN: No WEATHER_API_KEY environment variable
        WHEN: Initialize service
        THEN: Should raise ValueError
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {'WEATHER_API_KEY': '', 'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            with pytest.raises(ValueError, match="WEATHER_API_KEY environment variable is required"):
                service = AirQualityService()

    def test_missing_influxdb_token(self):
        """
        GIVEN: No INFLUXDB_TOKEN environment variable
        WHEN: Initialize service
        THEN: Should raise ValueError
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {'WEATHER_API_KEY': 'test-key', 'INFLUXDB_TOKEN': ''}, clear=True):
            with pytest.raises(ValueError, match="INFLUXDB_TOKEN environment variable is required"):
                service = AirQualityService()

    def test_default_location(self):
        """
        GIVEN: No LATITUDE/LONGITUDE set
        WHEN: Initialize service
        THEN: Should default to Las Vegas (36.1699, -115.1398)
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()
            assert service.latitude == '36.1699'
            assert service.longitude == '-115.1398'

    def test_custom_location(self):
        """
        GIVEN: Custom LATITUDE/LONGITUDE
        WHEN: Initialize service
        THEN: Should use custom location
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token',
            'LATITUDE': '40.7128',
            'LONGITUDE': '-74.0060'
        }, clear=True):
            service = AirQualityService()
            assert service.latitude == '40.7128'
            assert service.longitude == '-74.0060'

    def test_default_influxdb_url(self):
        """
        GIVEN: No INFLUXDB_URL set
        WHEN: Initialize service
        THEN: Should default to http://influxdb:8086
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()
            assert service.influxdb_url == 'http://influxdb:8086'

    def test_default_influxdb_org(self):
        """
        GIVEN: No INFLUXDB_ORG set
        WHEN: Initialize service
        THEN: Should default to 'home_assistant'
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()
            assert service.influxdb_org == 'home_assistant'

    def test_default_influxdb_bucket(self):
        """
        GIVEN: No INFLUXDB_BUCKET set
        WHEN: Initialize service
        THEN: Should default to 'events'
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()
            assert service.influxdb_bucket == 'events'

    def test_fetch_interval_default(self):
        """
        GIVEN: Service instance
        WHEN: Check fetch_interval
        THEN: Should be 3600 seconds (1 hour)
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()
            assert service.fetch_interval == 3600

    def test_cache_duration_default(self):
        """
        GIVEN: Service instance
        WHEN: Check cache_duration
        THEN: Should be 60 minutes
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()
            assert service.cache_duration == 60

    def test_base_url_configured(self):
        """
        GIVEN: Service instance
        WHEN: Check base_url
        THEN: Should be OpenWeather air pollution endpoint
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()
            assert service.base_url == "https://api.openweathermap.org/data/2.5/air_pollution"


class TestCompleteConfiguration:
    """Test complete service configuration"""

    def test_all_custom_configuration(self):
        """
        GIVEN: All environment variables set to custom values
        WHEN: Initialize service
        THEN: Should use all custom values
        """
        from src.main import AirQualityService

        custom_env = {
            'WEATHER_API_KEY': 'custom-api-key-12345',
            'INFLUXDB_TOKEN': 'custom-token-12345',
            'INFLUXDB_URL': 'http://prod-influxdb:8086',
            'INFLUXDB_ORG': 'production-org',
            'INFLUXDB_BUCKET': 'production-events',
            'LATITUDE': '51.5074',
            'LONGITUDE': '-0.1278',
            'HOME_ASSISTANT_URL': 'http://ha:8123',
            'HOME_ASSISTANT_TOKEN': 'ha-token'
        }

        with patch.dict(os.environ, custom_env, clear=True):
            service = AirQualityService()

            assert service.api_key == 'custom-api-key-12345'
            assert service.influxdb_token == 'custom-token-12345'
            assert service.influxdb_url == 'http://prod-influxdb:8086'
            assert service.influxdb_org == 'production-org'
            assert service.influxdb_bucket == 'production-events'
            assert service.latitude == '51.5074'
            assert service.longitude == '-0.1278'
            assert service.ha_url == 'http://ha:8123'
            assert service.ha_token == 'ha-token'

    def test_minimal_configuration(self):
        """
        GIVEN: Only required environment variables set
        WHEN: Initialize service
        THEN: Should use defaults for all other values
        """
        from src.main import AirQualityService

        with patch.dict(os.environ, {
            'WEATHER_API_KEY': 'test-key',
            'INFLUXDB_TOKEN': 'test-token'
        }, clear=True):
            service = AirQualityService()

            assert service.api_key == 'test-key'
            assert service.influxdb_token == 'test-token'
            assert service.influxdb_url == 'http://influxdb:8086'
            assert service.influxdb_org == 'home_assistant'
            assert service.influxdb_bucket == 'events'
            assert service.latitude == '36.1699'
            assert service.longitude == '-115.1398'
