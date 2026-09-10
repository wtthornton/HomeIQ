"""Unit tests for smart-meter adapter configuration."""

import os
from unittest.mock import patch

import pytest


class TestConfiguration:
    """Test service configuration"""

    def test_missing_influxdb_token(self):
        """GIVEN: No INFLUXDB_TOKEN | WHEN: Initialize | THEN: Raise ValueError"""
        from src.adapters.smart_meter import SmartMeterService

        with (
            patch.dict(os.environ, {"INFLUXDB_TOKEN": ""}, clear=True),
            pytest.raises(ValueError, match="INFLUXDB_TOKEN required"),
        ):
            SmartMeterService()

    def test_influxdb_config(self):
        """GIVEN: INFLUXDB_TOKEN=test-token | WHEN: Initialize | THEN: Stored on the service"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = SmartMeterService()
            assert service.influxdb_token == "test-token"

    def test_default_meter_type(self):
        """GIVEN: No METER_TYPE | WHEN: Initialize | THEN: Default to 'home_assistant'"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = SmartMeterService()
            assert service.meter_type == "home_assistant"

    def test_fetch_interval_default(self):
        """GIVEN: Service | WHEN: Check interval | THEN: Should be 300 seconds"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = SmartMeterService()
            assert service.fetch_interval == 300

    def test_fetch_interval_minimum(self):
        """GIVEN: FETCH_INTERVAL_SECONDS below 10s | WHEN: Initialize | THEN: Clamp to 10s"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(
            os.environ,
            {"INFLUXDB_TOKEN": "test-token", "FETCH_INTERVAL_SECONDS": "5"},
            clear=True,
        ):
            service = SmartMeterService()
            assert service.fetch_interval == 10


class TestAdapterCreation:
    """Test meter-adapter creation logic"""

    def test_create_ha_adapter_with_config(self):
        """GIVEN: HA config provided | WHEN: Create adapter | THEN: Return HomeAssistantAdapter"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(
            os.environ,
            {
                "INFLUXDB_TOKEN": "test-token",
                "HOME_ASSISTANT_URL": "http://test:8123",
                "HOME_ASSISTANT_TOKEN": "token",
            },
            clear=True,
        ):
            service = SmartMeterService()
            adapter = service._create_adapter()

            assert adapter is not None
            assert adapter.__class__.__name__ == "HomeAssistantAdapter"

    def test_create_ha_adapter_without_config(self):
        """GIVEN: No HA config | WHEN: Create adapter | THEN: Return None"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
            service = SmartMeterService()
            adapter = service._create_adapter()
            assert adapter is None

    def test_create_emporia_adapter_not_implemented(self):
        """GIVEN: meter_type=emporia | WHEN: Create | THEN: Return None with warning"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(
            os.environ, {"INFLUXDB_TOKEN": "test-token", "METER_TYPE": "emporia"}, clear=True
        ):
            service = SmartMeterService()
            adapter = service._create_adapter()
            assert adapter is None

    def test_create_unknown_adapter(self):
        """GIVEN: unknown meter_type | WHEN: Create | THEN: Return None"""
        from src.adapters.smart_meter import SmartMeterService

        with patch.dict(
            os.environ, {"INFLUXDB_TOKEN": "test-token", "METER_TYPE": "unknown"}, clear=True
        ):
            service = SmartMeterService()
            adapter = service._create_adapter()
            assert adapter is None
