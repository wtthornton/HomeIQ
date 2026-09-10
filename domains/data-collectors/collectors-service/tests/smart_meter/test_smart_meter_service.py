"""Unit tests for the smart-meter adapter's data fetching, phantom-load
detection, InfluxDB storage, and lifecycle (former smart-meter-service).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDataFetching:
    """Test power consumption data fetching"""

    @pytest.mark.asyncio
    async def test_fetch_with_adapter_success(
        self, service_instance, sample_meter_data, mock_ha_adapter
    ):
        """GIVEN: Adapter configured | WHEN: Fetch | THEN: Return data with timestamp"""
        mock_ha_adapter.fetch_consumption.return_value = sample_meter_data.copy()
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data is not None
        assert data["total_power_w"] == 2450.0
        assert "timestamp" in data

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
            "total_power_w": 1000.0,
            "daily_kwh": 10.0,
            "circuits": [
                {"name": "Circuit1", "power_w": 600.0},
                {"name": "Circuit2", "power_w": 400.0},
            ],
            "timestamp": datetime.now(),
        }
        mock_ha_adapter.fetch_consumption.return_value = data_no_pct
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data["circuits"][0]["percentage"] == 60.0
        assert data["circuits"][1]["percentage"] == 40.0

    @pytest.mark.asyncio
    async def test_fetch_error_returns_cached(
        self, service_instance, sample_meter_data, mock_ha_adapter
    ):
        """GIVEN: Fetch fails but cache exists | WHEN: Fetch | THEN: Return cached data"""
        service_instance.cached_data = sample_meter_data.copy()
        service_instance.last_fetch_time = datetime.now(UTC)
        mock_ha_adapter.fetch_consumption.side_effect = Exception("API error")
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data is not None
        assert data == service_instance.cached_data

    @pytest.mark.asyncio
    async def test_fetch_error_no_cache_returns_mock(self, service_instance, mock_ha_adapter):
        """GIVEN: Fetch fails and no cache | WHEN: Fetch | THEN: Fall back to mock data"""
        mock_ha_adapter.fetch_consumption.side_effect = Exception("API error")
        service_instance.adapter = mock_ha_adapter
        service_instance.session = AsyncMock()

        data = await service_instance.fetch_consumption()

        assert data is not None
        assert data["total_power_w"] == 2450.0

    @pytest.mark.asyncio
    async def test_fetch_no_adapter_returns_mock(self, service_instance):
        """GIVEN: No adapter | WHEN: Fetch | THEN: Return mock data"""
        service_instance.adapter = None

        data = await service_instance.fetch_consumption()

        assert data is not None
        assert data["total_power_w"] == 2450.0
        assert len(data["circuits"]) == 6


class TestPhantomLoadDetection:
    """Test phantom load detection at 3am"""

    @pytest.mark.asyncio
    async def test_high_3am_baseline_detected(self, service_instance, mock_ha_adapter):
        """GIVEN: High power at 3am | WHEN: Fetch | THEN: Set baseline and warn"""
        with patch("src.adapters.smart_meter.datetime") as mock_dt:
            mock_time = datetime(2025, 1, 1, 3, 0, 0)
            mock_dt.now.return_value = mock_time

            data = {
                "total_power_w": 250.0,  # High for 3am
                "daily_kwh": 1.0,
                "circuits": [],
                "timestamp": mock_time,
            }
            mock_ha_adapter.fetch_consumption.return_value = data
            service_instance.adapter = mock_ha_adapter
            service_instance.session = AsyncMock()

            await service_instance.fetch_consumption()

            assert service_instance.baseline_3am == 250.0

    @pytest.mark.asyncio
    async def test_low_3am_baseline_ok(self, service_instance, mock_ha_adapter):
        """GIVEN: Low power at 3am | WHEN: Fetch | THEN: Set baseline without warning"""
        with patch("src.adapters.smart_meter.datetime") as mock_dt:
            mock_time = datetime(2025, 1, 1, 3, 0, 0)
            mock_dt.now.return_value = mock_time

            data = {
                "total_power_w": 100.0,  # Low baseline
                "daily_kwh": 0.5,
                "circuits": [],
                "timestamp": mock_time,
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

        assert data["total_power_w"] > 10000


class TestInfluxDBStorage:
    """Test InfluxDB data storage"""

    @pytest.mark.asyncio
    async def test_store_whole_home_consumption(
        self, service_instance, sample_meter_data, mock_influxdb_client
    ):
        """GIVEN: Meter data | WHEN: Store | THEN: Write whole-home point"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(sample_meter_data)

        assert mock_influxdb_client.write.called

    @pytest.mark.asyncio
    async def test_store_circuit_data(
        self, service_instance, sample_meter_data, mock_influxdb_client
    ):
        """GIVEN: Circuit data | WHEN: Store | THEN: One batched write of all points"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(sample_meter_data)

        assert mock_influxdb_client.write.call_count == 1
        (points,), _ = mock_influxdb_client.write.call_args
        measurements = [p.to_line_protocol().split(",")[0] for p in points]
        assert measurements == ["smart_meter"] + ["smart_meter_circuit"] * len(
            sample_meter_data["circuits"]
        )

    @pytest.mark.asyncio
    async def test_store_skips_empty_data(self, service_instance, mock_influxdb_client):
        """GIVEN: None data | WHEN: Store | THEN: Skip"""
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(None)

        assert not mock_influxdb_client.write.called

    @pytest.mark.asyncio
    async def test_store_retries_then_succeeds(
        self, service_instance, sample_meter_data, mock_influxdb_client
    ):
        """GIVEN: First write fails | WHEN: Store retries | THEN: Second attempt succeeds"""
        service_instance.influxdb_client = mock_influxdb_client
        mock_influxdb_client.write.side_effect = [Exception("transient"), None]

        await service_instance.store_in_influxdb(sample_meter_data)

        assert mock_influxdb_client.write.call_count == 2

    @pytest.mark.asyncio
    async def test_store_handles_error_after_max_retries(
        self, service_instance, sample_meter_data, mock_influxdb_client
    ):
        """GIVEN: InfluxDB write always fails | WHEN: Store | THEN: Give up without raising"""
        service_instance.influxdb_client = mock_influxdb_client
        mock_influxdb_client.write.side_effect = Exception("InfluxDB write failed")

        await service_instance.store_in_influxdb(sample_meter_data, max_retries=2)

        assert mock_influxdb_client.write.call_count == 2


class TestEnrichConsumptionData:
    """Test the enrich-in-place helper directly."""

    def test_adds_timestamp_if_missing(self, service_instance):
        """Should add a UTC timestamp when not present in data."""
        data = {"total_power_w": 1000, "circuits": []}
        service_instance._enrich_consumption_data(data)
        assert "timestamp" in data

    def test_calculates_circuit_percentages(self, service_instance):
        """Should calculate percentage for circuits missing it."""
        data = {
            "total_power_w": 1000,
            "circuits": [{"name": "HVAC", "power_w": 500}],
        }
        service_instance._enrich_consumption_data(data)
        assert data["circuits"][0]["percentage"] == 50.0


class TestMockData:
    """Test mock data generation"""

    def test_mock_data_structure(self, service_instance):
        """GIVEN: No adapter | WHEN: Get mock | THEN: Return valid structure"""
        data = service_instance._get_mock_data()

        assert "total_power_w" in data
        assert "daily_kwh" in data
        assert "circuits" in data
        assert "timestamp" in data
        assert len(data["circuits"]) == 6

    def test_mock_data_updates_stats(self, service_instance):
        """GIVEN: Mock data request | WHEN: Generate | THEN: Update health stats"""
        initial_fetches = service_instance.health_handler.total_fetches

        service_instance._get_mock_data()

        assert service_instance.health_handler.total_fetches == initial_fetches + 1


class TestServiceLifecycle:
    """Test service startup and shutdown"""

    @pytest.mark.asyncio
    async def test_startup_creates_session(self, service_instance):
        """GIVEN: Service | WHEN: Startup | THEN: Create session"""
        await service_instance.startup()
        assert service_instance.session is not None
        await service_instance.shutdown()

    @pytest.mark.asyncio
    async def test_startup_creates_influxdb_client(self, service_instance):
        """GIVEN: Service | WHEN: Startup | THEN: Create InfluxDB client"""
        await service_instance.startup()
        assert service_instance.influxdb_client is not None
        await service_instance.shutdown()

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
