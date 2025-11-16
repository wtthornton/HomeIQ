"""
Unit tests for smart meter service
Tests configuration, data fetching, phantom load detection, and InfluxDB storage
"""

import pytest
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestConfiguration:
    """Test service configuration"""

    def test_missing_influxdb_token(self):
        """GIVEN: No INFLUXDB_TOKEN | WHEN: Initialize | THEN: Raise ValueError"""
        from src.main import SmartMeterService
        with patch.dict(os.environ, {'INFLUXDB_TOKEN': ''}, clear=True):
            with pytest.raises(ValueError, match="INFLUXDB_TOKEN required"):
                SmartMeterService()

    def test_default_meter_type(self):
        """GIVEN: No METER_TYPE | WHEN: Initialize | THEN: Default to 'home_assistant'"""
        from src.main import SmartMeterService
        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = SmartMeterService()
            assert service.meter_type == 'home_assistant'

    def test_fetch_interval_default(self):
        """GIVEN: Service | WHEN: Check interval | THEN: Should be 300 seconds"""
        from src.main import SmartMeterService
        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = SmartMeterService()
            assert service.fetch_interval == 300


class TestDataFetching:
    """Test power consumption data fetching"""

    @pytest.mark.asyncio
    async def test_fetch_with_adapter_success(self, service_instance, sample_meter_data, mock_ha_adapter):
        """GIVEN: Adapter configured | WHEN: Fetch | THEN: Return data with timestamp"""
        mock_ha_adapter.fetch_consumption.return_value = sample_meter_data.copy()
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data is not None
        assert data['total_power_w'] == 2450.0
        assert 'timestamp' in data

    @pytest.mark.asyncio
    async def test_fetch_updates_cache(self, service_instance, sample_meter_data, mock_ha_adapter):
        """GIVEN: Fetch succeeds | WHEN: Complete | THEN: Update cache"""
        mock_ha_adapter.fetch_consumption.return_value = sample_meter_data.copy()
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        await service_instance.fetch_consumption()

        assert service_instance.cached_data is not None
        assert service_instance.last_fetch_time is not None

    @pytest.mark.asyncio
    async def test_fetch_calculates_percentages(self, service_instance, mock_ha_adapter):
        """GIVEN: Data without percentages | WHEN: Fetch | THEN: Calculate percentages"""
        data_no_pct = {
            'total_power_w': 1000.0,
            'daily_kwh': 10.0,
            'circuits': [
                {'name': 'Circuit1', 'power_w': 600.0},
                {'name': 'Circuit2', 'power_w': 400.0},
            ],
            'timestamp': datetime.now()
        }
        mock_ha_adapter.fetch_consumption.return_value = data_no_pct
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data['circuits'][0]['percentage'] == 60.0
        assert data['circuits'][1]['percentage'] == 40.0

    @pytest.mark.asyncio
    async def test_fetch_error_returns_cached(self, service_instance, sample_meter_data, mock_ha_adapter):
        """GIVEN: Fetch fails but cache exists | WHEN: Fetch | THEN: Return cached data"""
        service_instance.cached_data = sample_meter_data.copy()
        mock_ha_adapter.fetch_consumption.side_effect = Exception("API error")
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data is not None
        assert data == service_instance.cached_data

    @pytest.mark.asyncio
    async def test_fetch_no_adapter_returns_mock(self, service_instance):
        """GIVEN: No adapter | WHEN: Fetch | THEN: Return mock data"""
        service_instance.adapter = None

        data = await service_instance.fetch_consumption()

        assert data is not None
        assert data['total_power_w'] == 2450.0
        assert len(data['circuits']) == 6


class TestPhantomLoadDetection:
    """Test phantom load detection at 3am"""

    @pytest.mark.asyncio
    async def test_high_3am_baseline_detected(self, service_instance, mock_ha_adapter):
        """GIVEN: High power at 3am | WHEN: Fetch | THEN: Set baseline and warn"""
        with patch('src.main.datetime') as mock_dt:
            mock_time = datetime(2025, 1, 1, 3, 0, 0)
            mock_dt.now.return_value = mock_time

            data = {
                'total_power_w': 250.0,  # High for 3am
                'daily_kwh': 1.0,
                'circuits': [],
                'timestamp': mock_time
            }
            mock_ha_adapter.fetch_consumption.return_value = data
            service_instance.adapter = mock_ha_adapter
            service_instance.session = AsyncMock()

            await service_instance.fetch_consumption()

            assert service_instance.baseline_3am == 250.0

    @pytest.mark.asyncio
    async def test_low_3am_baseline_ok(self, service_instance, mock_ha_adapter):
        """GIVEN: Low power at 3am | WHEN: Fetch | THEN: Set baseline without warning"""
        with patch('src.main.datetime') as mock_dt:
            mock_time = datetime(2025, 1, 1, 3, 0, 0)
            mock_dt.now.return_value = mock_time

            data = {
                'total_power_w': 100.0,  # Low baseline
                'daily_kwh': 0.5,
                'circuits': [],
                'timestamp': mock_time
            }
            mock_ha_adapter.fetch_consumption.return_value = data
            service_instance.adapter = mock_ha_adapter
            service_instance.session = AsyncMock()

            await service_instance.fetch_consumption()

            assert service_instance.baseline_3am == 100.0


