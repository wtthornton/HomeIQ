"""
Unit tests for service configuration and validation
Tests environment variable handling and default values
"""

import pytest
import os
from unittest.mock import patch


class TestServiceConfiguration:
    """Test main service configuration"""

    def test_missing_influxdb_token(self):
        """
        GIVEN: No INFLUXDB_TOKEN environment variable
        WHEN: Initialize service
        THEN: Should raise ValueError
        """
        from src.main import EnergyCorrelatorService

        # Clear the token
        with patch.dict(os.environ, {'INFLUXDB_TOKEN': ''}, clear=True):
            with pytest.raises(ValueError, match="INFLUXDB_TOKEN environment variable is required"):
                service = EnergyCorrelatorService()

    def test_default_processing_interval(self):
        """
        GIVEN: No PROCESSING_INTERVAL set
        WHEN: Initialize service
        THEN: Should default to 60 seconds
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = EnergyCorrelatorService()
            assert service.processing_interval == 60

    def test_custom_processing_interval(self):
        """
        GIVEN: PROCESSING_INTERVAL=300
        WHEN: Initialize service
        THEN: Should use 300 seconds
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {
            'INFLUXDB_TOKEN': 'test-token',
            'PROCESSING_INTERVAL': '300'
        }, clear=True):
            service = EnergyCorrelatorService()
            assert service.processing_interval == 300

    def test_default_lookback_minutes(self):
        """
        GIVEN: No LOOKBACK_MINUTES set
        WHEN: Initialize service
        THEN: Should default to 5 minutes
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = EnergyCorrelatorService()
            assert service.lookback_minutes == 5

    def test_custom_lookback_minutes(self):
        """
        GIVEN: LOOKBACK_MINUTES=10
        WHEN: Initialize service
        THEN: Should use 10 minutes
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {
            'INFLUXDB_TOKEN': 'test-token',
            'LOOKBACK_MINUTES': '10'
        }, clear=True):
            service = EnergyCorrelatorService()
            assert service.lookback_minutes == 10

    def test_default_influxdb_url(self):
        """
        GIVEN: No INFLUXDB_URL set
        WHEN: Initialize service
        THEN: Should default to http://influxdb:8086
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = EnergyCorrelatorService()
            assert service.influxdb_url == 'http://influxdb:8086'

    def test_custom_influxdb_url(self):
        """
        GIVEN: INFLUXDB_URL=http://custom-influxdb:9999
        WHEN: Initialize service
        THEN: Should use custom URL
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {
            'INFLUXDB_TOKEN': 'test-token',
            'INFLUXDB_URL': 'http://custom-influxdb:9999'
        }, clear=True):
            service = EnergyCorrelatorService()
            assert service.influxdb_url == 'http://custom-influxdb:9999'

    def test_default_influxdb_org(self):
        """
        GIVEN: No INFLUXDB_ORG set
        WHEN: Initialize service
        THEN: Should default to 'home_assistant'
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = EnergyCorrelatorService()
            assert service.influxdb_org == 'home_assistant'

    def test_default_influxdb_bucket(self):
        """
        GIVEN: No INFLUXDB_BUCKET set
        WHEN: Initialize service
        THEN: Should default to 'home_assistant_events'
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = EnergyCorrelatorService()
            assert service.influxdb_bucket == 'home_assistant_events'


class TestCorrelatorConfiguration:
    """Test correlator-specific configuration"""

    def test_correlation_window_configuration(self, correlator_instance):
        """
        GIVEN: Default correlator instance
        WHEN: Check correlation_window_seconds
        THEN: Should be 10 seconds
        """
        assert correlator_instance.correlation_window_seconds == 10

    def test_min_power_delta_configuration(self, correlator_instance):
        """
        GIVEN: Default correlator instance
        WHEN: Check min_power_delta
        THEN: Should be 10.0W
        """
        assert correlator_instance.min_power_delta == 10.0

    def test_correlator_influxdb_config(self, correlator_instance):
        """
        GIVEN: Correlator instance
        WHEN: Check InfluxDB configuration
        THEN: Should match provided values
        """
        assert correlator_instance.influxdb_url == 'http://test-influxdb:8086'
        assert correlator_instance.influxdb_token == 'test-token'
        assert correlator_instance.influxdb_org == 'test-org'
        assert correlator_instance.influxdb_bucket == 'test-bucket'


