from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from src.influxdb_batch_writer import InfluxDBBatchWriter


def _stub_schema():
    """Stand-in schema that yields plain dicts instead of InfluxDB Points."""
    schema = SimpleNamespace()
    schema.create_event_point = lambda event: {"id": event["id"]}
    schema.create_weather_point = lambda weather, location: {"loc": location, **weather}
    schema.validate_point = lambda point: (True, [])
    return schema


@pytest.fixture
def writer():
    manager = AsyncMock()
    manager.write_points = AsyncMock(return_value=True)

    batch_writer = InfluxDBBatchWriter(
        connection_manager=manager,
        batch_size=100,
        batch_timeout=0.1,
        max_pending_points=3,
        overflow_strategy="drop_oldest",
    )
    batch_writer.schema = _stub_schema()

    return batch_writer, manager


@pytest.mark.asyncio
async def test_backpressure_drops_oldest(writer):
    batch_writer, _ = writer

    for idx in range(4):
        assert await batch_writer.write_event({"id": idx})

    assert len(batch_writer.current_batch) == 3
    assert batch_writer.dropped_points == 1
    assert batch_writer.queue_overflow_events == 1


@pytest.mark.asyncio
async def test_drop_new_strategy_rejects_point():
    manager = AsyncMock()
    manager.write_points = AsyncMock(return_value=True)

    batch_writer = InfluxDBBatchWriter(
        connection_manager=manager,
        batch_size=100,
        max_pending_points=1,
        overflow_strategy="drop_new",
    )
    batch_writer.schema = _stub_schema()

    assert await batch_writer.write_event({"id": 1})
    result = await batch_writer.write_event({"id": 2})

    assert result is False
    assert batch_writer.dropped_points == 1
    assert batch_writer.queue_overflow_events == 1
