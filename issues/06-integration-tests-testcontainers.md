# Issue #6: [P1] Add Integration Test Suite with Testcontainers

**Status:** 🟢 Open
**Priority:** 🟡 P1 - High
**Effort:** 8-12 hours
**Dependencies:** None

## Description

Implement integration tests using Testcontainers to test with real InfluxDB, MQTT broker, and other dependencies instead of mocks.

## Modern 2025 Patterns

✅ **Testcontainers** - Real dependencies in Docker
✅ **Test isolation** - Each test gets fresh containers
✅ **End-to-end flows** - Complete data pipeline testing

## Acceptance Criteria

- [ ] InfluxDB container integration
- [ ] MQTT broker container integration
- [ ] End-to-end data flow tests
- [ ] Cross-service integration tests
- [ ] Performance tests with real infrastructure

## Code Template

```python
# tests/integration/test_data_pipeline_with_containers.py
import pytest
from testcontainers.influxdb import InfluxDbContainer
from testcontainers.core.container import DockerContainer

@pytest.fixture(scope="session")
def influxdb_container():
    """Real InfluxDB for integration tests"""
    with InfluxDbContainer("influxdb:2.7") as influx:
        yield influx

@pytest.fixture(scope="session")
def mqtt_container():
    """Real MQTT broker for integration tests"""
    with DockerContainer("eclipse-mosquitto:2.0") \
        .with_exposed_ports(1883) as mqtt:
        yield mqtt

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_data_flow(influxdb_container, mqtt_container):
    """Test complete data flow: MQTT → Ingestion → InfluxDB"""
    influx_url = influxdb_container.get_connection_url()
    mqtt_url = f"mqtt://localhost:{mqtt_container.get_exposed_port(1883)}"

    # Publish MQTT message
    await publish_test_event(mqtt_url, "sensor.temperature", 22.5)

    # Wait for ingestion
    await asyncio.sleep(2)

    # Query InfluxDB
    client = InfluxDBClient(url=influx_url)
    result = client.query('SELECT * FROM "state_changed" WHERE entity_id="sensor.temperature"')

    assert len(result) > 0
    assert result[0]["value"] == 22.5
```
