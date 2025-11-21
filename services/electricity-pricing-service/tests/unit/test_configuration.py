"""
Unit tests for service configuration and validation
"""

import os
from unittest.mock import patch

import pytest


class TestServiceConfiguration:
    """Test service configuration parsing"""

    def test_missing_influxdb_token(self):
        """
        GIVEN: No INFLUXDB_TOKEN environment variable
        WHEN: Initialize service
        THEN: Should raise ValueError
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": ""}, clear=True):
            with pytest.raises(ValueError, match="INFLUXDB_TOKEN environment variable is required"):
                ElectricityPricingService()

    def test_default_provider(self):
        """
        GIVEN: No PRICING_PROVIDER set
        WHEN: Initialize service
        THEN: Should default to 'awattar'
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = ElectricityPricingService()
            assert service.provider_name == "awattar"

    def test_custom_provider(self):
        """
        GIVEN: PRICING_PROVIDER=awattar
        WHEN: Initialize service
        THEN: Should use awattar provider
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {
            "INFLUXDB_TOKEN": "test-token",
            "PRICING_PROVIDER": "awattar",
        }, clear=True):
            service = ElectricityPricingService()
            assert service.provider_name == "awattar"

    def test_default_influxdb_url(self):
        """
        GIVEN: No INFLUXDB_URL set
        WHEN: Initialize service
        THEN: Should default to http://influxdb:8086
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = ElectricityPricingService()
            assert service.influxdb_url == "http://influxdb:8086"

    def test_custom_influxdb_url(self):
        """
        GIVEN: INFLUXDB_URL=http://custom:9999
        WHEN: Initialize service
        THEN: Should use custom URL
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {
            "INFLUXDB_TOKEN": "test-token",
            "INFLUXDB_URL": "http://custom:9999",
        }, clear=True):
            service = ElectricityPricingService()
            assert service.influxdb_url == "http://custom:9999"

    def test_default_influxdb_org(self):
        """
        GIVEN: No INFLUXDB_ORG set
        WHEN: Initialize service
        THEN: Should default to 'home_assistant'
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = ElectricityPricingService()
            assert service.influxdb_org == "home_assistant"

    def test_default_influxdb_bucket(self):
        """
        GIVEN: No INFLUXDB_BUCKET set
        WHEN: Initialize service
        THEN: Should default to 'events'
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = ElectricityPricingService()
            assert service.influxdb_bucket == "events"

    def test_fetch_interval_default(self):
        """
        GIVEN: Service instance
        WHEN: Check fetch_interval
        THEN: Should be 3600 seconds (1 hour)
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = ElectricityPricingService()
            assert service.fetch_interval == 3600

    def test_cache_duration_default(self):
        """
        GIVEN: Service instance
        WHEN: Check cache_duration
        THEN: Should be 60 minutes
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = ElectricityPricingService()
            assert service.cache_duration == 60


class TestProviderSelection:
    """Test provider selection logic"""

    def test_awattar_provider_selected(self):
        """
        GIVEN: PRICING_PROVIDER=awattar
        WHEN: Get provider
        THEN: Should return AwattarProvider
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {
            "INFLUXDB_TOKEN": "test-token",
            "PRICING_PROVIDER": "awattar",
        }, clear=True):
            service = ElectricityPricingService()
            assert service.provider.__class__.__name__ == "AwattarProvider"

    def test_unknown_provider_defaults_to_awattar(self):
        """
        GIVEN: PRICING_PROVIDER=unknown
        WHEN: Get provider
        THEN: Should default to AwattarProvider with warning
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {
            "INFLUXDB_TOKEN": "test-token",
            "PRICING_PROVIDER": "unknown_provider",
        }, clear=True):
            service = ElectricityPricingService()
            assert service.provider.__class__.__name__ == "AwattarProvider"

    def test_provider_name_case_insensitive(self):
        """
        GIVEN: PRICING_PROVIDER=AWATTAR (uppercase)
        WHEN: Get provider
        THEN: Should still match awattar provider
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {
            "INFLUXDB_TOKEN": "test-token",
            "PRICING_PROVIDER": "AWATTAR",
        }, clear=True):
            service = ElectricityPricingService()
            assert service.provider.__class__.__name__ == "AwattarProvider"


class TestCompleteConfiguration:
    """Test complete service configuration"""

    def test_all_custom_configuration(self):
        """
        GIVEN: All environment variables set to custom values
        WHEN: Initialize service
        THEN: Should use all custom values
        """
        from src.main import ElectricityPricingService

        custom_env = {
            "INFLUXDB_TOKEN": "custom-token-12345",
            "INFLUXDB_URL": "http://prod-influxdb:8086",
            "INFLUXDB_ORG": "production-org",
            "INFLUXDB_BUCKET": "production-events",
            "PRICING_PROVIDER": "awattar",
            "PRICING_API_KEY": "api-key-12345",
        }

        with patch.dict(os.environ, custom_env, clear=True):
            service = ElectricityPricingService()

            assert service.influxdb_token == "custom-token-12345"
            assert service.influxdb_url == "http://prod-influxdb:8086"
            assert service.influxdb_org == "production-org"
            assert service.influxdb_bucket == "production-events"
            assert service.provider_name == "awattar"
            assert service.api_key == "api-key-12345"

    def test_minimal_configuration(self):
        """
        GIVEN: Only required INFLUXDB_TOKEN set
        WHEN: Initialize service
        THEN: Should use defaults for all other values
        """
        from src.main import ElectricityPricingService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = ElectricityPricingService()

            assert service.influxdb_token == "test-token"
            assert service.influxdb_url == "http://influxdb:8086"
            assert service.influxdb_org == "home_assistant"
            assert service.influxdb_bucket == "events"
            assert service.provider_name == "awattar"
            assert service.api_key == ""
