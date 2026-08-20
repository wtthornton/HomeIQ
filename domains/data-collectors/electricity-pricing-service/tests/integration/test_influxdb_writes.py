"""InfluxDB write integration tests.

Payloads mirror what AwattarProvider.fetch_pricing returns plus the
`provider`/`timestamp` keys main.fetch_pricing injects — store_in_influxdb
validates against that shape and skips the write when it does not match.
"""

from datetime import UTC, datetime

import pytest


@pytest.fixture
async def service_with_mock(service_instance, mock_influxdb_client):
    """Service with the InfluxDB client mocked.

    startup() is deliberately not called: it would replace the mock with a
    real InfluxDBClient3 and spawn the collection loop.
    """
    service_instance.influxdb_client = mock_influxdb_client
    return service_instance


def _pricing(forecast_hours: int = 0) -> dict:
    now = datetime.now(UTC)
    return {
        "provider": "awattar",
        "current_price": 0.25,
        "currency": "EUR",
        "peak_period": True,
        "timestamp": now,
        "forecast_24h": [
            {"hour": i, "price": 0.20 + (i * 0.01), "timestamp": now} for i in range(forecast_hours)
        ],
    }


@pytest.mark.asyncio
async def test_batch_write_current_pricing(service_with_mock, mock_influxdb_client):
    await service_with_mock.store_in_influxdb(_pricing())

    assert mock_influxdb_client.write.called


@pytest.mark.asyncio
async def test_batch_write_forecast_data(service_with_mock, mock_influxdb_client):
    await service_with_mock.store_in_influxdb(_pricing(forecast_hours=24))

    points = mock_influxdb_client.write.call_args[0][0]
    assert len(points) == 25  # 1 current + 24 forecast


@pytest.mark.asyncio
async def test_write_error_handling(service_with_mock, mock_influxdb_client):
    mock_influxdb_client.write.side_effect = Exception("InfluxDB connection error")

    # Store must swallow the write failure: if it raises, this test fails.
    await service_with_mock.store_in_influxdb(_pricing())

    assert mock_influxdb_client.write.called


@pytest.mark.asyncio
async def test_write_empty_data(service_with_mock, mock_influxdb_client):
    await service_with_mock.store_in_influxdb({})

    assert not mock_influxdb_client.write.called


@pytest.mark.asyncio
async def test_write_with_missing_fields(service_with_mock, mock_influxdb_client):
    """A payload missing required tags is skipped, not written half-formed."""
    await service_with_mock.store_in_influxdb(
        {"current_price": 0.25, "timestamp": datetime.now(UTC), "forecast_24h": []}
    )

    assert not mock_influxdb_client.write.called