class TestHighPowerAlert:
    """Test high power consumption alerting"""

    @pytest.mark.asyncio
    async def test_high_power_logged(self, service_instance, sample_high_power, mock_ha_adapter):
        """GIVEN: Power >10kW | WHEN: Fetch | THEN: Log warning"""
        mock_ha_adapter.fetch_consumption.return_value = sample_high_power.copy()
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data['total_power_w'] > 10000


class TestInfluxDBStorage:
    """Test InfluxDB data storage"""

    @pytest.mark.asyncio
    async def test_store_whole_home_consumption(self, service_instance, sample_meter_data, mock_influxdb_client):
        """GIVEN: Meter data | WHEN: Store | THEN: Write whole-home point"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(sample_meter_data)

        assert mock_influxdb_client.write.called

    @pytest.mark.asyncio
    async def test_store_circuit_data(self, service_instance, sample_meter_data, mock_influxdb_client):
        """GIVEN: Circuit data | WHEN: Store | THEN: Write circuit points"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(sample_meter_data)

        # Called for whole-home + 3 circuits = 4 times
        assert mock_influxdb_client.write.call_count >= 4

    @pytest.mark.asyncio
    async def test_store_skips_empty_data(self, service_instance, mock_influxdb_client):
        """GIVEN: None data | WHEN: Store | THEN: Skip"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(None)

        assert not mock_influxdb_client.write.called

    @pytest.mark.asyncio
    async def test_store_handles_error(self, service_instance, sample_meter_data, mock_influxdb_client):
        """GIVEN: InfluxDB write fails | WHEN: Store | THEN: Handle gracefully"""
        service_instance.influxdb_client = mock_influxdb_client
        mock_influxdb_client.write.side_effect = Exception("InfluxDB write failed")

        await service_instance.store_in_influxdb(sample_meter_data)


class TestMockData:
    """Test mock data generation"""

    def test_mock_data_structure(self, service_instance):
        """GIVEN: No adapter | WHEN: Get mock | THEN: Return valid structure"""
        data = service_instance._get_mock_data()

        assert 'total_power_w' in data
        assert 'daily_kwh' in data
        assert 'circuits' in data
        assert 'timestamp' in data
        assert len(data['circuits']) == 6

    def test_mock_data_updates_stats(self, service_instance):
        """GIVEN: Mock data request | WHEN: Generate | THEN: Update health stats"""
        initial_fetches = service_instance.health_handler.total_fetches

        service_instance._get_mock_data()

        assert service_instance.health_handler.total_fetches == initial_fetches + 1


class TestAdapterCreation:
    """Test adapter creation logic"""

    def test_create_ha_adapter_with_config(self, service_instance):
        """GIVEN: HA config provided | WHEN: Create adapter | THEN: Return HomeAssistantAdapter"""
        service_instance.ha_url = 'http://test:8123'
        service_instance.ha_token = 'token'

        adapter = service_instance._create_adapter()

        assert adapter is not None
        assert adapter.__class__.__name__ == 'HomeAssistantAdapter'

    def test_create_ha_adapter_without_config(self):
        """GIVEN: No HA config | WHEN: Create adapter | THEN: Return None"""
        from src.main import SmartMeterService
        with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'test-token'}, clear=True):
            service = SmartMeterService()
            adapter = service._create_adapter()
            assert adapter is None

    def test_create_emporia_adapter_not_implemented(self):
        """GIVEN: meter_type=emporia | WHEN: Create | THEN: Return None with warning"""
        from src.main import SmartMeterService
        with patch.dict(os.environ, {
            'INFLUXDB_TOKEN': 'test-token',
            'METER_TYPE': 'emporia'
        }, clear=True):
            service = SmartMeterService()
            adapter = service._create_adapter()
            assert adapter is None

    def test_create_unknown_adapter(self):
        """GIVEN: unknown meter_type | WHEN: Create | THEN: Return None"""
        from src.main import SmartMeterService
        with patch.dict(os.environ, {
            'INFLUXDB_TOKEN': 'test-token',
            'METER_TYPE': 'unknown'
        }, clear=True):
            service = SmartMeterService()
            adapter = service._create_adapter()
            assert adapter is None


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