class TestConfigurationInStatistics:
    """Test configuration values exposed in statistics"""

    def test_config_in_statistics(self, correlator_instance):
        """
        GIVEN: Correlator instance
        WHEN: Get statistics
        THEN: Should include config section
        """
        stats = correlator_instance.get_statistics()
        assert 'config' in stats

    def test_correlation_window_in_statistics(self, correlator_instance):
        """
        GIVEN: Correlator instance
        WHEN: Get statistics config
        THEN: Should show correlation_window_seconds
        """
        stats = correlator_instance.get_statistics()
        assert stats['config']['correlation_window_seconds'] == 10

    def test_min_power_delta_in_statistics(self, correlator_instance):
        """
        GIVEN: Correlator instance
        WHEN: Get statistics config
        THEN: Should show min_power_delta_w
        """
        stats = correlator_instance.get_statistics()
        assert stats['config']['min_power_delta_w'] == 10.0


class TestEnvironmentVariableParsing:
    """Test environment variable type parsing"""

    def test_processing_interval_string_to_int(self):
        """
        GIVEN: PROCESSING_INTERVAL as string '120'
        WHEN: Parse configuration
        THEN: Should convert to int 120
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {
            'INFLUXDB_TOKEN': 'test-token',
            'PROCESSING_INTERVAL': '120'
        }, clear=True):
            service = EnergyCorrelatorService()
            assert service.processing_interval == 120
            assert isinstance(service.processing_interval, int)

    def test_lookback_minutes_string_to_int(self):
        """
        GIVEN: LOOKBACK_MINUTES as string '15'
        WHEN: Parse configuration
        THEN: Should convert to int 15
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {
            'INFLUXDB_TOKEN': 'test-token',
            'LOOKBACK_MINUTES': '15'
        }, clear=True):
            service = EnergyCorrelatorService()
            assert service.lookback_minutes == 15
            assert isinstance(service.lookback_minutes, int)


class TestCompleteConfiguration:
    """Test complete service configuration with all custom values"""

    def test_all_custom_configuration(self):
        """
        GIVEN: All environment variables set to custom values
        WHEN: Initialize service
        THEN: Should use all custom values
        """
        from src.main import EnergyCorrelatorService

        custom_env = {
            'INFLUXDB_TOKEN': 'custom-token-12345',
            'INFLUXDB_URL': 'http://prod-influxdb:8086',
            'INFLUXDB_ORG': 'production-org',
            'INFLUXDB_BUCKET': 'production-events',
            'PROCESSING_INTERVAL': '180',
            'LOOKBACK_MINUTES': '10',
        }

        with patch.dict(os.environ, custom_env, clear=True):
            service = EnergyCorrelatorService()

            assert service.influxdb_token == 'custom-token-12345'
            assert service.influxdb_url == 'http://prod-influxdb:8086'
            assert service.influxdb_org == 'production-org'
            assert service.influxdb_bucket == 'production-events'
            assert service.processing_interval == 180
            assert service.lookback_minutes == 10

    def test_minimal_configuration(self):
        """
        GIVEN: Only required INFLUXDB_TOKEN set
        WHEN: Initialize service
        THEN: Should use defaults for all other values
        """
        from src.main import EnergyCorrelatorService

        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = EnergyCorrelatorService()

            # Only token is custom, rest are defaults
            assert service.influxdb_token == 'test-token'
            assert service.influxdb_url == 'http://influxdb:8086'
            assert service.influxdb_org == 'home_assistant'
            assert service.influxdb_bucket == 'home_assistant_events'
            assert service.processing_interval == 60
            assert service.lookback_minutes == 5
