"""Tests for InfluxDBManager lifecycle, writes, queries, and health."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeiq_data.influxdb_manager import InfluxDBManager


@pytest.fixture()
def manager() -> InfluxDBManager:
    """Return a fresh InfluxDBManager instance (not connected)."""
    return InfluxDBManager(
        url="http://influxdb:8086",
        token="test-token",
        org="homeiq",
        bucket="test-bucket",
        timeout=5,
        write_retries=2,
    )


# ------------------------------------------------------------------
# Lifecycle tests
# ------------------------------------------------------------------


class TestConnect:
    """Tests for connect() and close()."""

    @pytest.mark.asyncio()
    async def test_connect_success(self, manager: InfluxDBManager) -> None:
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_query_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.query_api.return_value = mock_query_api

        with (
            patch("homeiq_data.influxdb_manager._get_influxdb") as mock_influx,
            patch.object(manager, "_ping", new_callable=AsyncMock),
        ):
            mock_mod = MagicMock()
            mock_mod.InfluxDBClient.return_value = mock_client
            mock_mod.client.write_api.SYNCHRONOUS = "sync"
            mock_influx.return_value = mock_mod

            result = await manager.connect()

        assert result is True
        assert manager.available is True

    @pytest.mark.asyncio()
    async def test_connect_failure(self, manager: InfluxDBManager) -> None:
        with (
            patch("homeiq_data.influxdb_manager._get_influxdb") as mock_influx,
            patch.object(
                manager,
                "_ping",
                new_callable=AsyncMock,
                side_effect=ConnectionError("refused"),
            ),
        ):
            mock_mod = MagicMock()
            mock_mod.InfluxDBClient.return_value = MagicMock()
            mock_influx.return_value = mock_mod

            result = await manager.connect()

        assert result is False
        assert manager.available is False

    @pytest.mark.asyncio()
    async def test_close(self, manager: InfluxDBManager) -> None:
        manager._client = MagicMock()
        manager._write_api = MagicMock()
        manager._query_api = MagicMock()
        manager._available = True

        await manager.close()

        assert manager.available is False
        assert manager._client is None
        assert manager._write_api is None

    @pytest.mark.asyncio()
    async def test_close_when_not_connected(self, manager: InfluxDBManager) -> None:
        """Closing a never-connected manager should not raise."""
        await manager.close()
        assert manager.available is False


# ------------------------------------------------------------------
# Write tests
# ------------------------------------------------------------------


class TestWritePoints:
    """Tests for write_points()."""

    @pytest.mark.asyncio()
    async def test_write_not_connected(self, manager: InfluxDBManager) -> None:
        result = await manager.write_points([MagicMock()])
        assert result is False

    @pytest.mark.asyncio()
    async def test_write_empty_list(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._write_api = MagicMock()
        result = await manager.write_points([])
        assert result is True

    @pytest.mark.asyncio()
    async def test_write_success(self, manager: InfluxDBManager) -> None:
        manager._available = True
        mock_write_api = MagicMock()
        mock_write_api.write = MagicMock()
        manager._write_api = mock_write_api

        points = [MagicMock(), MagicMock()]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            result = await manager.write_points(points)

        assert result is True
        assert manager._write_count == 2
        assert manager._last_write is not None
        mock_thread.assert_called_once()

    @pytest.mark.asyncio()
    async def test_write_custom_bucket(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._write_api = MagicMock()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            await manager.write_points([MagicMock()], bucket="custom-bucket")

        call_kwargs = mock_thread.call_args
        assert call_kwargs.kwargs["bucket"] == "custom-bucket"

    @pytest.mark.asyncio()
    async def test_write_retry_then_succeed(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._write_api = MagicMock()

        call_count = 0

        async def _side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("transient")

        with patch("asyncio.to_thread", side_effect=_side_effect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await manager.write_points([MagicMock()])

        assert result is True
        assert call_count == 2

    @pytest.mark.asyncio()
    async def test_write_exhausts_retries(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._write_api = MagicMock()

        with patch(
            "asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=ConnectionError("down"),
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            result = await manager.write_points([MagicMock()])

        assert result is False
        assert manager._write_errors == 1


# ------------------------------------------------------------------
# Query tests
# ------------------------------------------------------------------


class TestQuery:
    """Tests for query()."""

    @pytest.mark.asyncio()
    async def test_query_not_connected(self, manager: InfluxDBManager) -> None:
        result = await manager.query("from(bucket: \"b\") |> range(start: -1h)")
        assert result == []

    @pytest.mark.asyncio()
    async def test_query_success(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._query_api = MagicMock()

        mock_record = MagicMock()
        mock_record.values = {"_time": "2025-01-01T00:00:00Z", "_value": 42}
        mock_table = MagicMock()
        mock_table.records = [mock_record]

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=[mock_table]):
            result = await manager.query("from(bucket: \"b\") |> range(start: -1h)")

        assert len(result) == 1
        assert result[0]["_value"] == 42
        assert manager._query_count == 1

    @pytest.mark.asyncio()
    async def test_query_failure(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._query_api = MagicMock()

        with patch(
            "asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=Exception("query error"),
        ):
            result = await manager.query("bad query")

        assert result == []
        assert manager._query_errors == 1


# ------------------------------------------------------------------
# Health & diagnostics tests
# ------------------------------------------------------------------


class TestHealth:
    """Tests for check_health() and get_stats()."""

    @pytest.mark.asyncio()
    async def test_health_unavailable(self, manager: InfluxDBManager) -> None:
        health = await manager.check_health()
        assert health["status"] == "unavailable"
        assert health["backend"] == "influxdb"

    @pytest.mark.asyncio()
    async def test_health_healthy(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._client = MagicMock()

        with patch.object(manager, "_ping", new_callable=AsyncMock):
            health = await manager.check_health()

        assert health["status"] == "healthy"
        assert health["url"] == "http://influxdb:8086"

    @pytest.mark.asyncio()
    async def test_health_unhealthy(self, manager: InfluxDBManager) -> None:
        manager._available = True
        manager._client = MagicMock()

        with patch.object(
            manager,
            "_ping",
            new_callable=AsyncMock,
            side_effect=ConnectionError("gone"),
        ):
            health = await manager.check_health()

        assert health["status"] == "unhealthy"

    def test_get_stats(self, manager: InfluxDBManager) -> None:
        stats = manager.get_stats()
        assert stats["write_count"] == 0
        assert stats["available"] is False

    def test_properties(self, manager: InfluxDBManager) -> None:
        assert manager.url == "http://influxdb:8086"
        assert manager.bucket == "test-bucket"
        assert manager.available is False
