"""An open circuit is "upstream unavailable", never "not found" (TAP-6184).

`get_device_by_id` used to swallow `CircuitOpenError` into `None`, which the
devices endpoint turned into a 404 without trying its InfluxDB fallback — and
because `ml_engine_breaker` is a module singleton, one trip 404'd every device
for the rest of the process. These tests pin the re-raise on both methods.
"""

from unittest.mock import AsyncMock

import pytest
from homeiq_resilience import CircuitOpenError
from src.device_intelligence_client import DeviceIntelligenceClient


@pytest.fixture
def client() -> DeviceIntelligenceClient:
    instance = DeviceIntelligenceClient()
    instance._cross_client = AsyncMock()
    instance._cross_client.call.side_effect = CircuitOpenError("ml-engine breaker open")
    return instance


@pytest.mark.asyncio
async def test_open_circuit_propagates_from_get_device_by_id(client):
    with pytest.raises(CircuitOpenError):
        await client.get_device_by_id("dev1")


@pytest.mark.asyncio
async def test_open_circuit_propagates_from_get_device_capabilities(client):
    with pytest.raises(CircuitOpenError):
        await client.get_device_capabilities("dev1")
